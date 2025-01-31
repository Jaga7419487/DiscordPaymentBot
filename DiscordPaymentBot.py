import json
import os
import threading

import discord
import pygsheets
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, send_from_directory

from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system
from constants import BOT_STATUS, BOT_DESCRIPTION, LOG_SHOW_NUMBER, DEFAULT_LOG_SHOW_NUMBER, SUPPORTED_CURRENCY
from deprecated.AutoPianoBooking import piano_system

load_dotenv()
app = Flask(__name__)
greet_message = False


@app.route('/health_check.html')
def health_check():
    return send_from_directory(os.getcwd(), 'health_check.html')


def run_flask():
    # Use the port set by Koyeb
    port = int(os.environ.get('PORT', 8000))  # Default to 8000 if not set
    app.run(host='0.0.0.0', port=port)


def run(wks: pygsheets.Worksheet):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    pm_channel_id = int(os.getenv('PAYMENT_CHANNEL_ID'))

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        if greet_message:
            pm_channel = bot.get_channel(pm_channel_id)
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

    @bot.command(help=f"Show the {DEFAULT_LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def logall(message: commands.Context):
        await message.channel.send(show_log())

    @bot.command(name='currencies', help="Show all the supported currencies", brief="All supported currencies")
    async def show_all_currencies(message: commands.Context):
        currency_text = '\n'.join([f"**{key}**: {value}" for key, value in SUPPORTED_CURRENCY.items()])
        await message.channel.send(currency_text)

    @bot.command(help="Backup the current payment record in a separate file", brief="Backup the payment record")
    async def backup(message: commands.Context):
        do_backup(wks)
        await message.channel.send("Backup done\n" + show_backup())

    @bot.command(help="Show the backup records", brief="Show the backup records", hidden=True)
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    async def create(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please create in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to create")
            return
        person = message.message.content.split()[1]
        author = message.author.name
        if create_ppl(person, author, wks):
            await message.channel.send(f"### Person {person} created!\n{payment_record(wks)}")
            await bot.get_channel(int(os.getenv('LOG_CHANNEL_ID'))).send(f"{author}: Created new person: {person}")
        else:
            await message.channel.send(f"**Failed to create {person}!**\nPerson already exists.")

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    async def delete(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please delete in the **payment** channel")
            return
        if len(message.message.content.split()) < 2:
            await message.channel.send("Please input the name of the person you want to delete")
            return
        target = message.message.content.split()[1]
        author = message.author.name
        if delete_ppl(target, author, wks):
            await message.channel.send(f"### Person {target} deleted!\n{payment_record(wks)}")
            await bot.get_channel(int(os.getenv('LOG_CHANNEL_ID'))).send(f"{author}: Deleted person: {target}")
        else:
            await message.channel.send(f"**Failed to delete {target}!**\nPerson not found or has not paid off yet.")

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    async def pm(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks)

    @bot.command(help="Enters a payment record by averaging the amount", brief="Enters a payment record by averaging")
    async def pmavg(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks, avg=True)

    @bot.command(hidden=True, disabled=True)
    async def piano(message: commands.Context):
        await piano_system(bot, message)

    open('discord-payment-bot.json', 'w').close()
    bot.run(os.getenv('BOT_KEY'))


if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # always add google sheet credentials to the json file
    gc_list = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri",
               "token_uri",
               "auth_provider_x509_cert_url", "client_x509_cert_url", "universe_domain"]
    gc_dict = {key: os.getenv(key.upper()) for key in gc_list}
    gc_dict['private_key'] = gc_dict['private_key'].replace('\\n', '\n')
    with open('discord-payment-bot.json', 'w') as json_file:
        json.dump(gc_dict, json_file, indent=2)

    # Link to the Google Sheet
    gc = pygsheets.authorize(service_file='discord-payment-bot.json')
    sheet = gc.open_by_url(os.getenv('RECORD_SHEET_URL'))
    record_wks = sheet.worksheet_by_title('Records')

    run(record_wks)
