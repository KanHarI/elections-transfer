"""Why the Netanyahu bloc (Likud, RZ/Otzma, Shas, UTJ) fell from 64 to 53 seats.

Seats are ~120 × C / P, where C is the bloc's votes and P the votes of all lists
that passed the threshold. Every estimated flow of people from a 2022 group to a
2026 group changes C, P or both; its seat effect is linearised at the midpoint
of the two elections:

    effect = 120 × (ΔC / P̄ − C̄ · ΔP / P̄²)

Each flow is assigned to exactly one cause, so the causes add up to the
vote-driven change (120·C26/P26 − 120·C22/P22). What is left is seat arithmetic:
rounding in the D'Hondt allocation, surplus-vote agreements and the final count.
"""

import pickle

import numpy as np
import pandas as pd

from . import data
from .dataset import Dataset
from .export import RESULTS

COAL22, COAL26 = {"מחל", "ט", "שס", "ג"}, {"מחל", "ב", "ט", "שס", "ג"}
CHAREDI = {"שס", "ג"}
CHANGE22, CHANGE26 = {"פה", "כן", "ל", "אמת"}, {"דרך", "רק", "אמת", "ל"}
ARAB22, ARAB26 = {"עם", "ום"}, {"ודם", "עם"}
MERETZ, BALAD, JEWISH_HOME = "מרצ", "ד", "ב"
RESERVISTS, AMCHA = "די", "ך"


def _group(i: str, j: str) -> str:
    """Cause for a flow from 2022 category i to 2026 category j (ballot letters or specials)."""
    voted22 = i not in ("ABSTAIN", "NEW", "INVALID")
    if i in COAL22:
        if j in COAL26:
            return "Moves inside the Bibi bloc"
        if j in CHANGE26:
            return "Bibi bloc → Change bloc"
        if j == AMCHA:
            return "Burned: Bibi-bloc voters → Amcha Yisrael"
        if j == RESERVISTS:
            return "Burned: Bibi-bloc voters → Reservists"
        if j == "OTHER":
            return "Burned: Bibi-bloc voters → other small lists"
        if j in ("ABSTAIN", "INVALID"):
            return "Charedi-list voters stayed home" if i in CHAREDI else "Likud/RZ voters stayed home"
        return "Other switching"
    if i in CHANGE22:
        if j in COAL26:
            return "Change bloc → Bibi bloc"
        if j in (AMCHA, RESERVISTS, "OTHER"):
            return "Burned: Change-bloc voters → Reservists/Amcha/small lists"
        if j in ("ABSTAIN", "INVALID"):
            return "Change-bloc voters stayed home"
        return "Other switching"
    if j in ARAB26 and i not in ARAB22 and i != BALAD and not voted22:
        return "Arab turnout: new and returning voters"
    if i in ARAB22 and j in ("ABSTAIN", "INVALID"):
        return "Arab turnout: 2022 Arab voters stayed home"
    if i == MERETZ:
        return "Meretz no longer burned (→ Democrats etc.)"
    if i == BALAD:
        return "Balad no longer burned (→ Joint List etc.)"
    if i == JEWISH_HOME:
        return "Jewish Home (burned in 2022) voters return"
    if i == "NEW":
        return "New voters → Bibi bloc" if j in COAL26 else "New voters → Change bloc" if j in CHANGE26 else "Other"
    if i == "ABSTAIN":
        return ("2022 non-voters → Bibi bloc" if j in COAL26 else
                "2022 non-voters → Change bloc" if j in CHANGE26 else "Other")
    return "Other"


def decompose(ds: Dataset, flows: np.ndarray) -> pd.DataFrame:
    """Seat effect per cause for national flows (C22 × C26) of one model."""
    cats22 = [c.removeprefix("P:") for c in ds.cats22]
    cats26 = [c.removeprefix("P:") for c in ds.cats26]
    actual22, parties22 = data.load(25)
    votes22 = actual22[parties22].sum()

    # 2022 totals: the model's rows exclude people removed from shrinking clusters.
    def votes_of(letters):
        return float(votes22[list(letters)].sum())

    pass22 = COAL22 | CHANGE22 | ARAB22
    c22, p22 = votes_of(COAL22), votes_of(pass22)
    col = flows.sum(0)
    c26 = sum(col[j] for j, c in enumerate(cats26) if c in COAL26)
    p26 = sum(col[j] for j, c in enumerate(cats26) if c in COAL26 | CHANGE26 | ARAB26)
    c_mid, p_mid = (c22 + c26) / 2, (p22 + p26) / 2

    def effect(amount, dc, dp):
        return 120 * amount * (dc / p_mid - c_mid * dp / p_mid**2)

    rows = []
    for a, i in enumerate(cats22):
        for b, j in enumerate(cats26):
            dc = (j in COAL26) - (i in COAL22)
            dp = (j in COAL26 | CHANGE26 | ARAB26) - (i in pass22)
            rows.append({"cause": _group(i, j), "from": i, "to": j, "people": flows[a, b],
                         "seats": effect(flows[a, b], dc, dp)})
        if i in parties22:  # people removed from shrinking clusters (moved away / died)
            removed = float(votes22[i]) - flows[a].sum()
            rows.append({"cause": "Population turnover in shrinking areas", "from": i, "to": "removed",
                         "people": removed, "seats": effect(removed, -(i in COAL22), -(i in pass22))})
    df = pd.DataFrame(rows)
    df.attrs.update(c22=c22, p22=p22, c26=c26, p26=p26,
                    vote_driven=120 * c26 / p26 - 120 * c22 / p22)
    return df


def report(models_wanted=("vae", "constant")) -> dict[str, pd.DataFrame]:
    with open(RESULTS / "fits.pkl", "rb") as f:
        saved = pickle.load(f)
    ds = saved["dataset"]
    out = {}
    for r in saved["fits"]:
        key = "vae" if r.name.startswith("vae_") else r.name
        if key in models_wanted:
            out[key] = decompose(ds, r.national)
    return out


# Report rows: each groups one or more causes from _group.
ROWS = {
    "Arab turnout surge": ["Arab turnout: new and returning voters", "Arab turnout: 2022 Arab voters stayed home"],
    "Meretz no longer burned": ["Meretz no longer burned (→ Democrats etc.)"],
    "Balad no longer burned": ["Balad no longer burned (→ Joint List etc.)"],
    "Bibi-bloc votes burned (Reservists, Amcha, small lists)": [
        "Burned: Bibi-bloc voters → Reservists", "Burned: Bibi-bloc voters → Amcha Yisrael",
        "Burned: Bibi-bloc voters → other small lists"],
    "Bibi bloc ↔ Change bloc switching (net)": ["Bibi bloc → Change bloc", "Change bloc → Bibi bloc"],
    "2022 non-voters, excluding Arab lists": ["2022 non-voters → Bibi bloc", "2022 non-voters → Change bloc"],
    "New voters (net), excluding Arab lists": ["New voters → Bibi bloc", "New voters → Change bloc"],
    "Change-bloc votes burned (Reservists, Amcha, small lists)": [
        "Burned: Change-bloc voters → Reservists/Amcha/small lists"],
    "Jewish Home (burned in 2022) voters returning": ["Jewish Home (burned in 2022) voters return"],
    "Voters who stayed home in 2026": [
        "Charedi-list voters stayed home", "Likud/RZ voters stayed home", "Change-bloc voters stayed home"],
    "Other (population churn, small lists, invalid)": [
        "Other", "Population turnover in shrinking areas", "Other switching", "Moves inside the Bibi bloc"],
}


def summary() -> pd.DataFrame:
    """Seats per report row for the VAE and the constant matrix, plus each cause's seats."""
    res = report()
    out = []
    for row, causes in ROWS.items():
        rec = {"row": row}
        for key, df in res.items():
            sub = df[df.cause.isin(causes)]
            rec[f"{key}_seats"] = sub.seats.sum()
            rec[f"{key}_people"] = sub[sub.seats != 0].people.sum()
        out.append(rec)
    table = pd.DataFrame(out).set_index("row")
    table.attrs = res["vae"].attrs
    return table


def turnout_by_area(min_share: float = 0.6) -> pd.DataFrame:
    """Model-free: turnout at regular ballot boxes (double envelopes excluded) by the
    cluster's dominant 2022 camp."""
    from . import clusters

    b22, _ = data.load(25)
    b26, _ = data.load(26)
    reg22, reg26 = b22[~b22.envelope].copy(), b26[~b26.envelope].copy()
    reg22["cluster"], reg26["cluster"], _ = clusters.build(reg22, reg26)
    g22, g26 = reg22.groupby("cluster"), reg26.groupby("cluster")
    t = pd.DataFrame({"bzb22": g22.bzb.sum(), "v22": g22.voters.sum(), "valid22": g22.valid.sum(),
                      "bzb26": g26.bzb.sum(), "v26": g26.voters.sum()}).dropna()
    camps = {
        "Charedi (Shas + UTJ)": ["שס", "ג"],
        "Arab (Ra'am + Hadash–Ta'al + Balad)": ["עם", "ום", "ד"],
        "Change (YA + NU + YB + Labor + Meretz)": ["פה", "כן", "ל", "אמת", "מרצ"],
        "Right (Likud + RZ + Jewish Home)": ["מחל", "ט", "ב"],
    }
    t["camp"] = "Mixed"
    for name, letters in camps.items():
        share = g22[letters].sum().sum(axis=1).reindex(t.index) / t.valid22
        t.loc[share >= min_share, "camp"] = name
    agg = t.groupby("camp")[["bzb22", "v22", "bzb26", "v26"]].sum()
    agg.loc["All regular boxes"] = t[["bzb22", "v22", "bzb26", "v26"]].sum()
    agg["turnout22"], agg["turnout26"] = agg.v22 / agg.bzb22, agg.v26 / agg.bzb26
    agg["change_pts"] = 100 * (agg.turnout26 - agg.turnout22)
    agg["voters_growth"] = agg.v26 / agg.v22 - 1
    return agg


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    s = summary()
    a = s.attrs
    print(f"vote-driven change {a['vote_driven']:.2f} seats (120·C/P: {120 * a['c22'] / a['p22']:.2f} → "
          f"{120 * a['c26'] / a['p26']:.2f})")
    s["mean_seats"] = s[["vae_seats", "constant_seats"]].mean(axis=1)
    print(s.round(2).to_string())
    print("totals:", s[["vae_seats", "constant_seats", "mean_seats"]].sum().round(2).to_dict())
    print(turnout_by_area().round(3).to_string())
