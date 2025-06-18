import queue
import threading
from typing import List, Tuple, Union

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
from utils import B, I, channel_to_text

payment_records = firebase_manager.firebase_to_dict()
user_list = list(payment_records.keys())
firebase_queue = queue.Queue()


def record_to_text(author: str, payers: str, operation: str, payees: str, amount: float,
                   reason: str, timestamp=None, currency='', cancelled=False) -> str:
    """ Converts the payment record to a formatted string
    :param author: The author of the payment record
    :param payers: The left user(s) who owe money
    :param operation: The operation (owe/payback) of the payment
    :param payees: The right user(s) who receive money
    :param amount: The amount of money owed/paid
    :param reason: The reason for the payment
    :param timestamp: The timestamp of the payment record (for logging)
    :param currency: The currency of the payment record (for payment)
    :param cancelled: Whether the payment record is cancelled (for logging)
    :return: A formatted string representing the payment record
    """
    time_text = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] " if timestamp else ''
    cancelled_text = B(" Cancelled ") if cancelled else ''
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


def show_payment_record() -> str:
    """ Shows the payment records in a formatted string
    :return: A formatted string of payment records
    """
    zero = take_money = need_pay = ""
    sum = 0

    for name, amount in payment_records.items():
        sum += amount
        if amount == 0:
            zero += B(name) + " doesn't need to pay\n"
        elif amount > 0:
            take_money += f"{B(name)} should receive ${I(amount)}\n"
        else:
            need_pay += f"{B(name)} needs to pay ${I(-amount)}\n" 
    
    if round(sum, 5) != 0:
        return "Error in records! Sum of payments is not zero"

    zero = zero + "\n" if zero else zero
    take_money = take_money + "\n" if take_money else take_money
    need_pay = need_pay + "\n" if need_pay else need_pay

    return (zero + take_money + need_pay) or "Error! No payment records found"


def show_payment_logs(message: list[str]) -> str:
    """ (Deprecated, use show_logs instead) Shows the corresponding payment logs based on the input message
    :param message: A list of input message strings
    :return: A formatted string of the latest payment logs
    """
    try:
        n = int(message[1]) if len(message) > 1 and 0 < int(message[1]) < 50 else LOG_SHOW_NUMBER
    except ValueError:
        return B("Please enter a number between 1 and 50. Syntax: !log [number]")
    
    logs = firebase_manager.get_payment_logs(n)
    log_list = []
    for log in logs:
        log = log.to_dict()
        log_list.append(record_to_text(log['enteredBy'], log['payers'], log['operation'], log['payees'],
                                       log['amount'], log['reason'], timestamp=log['timestamp'], cancelled=log['cancelled']))
    log_text = '\n'.join(reversed(log_list))
    return log_text or B("No payment logs found")


def show_logs(message: list[str]) -> str:
    """ Shows all the history command inputs with optional filters
    :param message: A list of input message strings
    :return: A formatted string of all logs
    """
    # TODO: command/ui for showing all logs
    # no filter checking for now
    try:
        command_type = 'payment'
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
        return B("Please enter a valid number between 1 and 50. Syntax: !history [command_type] [number]")
    
    if command_type == 'all':
        command_type = None
    
    logs = firebase_manager.get_logs(n, command_type)
    log_list = []
    for log in logs:
        if command_type == 'payment':
            log_list.append(record_to_text(log['enteredBy'], log['payers'], log['operation'], log['payees'],
                                           log['amount'], log['reason'], timestamp=log['timestamp'], cancelled=log['cancelled']))
        else:
            log_list.append(f"[{log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] {B(log['channel'])} {log['enteredBy']}: {log['command']}")
    return '\n'.join(reversed(log_list)) or B("No logs found")


async def create_user(bot, message) -> str:
    """ Creates a new user
    :return: A string indicating the result of the user creation
    """
    msg = message.message.content.lower().split()
    if len(msg) < 2:
        return B("Please enter a name for the new user")
    
    name = msg[1]
    if name in user_list:
        return f"**Failed to create {name}!**\nPerson already exists."
    
    payment_records[name] = 0.0
    user_list.append(name)
    firebase_queue.put({
        "type": "create",
        "user": name,
        "timestamp": message.message.created_at.astimezone(TIMEZONE),
    })
    await bot.get_channel(LOG_CHANNEL_ID).send(f"{message.author.name}: Created new person: {name}")
    return f"### Person {name} created!\n{show_payment_record()}"


async def delete_user(bot, message) -> str:
    """ Deletes a user if they have no debts
    :return: A string indicating the result of the user deletion
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
    firebase_queue.put({
        "type": "delete",
        "user": name,
    })
    await bot.get_channel(LOG_CHANNEL_ID).send(f"{message.author.name}: Deleted person: {name}")
    return f"### Person {name} deleted!\n{show_payment_record()}"


def exchange_currency(from_cur: str, amount: float) -> tuple[float, float]:
    """
    :param from_cur: base currency to convert from
    :param amount: amount to convert
    :return converted amount:
    :return exchange rate: 
    """
    amount = float(amount)
    if from_cur == UNIFIED_CURRENCY:
        return amount, 1.0
    to_cur = UNIFIED_CURRENCY
    currencies = to_cur + '%2C' + from_cur
    url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_RATE_API_KEY}&symbols={currencies}"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    rates = response.json().get('rates', {})
    rate = rates.get(to_cur, 0) / rates.get(from_cur, 1)
    return amount * rate, round(rate, EXCHANGE_RATE_ROUND_OFF_DP)


def synchronize_payment_records(users: list[str], timestamp) -> None:
    """ Synchronizes payment records with the Firestore
    :param users: List of user names
    """
    for user in users:
        firebase_queue.put({
            "type": "payment",
            "user": user,
            "balance": payment_records[user],
            "timestamp": timestamp
        })


def payment_handling(ppl_to_pay: str, ppl_get_paid: str, amount: float, timestamp) -> str:
    """ Performs the payment operation
    :param ppl_to_pay: The left user (payer)
    :param ppl_get_paid: The right user (payee)
    :param amount: The amount to be paid (unified currency)
    :return: A string indicating the result of the payment operation
    """
    def owe(person_to_pay: str, person_get_paid: str) -> str:
        """ Performs a single owe operation between two persons """
        if person_to_pay == person_get_paid:
            return ''
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
        pay_list = ppl_to_pay.split(',')
        paid_list = ppl_get_paid.split(',')
        for each_to_pay in pay_list:
            for each_get_paid in paid_list:
                update += owe(each_to_pay, None) + owe(None, each_get_paid)
                update += '\n' if len(paid_list) > 1 else ''
            update += '\n' if len(pay_list) > 1 else ''
        # update = update[:-3] + update[-3:][:update[-3:].index(">")] if ">" in update[-3:] else update
        synchronize_payment_records(pay_list + paid_list, timestamp)
        return update
    except KeyError:
        return B("ERROR: Person not found")


async def payment_system(bot, message, prev_input=None) -> None:
    """ Process the payment command and updates the payment records
    :param bot: The Discord bot instance
    :param msg: Command message from the user
    :param prev_input: A dictionary of previous input for edit functionality
    """    
    def parse_cmd_input() -> Union[dict, str]:
        """ Parses the command input from the user
        
        e.g. !pm p1,p2 owe p3 100 -cny sc reason 123
        
        :return: A dictionary containing parsed payment information or an error message
        """
        
        def parse_optional_args(args: List[str]) -> Union[Tuple[bool, str, str], bool]:
            """ Parses optional arguments from the command input
            :param args: List of optional arguments from the command input
            :return: A tuple containing service charge flag, currency, and reason, or False if invalid
            """
            service_charge = False
            currency: str = UNIFIED_CURRENCY
            reason = ''

            for i in range(len(args)):
                if i <= 1 and args[i].startswith('-'):
                    if args[i][1:].upper() not in SUPPORTED_CURRENCY.keys():
                        return False
                    currency = args[i][1:].upper()
                elif args[i] == "sc":
                    service_charge = True
                else:
                    reason += args[i] + " "

            return service_charge, currency, reason[:-1]

        # left users
        ppl_to_pay = msg[1].lower()
        if any(ppl not in user_list for ppl in ppl_to_pay.split(',')):
            return B("Invalid input for provider!")
        
        # operation
        operation = msg[2].lower()
        if operation not in ["owe", "payback"]:
            return B("Invalid payment operation!")
        operation_owe = operation == "owe"

        # right user
        ppl_get_paid = msg[3].lower()
        if ppl_get_paid not in user_list:
            return B("Invalid input for receiver!")
        if ppl_get_paid in ppl_to_pay.split(','):
            return B("Invalid input: one cannot owe himself!")

        # amount
        if not is_valid_amount(msg[4]):
            return B("Invalid amount!")
        try:
            amount: float = round(eval(amt_parser(msg[4])), ROUND_OFF_DP)
        except ZeroDivisionError:
            return B("Invalid amount: Don't divide zero la...")
        except (ValueError, SyntaxError):
            return B("What have you entered for the amount .-.")
        if amount == 0.0:
            return B("Invalid amount: amount cannot be zero!")

        # optional args
        parse_result = parse_optional_args(msg[5:])
        if not parse_result:
            return B("Invalid currency!")
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
    
    async def parse_ui_input() -> Union[dict, str]:
        """ Parses the user input from the UI
        :return: A dictionary containing parsed payment information or an error message
        """
        if prev_input is None:
            menu = InputView(user_list)
        else:
            ptp = prev_input["ppl_to_pay"]
            op = prev_input["operation_owe"]
            pgp = prev_input["ppl_get_paid"]
            amt = prev_input["amount"]
            sc = prev_input["service_charge"]
            cur = prev_input["currency"]
            reason = prev_input["reason"]
            menu = InputView(user_list, ptp, op, pgp, amt, sc, cur, reason)
        
        menu.update_description()
        menu.message = await message.send(view=menu, embed=menu.embed_text)
        await menu.wait()

        if menu.cancelled:
            return "Process cancelled!"
        if not menu.finished:
            return "**> Input closed. You take too long!**"

        return {
            "ppl_to_pay": menu.pay_text,
            "operation_owe": menu.owe,
            "ppl_get_paid": menu.paid_text,
            "amount": menu.amount_text,
            "service_charge": menu.service_charge,
            "currency": menu.currency,
            "reason": menu.reason
        }
    
    def process_amount(amount: str) -> float:
        """ Handles the amount input and converts it to a float
        :param amount: The amount input from the user
        :return: The actual amount and the exchange rate
        """
        actual_amount, exchange_rate = exchange_currency(currency, amount)
        actual_amount *= 1.1 if service_charge else 1
        actual_amount = round(actual_amount, ROUND_OFF_DP)
        return actual_amount, exchange_rate

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    msg = message.message.content.lower().split()
    cmd_input = len(msg) >= 5

    if cmd_input:
        parsed_input = parse_cmd_input()
    else:
        parsed_input = await parse_ui_input()

    if isinstance(parsed_input, str):  # error enountered
        await message.channel.send(B(parsed_input))
        return
    
    ppl_to_pay = parsed_input["ppl_to_pay"]
    operation_owe = parsed_input["operation_owe"]
    ppl_get_paid = parsed_input["ppl_get_paid"]
    amount = parsed_input["amount"]
    service_charge = parsed_input["service_charge"]
    currency = parsed_input["currency"]
    reason = parsed_input["reason"]
    
    actual_amount, exchange_rate = process_amount(amount)
    
    # Generate log content
    reason_text = (' ' + reason if reason[0] in '(（' and reason[-1] in '）)' else f' ({reason})') if reason else ''
    operation_text = "owe" if operation_owe else "pay back"
    currency_text = f" [{currency}(1) -> {UNIFIED_CURRENCY}({exchange_rate})]" \
        if currency != UNIFIED_CURRENCY else ''
    log_content = f"{message.author}: {ppl_to_pay} {operation_text} {ppl_get_paid} ${actual_amount}" \
                    f"{reason_text}{currency_text}"
                    
    # switch pay & paid for pay back operation
    if not operation_owe:
        ppl_to_pay, ppl_get_paid = ppl_get_paid, ppl_to_pay

    # perform the payment operation    
    msg_time = message.message.created_at.astimezone(TIMEZONE)
    update = payment_handling(ppl_to_pay, ppl_get_paid, actual_amount, msg_time)
    
    # response content
    user_mention = ' '.join([f'<@{USER_MAPPING.get(each)}>' for each in ppl_to_pay.split(',') + [ppl_get_paid]
                                 if USER_MAPPING.get(each)])
    user_mention = '\n-# ' + user_mention if user_mention else ''
    response_content = f"`{log_content}`{user_mention}\n-# Updated records:\n{update}"
    
    # send the UNDO view before time-consuming operations
    undo_view = UndoView(not cmd_input, response_content)
    undo_view.message = await message.send(view=undo_view, embed=undo_view.embed_text)
    
    await log_channel.send(log_content)
    log_ref = firebase_manager.write_log('payment', channel_to_text(message.channel), message.author.name, message.message.content,
                            msg_time, payers=ppl_to_pay, operation=operation_text,
                            payees=ppl_get_paid, amount=actual_amount, reason=reason_text, cancelled=False)
    
    await undo_view.wait()
    
    # handle undo operation
    if undo_view.undo and undo_view.edit:
        payment_handling(ppl_get_paid, ppl_to_pay, actual_amount, undo_view.cancelled_at.astimezone(TIMEZONE))
        await message.channel.send(B("Undo has been executed for editing!\n-# Loading new UI panel for editing..."))
        undo_log_content = f"{undo_view.undo_user}: __UNDO__ **[**{log_content}**]**"
        await log_channel.send(undo_log_content)
        firebase_manager.update_log(log_ref, cancelled=True)
        firebase_manager.write_log('manage', channel_to_text(message.channel), undo_view.undo_user, 'undo',
                  undo_view.cancelled_at.astimezone(TIMEZONE), cancelledRecord=log_content)
        await payment_system(bot, message, prev_input={
            'ppl_to_pay': ppl_to_pay,
            'operation_owe': operation_owe,
            'ppl_get_paid': ppl_get_paid,
            'amount': amount,
            'service_charge': service_charge,
            'currency': currency,
            'reason': reason
        })
    elif undo_view.undo:
        payment_handling(ppl_get_paid, ppl_to_pay, actual_amount, undo_view.cancelled_at.astimezone(TIMEZONE))
        await message.channel.send(B("Undo has been executed!"))
        undo_log_content = f"{undo_view.undo_user}: __UNDO__ **[**{log_content}**]**"
        await log_channel.send(undo_log_content)
        firebase_manager.update_log(log_ref, cancelled=True)
        firebase_manager.write_log('manage', channel_to_text(message.channel), undo_view.undo_user, 'undo',
                  undo_view.cancelled_at.astimezone(TIMEZONE), cancelledRecord=log_content)


def terminate_worker():
    """ Terminates the firebase worker thread """
    firebase_queue.put(None)
    firebase_queue.join()


payment_thread = threading.Thread(target=firebase_worker, daemon=False)
payment_thread.start()
