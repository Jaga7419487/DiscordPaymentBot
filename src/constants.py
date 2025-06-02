import os

import pytz
from dotenv import load_dotenv

load_dotenv()

# bot
BOT_KEY = os.getenv('BOT_KEY')
PAYMENT_CHANNEL_ID = int(os.getenv('PAYMENT_CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
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
USER_MAPPING = {  # for mentioning
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
MENU_TIMEOUT = 3600.0
UNDO_TIMEOUT = 3600.0
ENCRYPTED_DELETE_TIMEOUT = 15

# koyeb
KOYEB_PUBLIC_LINK = os.getenv('KOYEB_PUBLIC_LINK')
TIMEZONE = pytz.timezone('Asia/Hong_Kong')  # ensure consistency between firestore and discord

# firebase
FIREBASE_KEY_PATH = "discord-payment-bot-firebase-adminsdk.json"
FIREBASE_KEY = {
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

# trader made (for exchange rates)
TRADER_MADE_API_KEY = os.getenv('TRADER_MADE_API_KEY')

BOT_DESCRIPTION = f"""
# Discord Payment Bot
## Purpose: Manage and record payments among a group
**Workflow:**
1. **Scenario:** When __Person A__ pays for __Person B__, __Person B__ owes __Person A__
2. **Centralized System:** A central person manages transactions, ensuring smooth exchanges
3. **Repayment Chain:** 
  - __Person A__ pays for __Person B__ → __Person B__ owes __Person A__
  - __Person B__ owes __Centralized Person__ → __Centralized Person__ owes __Person A__
**Bot Functionality:**
- **Interaction:** Users call the bot with '!' prefix (e.g., `!info`)
- **Response:** The bot responds to valid commands with appropriate messages
## Commands
`!info`: Display this information
`!list`: List all payment records, short: `!l`
`!create [name]`: Create a new user (e.g., `!create personA`)
`!delete [name]`: Delete a user with no debts (e.g., `!delete personA`)
`!log`: Show the latest {LOG_SHOW_NUMBER} payment records
`!logall`: Show all command logs
`!currencies`: Show supported currencies
`!encrypt`: Encrypt a message with a secret key
`!decrypt`: Decrypt an encrypted message with a key
**`!pm`: Enter a payment record (UI window if only `!pm` sent)**
> __Syntax:__
> `!pm [payee] [operation] [get paid] [amount] [-cur] [sc] [reason]`
> `payee`: People who should repay, separated by ',' without spaces
> `operation`: `owe`/`payback`
> `get paid`: Person to be repaid
> `amount`: Up to 3 decimal points
> `-cur`: Optional: `HKD/CNY/GBP` (default `HKD`)
> `sc`: Optional: include 10% service charge
> `reason`: Optional, no brackets needed
> Example: `!pm personA,personB owe personC 100 -CNY sc example reason`

- Developed by __Jaga Chau__ 25-12-2023
"""
