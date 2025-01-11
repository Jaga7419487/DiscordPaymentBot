import json
import os

import discord
import pygsheets
from discord.ext import commands
from dotenv import load_dotenv

from AutoPianoBooking import piano_system
from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system
from constants import BOT_STATUS, BOT_DESCRIPTION, LOG_SHOW_NUMBER, DEFAULT_LOG_SHOW_NUMBER

load_dotenv()


def run(wks: pygsheets.Worksheet):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    pm_channel_id = int(os.getenv('PAYMENT_CHANNEL_ID'))

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        pm_channel = bot.get_channel(pm_channel_id)
        await pm_channel.send(f"## I am back!\n**Here is the payment record list:**\n{payment_record(wks)}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command(help="Show the bot information", brief="Bot information")
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list", help="List out all payment records stored in the bot", brief="List all payment records")
    async def show(message: commands.Context):
        await message.channel.send(payment_record(wks))

    @bot.command(help=f"Show the {LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def log(message: commands.Context):
        await message.channel.send(show_log(LOG_SHOW_NUMBER))

    @bot.command(help=f"Show the {DEFAULT_LOG_SHOW_NUMBER} latest payment record inputs",
                 brief="Latest payment record inputs")
    async def logall(message: commands.Context):
        await message.channel.send(show_log())

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
        if create_ppl(person, wks):
            await message.channel.send(
                f"### Person {message.message.content.split()[1]} created!\n{payment_record(wks)}")
        else:
            await message.channel.send(f"{person} already exists!")

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    async def delete(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please delete in the **payment** channel")
            return

        if delete_ppl(message.message.content.split()[1], wks):
            await message.channel.send(
                f"**Person {message.message.content.split()[1]} deleted!**\n{payment_record(wks)}")
        else:
            await message.channel.send(f"**Fail to delete {message.message.content.split()[1]}!**\n"
                                       f"Person not found or has not paid off yet.")

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    async def pm(message: commands.Context):
        if message.channel.id != pm_channel_id:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message, wks)

    @bot.command(hidden=True, disabled=True)
    async def piano(message: commands.Context):
        await piano_system(bot, message)

    bot.run(os.getenv('BOT_KEY'))


if __name__ == '__main__':
    # Generate the gc file from .env if it doesn't exist
    if not os.path.exists('discord-payment-bot.json'):
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
