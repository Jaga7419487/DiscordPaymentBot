import base64
import os

import discord
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from discord.ext import commands

from constants import ENCRYPTED_DELETE_TIMEOUT


def encrypt_string(plaintext: str, key: str) -> str:
    """
    Encrypts a string using a key string.
    Returns base64-encoded encrypted string with embedded salt.
    """
    # Convert strings to bytes
    plaintext_bytes = plaintext.encode('utf-8')
    key_bytes = key.encode('utf-8')

    # Generate a random salt for each encryption
    salt = os.urandom(16)

    # Generate a proper length key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    fernet_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))

    # Create the cipher and encrypt
    cipher = Fernet(fernet_key)
    encrypted_bytes = cipher.encrypt(plaintext_bytes)

    # Combine salt and encrypted data (salt first, then encrypted data)
    result = base64.urlsafe_b64encode(salt + encrypted_bytes)

    # Return as a string
    return result.decode('utf-8')


def decrypt_string(encrypted_text: str, key: str) -> str:
    """
    Decrypts a previously encrypted string using the same key.
    Extracts the embedded salt from the encrypted data.
    """
    try:
        # Convert to bytes and decode from base64
        combined_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
        key_bytes = key.encode('utf-8')

        # Extract the salt (first 16 bytes) and the encrypted data
        salt = combined_bytes[:16]
        encrypted_bytes = combined_bytes[16:]

        # Regenerate the key using the extracted salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        fernet_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))

        # Decrypt
        cipher = Fernet(fernet_key)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)

        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        return f"Decryption failed: {str(e)}"


class EncryptionModal(discord.ui.Modal):
    plaintext_input = discord.ui.TextInput(
        label="Text to encrypt",
        placeholder="Enter your message here...",
        required=True,
        style=discord.TextStyle.paragraph
    )

    key_input = discord.ui.TextInput(
        label="Encryption key",
        placeholder="Enter your secret key",
        required=True
    )

    def __init__(self):
        super().__init__(title="Encrypt Text")

    async def on_submit(self, interaction: discord.Interaction):
        plaintext = self.plaintext_input.value
        key = self.key_input.value

        encrypted_text = encrypt_string(plaintext, key)

        await interaction.response.send_message(encrypted_text, ephemeral=True, delete_after=ENCRYPTED_DELETE_TIMEOUT)


class DecryptionModal(discord.ui.Modal):
    encrypted_input = discord.ui.TextInput(
        label="Encrypted text",
        placeholder="Paste the encrypted text here...",
        required=True,
        style=discord.TextStyle.paragraph
    )

    key_input = discord.ui.TextInput(
        label="Decryption key",
        placeholder="Enter your secret key",
        required=True
    )

    def __init__(self):
        super().__init__(title="Decrypt Text")

    async def on_submit(self, interaction: discord.Interaction):
        encrypted_text = self.encrypted_input.value
        key = self.key_input.value

        decrypted_text = decrypt_string(encrypted_text, key)

        if decrypted_text.startswith("Decryption failed"):
            decrypted_text = "⚠️ Decryption failed"

        await interaction.response.send_message(decrypted_text, ephemeral=True, delete_after=ENCRYPTED_DELETE_TIMEOUT)


class EncryptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Encrypt",
            style=discord.ButtonStyle.primary,
            emoji="🔒"
        )

    async def callback(self, interaction: discord.Interaction):
        # Disable the button after it's clicked
        self.disabled = True
        await interaction.message.edit(view=self.view)

        # Show the encryption modal
        modal = EncryptionModal()
        await interaction.response.send_modal(modal)


class DecryptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Decrypt",
            style=discord.ButtonStyle.secondary,
            emoji="🔓"
        )

    async def callback(self, interaction: discord.Interaction):
        # Disable the button after it's clicked
        self.disabled = True
        await interaction.message.edit(view=self.view)

        # Show the decryption modal
        modal = DecryptionModal()
        await interaction.response.send_modal(modal)


class EncryptView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(EncryptButton())


class DecryptView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(DecryptButton())


async def encrypt_command(message: commands.Context):
    """Command handler for encrypting text"""
    embed = discord.Embed(
        title="Encryption",
        description="Click the button below to encrypt a message",
        color=discord.Color.blue()
    )

    view = EncryptView()
    await message.send(embed=embed, view=view)


async def decrypt_command(message: commands.Context):
    """Command handler for decrypting text"""
    embed = discord.Embed(
        title="Decryption",
        description="Click the button below to decrypt a message",
        color=discord.Color.blue()
    )

    view = DecryptView()
    await message.send(embed=embed, view=view)


if __name__ == "__main__":
    password = "MyPassword"
    key = "MyKey"

    # Encrypt
    encrypted = encrypt_string(password, key)
    print(f"Encrypted: {encrypted}")

    # Decrypt
    decrypted = decrypt_string(encrypted, key)
    print(f"Decrypted: {decrypted}")
