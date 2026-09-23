import re
from typing import Optional

from app.config import PASSWORD_MIN_LENGTH

PASSWORD_MAX_LENGTH = 128

# Frequently breached passwords and obvious patterns for this audience.
# Checked case-insensitively after removing spaces.
COMMON_PASSWORDS = {
    "password", "password1", "password12", "password123", "password@123", "passw0rd", "p@ssw0rd", "p@ssword1",
    "12345678", "123456789", "1234567890", "12341234", "11111111", "00000000", "87654321", "qwerty123",
    "qwertyuiop", "qwerty12", "1q2w3e4r", "1qaz2wsx", "abc12345", "abcd1234", "iloveyou", "iloveyou1",
    "letmein1", "welcome1", "welcome123", "admin123", "admin@123", "changeme", "trustno1", "football1",
    "sunshine1", "princess1", "monkey123", "dragon123", "master123", "baseball1", "superman1",
    "upsa1234", "upsa2024", "upsa2025", "upsa2026", "upsa@123", "upsa@2026", "student1", "student123",
    "gradeiq1", "gradeiq123", "ghana123", "ghana1234", "accra123", "accra1234", "jesus123", "godislove",
}


def password_problems(password: str, email: Optional[str] = None, name: Optional[str] = None) -> list[str]:
    """
    Returns every rule the password breaks (empty list = strong enough).
    Rules: 8 to 128 characters, upper and lower case letters, a number, a symbol,
    not a common password, and not built from the student's name or email.
    """
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"no more than {PASSWORD_MAX_LENGTH} characters")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"\d", password):
        problems.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol such as ! @ # or ?")

    squashed = re.sub(r"\s+", "", password).lower()
    if squashed in COMMON_PASSWORDS or re.fullmatch(r"(.)\1+", squashed):
        problems.append("not a common or easily guessed password")

    # Words from the email name ("kwabena.o2" -> kwabena) and the full name
    personal = []
    if email:
        personal.extend(re.split(r"[^a-z]+", email.split("@")[0].lower()))
    if name:
        personal.extend(re.split(r"[^a-z]+", name.lower()))
    if any(len(word) >= 4 and word in squashed for word in personal):
        problems.append("not your name or email address")

    return problems


def password_error(password: str, email: Optional[str] = None, name: Optional[str] = None) -> Optional[str]:
    """One readable sentence describing what the password still needs, or None."""
    problems = password_problems(password, email, name)
    if not problems:
        return None
    if len(problems) == 1:
        return f"Your password needs {problems[0]}."
    return "Your password needs " + ", ".join(problems[:-1]) + f" and {problems[-1]}."
