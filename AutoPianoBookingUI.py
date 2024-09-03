import discord

from datetime import datetime, timedelta
from constants import MENU_TIMEOUT


def day_to_options() -> [discord.SelectOption]:
    options = []
    for i in range(7):
        day = datetime.today() + timedelta(days=i+1)
        label = f"{day.strftime('%a')} ({day.strftime('%d/%m')})"
        options.append(discord.SelectOption(label=label, value=str(i+1)))
    return options


def timeslot_to_options(session) -> [discord.SelectOption]:
    options = []
    start = end = 0

    match session:
        case 1:
            start = 1
            end = 11
        case 2:
            start = 11
            end = 23
        case 3:
            start = 23
            end = 31
        case _:
            raise ValueError("[AutoPianoBookingUI] timeslot_to_options: Invalid session")

    for i in range(start, end):
        options.append(discord.SelectOption(label=number_to_time(i), value=str(i)))
    return options


def duration_to_options(n=4) -> [discord.SelectOption]:
    options = [
                discord.SelectOption(label="30 minutes", value="1"),
                discord.SelectOption(label="1 hour", value="2"),
                discord.SelectOption(label="1.5 hours", value="3"),
                discord.SelectOption(label="2 hours", value="4")
            ]
    return options[:n]


def number_to_day(num) -> str:
    day = datetime.today() + timedelta(days=num - 1)
    return day.strftime('%a')


def number_to_time(num) -> str:
    if num < 1 or num > 31:
        return "???"
    start_time = datetime.strptime('07:00', '%H:%M')
    total_minutes = timedelta(minutes=(num-1)*30)
    new_time = start_time + total_minutes
    return new_time.strftime('%H:%M')


class RoomButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Room 114",
            custom_id="room_btn",
            row=0,
            disabled=False

        )

    async def callback(self, interaction: discord.Interaction):
        if self.view.room == 0:
            self.view.room = 1
        self.view.room_btn.label = f"Room {'111' if self.view.room == 1 else '114'}"
        self.view.room = 1 if self.view.room != 1 else 2
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class MorningButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Morning",
            custom_id="morning_btn",
            row=0,
            disabled=True
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.morning_btn.disabled = True
        self.view.afternoon_btn.disabled = False
        self.view.evening_btn.disabled = False

        self.view.time_slot_menu.options = timeslot_to_options(1)

        self.view.time_slot = 0
        self.view.duration = 0
        self.view.time_part = 1
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class AfternoonButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Afternoon",
            custom_id="afternoon_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.morning_btn.disabled = False
        self.view.afternoon_btn.disabled = True
        self.view.evening_btn.disabled = False

        self.view.time_slot_menu.options = timeslot_to_options(2)

        self.view.time_slot = 0
        self.view.duration = 0
        self.view.time_part = 2
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class EveningButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Evening",
            custom_id="evening_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.morning_btn.disabled = False
        self.view.afternoon_btn.disabled = False
        self.view.evening_btn.disabled = True

        self.view.time_slot_menu.options = timeslot_to_options(3)

        self.view.time_slot = 0
        self.view.duration = 0
        self.view.time_part = 3
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class DayMenu(discord.ui.Select):
    def __init__(self):
        options = day_to_options()
        super().__init__(
            placeholder="Which day?",
            options=options,
            custom_id="day_menu",
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.day = int(self.values[0])
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class TimeSlotMenu(discord.ui.Select):
    def __init__(self):
        # changeable menu from session
        options = timeslot_to_options(1)
        super().__init__(
            placeholder="Which time?",
            options=options,
            custom_id="time_slot_menu",
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.time_slot = int(self.values[0])
        self.view.update_description()
        self.view.duration_menu.options = duration_to_options(31 - self.view.time_slot)
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class DurationMenu(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="How long?",
            options=duration_to_options(),
            custom_id="duration_menu",
            row=3
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.duration = int(self.values[0])
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class EnterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Enter",
            custom_id="enter_btn",
            row=4,
            style=discord.ButtonStyle.primary,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        if self.view.correct_input():
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(view=self.view)
            await interaction.response.defer()
            self.view.stop()
        else:
            await interaction.response.send_message("Invalid input!", ephemeral=True)
            await interaction.message.edit(view=self.view)
            await interaction.response.defer()


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Cancel",
            custom_id="cancel_btn",
            row=4,
            style=discord.ButtonStyle.danger,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.cancelled = True
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)
        await interaction.response.send_message("Process cancelled!", ephemeral=True)
        self.view.stop()


class View(discord.ui.View):
    cancelled = False
    room = 1  # 111/114
    day = 0  # 1-7 (today:1, tmr:2, ...)
    time_part = 1  # 1/2/3 (M/A/E)
    time_slot = 1  # 1-30: 10+12+8 (M/A/E: 07/12/18)
    duration = 1  # 1/2/3/4 (0/5/1/1.5/2 hours)
    embed_text = discord.Embed(title="Auto piano booking", colour=0xFF0000, description="Room 111 Morning 7:00 ~ 7:30")

    room_btn: RoomButton = None
    morning_btn: MorningButton = None
    afternoon_btn: AfternoonButton = None
    evening_btn: EveningButton = None
    day_menu: DayMenu = None
    time_slot_menu: TimeSlotMenu = None
    duration_menu: DurationMenu = None
    enter_btn: EnterButton = None
    cancel_btn: CancelButton = None

    def __init__(self):
        super().__init__(timeout=MENU_TIMEOUT)

        self.cancelled = False

        self.room_btn = RoomButton()
        self.morning_btn = MorningButton()
        self.afternoon_btn = AfternoonButton()
        self.evening_btn = EveningButton()
        self.day_menu = DayMenu()
        self.time_slot_menu = TimeSlotMenu()
        self.duration_menu = DurationMenu()
        self.enter_btn = EnterButton()
        self.cancel_btn = CancelButton()

        self.add_item(self.room_btn)
        self.add_item(self.morning_btn)
        self.add_item(self.afternoon_btn)
        self.add_item(self.evening_btn)
        self.add_item(self.day_menu)
        self.add_item(self.time_slot_menu)
        self.add_item(self.duration_menu)
        self.add_item(self.enter_btn)
        self.add_item(self.cancel_btn)

    def update_description(self) -> None:
        room_text = f"Room {'111' if self.room == 1 else '114'}"
        day_text = number_to_day(self.day + 1) if self.day != 0 else '???'
        time_slot_text = 'Morning' if self.time_part == 1 else 'Afternoon' if self.time_part == 2 else 'Evening'
        time_period_text = f"{number_to_time(self.time_slot)} ~ {number_to_time(self.time_slot + self.duration)}"
        self.embed_text.description = f"{room_text} {day_text} {time_slot_text} {time_period_text}"

    def correct_input(self) -> bool:
        return self.day != 0 and self.time_part != 0 and self.time_slot != 0 and self.duration != 0

    async def on_timeout(self) -> None:
        self.cancelled = True
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        self.stop()


if __name__ == "__main__":
    from discord.ext import commands

    BOT_KEY = "MTE4OTEyMDQ1NDkwMDg1NDg4Nw.GnLE86.Wb7f7Eh3UiC5zGdrFdDBwkxFFBYLrQgtVOj23g"  # test bot

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")

    @bot.command()
    async def t(ctx: commands.Context):
        menu = View()
        menu.message = await ctx.send(view=menu)
        await menu.wait()
        room = menu.room
        day = menu.day
        time_slot = menu.time_slot
        duration = menu.duration

        await ctx.send(f"Room:{room}; day:{day}; time_slot:{time_slot}; duration:{duration}")
        await ctx.send(menu.embed_text.description)

    bot.run(BOT_KEY)
