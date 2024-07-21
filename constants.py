COMMAND = "pm"
CENTRALIZED_PERSON = "ppl"
BOT_STATUS = "->> !info"

LOG_SHOW_NUMBER = 10
DEFAULT_LOG_SHOW_NUMBER = 40
MENU_TIMEOUT = 3600.0
UNDO_TIMEOUT = 3600.0

# PAYMENT_RECORD_FILE = "payment_record.txt"
PAYMENT_RECORD_FILE = "test_record.txt"
# LOG_FILE = "log.txt"
LOG_FILE = "test_log.txt"
BACKUP_FILE = "backup_record.txt"

BOT_DESCRIPTION = f"""
When Person A help Person B pay something in real life, Person B should pay back Person A later. 
Payment bot is created for this purpose.
Let a person be the centralized one, transactions between other people will be done through this centralized person.

Let's say Person A helps Person B to paid something, then Person B owes Person A
Person B owes Centralized person -> Centralized person owes Person A

The bot responses if the message is successfully received. Send the record again if the bot does not response. 
Use the keyword "!" for calling this bot. The input window will close after 1 minute if no further interactions are detected.

_List of commands:_
- !info
The message you are reading now. Contains useful information to use this bot.
- !list
List out all payment records stored in the server side of the bot.
- **!pm**
Writing payment record
- !log
This shows the {LOG_SHOW_NUMBER} latest payment record messages sent by users.
- !logall
This shows the {DEFAULT_LOG_SHOW_NUMBER} latest payment record messages sent by users.
- !backup
This shows the backup records in the backup file.
- !showbackup
This backups the current payment record to the backup file.
"""


