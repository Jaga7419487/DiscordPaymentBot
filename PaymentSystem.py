import json
import queue
import threading
from datetime import datetime
from typing import List, Tuple, Union

import pandas as pd
import pygsheets
import requests
from discord.ext import commands
from google.oauth2 import service_account
from googleapiclient.discovery import build

from PaymentSystemUI import InputView, UndoView, is_valid_amount, amt_parser
from constants import *

log_queue = queue.Queue()
payment_queue = queue.Queue()


def get_document_content(document_id, n=-1) -> str:
    """
    Returns the content of a Google Document.
    If n == -1, returns all the lines.
    Otherwise, returns the last n lines.
    Ignores empty lines/spaces. If the document is empty, returns 'No content'.
    """
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    docs_service = build('docs', 'v1', credentials=credentials)
    document = docs_service.documents().get(documentId=document_id).execute()

    # Extract the full text content
    content = ''
    for element in document.get('body', {}).get('content', []):
        paragraph = element.get('paragraph')
        if paragraph:
            for text_run in paragraph.get('elements', []):
                text = text_run.get('textRun', {}).get('content', '')
                content += text

    # Remove empty lines or spaces
    lines = [line.strip() for line in content.split("\n")]

    # If the document is empty
    if not lines:
        return "No content"

    return '\n'.join(lines if n < 0 else lines[-n - 2:])


def write_doc(document_id, text_to_append):
    """
    Appends text to the end of a Google Document.
    """
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    docs_service = build('docs', 'v1', credentials=credentials)
    document = docs_service.documents().get(documentId=document_id).execute()
    end_index = document.get('body', {}).get('content', [])[-1].get('endIndex', 1)

    # Create the request to append text at the end index
    doc_requests = [
        {
            "insertText": {
                "location": {
                    "index": end_index - 1  # Subtract 1 to avoid appending after the implicit newline
                },
                "text": text_to_append
            }
        }
    ]

    # Execute the batchUpdate with the request
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": doc_requests}
    ).execute()


def wks_to_dict(wks: pygsheets.Worksheet) -> dict:
    df = wks.get_as_df()
    if df.empty:
        return {}
    record_dict = df.set_index(df['Name'].astype(str))['Amount'].to_dict()
    if '' in record_dict.keys():
        del record_dict['']
    return record_dict


def payment_to_wks(wks: pygsheets.Worksheet) -> None:
    record = read_payment_from_json()
    if not record:
        return
    wks.clear()
    df = pd.DataFrame(list(record.items()), columns=['Name', 'Amount'])
    wks.set_dataframe(df, 'A1')


def payment_to_json(record: dict) -> None:
    with open(PAYMENT_RECORD_FILE, 'w') as json_file:
        json.dump(record, json_file, indent=2)
    payment_queue.put(record)  # Update the worksheet


def read_payment_from_json() -> dict:
    with open(PAYMENT_RECORD_FILE, 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            print('Empty payment record file')
            return {}
    return data


def payment_worker(wks: pygsheets.Worksheet, stop_event: threading.Event):
    while not stop_event.is_set() or not payment_queue.empty():
        try:
            msg = payment_queue.get(timeout=1)
        except queue.Empty:
            continue  # Check stop_event again if no message was available
        if msg is None:
            break
        payment_to_wks(wks)
        payment_queue.task_done()


def log_worker(stop_event: threading.Event):
    while not stop_event.is_set() or not log_queue.empty():
        try:
            msg = log_queue.get(timeout=1)
        except queue.Empty:
            continue  # Check stop_event again if no message was available
        if msg is None:
            break
        current_time = datetime.now(TIMEZONE)
        write_doc(LOG_DOC_ID, f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        log_queue.task_done()


def show_log(num: int = -1) -> str:
    return get_document_content(LOG_DOC_ID, num)


def payment_record() -> str:
    zero = take_money = need_pay = ""
    count = 0.0

    record_dict = read_payment_from_json()
    centralized_person_name = CENTRALIZED_PERSON
    for name, amount in record_dict.items():
        count += amount
        if amount == 0:
            zero += f"**{name}** don\'t need to pay\n"
        elif amount > 0:
            take_money += f"**{centralized_person_name}** needs to pay **{name}** _${amount}_\n"
        else:
            need_pay += f"**{name}** needs to pay **{centralized_person_name}** _${abs(amount)}_\n"

    centralized_person_text = f"**{centralized_person_name}** "
    centralized_person_text += "doesn't need to pay" if count == 0 else \
        f"{'needs to pay' if count > 0 else 'will receive'} ${abs(round(count, 3))} in total"

    zero = zero + "\n" if zero else zero
    take_money = take_money + "\n" if take_money else take_money
    need_pay = need_pay + "\n" if need_pay else need_pay

    payment_record_content = zero + take_money + need_pay + centralized_person_text
    return payment_record_content


def create_ppl(name: str, author: str) -> bool:
    try:
        record_dict = read_payment_from_json()
        if name not in record_dict.keys() and name != CENTRALIZED_PERSON:
            record_dict[name.lower()] = 0.0
            payment_to_json(record_dict)
            log_queue.put(f"{author}: Created new person: {name}")
            return True
    except Exception as e:
        print(e)
    return False


def delete_ppl(target: str, author: str) -> bool:
    try:
        record_dict = read_payment_from_json()
        if target in record_dict.keys() and record_dict[target] == 0:
            del record_dict[target]
            payment_to_json(record_dict)
            log_queue.put(f"{author}: Deleted person: {target}")
            return True
    except Exception as e:
        print(e)
    return False


def payment_handling(ppl_to_pay: str, ppl_get_paid: str, amount: float) -> str:
    def owe(person_to_pay: str, person_get_paid: str, amount: float) -> str:
        if person_to_pay == person_get_paid:
            return ""
        if person_to_pay == CENTRALIZED_PERSON:
            target = person_get_paid
            add = True
        elif person_get_paid == CENTRALIZED_PERSON:
            target = person_to_pay
            add = False
        else:
            raise Exception("Centralized person not found.")  # should not happen

        original = payment_data[target]
        current = round(original + amount if add else original - amount, ROUND_OFF_DP)
        payment_data[target] = current

        p = original > 0
        p0 = original == 0
        c = current > 0
        c0 = current == 0

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

        # readability pro max!!!
        if p and c0:
            return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${original} → {target} doesn't need to pay\n"
        elif not p and c0:
            return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${original} → {target} doesn't need to pay\n"
        elif p0 and c:
            return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${current} (new record)\n"
        elif p0 and not c:
            return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${current} (new record)\n"
        elif p and c:
            return f"> -# {CENTRALIZED_PERSON} needs to pay {target}: ${original} → ${current}\n"
        elif not p and c:
            return f"> -# {target} needs to pay {CENTRALIZED_PERSON} ${original} → " \
                   f"{CENTRALIZED_PERSON} needs to pay {target} ${current}\n"
        elif p and not c:
            return f"> -# {CENTRALIZED_PERSON} needs to pay {target} ${original} → " \
                   f"{target} needs to pay {CENTRALIZED_PERSON} ${current}\n"
        else:
            return f"> -# {target} needs to pay {CENTRALIZED_PERSON}: ${original} → ${current}\n"

    update = ""
    payment_data = read_payment_from_json()

    # main logic
    try:
        pay_list = ppl_to_pay.split(',')
        paid_list = ppl_get_paid.split(',')
        for each_to_pay in pay_list:
            for each_get_paid in paid_list:
                if each_get_paid == CENTRALIZED_PERSON:
                    update += owe(each_to_pay, CENTRALIZED_PERSON, amount)
                elif each_to_pay == CENTRALIZED_PERSON:
                    update += owe(CENTRALIZED_PERSON, each_get_paid, amount)
                else:
                    update += owe(each_to_pay, CENTRALIZED_PERSON, amount) + \
                              owe(CENTRALIZED_PERSON, each_get_paid, amount)
                update += "> \n" if len(paid_list) > 1 else ""
            update += "> \n" if len(pay_list) > 1 else ""
        if ">" in update[-3:]:
            update = update[:-3] + update[-3:][:update[-3:].index(">")]
    except KeyError:
        print("Person not found.")
        return ""

    payment_to_json(payment_data)
    return update


def do_backup() -> str:
    current_time = datetime.now(TIMEZONE)
    backup_text = f"[{current_time.strftime('%Y-%m-%d %H:%M')}]\n"
    for name, amount in read_payment_from_json().items():
        backup_text += f"{name} {amount}\n"
    backup_text += "\n"
    write_doc(BACKUP_DOC_ID, backup_text)
    log_queue.put("-------------------------------------Backup-------------------------------------")
    return backup_text


def show_backup() -> str:
    return get_document_content(BACKUP_DOC_ID).split("\n\n")[-2]


async def payment_system(bot: commands.Bot, message: commands.Context, wks: pygsheets.Worksheet, avg=False):
    def parse_optional_args(args: List[str]) -> Union[Tuple[bool, str, str], bool]:
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

    def exchange_currency(from_cur: str, amount: float) -> tuple[float, float]:
        """
        :param from_cur: base currency to convert from
        :param amount: amount to convert
        :return: tuple of converted amount and exchange rate
        """
        if from_cur == UNIFIED_CURRENCY:
            return float(amount), 1.0
        to_cur = UNIFIED_CURRENCY
        url = f"https://marketdata.tradermade.com/api/v1/convert?api_key={TRADER_MADE_API_KEY}&" \
              f"from={from_cur}&to={to_cur}&amount={amount}"
        response = requests.get(url)
        data = response.json()
        return data['total'], data['quote']

    def parse_cmd_input(msg: list[str]):
        """ e.g. !pm p1,p2 owe p3 100 -cny sc rea son 123 """

        if len(msg) < 5:
            return ''

        ppl_to_pay = msg[1].lower()
        if any(ppl not in payment_list for ppl in ppl_to_pay.split(',')):
            return "**Invalid input for provider!**"

        operation = msg[2].lower()
        if operation not in ["owe", "payback"]:
            return "**Invalid payment operation!**"
        operation_owe = operation == "owe"

        ppl_get_paid = msg[3].lower()
        if ppl_get_paid not in payment_list:
            return "**Invalid input for receiver!**"

        if not is_valid_amount(msg[4]):
            return "**Invalid amount!**"
        try:
            amount: float = eval(amt_parser(msg[4]))
        except ZeroDivisionError:
            return "**Invalid amount: Don't divide zero la...**"
        except (ValueError, SyntaxError):
            return "**What have you entered for the amount .-.**"
        if amount == 0.0:
            return "**Invalid amount: amount cannot be zero!**"

        parse_result = parse_optional_args(msg[5:])
        if not parse_result:
            return "**Invalid currency!**"
        service_charge, currency, reason = parse_result

        if ppl_get_paid in ppl_to_pay.split(','):
            return "**Invalid input: one cannot pay himself!**"

        return {
            "ppl_to_pay": ppl_to_pay,
            "operation_owe": operation_owe,
            "ppl_get_paid": ppl_get_paid,
            "amount": amount,
            "service_charge": service_charge,
            "currency": currency,
            "reason": reason
        }

    async def parse_ui_input(prev_ptp, prev_op, prev_pgp, prev_amt, prev_sc, prev_cur, prev_reason):
        menu = InputView(payment_list, prev_ptp, prev_op, prev_pgp, prev_amt, prev_sc, prev_cur, prev_reason) \
            if prev_ptp else InputView(payment_list)
        menu.message = await message.send(view=menu)
        await menu.wait()

        if menu.cancelled:
            return ''
        if not menu.finished:
            return "**> Input closed. You take too long!**"

        return {
            "ppl_to_pay": menu.pay_text,
            "operation_owe": menu.owe,
            "ppl_get_paid": menu.paid_text,
            "amount": menu.amount_text,
            "service_charge": menu.service_charge,
            "currency": menu.currency if menu.currency else UNIFIED_CURRENCY,
            "reason": menu.reason if menu.reason else ""
        }

    async def handle_payment(prev_ptp: str = '', prev_op: str = '', prev_pgp: str = '', prev_amt: str = '',
                             prev_sc: bool = False, prev_cur: str = '', prev_reason: str = '') -> None:
        msg = message.message.content.lower().split()
        cmd_input = len(msg) >= 5

        if cmd_input:
            parsed_input = parse_cmd_input(msg)
        else:
            parsed_input = await parse_ui_input(prev_ptp, prev_op, prev_pgp, prev_amt, prev_sc, prev_cur, prev_reason)

        if isinstance(parsed_input, str) and parsed_input:
            await message.channel.send(f"**{parsed_input}**")
            return

        ppl_to_pay = parsed_input["ppl_to_pay"]
        operation_owe = parsed_input["operation_owe"]
        ppl_get_paid = parsed_input["ppl_get_paid"]
        amount = parsed_input["amount"]
        service_charge = parsed_input["service_charge"]
        currency = parsed_input["currency"]
        reason = parsed_input["reason"]

        """ amount -> actual_amount: float"""
        actual_amount, exchange_rate = exchange_currency(currency, amount)
        actual_amount *= 1.1 if service_charge else 1
        actual_amount /= (len(ppl_to_pay.split(',')) + 1) if avg else 1
        actual_amount = round(actual_amount, ROUND_OFF_DP)

        reason_text = (' ' + reason if reason[0] in '(（' and reason[-1] in '）)' else f' ({reason})') if reason else ''
        operation_text = "owe" if operation_owe else "pay back"
        currency_text = f" [{currency}({exchange_rate}) -> {UNIFIED_CURRENCY}(1)]" \
            if currency != UNIFIED_CURRENCY else ''
        log_content = f"{message.author}: {ppl_to_pay} {operation_text} {ppl_get_paid} ${actual_amount}" \
                      f"{reason_text}{currency_text}"

        # switch pay & paid for pay back operation
        if not operation_owe:
            ppl_to_pay, ppl_get_paid = ppl_get_paid, ppl_to_pay

        # perform the payment operation
        update = payment_handling(ppl_to_pay, ppl_get_paid, actual_amount)
        if not update:
            await message.channel.send("**ERROR: Payment handling failed**")
            return

        user_mention = ' '.join([f'<@{USER_MAPPING.get(each)}>' for each in ppl_to_pay.split(',') + [ppl_get_paid]
                                 if USER_MAPPING.get(each)])
        user_mention = '\n-# ' + user_mention if user_mention else ''

        await message.channel.send(f"__**Payment record successfully updated!**__\n`{log_content}`{user_mention}"
                                   f"\n> -# Updated records:\n{update}")
        await log_channel.send(log_content)
        log_queue.put(log_content)

        undo_view = UndoView(not cmd_input)
        undo_view.message = await message.send(view=undo_view)

        await undo_view.wait()

        # handle undo operation
        if undo_view.undo and undo_view.edit:
            undo_update = "> -# Updated records:\n" + payment_handling(ppl_get_paid, ppl_to_pay, actual_amount)
            await message.channel.send("**Undo has been executed for editing!**\n")
            undo_log_content = f"{message.author}: __UNDO__ **[**{log_content}**]**"
            log_queue.put(undo_log_content)
            await log_channel.send(undo_log_content)
            await handle_payment(ppl_to_pay, operation_owe, ppl_get_paid, amount, service_charge, currency,
                                 reason)
        elif undo_view.undo:
            undo_update = "> -# Updated records:\n" + payment_handling(ppl_get_paid, ppl_to_pay, actual_amount)
            await message.channel.send("**Undo has been executed!**\n")
            undo_log_content = f"{message.author}: __UNDO__ **[**{log_content}**]**"
            log_queue.put(undo_log_content)
            await log_channel.send(undo_log_content)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    payment_data = read_payment_from_json()
    payment_list = [CENTRALIZED_PERSON] + list(payment_data.keys())

    await handle_payment()
