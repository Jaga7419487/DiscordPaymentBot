from datetime import datetime
import json

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from constants import FIREBASE_KEY, FIREBASE_KEY_PATH, TIMEZONE


with open(FIREBASE_KEY_PATH, 'w') as f:
    json.dump(FIREBASE_KEY, f, indent=2)
    
cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

users_ref = db.collection('users')
logs_ref = db.collection('logs')


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
        'lastUpdated': timestamp,
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


def get_logs(n, command_type='payment'):
    """ Fetches logs accordingly, default is payment logs
    :param n: Number of the latest logs to fetch
    :param command_type: The type of command to filter logs by
    :return: Iterable of latest n logs of the specified type
    """
    logs = logs_ref
    if command_type:
        logs = logs.where(filter=FieldFilter('type', '==', command_type))
    logs = logs.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(n).stream()
    return logs


def write_bot_log() -> None:
    db.collection('bot').add({
        'startTime': datetime.now(TIMEZONE),
    })


def write_log(log_type: str, channel: str, entered_by: str, cmd: str, timestamp=datetime.now(TIMEZONE),
              **kwargs) -> None:
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
        'timestamp': timestamp,
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
        'lastUpdated': timestamp,
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
