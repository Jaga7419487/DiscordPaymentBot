import os

from dotenv import load_dotenv

load_dotenv()

# bot
BOT_KEY = os.getenv('BOT_KEY')
PAYMENT_CHANNEL_ID = int(os.getenv('PAYMENT_CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
CENTRALIZED_PERSON = os.getenv('CENTRALIZED_PERSON')  # all names should be in lowercase
TRADER_MADE_API_KEY = os.getenv('TRADER_MADE_API_KEY')
LOG_DOC_ID = os.getenv('LOG_DOC_ID')
BACKUP_DOC_ID = os.getenv('BACKUP_DOC_ID')
COMMAND = "pm"
BOT_STATUS = "->> !info"
UNIFIED_CURRENCY = "HKD"
VALID_CHARS_SET = set('0123456789+-*/.(（）)')
SUPPORTED_CURRENCY = {
    "AED": "UAE Dirham",
    "AOA": "Angolan Kwanza",
    "ARS": "Argentine Peso",
    "AUD": "Australian Dollar",
    "BGN": "Bulgaria Lev",
    "BHD": "Bahraini Dinar",
    "BRL": "Brazilian Real",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "CLP": "Chilean Peso",
    "CNY": "Chinese Yuan onshore",
    "CNH": "Chinese Yuan offshore",
    "COP": "Colombian Peso",
    "CZK": "Czech Koruna",
    "DKK": "Danish Krone",
    "EUR": "Euro",
    "GBP": "British Pound Sterling",
    "HKD": "Hong Kong Dollar",
    "HRK": "Croatian Kuna",
    "HUF": "Hungarian Forint",
    "IDR": "Indonesian Rupiah",
    "ILS": "Israeli New Sheqel",
    "INR": "Indian Rupee",
    "ISK": "Icelandic Krona",
    "JPY": "Japanese Yen",
    "KRW": "South Korean Won",
    "KWD": "Kuwaiti Dinar",
    "MAD": "Moroccan Dirham",
    "MXN": "Mexican Peso",
    "MYR": "Malaysian Ringgit",
    "NGN": "Nigerean Naira",
    "NOK": "Norwegian Krone",
    "NZD": "New Zealand Dollar",
    "OMR": "Omani Rial",
    "PEN": "Peruvian Nuevo Sol",
    "PHP": "Philippine Peso",
    "PLN": "Polish Zloty",
    "RON": "Romanian Leu",
    "RUB": "Russian Ruble",
    "SAR": "Saudi Arabian Riyal",
    "SEK": "Swedish Krona",
    "SGD": "Singapore Dollar",
    "THB": "Thai Baht",
    "TRY": "Turkish Lira",
    "TWD": "Taiwanese Dollar",
    "USD": "US Dollar",
    "VND": "Vietnamese Dong",
    "XAG": "Silver (troy ounce)",
    "XAU": "Gold (troy ounce)",
    "XPD": "Palladium",
    "XPT": "Platinum",
    "ZAR": "South African Rand",
}
USER_MAPPING = {
    'jaga': '635760265975169044',
    'larry': '641546398764105759',
    '741': '688994217745580067',
    'sdr': '616617935204777985',
    'tom': '707067744851329077',
    'hjl': '410441332012613634',
    'ryan': '619092133936365570',
    '6uo': '597352233490841601',
    'inevitable': '695475297675640882',
    'andes': '621959791698247680',
}

# digits
ROUND_OFF_DP = 3
LOG_SHOW_NUMBER = 10
LONG_LOG_SHOW_NUMBER = 20
MENU_TIMEOUT = 3600.0
UNDO_TIMEOUT = 3600.0

# google
SCOPES = ['https://www.googleapis.com/auth/documents']
SERVICE_ACCOUNT_FILE = 'temp/discord-payment-bot.json'
PAYMENT_RECORD_FILE = 'temp/payment-record.json'
GOOGLE_CRED = {
    "type": "service_account",
    "project_id": os.getenv('PROJECT_ID'),
    "private_key_id": os.getenv('PRIVATE_KEY_ID'),
    "private_key": os.getenv('PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('CLIENT_EMAIL'),
    "client_id": os.getenv('CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv('CLIENT_X509_CERT_URL'),
    "universe_domain": "googleapis.com"
}
RECORD_SHEET_URL = os.getenv('RECORD_SHEET_URL')

BOT_DESCRIPTION = f"""
# Discord Payment Bot
## Purpose: Store payment records among a group of people
**Workflow:**
1. **Scenario:** When __Person A__ help __Person B__ with a payment, __Person B__ is expected to pay back __Person A__ later
2. **Centralized System:** A single individual serves as the central point for transactions, ensuring smooth exchanges between other users (like a bank)
3. **Repayment Chain:** 
  - __Person A__ helps __Person B__ → __Person B__ owes __Person A__
  - __Person B__ owes __Centralized Person__ → __Centralized Person__ owes __Person A__
**Bot Functionality:**
- **Interaction:** Users can call the bot with '!' prefix (e.g. `!info`)
- **Response:** The bot is expected to response all valid calls with corresponding messages.
## List of commands
`!info`: The message you are reading now
`!list`: List out all payment records stored in the bot, short: `!l`
`!create [name]`: Creates a new user with a name (e.g. `!create personA`)
`!delete [name]`: Deletes a user if he has no debts (e.g. `!delete personA`)
`!log`: Shows the {LOG_SHOW_NUMBER} latest payment record inputs
`!logall`: Shows the {LONG_LOG_SHOW_NUMBER} latest payment record inputs
`!currencies`: Shows all the supported currencies
`!backup`: Backups the current payment record in a separate file
`!showbackup`: Shows the backup records
`!pmavg`: Enters a payment record with the amount divided by the number of payees (similar to **!pm**)
**`!pm`: Enters a payment record (UI window if only `!pm` sent)**
> __Syntax:__
> `!pm [payee] [operation] [get paid] [amount] [-CUR] [sc] [reason]`
> `payee`: People that should pay back the money later, separated by ',' without space
> `operation`: `owe`/`payback`
> `get paid`: Person that should be paid back later
> `amount`: Up to 3 decimal point
> `-CUR`: Optional: `HKD/CNY/GBP` (default `HKD`)
> `sc`: Optional: include 10% service charge
> `reason`: Optional, no brackets needed
> Example: `!pm personA,personB owe personC 100 -CNY sc example reason`

-# Developed by __Jaga Chau__ 25-12-2023
"""
