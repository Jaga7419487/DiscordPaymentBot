import json
from datetime import datetime
from typing import Literal

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from constants import FIREBASE_KEY, FIREBASE_KEY_PATH, TIMEZONE

with open(FIREBASE_KEY_PATH, 'w') as f:
    json.dump(FIREBASE_KEY, f, indent=2)

cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

users_ref = db.collection('users')
logs_ref = db.collection('logs')
bot_ref = db.collection('bot')
bookkeeping_ref = db.collection('bookkeeping')

RecordType = Literal["expense", "income"]


def firebase_to_dict() -> dict:
    """ Fetches all user balances from the Firestore 'users' collection
    :return: A dictionary {userID: balances}
    """
    users = users_ref.stream()
    return {user.id: user.to_dict().get('balance', 0) for user in users}


def update_user_balance(name: str, amount: float, timestamp=datetime.now(TIMEZONE)) -> None:
    """ Updates the balance of a user in the Firestore
    :param name: The name of the user to update
    :param amount: The amount to update the user's balance by (can be negative)
    :param timestamp: The timestamp of the update (default is current time)
    """
    users_ref.document(name).set({
        'balance': amount,
        'lastUpdated': timestamp.astimezone(TIMEZONE),
    }, merge=True)


def get_payment_logs(n):
    """ (Deprecated, use get_logs instead) Fetches the latest n payment records
    :param n: Number of the latest payment logs to fetch
    :return: Iterable of latest n payment logs
    """
    latest_payment_logs = logs_ref.where(filter=FieldFilter('type', '==', 'payment')) \
        .order_by('timestamp', direction=firestore.Query.DESCENDING) \
        .limit(n).stream()
    return latest_payment_logs


def get_logs(n, command_type='payment') -> list[dict]:
    """ Fetches logs accordingly, default is payment logs
    :param n: Number of the latest logs to fetch
    :param command_type: The type of command to filter logs by
    :return: list of latest n logs of the specified type
    """
    logs = logs_ref
    if command_type:
        logs = logs.where(filter=FieldFilter('type', '==', command_type))
    logs = logs.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(n).stream()
    return [log.to_dict() for log in logs]


def write_bot_log() -> None:
    bot_ref.add({
        'startTime': datetime.now(TIMEZONE),
    })


def write_log(log_type: str, channel: str, entered_by: str, cmd: str,
              timestamp=datetime.now(TIMEZONE), **kwargs) -> firestore.DocumentReference:
    """
    Writes a log to the Firestore
    :param log_type: The type of the log (e.g., 'info', 'payment', 'encrypt')
    :param timestamp: Consistent with the timestamp shown in Discord
    :param channel: The channel where the log was created
    :param entered_by: The user who entered the command
    :param cmd: The command string
    :param kwargs: Additional fields specific to the log type
    :return: The document reference of the created log
    """
    log_data = {
        'type': log_type,
        'timestamp': timestamp.astimezone(TIMEZONE),
        'channel': channel,
        'enteredBy': entered_by,
        'command': cmd,
    }
    log_data.update(kwargs)
    return logs_ref.add(log_data)[1]


def update_log(doc_ref: firestore.DocumentReference, **kwargs) -> None:
    """
    Updates an existing log document with new data
    :param doc_ref: The reference to the log document to update
    :param kwargs: The fields to update in the log document
    """
    doc_ref.update(kwargs)


def create_user(name: str, timestamp=datetime.now(TIMEZONE)) -> None:
    """ Creates a new user document in the Firestore
    :param name: The name of the user to create
    """
    users_ref.document(name).set({
        'balance': 0,
        'lastUpdated': timestamp.astimezone(TIMEZONE),
    })


def delete_user(name: str) -> None:
    """ Deletes a user document from the Firestore
    :param name: The name of the user to delete
    """
    user_ref = users_ref.document(name)
    if user_ref.get().exists:
        user_ref.delete()
    else:
        raise ValueError(f"User {name} does not exist.")


def add_bookkeeping_record(username: str, record_type: RecordType, category: str, name: str, amount: float,
                           timestamp=datetime.now(TIMEZONE)) -> firestore.DocumentReference:
    """
    Adds a bookkeeping record to the Firestore 'bookkeeping' collection
    :param username: The username of this record
    :param record_type: 'expense' or 'income'
    :param category: The category of the record
    :param name: The name/description of the record
    :param amount: The amount (number)
    :param timestamp: The timestamp of the record
    :return: The document reference of the created bookkeeping record
    """
    record_data = {
        'timestamp': timestamp.astimezone(TIMEZONE),
        'username': username,
        'type': record_type,
        'category': category,
        'name': name,
        'amount': amount,
    }
    return bookkeeping_ref.add(record_data)[1]


def get_bookkeeping_records(
    n: int,
    record_type: RecordType = None,
    category: str = None,
) -> list[dict]:
    """
    Retrieves the n bookkeeping records from Firestore with optional filters
    :param n: Number of records to retrieve
    :param record_type: 'expense' or 'income' (optional)
    :param category: category string (optional)
    :return: list of bookkeeping records (dicts)
    """
    query = bookkeeping_ref
    if record_type:
        query = query.where('type', '==', record_type)
    if category:
        query = query.where('category', '==', category)
    docs = query.limit(n).stream()
    return [doc.to_dict() for doc in docs]
