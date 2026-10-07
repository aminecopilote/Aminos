"""Text normalisation used for terminology matching (Arabic, French, English)."""
import re
import unicodedata

_ARABIC_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PREFIX = re.compile(r"^(وال|بال|كال|فال|لل|ال|و)(?=.{3,})")
_TOKEN = re.compile(r"[\w]+", re.UNICODE)


def normalize(text: str) -> str:
    """Lower-case, strip diacritics/tatweel, unify Arabic letter variants and digits."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(_TATWEEL, "")
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.translate(_ALEF_VARIANTS).translate(_DIGITS)
    text = text.casefold()
    # Latin accents: "législation" == "legislation" for matching purposes
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def stem(token: str) -> str:
    """Strip one Arabic proclitic (و/ب/ل/ك/ف + ال) so 'بالمحكمة' matches 'المحكمة'."""
    return _PREFIX.sub("", token)


def tokens(text: str) -> list[str]:
    return [stem(t) for t in _TOKEN.findall(normalize(text))]


def is_arabic(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum("؀" <= c <= "ۿ" for c in letters) / len(letters) > 0.5
