"""
Agent 1 -- Ingestion

Takes whatever limited input a manufacturer/distributor actually has
(a pasted spec paragraph, a supplier PDF datasheet, a CSV-like text dump)
and turns it into a normalized list of {page, line_no, text} blocks that
every downstream agent can cite back to. This page/line handle is the
foundation of the traceability guarantee -- nothing enters the graph
without a place it came from.
"""
import io
import re
from dataclasses import dataclass


@dataclass
class TextBlock:
    page: int
    line_no: int
    text: str


def ingest_plain_text(text: str, source_name: str = "pasted_text"):
    blocks = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if line:
            blocks.append(TextBlock(page=1, line_no=i, text=line))
    return blocks, source_name


def ingest_pdf(file_bytes: bytes, source_name: str = "uploaded.pdf"):
    import pdfplumber

    blocks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            # 1) Extract any real tables first -- these are the highest
            #    signal source for industrial spec sheets (2-column
            #    "Parameter | Value" tables are extremely common).
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for table in tables or []:
                for row in table:
                    cells = [c.strip() for c in row if c and c.strip()]
                    if len(cells) >= 2:
                        line = " : ".join(cells[:2])
                        blocks.append(TextBlock(page=page_idx, line_no=0, text=line))

            # 2) Fall back to raw text lines (covers non-tabular datasheets,
            #    nameplates transcribed as text, paragraph-style specs).
            text = page.extract_text() or ""
            for i, line in enumerate(text.splitlines(), start=1):
                line = line.strip()
                if line:
                    blocks.append(TextBlock(page=page_idx, line_no=i, text=line))

    return blocks, source_name


def ingest(raw_text: str = None, pdf_bytes: bytes = None, source_name: str = None):
    if pdf_bytes:
        return ingest_pdf(pdf_bytes, source_name or "uploaded.pdf")
    return ingest_plain_text(raw_text or "", source_name or "pasted_text")
