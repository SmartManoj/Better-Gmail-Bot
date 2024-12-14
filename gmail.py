# os.chdir('/run/media/smart/M/Smart-P2P')
import base64
import os.path
import re
from time import sleep
import traceback
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from pymsgbox import alert
from telegram import Bot
from dotenv import load_dotenv
from config import subject_to_delete, subject_to_delete_regex, body_to_delete, body_to_delete_regex, ignore_mails_from
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def send_telegram_message(from_address, subject, body):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'📧 {from_address}\n{subject}\n\n{body}')

# asyncio.run(send_telegram_message('test', 'test', 'test'))
# send_message('test', 'test', 'test');exit()
q = "is:unread "


creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
SCOPES = ["https://mail.google.com/"]

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("cs.json", SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())
service = build("gmail", "v1", credentials=creds)


def parse_header(header, name):
    for i in header:
        if i["name"] == name:
            return i["value"]


# last_processed_mail_id = '184423289dcbea8d'
def parse_msg(msg):
    if msg.get("payload").get("body").get("data"):
        return base64.urlsafe_b64decode(
            msg.get("payload").get("body").get("data").encode("ASCII")
        ).decode("utf-8")
    return msg.get("snippet")


q='is:unread newer_than:1d'
def get_mail():
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=q,
        )
        .execute()
    )
    messages = results.get("messages", [])
    for message in messages[::-1]:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        # check from is noreply@github.com
        subject = parse_header(msg["payload"]["headers"], "Subject")
        from_address = parse_header(msg["payload"]["headers"], "From")
        if any(from_address== i[0] and i[1] in subject for i in ignore_mails_from):
            continue
        body = parse_msg(msg)
        from bs4 import BeautifulSoup
        body = BeautifulSoup(body, 'html.parser').get_text()
        if any(s in subject for s in subject_to_delete) or any(re.match(r, subject) for r in subject_to_delete_regex) or any(s in body for s in body_to_delete) or any(re.match(r, body) for r in body_to_delete_regex):
            # delete the mail
            service.users().messages().delete(userId="me", id=message["id"]).execute()
        else:
            print(f'{from_address = }\n{subject = }\n{body = }')
            print('==')
            # remove extra newlines
            body = re.sub(r'\n+', '\n', body)
            body = body[:100]
            asyncio.run(send_telegram_message(from_address, subject, body))
            # print(a)
            service.users().messages().modify(
            userId="me", id=message["id"], body={"removeLabelIds": ["UNREAD"]}
        ).execute()

while True:
    try:
        get_mail()
        print('Sleeping for 60 seconds')
        sleep(60)
    except Exception as e:
        print(e)
        traceback.print_exc()
        alert('Error', str(e))