import firebase_manager
from constants import ROUND_OFF_DP
from utils import B, amt_parser, is_valid_amount


def add_bookkeeping_record(message) -> str:
    """Add a bookkeeping record and return a response message.

    Args:
        message: The command message from the user.

    Returns:
        str: A response message indicating the result of the operation.
    """
    msg = message.message.content.lower().split()
    if len(msg) < 5:
        return B("Usage: !log <type> <category> <name> <amount> [<timestamp>]")

    username = message.author.name.lower()
    record_type, category, name, amount = msg[1:5]
    # timestamp = msg[5] if len(msg) > 5 else None

    if record_type not in ["income", "expense"]:
        return B("Invalid type. Use 'income' or 'expense'")
    if not is_valid_amount(amount):
        return B("Invalid amount. Must be a number")

    amount = round(eval(amt_parser(msg[4])), ROUND_OFF_DP)
    if amount <= 0:
        return B("Amount must be greater than 0")

    firebase_manager.add_bookkeeping_record(
        username, record_type, category, name, amount
    )
    return B("Bookkeeping record added successfully")


def show_bookkeeping_records(msg: list[str]) -> str:
    """Return bookkeeping records with optional filters.

    Args:
        msg: The message content split into lowercase strings.

    Returns:
        str: The bookkeeping records.
    """

    return ""
