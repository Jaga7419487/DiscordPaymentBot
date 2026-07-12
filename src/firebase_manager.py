import json
from datetime import datetime
from typing import Literal

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from constants import FIREBASE_KEY, FIREBASE_KEY_PATH, TIMEZONE

with open(FIREBASE_KEY_PATH, "w") as f:
    json.dump(FIREBASE_KEY, f, indent=2)

cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

users_ref = db.collection("users")
logs_ref = db.collection("logs")
bot_ref = db.collection("bot")
bookkeeping_ref = db.collection("bookkeeping")

RecordType = Literal["expense", "income"]


def fetch_payment_list() -> dict:
    """
    Fetch all user balances from the Firestore users collection.

    Returns:
        dict: A mapping of user IDs to balances.
    """
    users = users_ref.stream()
    return {user.id: user.to_dict().get("balance", 0) for user in users}


def update_user_balance(
    name: str, amount: float, timestamp=datetime.now(TIMEZONE)
) -> None:
    """
    Update a user's balance in Firestore.

    Args:
        name: The name of the user to update.
        amount: The amount to update the balance by; can be negative.
        timestamp: The timestamp of the update.

    Returns:
        None.
    """
    users_ref.document(name).set(
        {
            "balance": amount,
            "lastUpdated": timestamp.astimezone(TIMEZONE),
        },
        merge=True,
    )


def get_payment_logs(n):
    """
    Fetch the latest payment logs.

    Args:
        n: Number of latest payment logs to fetch.

    Returns:
        Iterable: The latest payment log documents.
    """
    latest_payment_logs = (
        logs_ref.where(filter=FieldFilter("type", "==", "payment"))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(n)
        .stream()
    )
    return latest_payment_logs


def get_logs(n, command_type="payment") -> list[dict]:
    """
    Fetch logs with an optional type filter.

    Args:
        n: Number of latest logs to fetch.
        command_type: The log type to filter by.

    Returns:
        list[dict]: The latest logs of the requested type.
    """
    logs = logs_ref
    if command_type:
        logs = logs.where(filter=FieldFilter("type", "==", command_type))
    logs = (
        logs.order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(n)
        .stream()
    )
    return [log.to_dict() for log in logs]


def write_bot_log() -> None:
    bot_ref.add(
        {
            "startTime": datetime.now(TIMEZONE),
        }
    )


def write_log(
    log_type: str,
    channel: str,
    entered_by: str,
    cmd: str,
    timestamp=datetime.now(TIMEZONE),
    **kwargs,
) -> firestore.DocumentReference:
    """
    Write a log document to Firestore.

    Args:
        log_type: The type of the log.
        channel: The channel where the log was created.
        entered_by: The user who entered the command.
        cmd: The command string.
        timestamp: The timestamp to store with the log.
        kwargs: Additional fields specific to the log type.

    Returns:
        firestore.DocumentReference: The created log reference.
    """
    log_data = {
        "type": log_type,
        "timestamp": timestamp.astimezone(TIMEZONE),
        "channel": channel,
        "enteredBy": entered_by,
        "command": cmd,
    }
    log_data.update(kwargs)
    return logs_ref.add(log_data)[1]


def update_log(doc_ref: firestore.DocumentReference, **kwargs) -> None:
    """
    Update an existing log document.

    Args:
        doc_ref: The reference to the log document to update.
        kwargs: The fields to update in the log document.

    Returns:
        None.
    """
    doc_ref.update(kwargs)


def create_user(name: str, timestamp=datetime.now(TIMEZONE)) -> None:
    """
    Create a new user document in Firestore.

    Args:
        name: The name of the user to create.
        timestamp: The timestamp of the creation.

    Returns:
        None.
    """
    users_ref.document(name).set(
        {
            "balance": 0,
            "lastUpdated": timestamp.astimezone(TIMEZONE),
        }
    )


def delete_user(name: str) -> None:
    """
    Delete a user document from Firestore.

    Args:
        name: The name of the user to delete.

    Returns:
        None.
    """
    user_ref = users_ref.document(name)
    if user_ref.get().exists:
        user_ref.delete()
    else:
        raise ValueError(f"User {name} does not exist.")


def add_bookkeeping_record(
    username: str,
    record_type: RecordType,
    category: str,
    name: str,
    amount: float,
    timestamp=datetime.now(TIMEZONE),
) -> firestore.DocumentReference:
    """
    Add a bookkeeping record to Firestore.

    Args:
        username: The username for this record.
        record_type: The record type, either expense or income.
        category: The category of the record.
        name: The name or description of the record.
        amount: The amount.
        timestamp: The timestamp of the record.

    Returns:
        firestore.DocumentReference: The created bookkeeping record reference.
    """
    record_data = {
        "timestamp": timestamp.astimezone(TIMEZONE),
        "username": username,
        "type": record_type,
        "category": category,
        "name": name,
        "amount": amount,
    }
    return bookkeeping_ref.add(record_data)[1]


def get_bookkeeping_records(
    n: int,
    record_type: RecordType = None,
    category: str = None,
) -> list[dict]:
    """
    Retrieve bookkeeping records with optional filters.

    Args:
        n: Number of records to retrieve.
        record_type: The record type to filter by.
        category: The category to filter by.

    Returns:
        list[dict]: The matching bookkeeping records.
    """
    query = bookkeeping_ref
    if record_type:
        query = query.where("type", "==", record_type)
    if category:
        query = query.where("category", "==", category)
    docs = query.limit(n).stream()
    return [doc.to_dict() for doc in docs]
