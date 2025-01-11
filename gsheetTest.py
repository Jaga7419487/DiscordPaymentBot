import json
import os

import pandas as pd
import pygsheets
from dotenv import load_dotenv

"""
Generate the gc file from .env if it doesn't exist
"""
if not os.path.exists('discord-payment-bot.json'):
    gc_list = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri",
               "token_uri",
               "auth_provider_x509_cert_url", "client_x509_cert_url", "universe_domain"]
    load_dotenv()
    gc_dict = {key: os.getenv(key.upper()) for key in gc_list}
    gc_dict['private_key'] = gc_dict['private_key'].replace('\\n', '\n')
    print(gc_dict)
    with open('discord-payment-bot.json', 'w') as json_file:
        json.dump(gc_dict, json_file, indent=2)

"""
https://www.maxlist.xyz/2018/09/25/python_googlesheet_crud/#%E3%84%A7_Python_%E9%80%A3%E7%B5%90_Google_Sheet_API
"""


def wks_to_dict(wks):
    return wks.get_as_df().set_index('Name')['Amount'].to_dict()


def dict_to_df(record):
    return pd.DataFrame(list(record.items()), columns=['Name', 'Amount'])


gc = pygsheets.authorize(service_file='discord-payment-bot.json')

sheet = gc.open_by_url(
    'https://docs.google.com/spreadsheets/d/1HFQthZ49IP9POiGJXXRmiS7F3Z_0_lUtVCkV3Sy7SaI/edit?usp=sharing')
record_wks = sheet.worksheet_by_title('Records')

# read from the sheet
record_dict = wks_to_dict(record_wks)
print(record_dict)

# write to the sheet
df = dict_to_df({'Test1': 100, 'Test2': -50, 'Test3': -100, 'Test4': 50, 'Test5': 0})
record_wks.set_dataframe(df, 'A1')
