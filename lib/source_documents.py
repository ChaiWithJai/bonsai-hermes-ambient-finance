"""Read local analyst sources without substituting index summaries."""
import csv
import hashlib
import io
import subprocess
from pathlib import Path


def read_document(root: Path, relative_path: str) -> dict:
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Analyst source must be inside the repository.")
    raw = path.read_bytes()
    if path.suffix.lower() == ".csv":
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
        content = [{"row": i, "cells": row} for i, row in enumerate(rows, 1)]
        result = {"format": "csv", "rows": content}
    elif path.suffix.lower() == ".pdf":
        try:
            output = subprocess.run(["pdftotext", "-layout", "-", "-"],
                                    input=raw,
                                    check=True, capture_output=True, timeout=30)
        except FileNotFoundError as error:
            raise RuntimeError("Install Poppler's pdftotext to read PDF analyst sources.") from error
        pages = output.stdout.decode("utf-8").split("\f")
        content = [{"page": i, "text": page.strip()} for i, page in enumerate(pages, 1) if page.strip()]
        if not content:
            raise ValueError("PDF has no extractable text; OCR is not implemented.")
        result = {"format": "pdf", "pages": content}
    else:
        raise ValueError("Supported analyst sources are PDF and CSV.")
    return {"source": relative_path, "sha256": hashlib.sha256(raw).hexdigest(),
            "read_kind": "local_file", **result}
