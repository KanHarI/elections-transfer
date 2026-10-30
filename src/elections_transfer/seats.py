"""Knesset seat allocation: 3.25% threshold, then Bader-Ofer (D'Hondt) over 120
seats, with surplus-vote agreements.

Lists in a surplus agreement are pooled into one unit for the allocation, and the
unit's seats are then split between them by D'Hondt.
"""

import numpy as np

THRESHOLD = 0.0325
SEATS = 120

# Surplus-vote agreements, by ballot letters.
AGREEMENTS = {
    25: [("מחל", "ט"), ("פה", "כן"), ("שס", "ג"), ("אמת", "מרצ")],
    26: [("מחל", "ט"), ("דרך", "אמת"), ("רק", "ל"), ("ודם", "עם"), ("שס", "ג")],
}


def _dhondt(votes: list[float], seats: int) -> list[int]:
    v = np.array(votes, dtype=float)
    won = np.zeros(len(v), dtype=int)
    for _ in range(seats):
        won[np.argmax(v / (won + 1))] += 1
    return won.tolist()


def allocate(votes: dict[str, float], agreements=(), threshold: float = THRESHOLD,
             seats: int = SEATS) -> dict[str, int]:
    """Seats per list from valid votes per list (all lists, including those below the threshold)."""
    total = sum(votes.values())
    passing = {k: v for k, v in votes.items() if v >= threshold * total}
    units, seen = [], set()
    for a, b in agreements:
        members = [m for m in (a, b) if m in passing]
        if members:
            units.append(members)
            seen.update(members)
    units += [[k] for k in passing if k not in seen]
    unit_seats = _dhondt([sum(passing[m] for m in u) for u in units], seats)
    out = {}
    for unit, n in zip(units, unit_seats):
        out.update(zip(unit, _dhondt([passing[m] for m in unit], n)))
    return out
