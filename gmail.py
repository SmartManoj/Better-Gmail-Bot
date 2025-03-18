from markdownify import markdownify as md
# os.chdir('/run/media/smart/M/Smart-P2P')
import base64
import os.path
from pprint import pprint
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
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from config import subject_to_delete, subject_to_delete_regex, body_to_delete, body_to_delete_regex, subject_to_forward, mails_to_delete, mails_to_delete_with_subject, mails_to_ignore, subject_to_ignore, mails_to_ignore_with_subject, domains_to_ignore
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

async def send_telegram_message(from_address, subject, body, chat_id=TELEGRAM_CHAT_ID):
    bot = Bot(token=TELEGRAM_TOKEN)
    # encode <> to html entities
    text = f'📧 {from_address}\n{subject}\n\n{body}'
    text = re.sub(r'[_*[\]()~>#\+\-=|{}.!]', lambda x: '\\' + x.group(), text)
    text = text[:4096]
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='markdownv2')
    except Exception as e:
        print(e)
        await bot.send_message(chat_id=chat_id, text=text)

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
    elif msg.get("payload").get("parts") and 1:
        out_msg = []
        for part in msg.get("payload").get("parts"):
            if part.get("body").get("data"):
                out_msg.append(base64.urlsafe_b64decode(
                    part.get("body").get("data").encode("ASCII")
                ).decode("utf-8"))
        return '\n'.join(out_msg).split('Message ID:')[0]
    else:
        return msg.get("snippet")

if 0:
    mid = '1940abe95af7f332'
    msg = service.users().messages().get(userId="me", id=mid).execute()
    body = parse_msg(msg)
    print(body)
    # exit()
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
        print(message['id'])
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        # check from is noreply@github.com
        subject = parse_header(msg["payload"]["headers"], "Subject")
        from_address = parse_header(msg["payload"]["headers"], "From")
        body = parse_msg(msg)
        from bs4 import BeautifulSoup
        forward_mail = any(s in subject for s in subject_to_forward)
        # body = BeautifulSoup(body, 'html.parser').get_text()
        body = md(body)
        with open('body.txt', 'w') as f:
            f.write(body)
        forward_mail = False
        if forward_mail:
            print('forwarding', subject)
            asyncio.run(send_telegram_message('', subject, '', chat_id=TELEGRAM_GROUP_CHAT_ID))
        to_delete_with_subject = any(from_address== i[0] and i[1] in subject for i in mails_to_delete_with_subject)
        to_delete = any(from_address in i for i in mails_to_delete)
        subject_to_delete_condition = any(s in subject for s in subject_to_delete)
        print(subject_to_delete_condition, '@')
        if subject_to_delete_condition or any(re.match(r, subject) for r in subject_to_delete_regex) or any(s in body for s in body_to_delete) or any(re.match(r, body) for r in body_to_delete_regex) or to_delete_with_subject or to_delete:
            # delete the mail
            service.users().messages().delete(userId="me", id=message["id"]).execute()
        else:
            print(f'{from_address = }\n{subject = }\n{body = }')
            print('==')
            # remove extra newlines
            body = re.sub(r'\n+', '\n', body)
            print(body)
            if 'notifications@github.com' in from_address:
                # text = 'view it on GitHub'
                regex = r'''
Reply to this email directly or view it on GitHub:
(https://.*)
You are receiving this because you were mentioned.
'''
                link = re.search(regex, body)
                if link:
                    body =  body[:500] + '\n Link:' + link.group(1)
            else:
                body = body[:500]
            with open('ignore.txt', 'r') as f:
                ignore_text = f.read()
            if not forward_mail and not ignore_text in body and not any(i in from_address for i in mails_to_ignore) and not any(i in subject for i in subject_to_ignore) and not any(i in from_address for i in domains_to_ignore):
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