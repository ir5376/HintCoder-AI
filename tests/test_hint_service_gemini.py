from src.services.hint_service import HintService


def test_format_gemini_error_message_for_model_not_found():
    service = HintService(session=None)

    message = service._format_gemini_error_message(
        RuntimeError("404 NOT_FOUND: models/gemini-2.5-flash is no longer available to new users")
    )

    assert "currently unavailable" in message.lower()
    assert "gemini" in message.lower()
    assert "try again later" in message.lower()
