import os
import time

import pandas as pd
import pygsheets
import requests
from discord.ext import commands
from dotenv import load_dotenv

from PaymentSystemUI import InputView, UndoView, is_valid_amount, amt_parser
from constants import *

load_dotenv()


def payment_record_to_dict(wks: pygsheets.Worksheet) -> dict:
    df = wks.get_as_df()
    record_dict = df.set_index(df['Name'].astype(str))['Amount'].to_dict()
    if '' in record_dict.keys():
        del record_dict['']
    return record_dict


def write_payment_record(wks: pygsheets.Worksheet, record: dict) -> None:
    wks.clear()
    df = pd.DataFrame(list(record.items()), columns=['Name', 'Amount'])
    wks.set_dataframe(df, 'A1')


def write_log(message: str) -> None:
    with open(LOG_FILE, 'a', encoding="utf8") as file:
        file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def show_log(num: int = -1) -> str:
    log_content = ""
    log_lines = []

    with open(LOG_FILE, 'r', encoding='utf8') as file:
        show_num = num if num > 1 else DEFAULT_LOG_SHOW_NUMBER
        for line in file:
            log_lines.append(line)
        for line in log_lines[-min(show_num, len(log_lines)):]:
            if log_content == "":
                if line != "\n":
                    log_content = line
            else:
                log_content += line
    return log_content if log_content else "No log found"


def read_last_log() -> list[str]:
    content = ""
    with open(LOG_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content = line
    return content.split()


def payment_record(wks: pygsheets.Worksheet) -> str:
    zero = take_money = need_pay = ""
    count = 0.0

    record_dict = payment_record_to_dict(wks)
    centralized_person_name = os.getenv('CENTRALIZED_PERSON')
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


def create_ppl(name: str, author: str, wks: pygsheets.Worksheet) -> bool:
    try:
        record_dict = payment_record_to_dict(wks)
        if name not in record_dict.keys() and name != os.getenv('CENTRALIZED_PERSON'):
            record_dict[name.lower()] = 0.0
            write_payment_record(wks, record_dict)
            write_log(f"{author}: Created new person: {name}")
            return True
    except Exception as e:
        print(e)
    return False


def delete_ppl(target: str, author: str, wks: pygsheets.Worksheet) -> bool:
    try:
        record_dict = payment_record_to_dict(wks)
        if target in record_dict.keys() and record_dict[target] == 0:
            del record_dict[target]
            write_payment_record(wks, record_dict)
            write_log(f"{author}: Deleted person: {target}")
            return True
    except Exception as e:
        print(e)
    return False


def owe(payment_data: dict, person_to_pay: str, person_get_paid: str, amount: float) -> str:
    if person_to_pay == person_get_paid:
        return ""
    if person_to_pay == os.getenv('CENTRALIZED_PERSON'):
        target = person_get_paid
        add = True
    elif person_get_paid == os.getenv('CENTRALIZED_PERSON'):
        target = person_to_pay
        add = False
    else:
        write_log("function owe: centralized person not found")
        return ""

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
        return f"> -# {os.getenv('CENTRALIZED_PERSON')} needs to pay {target} ${original} -→ {target} doesn't need to pay\n"
    elif not p and c0:
        return f"> -# {target} needs to pay {os.getenv('CENTRALIZED_PERSON')} ${original} -→ {target} doesn't need to pay\n"
    elif p0 and c:
        return f"> -# {os.getenv('CENTRALIZED_PERSON')} needs to pay {target} ${current} (new record)\n"
    elif p0 and not c:
        return f"> -# {target} needs to pay {os.getenv('CENTRALIZED_PERSON')} ${current} (new record)\n"
    elif p and c:
        return f"> -# {os.getenv('CENTRALIZED_PERSON')} needs to pay {target}: ${original} -→ ${current}\n"
    elif not p and c:
        return f"> -# {target} needs to pay {os.getenv('CENTRALIZED_PERSON')} ${original} -→ " \
               f"{os.getenv('CENTRALIZED_PERSON')} needs to pay {target} ${current}\n"
    elif p and not c:
        return f"> -# {os.getenv('CENTRALIZED_PERSON')} needs to pay {target} ${original} -→ " \
               f"{target} needs to pay {os.getenv('CENTRALIZED_PERSON')} ${current}\n"
    else:
        return f"> -# {target} needs to pay {os.getenv('CENTRALIZED_PERSON')}: ${original} -→ ${current}\n"


def payment_handling(ppl_to_pay: str, ppl_get_paid: str, amount: float, wks: pygsheets.Worksheet) -> str:
    update = ""
    payment_data = payment_record_to_dict(wks)
    centralized_person = os.getenv('CENTRALIZED_PERSON')

    # main logic
    try:
        pay_list = ppl_to_pay.split(',')
        paid_list = ppl_get_paid.split(',')
        for each_to_pay in pay_list:
            for each_get_paid in paid_list:
                if each_get_paid == centralized_person:
                    update += owe(payment_data, each_to_pay, centralized_person, amount)
                elif each_to_pay == centralized_person:
                    update += owe(payment_data, centralized_person, each_get_paid, amount)
                else:
                    update += owe(payment_data, each_to_pay, centralized_person, amount) + \
                              owe(payment_data, centralized_person, each_get_paid, amount)
                update += "> \n" if len(paid_list) > 1 else ""
            update += "> \n" if len(pay_list) > 1 else ""
        if ">" in update[-3:]:
            update = update[:-3] + update[-3:][:update[-3:].index(">")]
    except KeyError:
        print("Person not found.")
        return ""

    write_payment_record(wks, payment_data)
    return update


def do_backup(wks: pygsheets.Worksheet) -> None:
    with open(BACKUP_FILE, 'w', encoding='utf8') as bkup_file:
        bkup_file.write(f"[{time.strftime('%Y-%m-%d %H:%M')}]\n")
        for name, amount in payment_record_to_dict(wks).items():
            bkup_file.write(f"{name} {amount}\n")
        bkup_file.write("\n")
    write_log(f"-------------------------------------Backup-------------------------------------")


def show_backup() -> str:
    content = ""
    with open(BACKUP_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content += line
    return content


def parse_optional_args(args: list[str]) -> tuple[bool, bool, [str]] or False:
    service_charge = False
    currency = UNIFIED_CURRENCY
    reason = ""

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


def exchange_currency(from_cur: str, amount: str) -> tuple[float, float]:
    """
    :param from_cur: base currency to convert from
    :param amount: amount to convert
    :return: tuple of converted amount and exchange rate
    """
    to_cur = 'HKD'
    url = f"https://marketdata.tradermade.com/api/v1/convert?api_key={os.getenv('TRADER_MADE_API_KEY')}&" \
          f"from={from_cur}&to={to_cur}&amount={amount}"
    response = requests.get(url)
    data = response.json()
    return data['total'], data['quote']


async def payment_system(bot: commands.Bot, message: commands.Context, wks: pygsheets.Worksheet, avg=False):
    async def single_pm(prev: [str or bool] = None):
        menu = None
        msg: list[str] = message.message.content.lower().split()

        if len(msg) >= 5:
            # Command line UI: e.g. !pm p1,p2 owe p3,p4 100 -CNY (reason)
            cmd_input = True

            ppl_to_pay: str = msg[1].lower()
            for ppl in ppl_to_pay.split(','):
                if ppl not in payment_data.keys().__str__().lower():
                    await message.channel.send("**Invalid input for provider!**")
                    return

            operation: str = msg[2].lower()
            if operation not in ["owe", "payback"]:
                await message.channel.send("**Invalid payment operation!**")
                return
            else:
                operation_owe = operation == "owe"

            ppl_get_paid: str = msg[3].lower()
            if ppl_get_paid not in payment_data.keys().__str__().lower():
                await message.channel.send("**Invalid input for receiver!**")
                return

            if is_valid_amount(msg[4]):
                try:
                    amount = eval(amt_parser(msg[4]))
                except ZeroDivisionError:
                    await message.channel.send("**Invalid amount: Don't divide zero la...**")
                    return
                except ValueError:
                    await message.channel.send("**What have you entered for the amount .-.**")
                    return
            else:
                await message.channel.send("**Invalid amount!**")
                return
            if amount == 0.0:
                await message.channel.send("**Invalid amount: amount cannot be zero!**")
                return
            amount = str(amount)

            # try:
            #     amount = float(msg[4])
            #     if amount == 0.0:
            #         await message.channel.send("**Invalid amount: amount cannot be zero!**")
            #         return
            #     amount = str(amount)
            # except ValueError:
            #     await message.channel.send("**Invalid input for amount!**")
            #     return

            parse_result = parse_optional_args(msg[5:])
            if not parse_result:
                await message.channel.send("**Invalid currency!**")
                return
            service_charge, currency, reason = parse_result

            if ppl_get_paid in ppl_to_pay.split(','):
                await message.channel.send("**Invalid input: one cannot pay himself!**")
                return

        else:
            # Graphic UI
            cmd_input = False

            menu = InputView(payment_data, prev[0], prev[1], prev[2], prev[3], prev[4], prev[5], prev[6]) \
                if prev else InputView(payment_data)
            menu.message = await message.send(view=menu)
            await menu.wait()

            ppl_to_pay = menu.pay_text
            operation_owe = menu.owe
            ppl_get_paid = menu.paid_text
            amount = menu.amount_text
            service_charge = menu.service_charge
            currency = menu.currency if menu.currency else UNIFIED_CURRENCY
            reason = menu.reason if menu.reason else ""

            if menu.cancelled:
                return
            if not menu.finished:
                await message.channel.send("**> Input closed. You take too long!**")
                return

        """ amount: float"""
        if currency != UNIFIED_CURRENCY and currency in SUPPORTED_CURRENCY.keys():
            amount, exchange_rate = exchange_currency(currency, amount)
        else:
            amount = float(amount)
            exchange_rate = 1.0

        amount *= 1.1 if service_charge else 1
        amount /= (len(ppl_to_pay.split(',')) + 1) if avg else 1
        amount = round(amount, ROUND_OFF_DP)

        if reason:
            if reason[0] in '(（' and reason[-1] in '）)':
                reason_text = ' ' + reason
            else:
                reason_text = ' (' + reason + ')'
        else:
            reason_text = ''
        operation_text = "owe" if operation_owe else "pay back"
        currency_text = f" [{currency}({exchange_rate}) -> HKD(1)]" if currency != UNIFIED_CURRENCY else ""
        log_content = f"{message.author}: {ppl_to_pay} {operation_text} {ppl_get_paid} ${amount}" \
                      f"{reason_text}{currency_text}"

        # switch pay & paid for pay back operation
        if not operation_owe:
            temp = ppl_to_pay
            ppl_to_pay = ppl_get_paid
            ppl_get_paid = temp

        # perform the payment operation
        update = payment_handling(ppl_to_pay, ppl_get_paid, amount, wks)
        if not update:
            await message.channel.send("**ERROR: Payment handling failed**")
            return

        # log the record
        user_mention = ' '.join([f'<@{USER_MAPPING.get(each)}>' for each in ppl_to_pay.split(',') + [ppl_get_paid]
                                 if USER_MAPPING.get(each)])
        user_mention = '\n-# ' + user_mention if user_mention else ''
        write_log(log_content)
        await log_channel.send(log_content)
        await message.channel.send(f"__**Payment record successfully updated!**__\n`{log_content}`{user_mention}"
                                   f"\n> -# Updated records:\n{update}")

        undo_view = UndoView(not cmd_input)
        undo_view.message = await message.send(view=undo_view)

        await undo_view.wait()

        # handle undo operation
        if undo_view.undo and undo_view.edit:
            undo_update = "> -# Updated records:\n"
            undo_update += payment_handling(ppl_get_paid, ppl_to_pay, amount, wks)
            await message.channel.send("**Undo has been executed for editing!**\n")
            undo_log_content = f"{message.author}: __UNDO__ **[**{log_content}**]**"
            write_log(undo_log_content)
            await log_channel.send(undo_log_content)
            await single_pm(
                [ppl_to_pay, operation_owe, ppl_get_paid, menu.amount_text, service_charge, currency, menu.reason])
        elif undo_view.undo:
            undo_update = "> -# Updated records:\n"
            undo_update += payment_handling(ppl_get_paid, ppl_to_pay, amount, wks)
            await message.channel.send("**Undo has been executed!**\n")
            undo_log_content = f"{message.author}: __UNDO__ **[**{log_content}**]**"
            write_log(undo_log_content)
            await log_channel.send(undo_log_content)

    log_channel = bot.get_channel(int(os.getenv('LOG_CHANNEL_ID')))
    payment_data = {os.getenv('CENTRALIZED_PERSON'): -1}
    payment_data.update(payment_record_to_dict(wks))

    # for each_pm in message.message.content.split('\n'):
    #     if each_pm:
    #         await single_pm()
    await single_pm()
