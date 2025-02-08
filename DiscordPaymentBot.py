import json
import threading
import time

import discord
import pygsheets
from discord.ext import commands
from flask import Flask, send_from_directory

from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system, \
    wks_to_dict, payment_to_wks
from constants import *

app = Flask(__name__)
greet_message = False


@app.route('/health_check.html')
def health_check():
    return send_from_directory(os.getcwd(), 'health_check.html')


def run_flask():
    app.run(host='0.0.0.0', port=8000)


def schedule_payment_updates(wks: pygsheets.Worksheet, stop_event: threading.Event):
    while not stop_event.is_set():
        time.sleep(UPDATE_INTERVAL)
        payment_to_wks(wks)


def run(wks: pygsheets.Worksheet):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        if greet_message:
            pm_channel = bot.get_channel(PAYMENT_CHANNEL_ID)
            await pm_channel.send(f"## I am back!\n**Here is the payment record list:**\n{payment_record(wks)}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command(help="Show the bot information", brief="Bot information")
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list", aliases=['l'], help="List out all payment records stored in the bot",
                 brief="List all payment records")
    async def show(message: commands.Context):
        await message.channel.send(payment_record(wks))

    @bot.command(help="Turn on/off greet message when bot is reconnected", brief="Greet message on/off")
    async def greet(message: commands.Context):
        global greet_message
        greet_message = not greet_message
        await message.channel.send(f'Greet message is now {"on" if greet_message else "off"}')

    @bot.command(help=f"Show the {LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def log(message: commands.Context):
        await message.channel.send(show_log(LOG_SHOW_NUMBER))

    @bot.command(help=f"Show the {LONG_LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def logall(message: commands.Context):
        await message.channel.send(show_log(LONG_LOG_SHOW_NUMBER))

    @bot.command(name='currencies', help="Show all the supported currencies", brief="All supported currencies")
    async def show_all_currencies(message: commands.Context):
        currency_text = '\n'.join([f"**{key}**: {value}" for key, value in SUPPORTED_CURRENCY.items()])
        await message.channel.send(currency_text)

    @bot.command(help="Backup the current payment record in a separate file", brief="Backup the payment record")
    async def backup(message: commands.Context):
        await message.channel.send("**Backup done**\n" + do_backup(wks))

    @bot.command(help="Show the backup records", brief="Show the backup records", hidden=True)
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    async def create(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please create in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to create")
            return
        person = message.message.content.split()[1]
        author = message.author.name
        if create_ppl(person, author, wks):
            await message.channel.send(f"### Person {person} created!\n{payment_record(wks)}")
            await bot.get_channel(LOG_CHANNEL_ID).send(f"{author}: Created new person: {person}")
        else:
            await message.channel.send(f"**Failed to create {person}!**\nPerson already exists.")

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    async def delete(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please delete in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to delete")
            return
        target = message.message.content.split()[1]
        author = message.author.name
        if delete_ppl(target, author, wks):
            await message.channel.send(f"### Person {target} deleted!\n{payment_record(wks)}")
            await bot.get_channel(LOG_CHANNEL_ID).send(f"{author}: Deleted person: {target}")
        else:
            await message.channel.send(f"**Failed to delete {target}!**\nPerson not found or has not paid off yet.")

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    async def pm(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks)

    @bot.command(help="Enters a payment record by averaging the amount", brief="Enters a payment record by averaging")
    async def pmavg(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks, avg=True)

    # @bot.command(hidden=True, disabled=True)
    # async def piano(message: commands.Context):
    #     await piano_system(bot, message)

    bot.run(BOT_KEY)


if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    with open(SERVICE_ACCOUNT_FILE, 'w') as json_file:
        json.dump(GOOGLE_CRED, json_file, indent=2)

    # Link to the Google Sheet
    gc = pygsheets.authorize(service_file=SERVICE_ACCOUNT_FILE)
    sheet = gc.open_by_url(RECORD_SHEET_URL)
    record_wks = sheet.worksheet_by_title('Records')
    with open(PAYMENT_RECORD_FILE, 'w') as json_file:
        json.dump(wks_to_dict(record_wks), json_file, indent=2)

    # Start the scheduler thread
    stop_event = threading.Event()
    update_scheduler = threading.Thread(target=schedule_payment_updates, args=(record_wks, stop_event), daemon=True)
    update_scheduler.start()

    try:
        run(record_wks)
    except Exception as e:
        print(e)
    finally:
        stop_event.set()
        update_scheduler.join()
        payment_to_wks(record_wks)
        open(SERVICE_ACCOUNT_FILE, 'w').close()  # Empty credential file -> Google Docs access error
        open(PAYMENT_RECORD_FILE, 'w').close()
