import pygsheets
import pandas as pd

gc = pygsheets.authorize(service_file='discord-payment-bot-857e11962dac.json')

sheet = gc.open_by_url(
    'https://docs.google.com/spreadsheets/d/1HFQthZ49IP9POiGJXXRmiS7F3Z_0_lUtVCkV3Sy7SaI/edit?usp=sharing')

wks = sheet.worksheet_by_title('Records')
df = wks.get_as_df()
record_dict = df.set_index('Name')['Amount'].to_dict()
print(record_dict)

"""
Generate the gc file from .env if it doesn't exist
"""

