import discord
from discord.ext import commands
from constants import MENU_TIMEOUT, UNDO_TIMEOUT, UNIFIED_CURRENCY
from ExchangeRateHandler import switch_currency


def dict_to_options(record_dict: dict):
    options = []
    for each_name in record_dict.keys():
        options.append(discord.SelectOption(label=each_name, value=each_name))
    return options


def choices_to_text(choices: list):
    text = ""
    for each in choices:
        text += each + ','
    return text[:-1]


class OweButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="pay back",
            custom_id="owe_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.owe_btn_response(interaction)


class ServiceChargeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="+10%",
            custom_id="service_charge_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.service_charge_btn_response(interaction)


class CurrencyButton(discord.ui.Button):
    def __init__(self, currency: str):
        super().__init__(
            label=currency,
            custom_id="currency_btn",
            emoji='💱',
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.currency_btn_response(interaction)


class SelectPplToPay(discord.ui.Select):
    def __init__(self, record: dict):
        options = dict_to_options(record)
        super().__init__(options=options, placeholder="Who needs to pay?", max_values=len(options), row=1)

    async def callback(self, interaction: discord.Interaction):
        await self.view.ppl_to_pay_response(interaction, self.values)


class SelectPersonGetPaid(discord.ui.Select):
    def __init__(self, record: dict):
        options = dict_to_options(record)
        super().__init__(options=options, placeholder="Who will get paid?", row=2)

    async def callback(self, interaction: discord.Interaction):
        await self.view.person_get_paid_response(interaction, self.values[0])


class AmountModal(discord.ui.Modal):
    amount = 0
    reason = ""

    amount_textinput = discord.ui.TextInput(
        label="Enter the amount",
        placeholder="Type the amount here...",
    )
    reason_textinput = discord.ui.TextInput(
        label="Reason",
        placeholder="Type the reason here...",
        required=False
    )

    def __init__(self, amount: float):
        super().__init__(title="Amount")
        self.amount = amount
        if amount != 0:
            self.amount_textinput.default = f"{amount}"

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            self.amount = float(self.amount_textinput.value)
            self.reason = f"({self.reason_textinput.value})" if self.reason_textinput.value != "" else ""
        except ValueError:
            await interaction.channel.send("Entered amount not a number!")
        self.stop()


class ModalTrigger(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Amount",
            emoji='💰',
            row=3,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.modal_trigger_response(interaction)


class EnterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Enter",
            custom_id="enter_btn",
            row=3,
            style=discord.ButtonStyle.primary,
            disabled=True
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.enter_btn_response(interaction)


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Cancel",
            custom_id="cancel_btn",
            row=3,
            style=discord.ButtonStyle.danger,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.cancel_btn_response(interaction)


class UndoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Undo",
            custom_id="undo_btn",
            style=discord.ButtonStyle.danger,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.undo_btn_response(interaction)


class View(discord.ui.View):
    cancelled = False
    finished = False
    owe = True
    currency = UNIFIED_CURRENCY
    service_charge = False
    reason = ""
    amount_text = "0"
    pay_text = paid_text = "???"
    embed_text = discord.Embed(title="Payment record", colour=0xC57CEE, description="??? owe ??? 0")

    owe_btn: OweButton = None
    service_charge_btn: ServiceChargeButton = None
    currency_btn: CurrencyButton = None
    ppl_to_pay_menu: SelectPplToPay = None
    person_get_paid_menu: SelectPersonGetPaid = None
    amount_modal: AmountModal = None
    modal_trigger: ModalTrigger = None
    enter_btn: EnterButton = None
    cancel_btn: CancelButton = None

    def __init__(self, record: dict):
        super().__init__(timeout=MENU_TIMEOUT)

        self.owe_btn = OweButton()
        self.service_charge_btn = ServiceChargeButton()
        self.currency_btn = CurrencyButton(self.currency)
        self.modal_trigger = ModalTrigger()
        self.enter_btn = EnterButton()
        self.cancel_btn = CancelButton()

        self.ppl_to_pay_menu = SelectPplToPay(record)
        self.person_get_paid_menu = SelectPersonGetPaid(record)

        self.add_item(self.owe_btn)
        self.add_item(self.service_charge_btn)
        self.add_item(self.currency_btn)
        self.add_item(self.ppl_to_pay_menu)
        self.add_item(self.person_get_paid_menu)
        self.add_item(self.modal_trigger)
        self.add_item(self.enter_btn)
        self.add_item(self.cancel_btn)

    def __del__(self):
        del self.owe_btn
        del self.currency_btn
        del self.modal_trigger
        del self.enter_btn
        del self.cancel_btn
        del self.ppl_to_pay_menu
        del self.person_get_paid_menu

    def update_description(self) -> None:
        self.embed_text.description = f"{self.pay_text} {'owe' if self.owe else 'pay back'} {self.paid_text} " \
                                      f"{self.amount_text}{' '+self.reason}" \
                                      f"{f' [{self.currency}]' if self.currency != UNIFIED_CURRENCY else ''}" \
                                      f"{' [+10%]' if self.service_charge else ''}"

    def correct_input(self) -> bool:
        return not (self.pay_text == "???" or self.paid_text == "???" or
                    self.amount_text == '0' or self.amount_text == "0.0" or
                    self.paid_text in self.pay_text)

    async def owe_btn_response(self, interaction: discord.Interaction):
        self.owe = not self.owe
        self.owe_btn.label = "pay back" if self.owe else "owe"
        self.update_description()
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def service_charge_btn_response(self, interaction: discord.Interaction):
        self.service_charge = not self.service_charge
        self.service_charge_btn.label = "✅" if self.service_charge else "+10%"
        self.update_description()
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def currency_btn_response(self, interaction: discord.Interaction):
        self.currency = switch_currency(self.currency)
        self.currency_btn.label = self.currency
        self.update_description()
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def ppl_to_pay_response(self, interaction: discord.Interaction, choices: list):
        self.pay_text = choices_to_text(choices)
        self.update_description()
        self.enter_btn.disabled = False if self.correct_input() else True
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def person_get_paid_response(self, interaction: discord.Interaction, choice: str):
        self.paid_text = choice
        self.update_description()
        self.enter_btn.disabled = False if self.correct_input() else True
        await interaction.message.edit(view=self, embed=self.embed_text)
        await interaction.response.defer()

    async def modal_trigger_response(self, interaction: discord.Interaction):
        self.amount_modal = AmountModal(float(self.amount_text))
        await interaction.response.send_modal(self.amount_modal)
        await self.amount_modal.wait()

        self.amount_text = f"{self.amount_modal.amount}"
        self.reason = self.amount_modal.reason
        self.update_description()
        self.enter_btn.disabled = False if self.correct_input() else True
        await interaction.message.edit(view=self, embed=self.embed_text)

    async def enter_btn_response(self, interaction: discord.Interaction):
        if not self.correct_input():
            await interaction.response.send_message(
                "Incorrect input! (This message should not appear)",
                ephemeral=True
            )
            await interaction.response.defer()
        else:
            self.finished = True
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            await interaction.response.defer()
            self.stop()

    async def cancel_btn_response(self, interaction: discord.Interaction):
        self.cancelled = True
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Process cancelled!", ephemeral=True)
        self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        self.stop()


class UndoView(discord.ui.View):
    undo: bool = None
    undo_btn: UndoButton = None

    def __init__(self):
        super().__init__(timeout=UNDO_TIMEOUT)
        self.undo = False
        self.undo_btn = UndoButton()
        self.add_item(self.undo_btn)

    async def undo_btn_response(self, interaction: discord.Interaction):
        self.undo = True
        self.children[0].disabled = True
        self.children[0].label = "Undo done"
        await self.message.edit(view=self)
        await interaction.response.defer()
        self.stop()

    async def on_timeout(self) -> None:
        self.children[0].disabled = True
        await self.message.edit(view=self)


if __name__ == "__main__":
    BOT_KEY = "MTE4OTEyMDQ1NDkwMDg1NDg4Nw.GnLE86.Wb7f7Eh3UiC5zGdrFdDBwkxFFBYLrQgtVOj23g"  # test bot
    payment_data = {
        "ppl1": 100,
        "ppl2": -100,
        "ppl3": 0
    }

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f"Current logged in user --> {bot.user}")

    @bot.command()
    async def test(ctx: commands.Context):
        menu = View(payment_data)
        # await ctx.send(f"{ctx.author}: {ctx.message.content}")
        menu.message = await ctx.send(view=menu)
        await menu.wait()
        ppl_to_pay = menu.pay_text
        person_get_paid = menu.paid_text
        amount = menu.amount_text
        reason = menu.reason
        finished = menu.finished
        owe = menu.owe

        if menu.cancelled:
            return

        await ctx.send(f"people to pay: {ppl_to_pay}\nperson get paid: {person_get_paid}\namount: {amount}"
                       f"\nreason: {reason}\nfinished: {finished}\nowe: {owe}")

        undo = UndoView()
        undo.message = await ctx.send(view=undo)
        await undo.wait()
        await ctx.send(f"undo: {undo.undo}")

    bot.run(BOT_KEY)
