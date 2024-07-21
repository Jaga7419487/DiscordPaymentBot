import discord
from discord.ext import commands


BOT_KEY = "MTE4OTEyMDQ1NDkwMDg1NDg4Nw.GnLE86.Wb7f7Eh3UiC5zGdrFdDBwkxFFBYLrQgtVOj23g"

record = {
    "Jaga": 123,
    "Larry": 234,
    "741": 74912
}


def dict_to_options(record_dict: dict):
    options = []
    for each_name in record_dict.keys():
        options.append(discord.SelectOption(label=each_name, value=each_name))
    return options


def choices_to_text(choices: list):
    text = ""
    for each in choices:
        text += each + ', '
    return text[:-2]


class FavouriteGameSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Cs", value="cs"),
            discord.SelectOption(label="Minecraft", value="mc"),
            discord.SelectOption(label="Fortnite", value="f")
        ]
        super().__init__(options=options, placeholder="What do you like to play?", max_values=2)

    async def callback(self, interaction: discord.Interaction):
        self.view.respond_to_answer2(interaction, self.values)


class SurveyView(discord.ui.View):
    answer1 = None
    answer2 = None

    @discord.ui.select(
        placeholder="what is your age?",
        options=[
            discord.SelectOption(label="1", value="1"),
            discord.SelectOption(label="2", value="2"),
            discord.SelectOption(label="3", value="3"),
        ]
    )
    async def select_age(self, interaction: discord.Interaction, select_item: discord.ui.Select):
        self.answer1 = select_item.values
        self.children[0].disabled = True
        game_select = FavouriteGameSelect()
        self.add_item(game_select)
        await interaction.message.edit(view=self)
        await interaction.response.defer()

    async def respond_to_answer2(self, interaction: discord.Interaction, choices):
        self.answer2 = choices
        self.children[1].disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.defer()
        self.stop()


class SelectPplToPay(discord.ui.Select):
    def __init__(self):
        options = dict_to_options(record)
        super().__init__(options=options, placeholder="Who needs to pay?", max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        await self.view.ppl_to_pay_response(interaction, self.values)


class SelectPersonGetPaid(discord.ui.Select):
    def __init__(self):
        options = dict_to_options(record)
        super().__init__(options=options, placeholder="Who will get paid?")

    async def callback(self, interaction: discord.Interaction):
        await self.view.person_get_paid_response(interaction, self.values)


class ModalTrigger(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Amount")

    async def callback(self, interaction: discord.Interaction):
        await self.view.modal_trigger_response(interaction)


class Modal(discord.ui.Modal):
    amount = 0
    amount_textinput = discord.ui.TextInput(
        label="Amount",
        placeholder="Type your amount here..."
    )

    def __init__(self):
        super().__init__(title="Testing")

    async def on_submit(self, interaction: discord.Interaction):
        self.amount = self.amount_textinput.value
        await interaction.response.defer()
        self.stop()


class EnterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Enter")

    async def callback(self, interaction: discord.Interaction):
        await self.view.enter_btn_response(interaction)


class View(discord.ui.View):
    ppl_to_pay = None
    person_get_paid = None
    amount = 0
    pay_text = "___"
    paid_text = "___"
    amount_text = "___"
    embed_text = discord.Embed(title="Payment record", colour=0xC57CEE)
    ppl_to_pay_menu = SelectPplToPay()
    person_get_paid_menu = SelectPersonGetPaid()
    modal_trigger_btn = ModalTrigger()
    enter_btn = EnterButton()

    def __init__(self):
        super().__init__()
        self.add_item(self.ppl_to_pay_menu)
        self.add_item(self.person_get_paid_menu)
        self.add_item(self.modal_trigger_btn)
        self.add_item(self.enter_btn)

    async def ppl_to_pay_response(self, interaction: discord.Interaction, choices):
        self.ppl_to_pay = choices
        self.pay_text = choices_to_text(choices)
        self.embed_text.description = self.pay_text + " owe " + self.paid_text + ' ' + self.amount_text
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def person_get_paid_response(self, interaction: discord.Interaction, choice):
        self.person_get_paid = choice
        self.paid_text = choice[0]
        self.embed_text.description = self.pay_text + " owe " + self.paid_text + ' ' + self.amount_text
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def modal_trigger_response(self, interaction: discord.Interaction):
        modal = Modal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.amount = float(modal.amount)
        self.amount_text = modal.amount
        self.embed_text.description = self.pay_text + " owe " + self.paid_text + ' ' + self.amount_text
        await interaction.response.send_message(modal.amount)


def run():
    intents = discord.Intents.all()

    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")

    @bot.command()
    async def s(ctx):
        view = SurveyView()
        await ctx.send(view=view)

        await view.wait()

        results = {
            "a1": view.answer1,
            "a2": view.answer2,
        }

        await ctx.send(f"{results}")

    @bot.command()
    async def t(ctx: commands.Context):
        menu = View()
        await ctx.send(view=menu)
        await menu.wait()
        await ctx.send("Payment updated! blablablablabla")

    bot.run(BOT_KEY)


run()
