import re

_MDV2_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def escape_markdown_v2(text: str) -> str:
    return _MDV2_SPECIAL.sub(r"\\\1", text)
