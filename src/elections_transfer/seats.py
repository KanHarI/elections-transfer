"""Knesset seat allocation: 3.25% threshold, then D'Hondt (Bader-Ofer) over 120 seats.

Surplus-vote agreements are ignored, so a list can be off by one seat from the
official result.
"""

import numpy as np

THRESHOLD = 0.0325
SEATS = 120


def allocate(votes: dict[str, float], threshold: float = THRESHOLD, seats: int = SEATS) -> dict[str, int]:
    """Seats per list from valid votes per list (all lists, including those below the threshold)."""
    total = sum(votes.values())
    passing = {k: v for k, v in votes.items() if v >= threshold * total}
    names = list(passing)
    v = np.array([passing[k] for k in names], dtype=float)
    won = np.zeros(len(names), dtype=int)
    for _ in range(seats):
        won[np.argmax(v / (won + 1))] += 1
    return {k: int(s) for k, s in zip(names, won)}
