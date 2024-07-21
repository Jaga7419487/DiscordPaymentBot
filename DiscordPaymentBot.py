import time
import PMBotUI
import discord
from discord.ext import commands
from constants import *

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
- !create
This is used to create a new person in the payment record.
- !delete
This is used to delete a person (including his amount) in the payment record.
"""


def payment_record_to_dict() -> dict:
    payment_data = {CENTRALIZED_PERSON: -1}
    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            payment_data[record[0].lower()] = float(record[1])
    return payment_data


def write_log(message: str) -> None:
    with open(LOG_FILE, 'a', encoding="utf8") as file:
        file.write(message + "\n")


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
    return log_content


def read_last_log() -> list[str]:
    content = ""
    with open(LOG_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content = line
    return content.split()


def payment_record() -> str:
    zero = take_money = need_pay = centralized_person = ""
    count = 0.0

    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            count += float(record[1])
            if float(record[1]) == 0:
                zero += f"**{record[0]}** don\'t need to pay\n"
            elif float(record[1]) > 0:
                take_money += f"**{CENTRALIZED_PERSON}** needs to pay **{record[0]}** _${record[1]}_\n"
            else:
                need_pay += f"**{record[0]}** needs to pay **{CENTRALIZED_PERSON}** _${record[1][1:]}_\n"

        centralized_person = f"**{CENTRALIZED_PERSON}** {'needs to pay' if count > 0 else 'will receive'} " \
                             f"{abs(round(count, 3))} in total"

    payment_record_content = zero + "\n" + take_money + "\n" + need_pay + "\n" + centralized_person
    return payment_record_content


def create_ppl(name: str, amount=0.0) -> None:
    with open(PAYMENT_RECORD_FILE, 'a', encoding='utf8') as file:
        file.write(name + " " + str(amount) + "\n")


def delete_ppl(target: str) -> None:
    payment_data = {}

    with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as file:
        for line in file:
            record = line.split()
            payment_data[record[0].lower()] = record[1]

    try:
        del payment_data[target]
    except KeyError:
        print(f"{target} not found")

    with open(PAYMENT_RECORD_FILE, "w+", encoding='utf8') as file:
        for name, amount in payment_data.items():
            file.write(name + ' ' + amount + "\n")


def owe(payment_data: dict, person_to_pay: str, person_get_paid: str, amount: float) -> str:
    if person_to_pay == person_get_paid:
        return ""
    if person_to_pay == CENTRALIZED_PERSON:
        target = person_get_paid
        add = True
    elif person_get_paid == CENTRALIZED_PERSON:
        target = person_to_pay
        add = False
    else:
        write_log("funtion owe: centralized person not found")
        return ""

    original = payment_data[target]
    current = round(original + amount if add else original - amount, 3)
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
        return f"{CENTRALIZED_PERSON} needs to pay {target} ${original} -→ {target} doesn't need to pay\n"
    elif not p and c0:
        return f"{target} needs to pay {CENTRALIZED_PERSON} ${original} -→ {target} doesn't need to pay\n"
    elif p0 and c:
        return f"{CENTRALIZED_PERSON} needs to pay {target} ${current} (new record)\n"
    elif p0 and not c:
        return f"{target} needs to pay {CENTRALIZED_PERSON} ${current} (new record)\n"
    elif p and c:
        return f"{CENTRALIZED_PERSON} needs to pay {target}: ${original} -→ ${current}\n"
    elif not p and c:
        return f"{target} needs to pay {CENTRALIZED_PERSON} ${original} -→ " \
               f"{CENTRALIZED_PERSON} needs to pay {target} ${current}\n"
    elif p and not c:
        return f"{CENTRALIZED_PERSON} needs to pay {target} ${original} -→ " \
               f"{target} needs to pay {CENTRALIZED_PERSON} ${current}\n"
    else:
        return f"{target} needs to pay {CENTRALIZED_PERSON}: ${original} -→ ${current}\n"


def payment_handling(ppl_to_pay: str, ppl_get_paid: str, amount: float) -> str:
    update = ""
    payment_data = payment_record_to_dict()
    del payment_data[CENTRALIZED_PERSON]

    # main logic
    try:
        for each_to_pay in ppl_to_pay.split(','):
            for each_get_paid in ppl_get_paid.split(','):
                if each_get_paid == CENTRALIZED_PERSON:
                    update += owe(payment_data, each_to_pay, CENTRALIZED_PERSON, amount)
                elif each_to_pay == CENTRALIZED_PERSON:
                    update += owe(payment_data, CENTRALIZED_PERSON, each_get_paid, amount)
                else:
                    update += owe(payment_data, each_to_pay, CENTRALIZED_PERSON, amount) + \
                              owe(payment_data, CENTRALIZED_PERSON, each_get_paid, amount)
            update += "\n"
    except KeyError:
        print("Person not found.")
        return ""

    with open(PAYMENT_RECORD_FILE, "w+", encoding='utf8') as file:
        for name, amount in payment_data.items():
            file.write(name + ' ' + str(amount) + '\n')

    return update


def do_backup() -> None:
    with open(BACKUP_FILE, 'a', encoding='utf8') as bkup_file:
        bkup_file.write('[' + time.strftime('%Y-%m-%d %H:%M') + "]\n")
        with open(PAYMENT_RECORD_FILE, 'r', encoding='utf8') as pm_file:
            for line in pm_file:
                bkup_file.write(line)
        bkup_file.write("\n")


def show_backup() -> str:
    content = ""
    with open(BACKUP_FILE, 'r', encoding='utf8') as file:
        for line in file:
            content += line
    return content


def run():
    '''
        @bot.event
        async def on_message(message):
            if message.author == bot.user:  # avoid infinite calling itself
                return

            msg = message.content.lower().split()
            if len(msg) == 0:
                return

            if msg[0] != COMMAND:
                return

            if len(msg) == 1:
                await message.channel.send("gan man 18 sui ~~~")
                return

            if msg[1] == "help":
                await message.channel.send(BOT_DESCRIPTION)
                return

            if msg[1] == "list":
                await message.channel.send(payment_record())
                return

            if msg[1] == "total":
                await message.channel.send(total_amount())
                return

            if msg[1] == "log":
                await message.channel.send(show_log())
                return

            if msg[1] == "backup":
                if len(msg) >= 3 and msg[2] == "do":
                    do_backup()
                    write_log(f"\n----------backup: [{time.ctime(time.time())}]----------")
                    await message.channel.send("Backup done")
                await message.channel.send(show_backup())
                return

            if len(msg) >= 3 and msg[1] == "delete":
                delete_ppl(msg[20])
                await message.channel.send(f"{msg[2]} successfully deleted!")
                await message.channel.send("\n\nUpdated payment:\n" + payment_record())
                write_log(message.author + ": " + message.content)
                write_log(f"{message.author}: {message.content}")

            if len(msg) >= 3 and msg[1] == "create":
                create_ppl(msg[2])
                await message.channel.send(f"{msg[2]} successfully created!")
                await message.channel.send("\n\nUpdated payment:\n" + payment_record())
                write_log(f"{message.author}: {message.content}")

            if len(msg) >= 5 and msg[2] == "owe":  # msg[1] owe msg[3] msg[4]
                """ avg logic: fuc up FUCKKKKKKKKKKKKKKKKKKKK
                if len(msg) >= 6 and msg[5] == "avg":
                    payment_handling(msg[1], msg[3], round(float(msg[4])/len(msg[3].split(',')), 3))
                else:
                    payment_handling(msg[1], msg[3], float(msg[4]))
                    await message.channel.send("Payment record successfully updated!")
                    await message.channel.send("\n\nUpdated payment:\n" + payment_record())
                """
                try:
                    if float(msg[4]):
                        pass
                except ValueError:
                    await message.channel.send("Entered amount not a number")
                    return

                write_log(f"{message.author}: {message.content}")
                update = payment_handling(msg[1], msg[3], float(msg[4]))

                if update:
                    await message.channel.send("Payment record successfully updated!\n")
                    await message.channel.send(update)
                else:
                    await message.channel.send("Person not found")
                    write_log("-----ERROR: Person not found-----")
        '''

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command()
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list")
    async def show(message: commands.Context):
        await message.channel.send(payment_record())

    @bot.command()
    async def log(message: commands.Context):
        await message.channel.send(show_log(LOG_SHOW_NUMBER))

    @bot.command()
    async def logall(message: commands.Context):
        await message.channel.send(show_log())

    @bot.command()
    async def backup(message: commands.Context):
        do_backup()
        write_log(f"\n---------------backup: [{time.strftime('%Y-%m-%d %H:%M')}]---------------")
        await message.channel.send("Backup done")
        await message.channel.send(show_backup())

    @bot.command()
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command()
    async def create(message: commands.Context):
        await message.channel.send("Oh no, lazy Jaga hasn't done this part")

    @bot.command()
    async def delete(message: commands.Context):
        await message.channel.send("Oh no, lazy Jaga hasn't done this part")

    @bot.command()
    async def pm(message: commands.Context):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        payment_data = payment_record_to_dict()

        reason = None

        msg: list[str] = message.message.content.lower().split()
        if len(msg) >= 5:
            # command line UI (e.g. !pm p1,p2 owe p3,p4 100 (reason))

            # fetching and check inputs

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

            try:
                amount = float(msg[4])
                if amount == 0.0:
                    await message.channel.send("**Invalid amount: amount cannot be zero!**")
                    return
            except ValueError:
                await message.channel.send("**Invalid input for amount!**")
                return

            if len(msg) > 5:
                reason = " ".join(msg[5:])
            else:
                reason = ""

            if ppl_get_paid in ppl_to_pay.split(','):
                await message.channel.send("**Invalid input: one cannot pay himself!**")
                return

        else:
            # graphic UI
            menu = PMBotUI.View(payment_data)
            menu.message = await message.send(view=menu)
            await menu.wait()

            ppl_to_pay = menu.pay_text
            operation_owe = menu.owe
            ppl_get_paid = menu.paid_text
            amount = menu.amount_text
            reason = menu.reason if menu.reason else ""

            if menu.cancelled:
                return
            if not menu.finished:
                await message.channel.send("**> Input closed. You take too long!**")
                return

        # log the record
        log_content = f"{message.author}: {ppl_to_pay} " \
                      f"{'owe' if operation_owe else 'pay back'} {ppl_get_paid} {amount} {reason}"
        write_log(log_content)
        await log_channel.send(log_content)

        # switch pay & paid for pay back operation
        if not operation_owe:
            temp = ppl_to_pay
            ppl_to_pay = ppl_get_paid
            ppl_get_paid = temp

        # perform the payment operation
        update = payment_handling(ppl_to_pay, ppl_get_paid, float(amount))

        # error occurred
        if not update:
            await message.channel.send("**ERROR: Payment handling failed**")
            return

        await message.channel.send("**Payment record successfully updated!**\n")
        await message.channel.send("Updated records:\n" + update)

        undo_view = PMBotUI.UndoView()
        undo_view.message = await message.send(view=undo_view)
        await undo_view.wait()

        # handle undo operation
        if undo_view.undo:
            undo_update = "Updated records:\n"
            undo_update += payment_handling(ppl_get_paid, ppl_to_pay, float(amount))
            await message.channel.send("**Undo has been executed!**")
            await message.channel.send(undo_update)
            undo_log_content = f"{message.author}: undo **[**{log_content}**]**"
            write_log(undo_log_content)
            await log_channel.send(undo_log_content)

    bot.run(BOT_KEY)


if __name__ == '__main__':
    run()
