import re

def sanitize_tag(tag: str) -> str:
    """
    Normalizes a tag by removing all non-alphanumeric characters
    and converting it to uppercase. Returns an empty string if the input
    is not a string.
    """
    if not isinstance(tag, str): 
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', tag).upper()