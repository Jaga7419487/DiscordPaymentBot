COMMAND = "pm"
BOT_STATUS = "->> !info"
UNIFIED_CURRENCY = "HKD"
SUPPORTED_CURRENCY = ['HKD', 'CNY', "JPY", "GBP"]

ROUND_OFF_DP = 3
LOG_SHOW_NUMBER = 10
DEFAULT_LOG_SHOW_NUMBER = 40
MENU_TIMEOUT = 3600.0
UNDO_TIMEOUT = 3600.0

PAYMENT_RECORD_FILE = "payment_record.txt"
LOG_FILE = "log.txt"
BACKUP_FILE = "backup_record.txt"
CURRENCY_FILE = "latest_currency.txt"

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
`!list`: List out all payment records stored in the bot
`!create [name]`: Creates a new user with a name (e.g. `!create personA`)
`!delete [name]`: Deletes a user if he has no debts (e.g. `!delete personA`)
`!log`: Shows the {LOG_SHOW_NUMBER} latest payment record inputs
`!logall`: Shows the {DEFAULT_LOG_SHOW_NUMBER} latest payment record inputs
`!backup`: Backups the current payment record in a separate file
`!showbackup`: Shows the backup records
`!piano`: Book piano room for specific date & time at 00:00
**`!pm`: Enters a payment record (UI window if only `!pm` sent)**
> __Syntax:__
> `!pm [payee] [operation] [get paid] [amount] [-CUR] [sc] [reason]`
> `payee`: People that should pay back the money later, separated by ',' without space
> `operation`: `owe`/`payback`
> `get paid`: Person that should be paid back later
> `amount`: Up to 3 decimal point
> `-CUR`: Optional: `HKD/CNY/GBP` (default `HKD`)
> `sc`: Optional: include 10% service charge
> `reason`: Optional
> Example: `!pm personA,personB owe personC 100 -CNY sc (example)`

-# Developed by __Jaga Chau__ 25-12-2023
"""
