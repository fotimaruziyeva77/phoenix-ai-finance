"""
Realistic knowledge snippets (as if extracted from PDF handbooks / policy docs).

Used by retrieval integration tests; wording is stable so PostgreSQL ``simple`` FTS matches predictably.
"""

# --- Same-bot corpus: shipping & returns (chunk 0 should rank above chunk 1 for this query) ---
QUERY_INTERNATIONAL_SHIPPING = "international shipping"

CHUNK_INTL_SHIPPING_DENSE = (
    "International shipping routes are handled by our partner carriers. "
    "International shipping quotes appear at checkout before you pay. "
    "Most international shipping delays are customs-related; allow extra days."
)

CHUNK_INTL_SHIPPING_SPARSE = (
    "Domestic shipping is free for orders over fifty dollars. "
    "For international shipping questions, email exports@example.com. "
    "Standard domestic shipping takes three to five business days."
)

CHUNK_RETURNS_DOMESTIC_ONLY = (
    "Returns use prepaid domestic shipping labels printed from your account. "
    "Drop the package at any authorized carrier location. "
    "Refunds post after the warehouse scans the return."
)

# --- Second bot: same distinctive phrase to prove isolation (must not appear in bot A search) ---
CHUNK_OTHER_BOT_DECOY = (
    "International shipping for enterprise accounts uses dedicated customs brokers. "
    "Contact your account manager for international shipping SLA terms."
)

# --- Refund-focused (user asks about refunds) ---
QUERY_REFUND = "refund processing"

CHUNK_REFUND_POLICY = (
    "Refund processing begins after the warehouse receives your return. "
    "Refund processing usually finishes within five business days. "
    "Expedited refund processing is available for defective items reported within 48 hours."
)

CHUNK_BILLING_UNRELATED = (
    "Invoices list subtotal, tax, and payment method. "
    "Net thirty terms apply to approved business accounts only. "
    "Late fees are assessed after the due date shown on the statement."
)
