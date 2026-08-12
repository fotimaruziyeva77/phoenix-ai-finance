"""
Embedded sample PDFs for knowledge pipeline tests (no runtime PDF generation deps).

``hello_pdf()`` is a one-page document with extractable text "Hello PDF".
``two_page_hello_pdf()`` duplicates that page for multi-page assertions.
"""

from __future__ import annotations

import base64
from io import BytesIO

# One-page PDF with visible text "Hello PDF" (fpdf2-generated; embedded for offline CI).
_HELLO_PDF_B64 = (
    "JVBERi0xLjMKJenr8b8KMSAwIG9iago8PAovQ291bnQgMQovS2lkcyBbMyAwIFJdCi9NZWRpYUJveCBbMCAwIDU5NS4yOCA4NDEuODldCi9UeXBlIC9QYWdlcwo+PgplbmRvYmoKMiAwIG9iago8PAovT3BlbkFjdGlvbiBbMyAwIFIgL0ZpdEggbnVsbF0KL1BhZ2VMYXlvdXQgL09uZUNvbHVtbgovUGFnZXMgMSAwIFIKL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDQgMCBSCi9QYXJlbnQgMSAwIFIKL1Jlc291cmNlcyA2IDAgUgovVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovRmlsdGVyIC9GbGF0ZURlY29kZQovTGVuZ3RoIDcxCj4+CnN0cmVhbQp4nDNS8OIy0DM1VyjncgpR0HczVDA00jMwUAhJU3ANAQkZWegZmypYGBrrmZoohKQoaHik5uTkKwS4uGkqhGSBFAEA38gO/QplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwKL0Jhc2VGb250IC9IZWx2ZXRpY2EKL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcKL1N1YnR5cGUgL1R5cGUxCi9UeXBlIC9Gb250Cj4+CmVuZG9iago2IDAgb2JqCjw8Ci9Gb250IDw8L0YxIDUgMCBSPj4KL1Byb2NTZXQgWy9QREYgL1RleHQgL0ltYWdlQiAvSW1hZ2VDIC9JbWFnZUldCj4+CmVuZG9iago3IDAgb2JqCjw8Ci9DcmVhdGlvbkRhdGUgKEQ6MjAyNjA0MDUwMTE2NTdaKQo+PgplbmRvYmoKeHJlZgowIDgKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE1IDAwMDAwIG4gCjAwMDAwMDAxMDIgMDAwMDAgbiAKMDAwMDAwMDIwNSAwMDAwMCBuIAowMDAwMDAwMjg1IDAwMDAwIG4gCjAwMDAwMDA0MjcgMDAwMDAgbiAKMDAwMDAwMDUyNCAwMDAwMCBuIAowMDAwMDAwNjExIDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgOAovUm9vdCAyIDAgUgovSW5mbyA3IDAgUgovSUQgWzw3N0IxMTA1QUQxMjMxQTYxNTFBNkI2MzMwOEI5RTg5OT48NzdCMTEwNUFEMTIzMUE2MTUxQTZCNjMzMDhCOUU4OTk+XQo+PgpzdGFydHhyZWYKNjY2CiUlRU9GCg=="
)


def hello_pdf() -> bytes:
    return base64.b64decode(_HELLO_PDF_B64)


def two_page_hello_pdf() -> bytes:
    """Two-page PDF with the same extractable text on each page (via pypdf)."""
    from pypdf import PdfReader, PdfWriter

    src = hello_pdf()
    reader = PdfReader(BytesIO(src), strict=False)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_page(reader.pages[0])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
