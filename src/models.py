"""Data models describing an NDA generation request."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

# Sample data used to give each generated NDA distinct, realistic parameters.
_DISCLOSING_PARTIES = [
    "Acme Robotics, Inc.",
    "Northwind Analytics LLC",
    "Blue Harbor Biotech Corp.",
    "Quantum Ledger Technologies, Inc.",
    "Evergreen Health Systems LLC",
    "Stellar Aerospace Holdings, Inc.",
    "Meridian Capital Partners LP",
    "Cobalt Semiconductor Co.",
    "Lighthouse Media Group, Inc.",
    "Summit Renewable Energy LLC",
]

_RECEIVING_PARTIES = [
    "Jordan Avery Consulting",
    "Pinecrest Advisory Group LLC",
    "Dr. Morgan Lee",
    "Vertex Engineering Services, Inc.",
    "Harlow & Associates LLP",
    "Riverstone Software Studio",
    "Casey Ramirez",
    "Brightline Strategy Partners",
    "Optima Research Labs, Inc.",
    "Delphi Integration Group",
]

_JURISDICTIONS = [
    "the State of Delaware",
    "the State of California",
    "the State of New York",
    "the Commonwealth of Massachusetts",
    "the State of Texas",
    "the State of Washington",
]

_PURPOSES = [
    "evaluating a potential business relationship",
    "a prospective software development engagement",
    "discussions regarding a possible acquisition",
    "a joint research and development collaboration",
    "evaluating a potential investment",
    "a prospective manufacturing partnership",
]


@dataclass
class NDARequest:
    """Parameters describing a single NDA to generate."""

    disclosing_party: str
    receiving_party: str
    effective_date: date
    term_years: int
    jurisdiction: str
    purpose: str
    mutual: bool
    index: int = 0
    # Free-form extras a provider may use; reserved for future options.
    extras: dict = field(default_factory=dict)

    @classmethod
    def random(cls, index: int = 0, rng: random.Random | None = None) -> "NDARequest":
        """Build a randomized but plausible NDA request."""
        rng = rng or random
        effective = date.today() + timedelta(days=rng.randint(0, 30))
        return cls(
            disclosing_party=rng.choice(_DISCLOSING_PARTIES),
            receiving_party=rng.choice(_RECEIVING_PARTIES),
            effective_date=effective,
            term_years=rng.choice([1, 2, 3, 5]),
            jurisdiction=rng.choice(_JURISDICTIONS),
            purpose=rng.choice(_PURPOSES),
            mutual=rng.random() < 0.4,
            index=index,
        )
