import re
HTML_TAG = re.compile(r"<[^>]+>")
def clean_text(value: str) -> str:
    return HTML_TAG.sub("", value).strip()
def validate_sku(sku: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}-[0-9]{4,}", sku))
