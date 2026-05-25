import re
import unicodedata


def slugify_attribute(value: str) -> str:
    """Normalize a label to a stable underscore slug.

    Rules (spec 02):
    1. Lowercase, strip accents (NFKD + ASCII).
    2. Replace '&' with '_and_' before generic substitution.
    3. Replace remaining non-alphanumerics with '_'.
    4. Collapse multiple '_', strip leading/trailing '_'.
    5. Truncate to 100 chars.
    """
    value = value.lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.replace("&", "_and_")
    value = value.replace("+", "_plus_")
    value = re.sub(r"[^\w]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:100]
