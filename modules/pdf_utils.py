import pdfplumber


def extract_text(file) -> str:
    with pdfplumber.open(file) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    full_text = "\n".join(pages).strip()

    if not full_text:
        raise ValueError(
            "No text could be extracted from the uploaded PDF. "
            "The file may be scanned or image-only."
        )

    return full_text
