from src.utils.pii_scrubber import scrub_text


def test_scrub_text_removes_email():
    text = "Contact me at test.user@example.com for details."
    cleaned = scrub_text(text)
    assert "example.com" not in cleaned
    assert "[email removed]" in cleaned


def test_scrub_text_removes_phone_number():
    text = "My number is +91 9876543210, please call."
    cleaned = scrub_text(text)
    assert "9876543210" not in cleaned
    assert "[phone removed]" in cleaned


def test_scrub_text_removes_aadhaar_like_id():
    text = "ID: 1234 5678 9012 should not be stored."
    cleaned = scrub_text(text)
    assert "1234 5678 9012" not in cleaned
    assert "[id removed]" in cleaned

