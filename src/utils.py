from constants import EMOJI_MAPPING, PAYMENT_CHANNEL_ID, VALID_CHARS_SET


def B(text: str) -> str:
    """Return the input in bold text"""
    return f"**{text}**"


def I(text: str) -> str:
    """Return the input in italic text"""
    return f"*{text}*"


def U(text: str) -> str:
    """Return the input in underline text"""
    return f"__{text}__"


def channel_to_text(channel) -> str:
    """Return the channel name from the channel ID"""
    if channel.id == PAYMENT_CHANNEL_ID:
        return "payment"
    elif channel.type[0] == "private":
        return "private"
    else:
        return "others"


def is_valid_amount(amt: str) -> bool:
    return VALID_CHARS_SET.issuperset(amt)


def amt_parser(amt: str) -> str:
    return amt.replace('^', '**').replace('（', '(').replace('）', ')')
    
    
def get_emoji(emoji_name: str) -> str:
    """Return the emoji for the given name
    :param emoji_name: The name of the emoji
    :return: The emoji character or a question mark if not found
    """
    return EMOJI_MAPPING.get(emoji_name.upper(), EMOJI_MAPPING['?'])
