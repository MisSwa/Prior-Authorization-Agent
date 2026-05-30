import io
from unittest.mock import MagicMock, patch

import pytest

from modules.pdf_utils import extract_text


def _mock_pdf(page_texts: list[str | None]) -> MagicMock:
    pages = []
    for text in page_texts:
        page = MagicMock()
        page.extract_text.return_value = text
        pages.append(page)
    pdf = MagicMock()
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    pdf.pages = pages
    return pdf


def test_single_page_returns_text() -> None:
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf(["Hello world"])):
        result = extract_text(io.BytesIO(b"fake"))
    assert result == "Hello world"


def test_multi_page_concatenates_all_pages() -> None:
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf(["Page 1", "Page 2"])):
        result = extract_text(io.BytesIO(b"fake"))
    assert result == "Page 1\nPage 2"


def test_none_page_treated_as_empty_string() -> None:
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf([None, "Page 2"])):
        result = extract_text(io.BytesIO(b"fake"))
    assert result == "Page 2"


def test_raises_value_error_when_no_text_extracted() -> None:
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf([None])):
        with pytest.raises(ValueError, match="No text could be extracted"):
            extract_text(io.BytesIO(b"fake"))


# ---------------------------------------------------------------------------
# Edge cases: inputs that should raise ValueError
# ---------------------------------------------------------------------------


def test_empty_pages_list_raises_value_error() -> None:
    """A PDF with zero pages produces no text and must raise."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf([])):
        with pytest.raises(ValueError, match="No text could be extracted"):
            extract_text(io.BytesIO(b"fake"))


def test_all_empty_string_pages_raises_value_error() -> None:
    """Pages that each return '' (empty string) should collectively raise."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf(["", ""])):
        with pytest.raises(ValueError, match="No text could be extracted"):
            extract_text(io.BytesIO(b"fake"))


def test_whitespace_only_pages_raises_value_error() -> None:
    """Pages containing only whitespace collapse to '' after strip and must raise."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf(["   ", "\t\n"])):
        with pytest.raises(ValueError, match="No text could be extracted"):
            extract_text(io.BytesIO(b"fake"))


def test_none_mixed_with_empty_string_raises_value_error() -> None:
    """None and '' together still produce no usable text."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf([None, ""])):
        with pytest.raises(ValueError, match="No text could be extracted"):
            extract_text(io.BytesIO(b"fake"))


def test_error_message_mentions_scanned_or_image_only() -> None:
    """The ValueError message should hint at the likely cause."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf([None, None])):
        with pytest.raises(ValueError) as exc_info:
            extract_text(io.BytesIO(b"fake"))
    message = str(exc_info.value).lower()
    assert "scanned" in message or "image-only" in message


# ---------------------------------------------------------------------------
# Edge cases: inputs that should succeed
# ---------------------------------------------------------------------------


def test_output_is_stripped_of_surrounding_whitespace() -> None:
    """Leading/trailing whitespace around the full result is removed."""
    with patch("modules.pdf_utils.pdfplumber.open", return_value=_mock_pdf(["  Hello  "])):
        result = extract_text(io.BytesIO(b"fake"))
    assert result == "Hello"


def test_three_pages_concatenated_with_newlines() -> None:
    """Three pages are joined with single newline separators."""
    with patch(
        "modules.pdf_utils.pdfplumber.open",
        return_value=_mock_pdf(["First", "Second", "Third"]),
    ):
        result = extract_text(io.BytesIO(b"fake"))
    assert result == "First\nSecond\nThird"
