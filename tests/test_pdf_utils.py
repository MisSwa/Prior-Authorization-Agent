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
