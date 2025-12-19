import re


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return "+7" + digits[1:]
    if digits.startswith("7") and len(digits) == 10:
        return "+7" + digits
    if phone and phone.startswith("+7") and len(digits) == 11:
        return phone
    return ""


def is_valid_iin(iin: str) -> bool:
    return bool(re.fullmatch(r"\d{12}", iin or ""))


def is_valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))

