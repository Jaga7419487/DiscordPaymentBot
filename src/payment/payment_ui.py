import discord

from constants import MENU_TIMEOUT, SUPPORTED_CURRENCY, UNDO_TIMEOUT, UNIFIED_CURRENCY
from utils import B, amt_parser, is_valid_amount


def list_to_options(record: list):
    options = []
    for each_name in record:
        options.append(discord.SelectOption(label=each_name, value=each_name))
    return options


def choices_to_text(choices: list):
    text = ""
    for each in choices:
        text += each + ','
    return text[:-1]


class OweButton(discord.ui.Button):
    def __init__(self, owe: bool):
        super().__init__(
            label="pay back" if owe else "owe",
            custom_id="owe_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.owe = not self.view.owe
        self.view.owe_btn.label = "pay back" if self.view.owe else "owe"
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class ServiceChargeButton(discord.ui.Button):
    def __init__(self, service_charge: bool):
        super().__init__(
            label="✅" if service_charge else "+10%",
            custom_id="service_charge_btn",
            row=0,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.service_charge = not self.view.service_charge
        self.view.service_charge_btn.label = "✅" if self.view.service_charge else "+10%"
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class SelectPplToPay(discord.ui.Select):
    def __init__(self, record: list):
        options = list_to_options(record)
        super().__init__(options=options, placeholder="Who needs to pay?", max_values=len(options), row=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.pay_text = choices_to_text(self.values)
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class SelectPersonGetPaid(discord.ui.Select):
    def __init__(self, record: list):
        options = list_to_options(record)
        super().__init__(options=options, placeholder="Who will get paid?", row=2)

    async def callback(self, interaction: discord.Interaction):
        self.view.paid_text = self.values[0]
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)
        await interaction.response.defer()


class AmountModal(discord.ui.Modal):
    amount_textinput = discord.ui.TextInput(
        label="AMOUNT (3 d.p.)",
        placeholder="Type the amount here...",
        required=True
    )
    reason_textinput = discord.ui.TextInput(
        label="REASON",
        placeholder="Type the reason here...",
        required=False
    )
    currency_textinput = discord.ui.TextInput(
        label="CURRENCY (JPY, CNY...)",
        placeholder="HKD",
        required=False
    )

    def __init__(self, amount: str, reason: str, currency: str):
        super().__init__(title="Amount")
        self.amount = amount
        if float(amount) != 0.0:
            self.amount_textinput.default = amount

        self.reason = reason
        if reason and self.reason[0] in '(（' and self.reason[-1] in '）)':  # remove brackets
            self.reason_textinput.default = reason[1:-1]
        else:
            self.reason_textinput.default = reason

        self.currency = currency if currency != UNIFIED_CURRENCY else UNIFIED_CURRENCY
        if currency != UNIFIED_CURRENCY:
            self.currency_textinput.default = currency

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if is_valid_amount(self.amount_textinput.value):
                self.amount = str(eval(amt_parser(self.amount_textinput.value)))
            else:
                await interaction.response.send_message("Invalid amount!", ephemeral=True)
        except ZeroDivisionError:
            await interaction.response.send_message(B("Invalid amount: Don't divide zero la..."), ephemeral=True)
        except (ValueError, SyntaxError):
            await interaction.response.send_message(B("What have you entered for the amount .-."), ephemeral=True)

        if self.reason_textinput.value and self.reason_textinput.value[0] in '(（' \
                and self.reason_textinput.value[-1] == '）)':
            self.reason = self.reason_textinput.value[1:-1]
        else:
            self.reason = self.reason_textinput.value

        if self.currency_textinput.value.upper() in SUPPORTED_CURRENCY.keys():
            self.currency = self.currency_textinput.value.upper()
        elif self.currency_textinput.value == '':
            self.currency = UNIFIED_CURRENCY
        else:
            await interaction.response.send_message("Invalid currency!", ephemeral=True)

        if not interaction.response.is_done():
            await interaction.response.defer()
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
        self.view.amount_modal = AmountModal(self.view.amount_text, self.view.reason, self.view.currency)
        await interaction.response.send_modal(self.view.amount_modal)
        await self.view.amount_modal.wait()

        self.view.amount_text = self.view.amount_modal.amount
        self.view.reason = self.view.amount_modal.reason
        self.view.currency = self.view.amount_modal.currency
        self.view.update_description()
        await interaction.message.edit(view=self.view, embed=self.view.embed_text)


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
        if not self.view.correct_input():
            await interaction.response.send_message(
                "Incorrect input! (This message should not appear)",
                ephemeral=True
            )
            await interaction.response.defer()
        else:
            self.view.finished = True
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(view=self.view)
            await interaction.response.defer()
            self.view.stop()


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
        self.view.cancelled = True
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)
        await interaction.response.defer()
        self.view.stop()


class UndoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Undo",
            custom_id="undo_btn",
            style=discord.ButtonStyle.danger,
            disabled=False
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.undo = True
        self.view.undo_user = interaction.user.name
        self.view.cancelled_at = interaction.message.created_at
        self.label = "Undo done"
        for item in self.view.children:
            item.disabled = True
        await self.view.message.edit(view=self.view)
        await interaction.response.defer()
        self.view.stop()


class EditButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Edit",
            custom_id="edit_btn",
            style=discord.ButtonStyle.danger,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.undo = True
        self.view.edit = True
        self.view.undo_user = interaction.user.name
        self.view.cancelled_at = interaction.message.created_at
        self.label = "Edit triggered"
        for item in self.view.children:
            item.disabled = True
        await self.view.message.edit(view=self.view)
        await interaction.response.defer()
        self.view.stop()


class InputView(discord.ui.View):
    def __init__(self, record: list, pay_text="???", owe=True, paid_text="???", amount="0",
                 service_charge=False, currency=UNIFIED_CURRENCY, reason=""):
        super().__init__(timeout=MENU_TIMEOUT)

        self.cancelled = False
        self.finished = False

        self.pay_text = pay_text
        self.owe = owe
        self.paid_text = paid_text
        self.amount_text = amount
        self.service_charge = service_charge
        self.currency = currency
        self.reason = reason

        self.embed_text = discord.Embed(title="Payment record", colour=0xC57CEE, description="??? owe ??? $???")

        self.owe_btn = OweButton(self.owe)
        self.service_charge_btn = ServiceChargeButton(self.service_charge)
        self.modal_trigger = ModalTrigger()
        self.enter_btn = EnterButton()
        self.cancel_btn = CancelButton()

        self.ppl_to_pay_menu = SelectPplToPay(record)
        self.person_get_paid_menu = SelectPersonGetPaid(record)

        self.add_item(self.owe_btn)
        self.add_item(self.service_charge_btn)
        self.add_item(self.ppl_to_pay_menu)
        self.add_item(self.person_get_paid_menu)
        self.add_item(self.modal_trigger)
        self.add_item(self.enter_btn)
        self.add_item(self.cancel_btn)

    def correct_input(self) -> bool:
        return not (self.pay_text == "???" or self.paid_text == "???" or
                    self.amount_text == '0' or self.amount_text == "0.0" or
                    self.paid_text in self.pay_text)

    def update_description(self) -> None:
        operation = "owe" if self.owe else "pay back"
        currency_text = f" [{self.currency}]" if self.currency != UNIFIED_CURRENCY else ""
        service_charge_text = ' [+10%]' if self.service_charge else ''
        if self.reason:
            if self.reason[0] in '(（' and self.reason[-1] in '）)':
                reason_text = ' ' + self.reason
            else:
                reason_text = ' (' + self.reason + ')'
        else:
            reason_text = ''
        self.embed_text.description = f"{self.pay_text} {operation} {self.paid_text} " \
                                      f"{self.amount_text}{reason_text}" \
                                      f"{currency_text}{service_charge_text}"
        self.enter_btn.disabled = not self.correct_input()

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        self.stop()


class UndoView(discord.ui.View):
    def __init__(self, show_edit_btn: bool, response_content: str):
        super().__init__(timeout=UNDO_TIMEOUT)

        self.undo = False
        self.edit = False
        self.undo_user = None
        self.cancelled_at = None
        self.undo_btn = UndoButton()
        self.add_item(self.undo_btn)
        
        self.embed_text = discord.Embed(title="Payment record successfully updated!", description=response_content)

        if show_edit_btn:
            self.edit_btn = EditButton()
            self.add_item(self.edit_btn)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        self.stop()
