from discord.ext import commands
import discord

from botInfo import BOT_KEY
from constants import BOT_STATUS, BOT_DESCRIPTION, LOG_SHOW_NUMBER
from PaymentSystem import payment_record, show_log, do_backup, show_backup, create_ppl, delete_ppl, payment_system


def run():
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
        await message.channel.send("Backup done\n" + show_backup())

    @bot.command()
    async def showbackup(message: commands.Context):
        await message.channel.send(show_backup())

    @bot.command()
    async def create(message: commands.Context):
        if create_ppl(message.message.content.split()[1]):
            await message.channel.send(f"### Person {message.message.content.split()[1]} created!\n{payment_record()}")
        else:
            await message.channel.send("Please input the name of the person to be created")

    @bot.command()
    async def delete(message: commands.Context):
        if delete_ppl(message.message.content.split()[1]):
            await message.channel.send(f"**Person {message.message.content.split()[1]} deleted!**\n{payment_record()}")
        else:
            await message.channel.send(f"**Fail to delete {message.message.content.split()[1]}!**\n"
                                       f"Person not found or has not paid off yet.")

    @bot.command()
    async def pm(message: commands.Context):
        await payment_system(bot, message)

    @bot.command()
    async def piano(message: commands.Context):
        await message.channel.send("Piano booking system is under construction")

    bot.run(BOT_KEY)


if __name__ == '__main__':
    run()
