"""Create an empty custom.py skeleton (git-ignored user customizations).

Run once after cloning:  python setup.py
Leaves an existing custom.py untouched.
"""
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE = '''"""User customizations (git-ignored).

Each entry in ``handlers`` maps a mail (matched by sender + subject substring)
to an ``action`` callable. ``process`` is called by gmail.py for every mail;
it runs the first matching action and returns its name, or None.

An action has the signature:
    action(from_address, subject, body, msg, service) -> bool
and returns True when it handled the mail.
"""
import re

import requests


# Example action -- extract a link from the body and open it.
def example_action(from_address, subject, body, msg, service):
    return False


handlers = {
    # 'name': {
    #     'from': 'sender@example.com',
    #     'subject': 'some subject substring',
    #     'action': example_action,
    # },
}


def process(from_address, subject, body, msg, service):
    for name, rule in handlers.items():
        if rule['from'] in from_address and rule['subject'] in subject:
            try:
                if rule['action'](from_address, subject, body, msg, service):
                    return name
            except Exception as e:
                print(f'custom handler {name!r} error:', e)
    return None
'''


def main():
    if os.path.exists('custom.py'):
        print('custom.py already exists; leaving it untouched.')
        return
    with open('custom.py', 'w') as f:
        f.write(TEMPLATE)
    print('Created empty custom.py skeleton.')


if __name__ == '__main__':
    main()
