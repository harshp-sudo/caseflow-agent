"""All policy and order records in this module are fictional, public demo fixtures."""

import re

POLICIES = [
    {"id": "shipping", "title": "Shipping and delivery",
     "text": "Standard delivery takes 3 to 5 business days after dispatch. "
             "If tracking has not changed for 7 business days, contact support for investigation.",
     "tags": "shipping delivery late parcel tracking dispatch arrive shipment"},
    {"id": "returns", "title": "Returns and refunds",
     "text": "Unused items may be submitted for return review within 30 days of delivery. "
             "A human support specialist must review all refund requests. "
             "This assistant cannot issue refunds or promise approval.",
     "tags": "refund return reimburse cancel cancellation chargeback money reverse"},
    {"id": "payments", "title": "Pending payment",
     "text": "A pending payment may take up to 24 hours to settle. "
             "If a payment remains pending after that window, contact support. "
             "Do not share card numbers or authentication codes with the assistant.",
     "tags": "payment pending charged charge card transaction billing settle"},
    {"id": "account", "title": "Account access",
     "text": "Use the password reset option on the sign-in page to recover account access. "
             "Support will never ask for a password or a one-time authentication code.",
     "tags": "account password reset login sign access recover"},
]

ORDERS = {
    "DEMO-1001": {"order_id": "DEMO-1001", "status": "dispatched", "business_days_since_dispatch": 2},
    "DEMO-1002": {"order_id": "DEMO-1002", "status": "payment_pending", "hours_pending": 26},
}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_policies(query: str, limit: int = 2) -> list[dict]:
    """Small inspectable lexical retriever; not an embedding/vector-search claim."""
    q = tokens(query)
    ranked = [(len(q & tokens(d["title"] + " " + d["tags"])), d) for d in POLICIES]
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [{k: d[k] for k in ("id", "title", "text")} for score, d in ranked[:limit] if score]


def lookup_demo_order(order_id: str | None) -> dict | None:
    order = ORDERS.get(order_id or "")
    return dict(order) if order else None

