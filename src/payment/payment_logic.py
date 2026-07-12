from datetime import datetime
import queue
import threading
from typing import List, Tuple, Union

import discord
import requests

import firebase_manager
from constants import (
    EXCHANGE_RATE_ROUND_OFF_DP,
    LOG_CHANNEL_ID,
    LOG_SHOW_NUMBER,
    OPEN_EXCHANGE_RATE_API_KEY,
    ROUND_OFF_DP,
    SUPPORTED_CURRENCY,
    TIMEZONE,
    UNIFIED_CURRENCY,
    USER_MAPPING,
)
from payment.payment_ui import InputView, UndoView, amt_parser, is_valid_amount
from utils import B, I, channel_to_text, get_mapped_name

payment_records = firebase_manager.fetch_payment_list()
user_list = list(payment_records.keys())
firebase_queue = queue.Queue()


def parse_optional_args(args: List[str]) -> Union[Tuple[bool, str, str], bool]:
    """
    Parse optional command arguments.

    Args:
        args: Optional arguments from the command input.

    Returns:
        tuple[bool, str, str] | bool: Service charge flag, currency, and reason,
        or False if the arguments are invalid.
    """
    service_charge = False
    currency: str = UNIFIED_CURRENCY
    reason = ""

    for i in range(len(args)):
        if i <= 1 and args[i].startswith("-"):
            if args[i][1:].upper() not in SUPPORTED_CURRENCY.keys():
                return False
            currency = args[i][1:].upper()
        elif args[i] == "sc":
            service_charge = True
        else:
            reason += args[i] + " "

    return service_charge, currency, reason[:-1]


def parse_payment_cmd(tokens: list[str]) -> Union[dict, str]:
    """
    Parse command tokens into a payment record dict.

    Args:
        tokens: Lowered tokens from one payment line (without command prefix).

    Returns:
        dict with keys: ppl_to_pay, operation_owe, ppl_get_paid, amount,
        service_charge, currency, reason — or an error string on failure.
    """
    if len(tokens) < 4:
        return "Invalid input! Expected: <payers> owe/payback <payee> <amount> [currency] [sc] [reason]"

    # left users
    ppl_to_pay = tokens[0]
    if any(p not in user_list for p in ppl_to_pay.split(",")):
        return "Invalid input for provider!"

    # operation
    operation = tokens[1].lower()
    if operation not in ["owe", "payback"]:
        return "Invalid payment operation!"
    operation_owe = operation == "owe"

    # right user
    ppl_get_paid = tokens[2].lower()
    if ppl_get_paid not in user_list:
        return "Invalid input for receiver!"
    if ppl_get_paid in ppl_to_pay.split(","):
        return "Invalid input: one cannot owe himself!"

    # amount
    if not is_valid_amount(tokens[3]):
        return "Invalid amount!"
    try:
        amount: float = round(eval(amt_parser(tokens[3])), ROUND_OFF_DP)
    except ZeroDivisionError:
        return "Invalid amount: Don't divide zero la..."
    except (ValueError, SyntaxError):
        return "What have you entered for the amount .-."
    if amount == 0.0:
        return "Invalid amount: amount cannot be zero!"

    # optional args
    parse_result = parse_optional_args(tokens[4:])
    if not parse_result:
        return "Invalid currency!"
    service_charge, currency, reason = parse_result

    return {
        "ppl_to_pay": ppl_to_pay,
        "operation_owe": operation_owe,
        "ppl_get_paid": ppl_get_paid,
        "amount": amount,
        "service_charge": service_charge,
        "currency": currency,
        "reason": reason,
    }


def record_to_text(
    author: str,
    payers: str,
    operation: str,
    payees: str,
    amount: float,
    reason: str,
    timestamp=None,
    currency="",
    cancelled=False,
) -> str:
    """
    Format a payment record for display.

    Args:
        author: The author of the payment record.
        payers: The left user(s) who owe money.
        operation: The operation of the payment (owe/payback).
        payees: The right user(s) who receive money.
        amount: The amount of money owed or paid.
        reason: The reason for the payment.
        timestamp: The timestamp of the payment record.
        currency: The currency of the payment record.
        cancelled: Whether the payment record is cancelled.

    Returns:
        str: The formatted payment record.
    """
    time_text = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] " if timestamp else ""
    cancelled_text = B(" Cancelled ") if cancelled else ""
    return f"{time_text}{cancelled_text}{author}: {payers} {operation} {payees} ${amount}{reason}{currency}"


def firebase_worker():
    while True:
        task = firebase_queue.get()
        if task is None:
            firebase_queue.task_done()
            return

        match task["type"]:
            case "create":
                firebase_manager.create_user(task["user"], task["timestamp"])
            case "delete":
                firebase_manager.delete_user(task["user"])
            case "payment":
                user = task["user"]
                balance = task["balance"]
                timestamp = task["timestamp"]
                firebase_manager.update_user_balance(user, balance, timestamp)

        firebase_queue.task_done()


def show_payment_record(author_id=None) -> str:
    """
    Shows the payment records in a formatted string.

    Args:
        author_id (int, optional): The Discord user id of the command sender. Defaults to None.

    Returns:
        str: A formatted string of payment records, or an error message.
    """
    zero = take_money = need_pay = ""
    sum = 0
    mapped_name = get_mapped_name(author_id)

    zero_items = []
    take_money_items = []
    need_pay_items = []

    for name, amount in payment_records.items():
        sum += amount
        record_text = ""
        if amount == 0:
            record_text = B(name) + " doesn't need to pay\n"
        elif amount > 0:
            record_text = f"{B(name)} should receive ${I(amount)}\n"
        else:
            record_text = f"{B(name)} needs to pay ${I(-amount)}\n"

        if name == mapped_name:
            record_text = f"> ### {record_text.rstrip()}\n"

        if amount == 0:
            zero_items.append(record_text)
        elif amount > 0:
            take_money_items.append((amount, record_text))
        else:
            need_pay_items.append((-amount, record_text))

    zero = "".join(zero_items)
    take_money = "".join(
        record_text
        for _, record_text in sorted(take_money_items, key=lambda item: item[0])
    )
    need_pay = "".join(
        record_text
        for _, record_text in sorted(need_pay_items, key=lambda item: item[0])
    )

    if round(sum, 5) != 0:
        return "Error in records! Sum of payments is not zero"

    zero = zero + "\n" if zero else zero
    take_money = take_money + "\n" if take_money else take_money
    need_pay = need_pay + "\n" if need_pay else need_pay

    return (zero + take_money + need_pay) or "Error! No payment records found"


def refetch_payment_record() -> str:
    """re-fetch payment records from firebase"""
    global payment_records, user_list
    payment_records = firebase_manager.fetch_payment_list()
    user_list = list(payment_records.keys())


def show_payment_logs(message: list[str]) -> str:
    """
    Show the latest payment logs.

    Args:
        message: A split command message.

    Returns:
        str: The formatted latest payment logs.
    """
    try:
        n = (
            int(message[1])
            if len(message) > 1 and 0 < int(message[1]) < 50
            else LOG_SHOW_NUMBER
        )
    except ValueError:
        return B("Please enter a number between 1 and 50. Syntax: !log [number]")

    logs = firebase_manager.get_payment_logs(n)
    log_list = []
    for log in logs:
        log = log.to_dict()
        log_list.append(
            record_to_text(
                log["enteredBy"],
                log["payers"],
                log["operation"],
                log["payees"],
                log["amount"],
                log["reason"],
                timestamp=log["timestamp"],
                cancelled=log["cancelled"],
            )
        )
    log_text = "\n".join(reversed(log_list))
    return log_text or B("No payment logs found")


def show_logs(message: list[str]) -> str:
    """
    Show command history with optional filters.

    Args:
        message: A split command message.

    Returns:
        str: The formatted log history.
    """
    # TODO: command/ui for showing all logs
    # no filter checking for now
    try:
        command_type = "payment"
        n = LOG_SHOW_NUMBER  # Default value

        if len(message) > 1:
            # Case 1: !history command_type number
            if len(message) > 2 and message[1].isalpha() and message[2].isdigit():
                command_type = message[1]
                n = int(message[2]) if 0 < int(message[2]) < 50 else LOG_SHOW_NUMBER

            # Case 2: !history command_type
            elif message[1].isalpha():
                command_type = message[1]

            # Case 3: !history number
            elif message[1].isdigit():
                n = int(message[1]) if 0 < int(message[1]) < 50 else LOG_SHOW_NUMBER

        # Case 4: !history (default, handled by initial values)
    except ValueError:
        return B(
            "Please enter a valid number between 1 and 50. Syntax: !history [command_type] [number]"
        )

    if command_type == "all":
        command_type = None

    logs = firebase_manager.get_logs(n, command_type)
    log_list = []
    for log in logs:
        if command_type == "payment":
            log_list.append(
                record_to_text(
                    log["enteredBy"],
                    log["payers"],
                    log["operation"],
                    log["payees"],
                    log["amount"],
                    log["reason"],
                    timestamp=log["timestamp"],
                    cancelled=log["cancelled"],
                )
            )
        else:
            log_list.append(
                f"[{log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] {B(log['channel'])} {log['enteredBy']}: {log['command']}"
            )
    return "\n".join(reversed(log_list)) or B("No logs found")


async def create_user(bot, message) -> str:
    """
    Create a new user.

    Args:
        bot: The Discord bot instance.
        message: The command message from the user.

    Returns:
        str: The result of the user creation.
    """
    msg = message.message.content.lower().split()
    if len(msg) < 2:
        return B("Please enter a name for the new user")

    name = msg[1]
    if name in user_list:
        return f"**Failed to create {name}!**\nPerson already exists."

    payment_records[name] = 0.0
    user_list.append(name)
    firebase_queue.put(
        {
            "type": "create",
            "user": name,
            "timestamp": message.message.created_at.astimezone(TIMEZONE),
        }
    )
    await bot.get_channel(LOG_CHANNEL_ID).send(
        f"{message.author.name}: Created new person: {name}"
    )
    return f"### Person {name} created!\n{show_payment_record()}"


async def delete_user(bot, message) -> str:
    """
    Delete a user if they have no debts.

    Args:
        bot: The Discord bot instance.
        message: The command message from the user.

    Returns:
        str: The result of the user deletion.
    """
    msg = message.message.content.lower().split()
    if len(msg) < 2:
        return B("Please enter a name for the user to delete")

    name = msg[1]
    if name not in user_list:
        return f"**Failed to delete {name}!**\nPerson does not exist."

    if payment_records[name] != 0.0:
        return f"**Failed to delete {name}!**\nPerson has debts, cannot be deleted."

    del payment_records[name]
    user_list.remove(name)
    firebase_queue.put(
        {
            "type": "delete",
            "user": name,
        }
    )
    await bot.get_channel(LOG_CHANNEL_ID).send(
        f"{message.author.name}: Deleted person: {name}"
    )
    return f"### Person {name} deleted!\n{show_payment_record()}"


def exchange_currency(from_cur: str, amount: float) -> tuple[float, float]:
    """
    Convert an amount to the unified currency.

    Args:
        from_cur: The base currency to convert from.
        amount: The amount to convert.

    Returns:
        tuple[float, float]: The converted amount and exchange rate.
    """
    amount = float(amount)
    if from_cur == UNIFIED_CURRENCY:
        return amount, 1.0
    to_cur = UNIFIED_CURRENCY
    currencies = to_cur + "%2C" + from_cur
    url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_RATE_API_KEY}&symbols={currencies}"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    rates = response.json().get("rates", {})
    rate = rates.get(to_cur, 0) / rates.get(from_cur, 1)
    return amount * rate, round(rate, EXCHANGE_RATE_ROUND_OFF_DP)


def synchronize_payment_records(users: list[str], timestamp) -> None:
    """
    Queue balance updates for the given users.

    Args:
        users: The user names to sync.
        timestamp: The timestamp to write with the updates.

    Returns:
        None.
    """
    for user in users:
        firebase_queue.put(
            {
                "type": "payment",
                "user": user,
                "balance": payment_records[user],
                "timestamp": timestamp,
            }
        )


def payment_handling(
    ppl_to_pay: str, ppl_get_paid: str, amount: float, timestamp
) -> str:
    """
    Apply a payment transaction and return the update summary.

    Args:
        ppl_to_pay: The left user or users who pay.
        ppl_get_paid: The right user or users who receive payment.
        amount: The amount to be paid in unified currency.
        timestamp: The timestamp to associate with the update.

    Returns:
        str: A summary of the payment changes.
    """

    def owe(person_to_pay: str, person_get_paid: str) -> str:
        """Performs a single owe operation between two persons"""
        if person_to_pay == person_get_paid:
            return ""
        if person_to_pay is None:
            target = person_get_paid
            add = True
        elif person_get_paid is None:
            target = person_to_pay
            add = False
        else:
            raise Exception("Core logic error????????????")  # should not happen

        original = payment_records[target]
        current = round(original + amount if add else original - amount, ROUND_OFF_DP)
        payment_records[target] = current

        p = original > 0  # originally positive
        p0 = original == 0  # originally zero
        c = current > 0  # currently positive
        c0 = current == 0  # currently zero

        original = abs(original)
        current = abs(current)

        """
        p 0: jaga pay XXX __ -> XXX don't pay
        !p 0: XXX pay jaga __ -> XXX don't pay
        0 c: jaga pay XXX __ (new record)
        0 !c: XXX pay jaga __ (new record)

        p c: jaga pay XXX: __ -> __
        !p c: XXX pay jaga __ -> jaga pay XXX __
        p !c: jaga pay XXX __ -> XXX pay jaga __
        !p !c: XXX pay jaga: __ -> __
        """

        # ???
        if p and c0:
            return f"-# {B(target)} should receive ${original} → {B(target)} doesn't need to pay\n"
        elif not p and c0:
            return f"-# {B(target)} needs to pay ${original} → {B(target)} doesn't need to pay\n"
        elif p0 and c:
            return f"-# {B(target)} should receive ${current} (new record)\n"
        elif p0 and not c:
            return f"-# {B(target)} needs to pay ${current} (new record)\n"
        elif p and c:
            return f"-# {B(target)} should receive: ${original} → ${current}\n"
        elif not p and c:
            return f"-# {B(target)} needs to pay ${original} → {B(target)} should receive ${current}\n"
        elif p and not c:
            return f"-# {B(target)} should receive ${original} → {B(target)} needs to pay ${current}\n"
        else:
            return f"-# {B(target)} needs to pay: ${original} → ${current}\n"

    try:
        update = ""
        pay_list = ppl_to_pay.split(",")
        paid_list = ppl_get_paid.split(",")
        for each_to_pay in pay_list:
            for each_get_paid in paid_list:
                update += owe(each_to_pay, None) + owe(None, each_get_paid)
                update += "\n" if len(paid_list) > 1 else ""
            update += "\n" if len(pay_list) > 1 else ""
        synchronize_payment_records(pay_list + paid_list, timestamp)
        return update
    except KeyError:
        return B("ERROR: Person not found")


def build_reason_text(reason: str) -> str:
    if reason:
        if reason[0] in "(（" and reason[-1] in "）)":
            return " " + reason
        else:
            return f" ({reason})"
    else:
        return ""


def build_currency_text(currency: str, exchange_rate: float) -> str:
    if currency != UNIFIED_CURRENCY:
        return f" [{currency}(1) -> {UNIFIED_CURRENCY}({exchange_rate})]"
    else:
        return ""


def process_amount(
    amount: str, currency: str, service_charge: bool
) -> Tuple[float, float]:
    """
    Convert the entered amount into unified currency.

    Args:
        amount: The amount input from the user.
        currency: The currency of the amount.
        service_charge: Whether to apply a service charge.

    Returns:
        tuple[float, float]: The converted amount and exchange rate.
    """
    actual_amount, exchange_rate = exchange_currency(currency, amount)
    actual_amount *= 1.1 if service_charge else 1
    actual_amount = round(actual_amount, ROUND_OFF_DP)
    return actual_amount, exchange_rate


def parse_payment(message: discord.Message, parsed: dict, msg_time: datetime) -> tuple:
    ppl_to_pay = parsed["ppl_to_pay"]
    operation_owe = parsed["operation_owe"]
    ppl_get_paid = parsed["ppl_get_paid"]
    amount = parsed["amount"]
    service_charge = parsed["service_charge"]
    currency = parsed["currency"]
    reason = parsed["reason"]

    # Convert currency and apply surcharge
    actual_amount, exchange_rate = process_amount(amount, currency, service_charge)

    # Generate log content
    reason_text = build_reason_text(reason)
    operation_text = "owe" if operation_owe else "pay back"
    currency_text = build_currency_text(currency, exchange_rate)
    log_content = (
        f"{message.author}: {ppl_to_pay} {operation_text} {ppl_get_paid} ${actual_amount}"
        f"{reason_text}{currency_text}"
    )

    # switch pay & paid for pay back operation
    if not operation_owe:
        ppl_to_pay, ppl_get_paid = ppl_get_paid, ppl_to_pay

    # perform the payment operation
    update = payment_handling(ppl_to_pay, ppl_get_paid, actual_amount, msg_time)

    return (
        ppl_to_pay,
        operation_text,
        ppl_get_paid,
        actual_amount,
        reason_text,
        log_content,
        update,
    )


async def payment_system(bot, message, prev_input=None) -> None:
    """
    Process a payment command and update the payment records.

    Args:
        bot: The Discord bot instance.
        message: The command message from the user.
        prev_input: Previous parsed input for edit flow.

    Returns:
        None.
    """

    async def parse_ui_input() -> Union[dict, str]:
        """
        Parse the UI-based payment input.

        Returns:
            dict[str, object] | str: Parsed payment data or an error message.
        """
        if prev_input is None:
            menu = InputView(message.author.id, user_list)
        else:
            ptp = prev_input["ppl_to_pay"]
            op = prev_input["operation_owe"]
            pgp = prev_input["ppl_get_paid"]
            amt = prev_input["amount"]
            sc = prev_input["service_charge"]
            cur = prev_input["currency"]
            reason = prev_input["reason"]
            menu = InputView(
                message.author.id, user_list, ptp, op, pgp, amt, sc, cur, reason
            )

        menu.update_description()
        menu.message = await message.reply(view=menu, embed=menu.embed_text)
        await menu.wait()

        if menu.cancelled:
            return "Process cancelled!"
        if not menu.finished:
            await menu.message.reply(
                B(f"> Input closed. <@{message.author.id}> bro gone where?")
            )
            return ""

        return {
            "ppl_to_pay": menu.pay_text,
            "operation_owe": menu.owe,
            "ppl_get_paid": menu.paid_text,
            "amount": menu.amount_text,
            "service_charge": menu.service_charge,
            "currency": menu.currency,
            "reason": menu.reason,
        }

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    msg = message.message.content.lower().split()
    cmd_input = len(msg) >= 5

    # Multi-line detection: split by newlines, process each line as a separate record
    raw_lines = message.message.content.split("\n")
    is_multi_line = len(raw_lines) > 1 and cmd_input and prev_input is None
    if is_multi_line:
        await handle_multi_line_payment(message, raw_lines, log_channel)
        return

    if cmd_input:
        parsed_input = parse_payment_cmd(msg[1:])
    else:
        parsed_input = await parse_ui_input()

    if isinstance(parsed_input, str):  # error enountered
        if parsed_input:
            await message.reply(B(parsed_input))
        return

    response_msg = await message.reply(B("Processing payment... Please wait."))
    msg_time = message.message.created_at.astimezone(TIMEZONE)

    ppl_to_pay, op_text, ppl_get_paid, amount, reason, log_content, update = (
        parse_payment(message, parsed_input, msg_time)
    )

    # response content
    user_mention = " ".join(
        [
            f"<@{USER_MAPPING.get(each)}>"
            for each in ppl_to_pay.split(",") + [ppl_get_paid]
            if USER_MAPPING.get(each)
        ]
    )
    user_mention = "\n-# " + user_mention if user_mention else ""
    response_content = f"`{log_content}`{user_mention}\n-# Updated records:\n{update}"

    # send the UNDO view before time-consuming operations
    undo_view = UndoView(message.author.id, not cmd_input, response_content)
    undo_view.message = await response_msg.edit(
        content=None, view=undo_view, embed=undo_view.embed_text
    )

    await log_channel.send(log_content)
    log_ref = firebase_manager.write_log(
        "payment",
        channel_to_text(message.channel),
        message.author.name,
        message.message.content,
        msg_time,
        payers=ppl_to_pay,
        operation=op_text,
        payees=ppl_get_paid,
        amount=amount,
        reason=reason,
        cancelled=False,
    )

    await undo_view.wait()

    # handle undo operation
    if undo_view.undo and undo_view.edit:
        payment_handling(
            ppl_get_paid,
            ppl_to_pay,
            amount,
            undo_view.cancelled_at.astimezone(TIMEZONE),
        )
        await undo_view.message.reply(
            B(
                "Undo has been executed for editing!\n-# Loading new UI panel for editing..."
            )
        )
        undo_log_content = f"{undo_view.undo_user}: __UNDO__ **[**{log_content}**]**"
        await log_channel.send(undo_log_content)
        firebase_manager.update_log(log_ref, cancelled=True)
        firebase_manager.write_log(
            "manage",
            channel_to_text(message.channel),
            undo_view.undo_user,
            "undo",
            undo_view.cancelled_at.astimezone(TIMEZONE),
            cancelledRecord=log_content,
        )
        await payment_system(
            bot,
            message,
            prev_input={
                "ppl_to_pay": ppl_to_pay,
                "operation_owe": parsed_input["operation_owe"],
                "ppl_get_paid": ppl_get_paid,
                "amount": parsed_input["amount"],
                "service_charge": parsed_input["service_charge"],
                "currency": parsed_input["currency"],
                "reason": parsed_input["reason"],
            },
        )
    elif undo_view.undo:
        payment_handling(
            ppl_get_paid,
            ppl_to_pay,
            amount,
            undo_view.cancelled_at.astimezone(TIMEZONE),
        )
        await undo_view.message.reply(B("Undo has been executed!"))
        undo_log_content = f"{undo_view.undo_user}: __UNDO__ **[**{log_content}**]**"
        await log_channel.send(undo_log_content)
        firebase_manager.update_log(log_ref, cancelled=True)
        firebase_manager.write_log(
            "manage",
            channel_to_text(message.channel),
            undo_view.undo_user,
            "undo",
            undo_view.cancelled_at.astimezone(TIMEZONE),
            cancelledRecord=log_content,
        )


async def handle_multi_line_payment(message, raw_lines: list[str], log_channel) -> None:
    """
    Process multi-line payment input (command-line only).
    Each non-empty line after the first is parsed as a separate record.
    All records share a single UndoView that reverses every transaction.

    Args:
        message: The command message from the user.
        raw_lines: Lines split from the raw message content.
        log_channel: The discord log channel to send logs to.
    """
    parsed_txns = []
    errors = []

    for i, line in enumerate(raw_lines):
        line = line.strip()
        if not line:
            continue
        # Strip command prefix from the first line only
        tokens = line.lower().split()
        if i == 0 and tokens and tokens[0] == "!pm":
            tokens = tokens[1:]
        if len(tokens) < 4:
            errors.append(
                f"-# Line {i + 1}: Invalid format (expected: <payers> owe/payback <payee> <amount>)"
            )
            continue
        parsed = parse_payment_cmd(tokens)
        if isinstance(parsed, str):
            errors.append(f"-# Line {i + 1}: {parsed}")
            continue
        parsed_txns.append(parsed)

    if not parsed_txns:
        reply = "\n".join(errors) if errors else "No valid payment records found."
        await message.reply(B(reply))
        return

    # Report parsing errors but still process valid lines
    if errors:
        await message.reply(B("Some lines could not be parsed:\n" + "\n".join(errors)))

    # Process each parsed transaction
    response_msg = await message.reply(B("Processing payment... Please wait."))
    msg_time = message.message.created_at.astimezone(TIMEZONE)

    processed_txns = []  # {ppl_to_pay, ppl_get_paid, actual_amount, log_content, log_ref}
    for parsed in parsed_txns:
        ppl_to_pay, op_text, ppl_get_paid, amount, reason, log_content, update = (
            parse_payment(message, parsed, msg_time)
        )

        # Log to firebase immediately
        log_ref = firebase_manager.write_log(
            "payment",
            channel_to_text(message.channel),
            message.author.name,
            log_content,
            msg_time,
            payers=ppl_to_pay,
            operation=op_text,
            payees=ppl_get_paid,
            amount=amount,
            reason=reason,
            cancelled=False,
        )
        await log_channel.send(log_content)

        processed_txns.append(
            {
                "ppl_to_pay": ppl_to_pay,
                "ppl_get_paid": ppl_get_paid,
                "actual_amount": amount,
                "log_content": log_content,
                "log_ref": log_ref,
                "update": update,
            }
        )

    # Build combined response
    update_blocks = [
        f"`{t['log_content']}`\n-# Updated:\n{t['update']}" for t in processed_txns
    ]
    all_mentioned = set()
    for t in processed_txns:
        for u in t["ppl_to_pay"].split(",") + [t["ppl_get_paid"]]:
            if USER_MAPPING.get(u):
                all_mentioned.add(USER_MAPPING[u])
    mention_text = " ".join(f"<@{uid}>" for uid in all_mentioned)
    mention_text = f"\n-# {mention_text}" if mention_text else ""
    combined_response = "\n\n".join(update_blocks) + mention_text

    # Single UndoView for the whole batch
    undo_view = UndoView(message.author.id, False, combined_response)
    undo_view.message = await response_msg.edit(
        view=undo_view, embed=undo_view.embed_text
    )
    await undo_view.wait()

    # Bulk undo: reverse every transaction in reverse order
    if undo_view.undo:
        for txn in reversed(processed_txns):
            payment_handling(
                txn["ppl_get_paid"],
                txn["ppl_to_pay"],
                txn["actual_amount"],
                undo_view.cancelled_at.astimezone(TIMEZONE),
            )
            firebase_manager.update_log(txn["log_ref"], cancelled=True)
            undo_log = f"{undo_view.undo_user}: __UNDO__ **[**{txn['log_content']}**]**"
            await log_channel.send(undo_log)
            firebase_manager.write_log(
                "manage",
                channel_to_text(message.channel),
                undo_view.undo_user,
                "undo",
                undo_view.cancelled_at.astimezone(TIMEZONE),
                cancelledRecord=txn["log_content"],
            )
        await undo_view.message.reply(B("All records have been undone!"))


def terminate_worker():
    """Terminates the firebase worker thread"""
    firebase_queue.put(None)
    firebase_queue.join()


payment_thread = threading.Thread(target=firebase_worker, daemon=False)
payment_thread.start()
