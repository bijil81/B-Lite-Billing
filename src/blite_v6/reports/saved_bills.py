"""Saved bill file helpers for Reports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import time
from typing import Any, Callable


_PDF_LIST_CACHE: dict[tuple[str, float, str], dict[str, Any]] = {}
_PDF_LIST_CACHE_MAX_SIZE = 20


@dataclass(frozen=True)
class SavedBillFile:
    invoice_no: str
    customer_name: str
    modified_text: str
    size_text: str
    file_path: str
    file_name: str

    @property
    def tree_values(self) -> tuple[str, str, str, str]:
        return (self.invoice_no, self.customer_name, self.modified_text, self.size_text)


def _evict_cache() -> None:
    if len(_PDF_LIST_CACHE) > _PDF_LIST_CACHE_MAX_SIZE:
        oldest = next(iter(_PDF_LIST_CACHE))
        _PDF_LIST_CACHE.pop(oldest, None)


def parse_saved_bill_filename(file_name: str) -> tuple[str, str]:
    stem = os.path.basename(file_name).replace(".pdf", "")
    parts = stem.split("_")
    invoice_no = parts[0] if parts else ""
    customer_name = "_".join(parts[1:]) if len(parts) > 1 else ""
    return invoice_no, customer_name


def saved_bill_file_from_path(file_path: str) -> SavedBillFile:
    file_name = os.path.basename(file_path)
    invoice_no, customer_name = parse_saved_bill_filename(file_name)
    try:
        modified = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d-%m-%Y %H:%M")
        size = f"{os.path.getsize(file_path) // 1024}KB"
    except Exception:
        modified, size = "", ""
    return SavedBillFile(
        invoice_no=invoice_no,
        customer_name=customer_name,
        modified_text=modified,
        size_text=size,
        file_path=file_path,
        file_name=file_name,
    )


def list_saved_bill_files(bills_dir: str, query: str = "") -> list[SavedBillFile]:
    if not os.path.exists(bills_dir):
        return []

    q = (query or "").lower()
    try:
        cache_key = (bills_dir, os.path.getmtime(bills_dir), q)
    except Exception:
        cache_key = None

    if cache_key is not None:
        cached = _PDF_LIST_CACHE.get(cache_key)
        if cached and (time.time() - cached["time"]) <= 5.0:
            files = cached["files"]
        else:
            files = sorted(
                [f for f in os.listdir(bills_dir) if f.endswith(".pdf") and (not q or q in f.lower())],
                reverse=True,
            )
            _PDF_LIST_CACHE[cache_key] = {"time": time.time(), "files": files}
            _evict_cache()
    else:
        files = sorted(
            [f for f in os.listdir(bills_dir) if f.endswith(".pdf") and (not q or q in f.lower())],
            reverse=True,
        )

    return [saved_bill_file_from_path(os.path.join(bills_dir, file_name)) for file_name in files]


def selected_saved_bill_from_tree(
    iid: str,
    values: tuple[Any, ...] | list[Any],
    file_map: dict[str, str],
) -> dict[str, str]:
    file_path = file_map.get(iid, "")
    file_name = os.path.basename(file_path or "")
    invoice_no = str(values[0]).strip() if values else ""
    customer_name = str(values[1]).strip() if len(values) > 1 else ""
    if not invoice_no and file_name:
        invoice_no = parse_saved_bill_filename(file_name)[0]
    return {
        "iid": iid,
        "invoice_no": invoice_no,
        "customer_name": customer_name,
        "file_path": file_path,
        "file_name": file_name,
    }


def find_report_row_by_invoice(rows: list[dict[str, Any]], invoice_no: str) -> dict[str, Any] | None:
    invoice_key = str(invoice_no or "").strip()
    if not invoice_key:
        return None
    return next((row for row in rows if str(row.get("invoice", "")).strip() == invoice_key), None)


def extract_pdf_text(file_path: str) -> str | None:
    try:
        import fitz

        doc = fitz.open(file_path)
        try:
            text = ""
            for page in doc:
                text += page.get_text()
        finally:
            doc.close()
        return text or "PDF contains no extractable text."
    except Exception:
        pass

    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text or "Empty PDF."
    except Exception:
        return None


def build_saved_bill_preview_text(
    file_path: str,
    report_rows: list[dict[str, Any]],
    bill_text_builder: Callable[[dict[str, Any]], str],
) -> str:
    extracted_text = extract_pdf_text(file_path)
    if extracted_text is not None:
        return extracted_text

    file_name = os.path.basename(file_path)
    invoice_no = parse_saved_bill_filename(file_name)[0]
    matched = find_report_row_by_invoice(report_rows, invoice_no)
    if matched:
        return bill_text_builder(matched)

    return (
        f"{file_name}\n\n"
        "Inline PDF text preview is not available in this build.\n"
        "Or double-click to open in PDF viewer."
    )
