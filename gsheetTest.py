import pygsheets
import pandas as pd


def wks_to_dict(wks):
    df = wks.get_as_df()
    return df.set_index('Name')['Amount'].to_dict()


def dict_to_df(record):
    return pd.DataFrame(list(record.items()), columns=['Name', 'Amount'])


gc = pygsheets.authorize(service_file='discord-payment-bot-857e11962dac.json')

sheet = gc.open_by_url(
    'https://docs.google.com/spreadsheets/d/1HFQthZ49IP9POiGJXXRmiS7F3Z_0_lUtVCkV3Sy7SaI/edit?usp=sharing')
record_wks = sheet.worksheet_by_title('Records')

# read from the sheet
# record_dict = wks_to_dict(record_wks)

# write to the sheet
# df = dict_to_df({'Test1': 100, 'Test2': -50, 'Test3': -100, 'Test4': 50, 'Test5': 0})
# record_wks.set_dataframe(df, 'A1')


"""
https://www.maxlist.xyz/2018/09/25/python_googlesheet_crud/#%E3%84%A7_Python_%E9%80%A3%E7%B5%90_Google_Sheet_API

Generate the gc file from .env if it doesn't exist
"""

