import asyncio

import discord
from discord.ext import commands
from functools import wraps

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
    
    def require_active_bot(func):
        """Decorator to require the bot to be active"""
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if not bot_state.active:
                await ctx.send("Bot is not started! Call !switch to start the bot")
                return
            return await func(ctx, *args, **kwargs)
        return wrapper
    
    def require_payment_channel(func):
        """Decorator to require the command to be called in the payment channel"""
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if ctx.channel.id != PAYMENT_CHANNEL_ID:
                await ctx.send("Please input the record in the **payment** channel")
                return
            return await func(ctx, *args, **kwargs)
        return wrapper

    @bot.event
    async def on_ready():
        print(f"Logged in bot --> {bot.user} (Call !switch to start/stop)")
        await bot.change_presence(activity=discord.Game(name=BOT_STATUS))
        write_bot_log()
        await start_background_tasks(bot)

    @bot.command(hidden=True)
    async def switch(message: commands.Context):
        state = bot_state.toggle()
        await message.channel.send(B(f"Bot {'started' if state else 'stopped'}!"))
        write_log('manage', channel_to_text(message.channel), message.author.name, message.message.content,
                  message.message.created_at.astimezone(TIMEZONE))

    @bot.command(hidden=True)
    @require_active_bot
    async def status(message: commands.Context):
        await message.channel.send("Bot is active!")
        write_log('read', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(help="Show the bot information", brief="Bot information")
    @require_active_bot
    async def info(message: commands.Context):
        await message.channel.send(BOT_DESCRIPTION)
        write_log('read', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(name="list", aliases=['l', 'L'], help="List out all payment records stored in the bot",
                 brief="List all payment records")
    @require_active_bot
    async def show(message: commands.Context):
        await message.channel.send(show_payment_record())
        write_log('read', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(help=f"Show the history of command inputs", brief="Latest command inputs")
    @require_active_bot
    async def history(message: commands.Context):
        response = await message.channel.send('loading...')
        await response.edit(content=show_logs(message.message.content.lower().split()))
        write_log('read', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(name='currencies', help="Show all the supported currencies", brief="All supported currencies")
    @require_active_bot
    async def show_all_currencies(message: commands.Context):
        currency_text = '\n'.join([f"{B(key)}: {value}" for key, value in SUPPORTED_CURRENCY.items()])
        await message.channel.send(currency_text)
        write_log('read', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(help="Create a new user with a name", brief="Create a new user")
    @require_active_bot
    @require_payment_channel
    async def create(message: commands.Context):
        response = await message.channel.send('loading...')
        result = await create_user(bot, message)
        await response.edit(content=result)
        write_log('manage', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(help="Delete a user if he has no debts", brief="Delete a user")
    @require_active_bot
    @require_payment_channel
    async def delete(message: commands.Context):
        response = await message.channel.send('loading...')
        result = await delete_user(bot, message)
        await response.edit(content=result)
        write_log('manage', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.command(help="Enters a payment record", brief="Enters a payment record")
    @require_active_bot
    @require_payment_channel
    async def pm(message: commands.Context):
        await payment_system(bot, message)
            
    @bot.command(aliases=['enc'], help="Encrypt a string with a key", brief="Encrypt a string")
    @require_active_bot
    async def encrypt(message: commands.Context):
        await encrypt_command(message)  
        write_log('others', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))
            
    @bot.command(aliases=['dec'], help="Decrypt a string with a key", brief="Decrypt a string")
    @require_active_bot
    async def decrypt(message: commands.Context):
        await decrypt_command(message)
        write_log('others', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))
            
    @bot.command(hidden=True)
    @require_active_bot
    async def piano(message: commands.Context):
        await piano_system(bot, message)

    @bot.command(hidden=True)
    @require_active_bot
    async def emoji(message: commands.Context):
        emoji = str(message.message.content.upper().split()[-1])
        await message.message.add_reaction(get_emoji(emoji))
        write_log('others', channel_to_text(message.channel), message.author.name, message.message.content,
                    message.message.created_at.astimezone(TIMEZONE))

    @bot.event
    async def on_logout():
        terminate_worker()
        print("Bot is shutting down...")

    bot.run(BOT_KEY)


if __name__ == '__main__':
    start_bot()
