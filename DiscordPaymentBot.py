import discord
from discord.ext import commands

from AutoPianoBooking import piano_system
from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system
from botInfo import BOT_KEY, PAYMENT_CHANNEL_ID
from constants import BOT_STATUS, BOT_DESCRIPTION, LOG_SHOW_NUMBER, DEFAULT_LOG_SHOW_NUMBER


def run():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")
        pm_channel = bot.get_channel(PAYMENT_CHANNEL_ID)
        await pm_channel.send(f"## I am back!\n**Here is the payment record list:**\n{payment_record()}")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

    @bot.command(help="Show the bot information", brief="Bot information")
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list", help="List out all payment records stored in the bot", brief="List all payment records")
    async def show(message: commands.Context):
        await message.channel.send(payment_record())

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
        do_backup()
        await message.channel.send("Backup done\n" + show_backup())

    @bot.command(help="Show the backup records", brief="Show the backup records", hidden=True)
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    async def create(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please create in the **payment** channel")
            return
        if create_ppl(message.message.content.split()[1]):
            await message.channel.send(f"### Person {message.message.content.split()[1]} created!\n{payment_record()}")
        else:
            await message.channel.send("Please input the name of the person to be created")

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    async def delete(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please delete in the **payment** channel")
            return

        if delete_ppl(message.message.content.split()[1]):
            await message.channel.send(f"**Person {message.message.content.split()[1]} deleted!**\n{payment_record()}")
        else:
            await message.channel.send(f"**Fail to delete {message.message.content.split()[1]}!**\n"
                                       f"Person not found or has not paid off yet.")

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    async def pm(message: commands.Context):
        if message.channel.id != PAYMENT_CHANNEL_ID:
            await message.channel.send("Please input the record in the **payment** channel")
            return
        await payment_system(bot, message)

    @bot.command(hidden=True)
    async def piano(message: commands.Context):
        await piano_system(bot, message)

    bot.run(BOT_KEY)


if __name__ == '__main__':
    run()
