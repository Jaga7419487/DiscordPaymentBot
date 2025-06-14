import discord
from discord.ext import commands
from functools import wraps

from bookkeeping import add_bookkeeping_record, show_bookkeeping_records
from constants import BOT_KEY, BOT_STATUS, BOT_DESCRIPTION, SUPPORTED_CURRENCY, TIMEZONE
from encryption import decrypt_command, encrypt_command
from firebase_manager import write_bot_log, write_log
from backend import start_fastapi
from payment.payment_logic import create_user, delete_user, show_logs, show_payment_record, payment_system, terminate_worker
from piano.piano_logic import piano_system
from ping_worker import ping_bot
from utils import *


class BotState:
    """ A class to manage the state of the bot. """

    def __init__(self):
        self.active = True

    def toggle(self):
        self.active = not self.active
        return self.active


async def start_background_tasks(bot):
    """ Let the bot to handle background tasks """
    bot.loop.create_task(ping_bot())
    bot.loop.create_task(start_fastapi())


def start_bot():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)
    bot_state = BotState()
    
    def command_wrapper(bot_active=True, in_payment_channel=False, command_type=None):
        """ A wrapper to wrap commands with common checks and logging.
        :param bot_active: Whether the bot is active or not.
        :param in_payment_channel: Whether the command should be executed in the payment channel.
        :param command_type: The type of command to log.
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(ctx: commands.Context, *args, **kwargs):
                if bot_active and not bot_state.active:
                    await ctx.send("Bot is not started! Call !switch to start the bot")
                    return
                if in_payment_channel and ctx.channel.id != PAYMENT_CHANNEL_ID:
                    await ctx.send("Please input the record in the **payment** channel")
                    return
                await func(ctx, *args, **kwargs)
                if command_type:
                    write_log(command_type, channel_to_text(ctx.channel), ctx.author.name, ctx.message.content,
                            ctx.message.created_at.astimezone(TIMEZONE))
            return wrapper
        return decorator

    @bot.event
    async def on_ready():
        print(f"Logged in bot --> {bot.user} (Call !switch to start/stop)")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))
        write_bot_log()
        await start_background_tasks(bot)
        
    @bot.event
    async def on_logout():
        terminate_worker()
        print("Bot is shutting down...")

    @bot.command(hidden=True)
    @command_wrapper(bot_active=False, command_type='manage')
    async def switch(message: commands.Context):
        state = bot_state.toggle()
        await message.channel.send(B(f"Bot {'started' if state else 'stopped'}!"))

    @bot.command(hidden=True)
    @command_wrapper(command_type='read')
    async def status(message: commands.Context):
        await message.channel.send("Bot is active!")

    @bot.command(help="Show the bot information", brief="Bot information")
    @command_wrapper(command_type='read')
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)

    @bot.command(name="list", aliases=['l', 'L'], help="List out all payment records stored in the bot",
                 brief="List all payment records")
    @command_wrapper(command_type='read')
    async def show(message: commands.Context):
        await message.channel.send(show_payment_record())

    @bot.command(help=f"Show the history of command inputs", brief="Latest command inputs")
    @command_wrapper(command_type='read')
    async def history(message: commands.Context):
        response = await message.channel.send('loading...')
        await response.edit(content=show_logs(message.message.content.lower().split()))

    @bot.command(name='currencies', help="Show all the supported currencies", brief="All supported currencies")
    @command_wrapper(command_type='read')
    async def show_all_currencies(message: commands.Context):
        currency_text = '\n'.join([f"{B(key)}: {value}" for key, value in SUPPORTED_CURRENCY.items()])
        await message.channel.send(currency_text)

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    @command_wrapper(in_payment_channel=True, command_type='manage')
    async def create(message: commands.Context):
        response = await message.channel.send('loading...')
        result = await create_user(bot, message)
        await response.edit(content=result)

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    @command_wrapper(in_payment_channel=True, command_type='manage')
    async def delete(message: commands.Context):
        response = await message.channel.send('loading...')
        result = await delete_user(bot, message)
        await response.edit(content=result)

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    @command_wrapper(in_payment_channel=True)
    async def pm(message: commands.Context):
        await payment_system(bot, message)
            
    @bot.command(aliases=['enc'], help="Encrypt a string with a key", brief="Encrypt a string")
    @command_wrapper(command_type='others')
    async def encrypt(message: commands.Context):
        await encrypt_command(message)
            
    @bot.command(aliases=['dec'], help="Decrypt a string with a key", brief="Decrypt a string")
    @command_wrapper(command_type='others')
    async def decrypt(message: commands.Context):
        await decrypt_command(message)
            
    @bot.command(hidden=True)
    @command_wrapper(command_type='others')
    async def piano(message: commands.Context):
        await piano_system(bot, message)

    @bot.command(hidden=True)
    @command_wrapper(command_type='others')
    async def emoji(message: commands.Context):
        emoji = str(message.message.content.upper().split()[-1])
        await message.message.add_reaction(get_emoji(emoji))

    @bot.command(hidden=True)
    @command_wrapper(command_type='others')
    async def log(message: commands.Context):
        await message.send(add_bookkeeping_record(message))

    bot.run(BOT_KEY)


if __name__ == '__main__':
    start_bot()
