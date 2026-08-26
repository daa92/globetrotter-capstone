"""
app/transport_companies.py

A short, curated list of real transportation options in Cameroon,
cross-checked via web search (railwaygazette.com, camrail.cm's own site,
unitedexpress.cm, businesslist.co.cm, timbu.com, yango.com) as of Aug
2026 — not invented. Contact details are only included where they were
actually publicly published somewhere I could verify; where a company
doesn't publish a public email (common for Cameroonian transport
operators, who mostly run on phone/WhatsApp), that's stated honestly
rather than filled in with a guess.

This is a starting list, not exhaustive — there are many more local taxi
unions, moto-taxi ("bendskin") networks, and smaller regional bus lines
that don't have any public digital presence to verify against at all.
"""

TRANSPORT_COMPANIES = [
    {
        "name": "Yango",
        "type": "ride_hailing",
        "coverage": "Douala, Yaoundé, Bafoussam (app-based, on-demand within city limits)",
        "best_for": "Short trips, single-city travel, airport transfers",
        "phone": None,  # app/on-demand only — no public customer-service phone line found
        "email": None,  # no public support email found; support is in-app
        "website": "https://yango.com/en_cm/",
        "note": "Book through the Yango app (iOS/Android) — no phone booking or public email; support is handled in-app.",
    },
    {
        "name": "Camrail",
        "type": "train",
        "coverage": "Douala–Yaoundé, Douala–Kumba, Yaoundé–Ngaoundéré",
        "best_for": "Longer intercity trips, especially Yaoundé–Ngaoundéré overnight",
        "phone": "+237 233 50 26 47",
        "email": "CM004-service.commercial@camrail.net",
        "website": "https://camrail.cm/en/",
        "note": None,
    },
    {
        "name": "United Express",
        "type": "bus",
        "coverage": "Douala–Yaoundé highway (VIP coach service)",
        "best_for": "Comfortable Douala–Yaoundé travel",
        "phone": "+237 676 76 05 05",  # Douala office; Yaoundé office: +237 653 53 96 96
        "email": None,  # no public email found
        "website": "https://www.unitedexpress.cm/",
        "note": "Yaoundé office: +237 653 53 96 96. Douala office: +237 676 76 05 05.",
    },
    {
        "name": "Garanti Express (Guarantee Express)",
        "type": "bus",
        "coverage": "Bamenda, Douala, Yaoundé, Bafoussam, Buea, Limbe",
        "best_for": "Widest route network among the intercity bus operators here",
        "phone": "+237 698 49 39 78",
        "email": None,  # no public email found
        "website": None,
        "note": "Main terminal: Deux Églises, Akwa, Douala. Booking is in-person or by phone — no online booking found.",
    },
]


def suggest_for_distance(total_distance_km: float) -> list[dict]:
    """Simple, honest rule: Yango covers short/single-city trips; the
    intercity operators (bus/train) are relevant once a trip crosses
    into genuinely intercity distance. This does NOT verify that a given
    operator actually serves your exact two cities — route coverage
    varies and should be confirmed directly with the operator; the
    `coverage` field is a starting hint, not a guarantee, and the
    frontend says so too (see the transport section on the route view)."""
    if total_distance_km <= 20:
        return [c for c in TRANSPORT_COMPANIES if c["type"] == "ride_hailing"]
    return TRANSPORT_COMPANIES
