# Discord Payment Bot

## Overview

The **Discord Payment Bot** is a tool designed to manage and record payments among a group of users. It provides a centralized system for tracking debts, repayments, and other financial interactions. Instead of wasting time paying your friends back and forth manually, you can simply enter a command in Discord to record payments.

## Features

- **Payment Management**: Record and manage debts and repayments among users.
- **Encryption and Decryption**: Securely encrypt and decrypt messages using a secret key.
- **Firebase Integration**: Store and retrieve user balances and logs from Firestore.
- **Undo and Edit**: Undo or edit payment records for flexibility.
- **Currency Conversion**: Automatically convert amounts to a unified currency.

## Commands

### General

- `!info`: Display bot information and usage instructions.
- `!list` or `!l`: List all payment records.
- `!history [type] [n]`: Show all logs, optionally filtered by type and limited to `n` entries.
- `!currencies`: Show all supported currencies.

### User Management

- `!create [name]`: Create a new user.
- `!delete [name]`: Delete a user if they have no debts.

### Payment Management

- `!pm`: Enter a payment record via a UI or command.
  - **Syntax**: `!pm [payee] [operation] [get paid] [amount] [-cur] [sc] [reason]`
  - **Example**: `!pm personA owe personB 100 -CNY sc dinner`

### Encryption

- `!encrypt` or `!enc`: Encrypt a message with a secret key.
- `!decrypt` or `!dec`: Decrypt a message with a secret key.
