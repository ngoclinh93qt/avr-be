"""Per-field answer quality validator for clarification form submissions.

Validates individual form field answers to determine if they are clear enough
to be accepted, or should be flagged for re-clarification.
"""

import re
from typing import Optional

# Vietnamese vowels including tonal variants
_VOWELS = set("aeiouàáâãäåèéêëìíîïòóôõöùúûüăđêôơưaàảãạăắặẳẵặâấậẩẫ"
              "AEIOUÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜĂĐÊÔƠƯ")

_TIME_KEYWORDS = re.compile(
    r"\d|tháng|năm|tuần|ngày|giờ|month|year|week|day|hour", re.IGNORECASE
)


def validate_field_answer(field_name: str, value: str) -> tuple[str, Optional[str]]:
    """Validate quality of a user's form field answer.

    Returns:
        ("confirmed", None)           — answer is clear enough to accept
        ("uncertain", "lý do tiếng Việt") — answer is vague/unclear
    """
    v = value.strip()

    # Skip validation for optional notes
    if field_name == "additional_notes":
        return "confirmed", None

    # Too short (< 3 non-space chars)
    meaningful_chars = re.sub(r"\s+", "", v)
    if len(meaningful_chars) < 3:
        return "uncertain", "Câu trả lời quá ngắn, vui lòng mô tả chi tiết hơn."

    # sample_size: must contain digits representing a valid positive integer
    if field_name == "sample_size":
        digits = re.sub(r"[^\d]", "", v)
        if not digits:
            return "uncertain", "Vui lòng nhập một con số cụ thể cho cỡ mẫu."
        try:
            n = int(digits)
            if n <= 0:
                return "uncertain", "Cỡ mẫu phải là số dương."
            if n > 100_000:
                return "uncertain", "Cỡ mẫu quá lớn, vui lòng kiểm tra lại."
        except ValueError:
            return "uncertain", "Không nhận diện được con số, vui lòng nhập lại."
        return "confirmed", None

    # follow_up_duration: must contain digit or time keyword
    if field_name == "follow_up_duration":
        if not _TIME_KEYWORDS.search(v):
            return "uncertain", "Vui lòng chỉ rõ thời gian theo dõi (ví dụ: 12 tháng, 2 năm)."
        return "confirmed", None

    # primary_endpoint / population / intervention / comparator / exposure:
    # need >= 5 meaningful chars and at least one word of >= 3 chars
    if field_name in ("primary_endpoint", "population", "intervention",
                      "comparator", "exposure", "reference_standard"):
        if len(meaningful_chars) < 5:
            return "uncertain", "Câu trả lời cần chi tiết hơn (ít nhất 5 ký tự)."
        words = re.findall(r"[a-zA-ZÀ-ỹ]{3,}", v)
        if not words:
            return "uncertain", "Vui lòng mô tả rõ hơn, tránh dùng ký tự đặc biệt hoặc chữ viết tắt không rõ."
        if _is_gibberish(v):
            return "uncertain", "Câu trả lời không rõ ràng, vui lòng mô tả cụ thể hơn."
        return "confirmed", None

    # Default: len > 2 and alphanumeric ratio > 0.5
    alnum = sum(c.isalnum() for c in v)
    if alnum / max(len(v), 1) < 0.5:
        return "uncertain", "Câu trả lời chứa quá nhiều ký tự đặc biệt, vui lòng mô tả bằng chữ."
    return "confirmed", None


def _is_gibberish(text: str) -> bool:
    """Return True if text looks like random characters (no meaningful vowels in short words)."""
    # Only flag very short text with no vowels at all
    words = re.findall(r"[a-zA-ZÀ-ỹ]+", text)
    if not words:
        return True
    # If all words are 1-3 chars and none contain a vowel → gibberish
    short_no_vowel = [w for w in words if len(w) <= 3 and not any(c in _VOWELS for c in w)]
    return len(short_no_vowel) == len(words) and len(words) >= 2
