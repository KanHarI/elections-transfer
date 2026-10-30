"""Why the Netanyahu bloc (Likud, RZ/Otzma, Shas, UTJ) fell from 64 to 53 seats.

Seats are ~120 × C / P, where C is the bloc's votes and P the votes of all lists
that passed the threshold. Every estimated flow of people from a 2022 group to a
2026 group changes C, P or both; its seat effect is linearised at the midpoint
of the two elections:

    effect = 120 × (ΔC / P̄ − C̄ · ΔP / P̄²)

Each flow is assigned to exactly one cause, so the causes add up to the
vote-driven change (120·C26/P26 − 120·C22/P22). What is left is seat arithmetic:
rounding in the D'Hondt allocation, surplus-vote agreements and the final count.

The same formula with C restricted to one half of the bloc (Charedi lists, or
Likud/RZ/Otzma) splits every effect between the two halves; the halves add up
to the bloc.
"""

import pickle

import numpy as np
import pandas as pd

from . import data
from .dataset import Dataset
from .export import RESULTS

COAL22, COAL26 = {"מחל", "ט", "שס", "ג"}, {"מחל", "ב", "ט", "שס", "ג"}
CHAREDI = {"שס", "ג"}
NONCHAREDI22, NONCHAREDI26 = COAL22 - CHAREDI, COAL26 - CHAREDI  # Likud, RZ (+ Otzma in 2026)
CHANGE22, CHANGE26 = {"פה", "כן", "ל", "אמת"}, {"דרך", "רק", "אמת", "ל"}
ARAB22, ARAB26 = {"עם", "ום"}, {"ודם", "עם"}
MERETZ, BALAD, JEWISH_HOME = "מרצ", "ד", "ב"
RESERVISTS, AMCHA = "די", "ך"


def _group(i: str, j: str) -> str:
    """Cause for a flow from 2022 category i to 2026 category j (ballot letters or specials)."""
    voted22 = i not in ("ABSTAIN", "NEW", "INVALID")
    if i in COAL22:
        if i in CHAREDI and j in NONCHAREDI26:
            return "Charedi lists → Likud/Otzma/RZ"
        if i in NONCHAREDI22 and j in CHAREDI:
            return "Likud/RZ → Charedi lists"
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

    pass22, pass26 = COAL22 | CHANGE22 | ARAB22, COAL26 | CHANGE26 | ARAB26
    col = flows.sum(0)

    def votes26_of(letters):
        return float(sum(col[j] for j, c in enumerate(cats26) if c in letters))

    p22, p26 = votes_of(pass22), votes26_of(pass26)
    p_mid = (p22 + p26) / 2
    halves = {  # name: (2022 lists, 2026 lists)
        "charedi": (CHAREDI, CHAREDI),
        "noncharedi": (NONCHAREDI22, NONCHAREDI26),
    }
    mids = {h: (votes_of(l22) + votes26_of(l26)) / 2 for h, (l22, l26) in halves.items()}

    def effects(amount, i, j, removed=False):
        dp = (0 if removed else (j in pass26)) - (i in pass22)
        return {f"seats_{h}": 120 * amount * (((0 if removed else (j in l26)) - (i in l22)) / p_mid
                                               - mids[h] * dp / p_mid**2)
                for h, (l22, l26) in halves.items()}

    rows = []
    for a, i in enumerate(cats22):
        for b, j in enumerate(cats26):
            rows.append({"cause": _group(i, j), "from": i, "to": j, "people": flows[a, b],
                         **effects(flows[a, b], i, j)})
        if i in parties22:  # people removed from shrinking clusters (moved away / died)
            removed = float(votes22[i]) - flows[a].sum()
            rows.append({"cause": "Population turnover in shrinking areas", "from": i, "to": "removed",
                         "people": removed, **effects(removed, i, None, removed=True)})
    df = pd.DataFrame(rows)
    df["seats"] = df.seats_charedi + df.seats_noncharedi
    c22, c26 = votes_of(COAL22), votes26_of(COAL26)
    df.attrs.update(
        c22=c22, p22=p22, c26=c26, p26=p26, p_mid=p_mid, mids=mids,
        vote_driven=120 * c26 / p26 - 120 * c22 / p22,
        vote_driven_charedi=120 * votes26_of(CHAREDI) / p26 - 120 * votes_of(CHAREDI) / p22,
        vote_driven_noncharedi=120 * votes26_of(NONCHAREDI26) / p26 - 120 * votes_of(NONCHAREDI22) / p22,
    )
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
    "Charedi lists → Likud/Otzma/RZ (net)": ["Charedi lists → Likud/Otzma/RZ", "Likud/RZ → Charedi lists"],
    "2022 non-voters, excluding Arab lists": ["2022 non-voters → Bibi bloc", "2022 non-voters → Change bloc"],
    "New voters (net), excluding Arab lists": ["New voters → Bibi bloc", "New voters → Change bloc"],
    "Charedi turnout below other Jewish areas": [],  # filled by charedi_turnout_gap()
    "Change-bloc votes burned (Reservists, Amcha, small lists)": [
        "Burned: Change-bloc voters → Reservists/Amcha/small lists"],
    "Jewish Home (burned in 2022) voters returning": ["Jewish Home (burned in 2022) voters return"],
    "Voters who stayed home in 2026": [
        "Charedi-list voters stayed home", "Likud/RZ voters stayed home", "Change-bloc voters stayed home"],
    "Other (population churn, small lists, invalid)": [
        "Other", "Population turnover in shrinking areas", "Other switching", "Moves inside the Bibi bloc"],
}
MOBILISATION_ROWS = ("2022 non-voters, excluding Arab lists", "New voters (net), excluding Arab lists")
SEAT_COLUMNS = ("seats_charedi", "seats_noncharedi", "seats")


def charedi_turnout_gap(attrs: dict, min_share: float = 0.6) -> dict:
    """Votes not cast because turnout in Charedi-majority polling places rose less
    than in other Jewish ones (neither Charedi- nor Arab-majority), valued at how
    Charedi-majority places actually voted in 2026. Model-free."""
    t = _clusters_by_camp(min_share)
    ch = t[t.camp == "Charedi (Shas + UTJ)"]
    other = t[~t.camp.isin(["Charedi (Shas + UTJ)", "Arab (Ra'am + Hadash–Ta'al + Balad)"])]
    rise = lambda d: d.v26.sum() / d.bzb26.sum() - d.v22.sum() / d.bzb22.sum()
    missing = ch.bzb26.sum() * (ch.v22.sum() / ch.bzb22.sum() + rise(other)) - ch.v26.sum()
    valid = missing * ch.valid26.sum() / ch.v26.sum()
    share = {k: ch[f"votes26_{k}"].sum() / ch.valid26.sum() for k in ("charedi", "noncharedi", "passing")}
    p_mid, mids = attrs["p_mid"], attrs["mids"]
    seats = {f"seats_{h}": 120 * valid * (share[h] / p_mid - mids[h] * share["passing"] / p_mid**2)
             for h in ("charedi", "noncharedi")}
    seats["seats"] = seats["seats_charedi"] + seats["seats_noncharedi"]
    return {"missing_voters": missing, "rise_charedi": rise(ch), "rise_other": rise(other), "shares": share, **seats}


def summary() -> dict[str, pd.DataFrame]:
    """Per model: seats per report row, split into Charedi lists and Likud/Otzma/RZ.

    The mobilisation rows are counted as if Charedi-majority areas' turnout had
    risen like other Jewish areas'; the Charedi-turnout row is the difference, so
    the rows still add up to the actual change."""
    out = {}
    for key, df in report().items():
        gap = charedi_turnout_gap(df.attrs)
        rows = []
        for row, causes in ROWS.items():
            sub = df[df.cause.isin(causes)]
            rec = {"row": row, "people": sub[sub.seats.abs() > 1e-9].people.sum()}
            rec.update({c: sub[c].sum() for c in SEAT_COLUMNS})
            rows.append(rec)
        table = pd.DataFrame(rows).set_index("row")
        # Move the missing Charedi votes out of the mobilisation rows, in proportion
        # to how many new / returning voters each row sent to the Charedi lists.
        intake = df[df["from"].isin(["ABSTAIN", "NEW"]) & df["to"].isin(CHAREDI)].groupby("from").people.sum()
        weights = {MOBILISATION_ROWS[0]: intake.get("ABSTAIN", 0), MOBILISATION_ROWS[1]: intake.get("NEW", 0)}
        total = sum(weights.values())
        for row, w in weights.items():
            for c in SEAT_COLUMNS:
                table.loc[row, c] += gap[c] * w / total
        for c in SEAT_COLUMNS:
            table.loc["Charedi turnout below other Jewish areas", c] = -gap[c]
        table.loc["Charedi turnout below other Jewish areas", "people"] = -gap["missing_voters"]
        table.attrs = {**df.attrs, "gap": gap}
        out[key] = table
    return out


def _clusters_by_camp(min_share: float = 0.6) -> pd.DataFrame:
    """Per cluster: registered voters, voters and 2026 votes by bloc half, plus the
    camp holding a `min_share` majority of its 2022 valid votes (regular boxes only)."""
    from . import clusters

    b22, _ = data.load(25)
    b26, _ = data.load(26)
    reg22, reg26 = b22[~b22.envelope].copy(), b26[~b26.envelope].copy()
    reg22["cluster"], reg26["cluster"], _ = clusters.build(reg22, reg26)
    g22, g26 = reg22.groupby("cluster"), reg26.groupby("cluster")
    pass26 = [c for c in COAL26 | CHANGE26 | ARAB26]
    t = pd.DataFrame({
        "bzb22": g22.bzb.sum(), "v22": g22.voters.sum(), "valid22": g22.valid.sum(),
        "bzb26": g26.bzb.sum(), "v26": g26.voters.sum(), "valid26": g26.valid.sum(),
        "votes26_charedi": g26[list(CHAREDI)].sum().sum(axis=1),
        "votes26_noncharedi": g26[list(NONCHAREDI26)].sum().sum(axis=1),
        "votes26_passing": g26[pass26].sum().sum(axis=1),
    }).dropna()
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
    return t


def official_seats() -> dict:
    """Seats per election from the vote files: threshold, D'Hondt and surplus
    agreements (reproduces the official 64 and 53)."""
    from . import seats

    out = {}
    for k in (25, 26):
        df, parties = data.load(k)
        s = seats.allocate(df[parties].sum().to_dict(), seats.AGREEMENTS[k])
        coal = COAL22 if k == 25 else COAL26
        out[k] = {"bloc": sum(s.get(p, 0) for p in coal), "charedi": sum(s.get(p, 0) for p in CHAREDI),
                  "noncharedi": sum(s.get(p, 0) for p in coal - CHAREDI)}
    return out


def turnout_by_area(min_share: float = 0.6) -> pd.DataFrame:
    """Model-free: turnout at regular ballot boxes (double envelopes excluded) by the
    cluster's dominant 2022 camp."""
    t = _clusters_by_camp(min_share)
    agg = t.groupby("camp")[["bzb22", "v22", "bzb26", "v26"]].sum()
    agg.loc["All regular boxes"] = t[["bzb22", "v22", "bzb26", "v26"]].sum()
    agg["turnout22"], agg["turnout26"] = agg.v22 / agg.bzb22, agg.v26 / agg.bzb26
    agg["change_pts"] = 100 * (agg.turnout26 - agg.turnout22)
    agg["voters_growth"] = agg.v26 / agg.v22 - 1
    return agg


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    for key, table in summary().items():
        a = table.attrs
        print(f"== {key}: vote-driven {a['vote_driven']:.2f} (Charedi {a['vote_driven_charedi']:.2f}, "
              f"Likud/Otzma/RZ {a['vote_driven_noncharedi']:.2f})")
        print(table.round(2).to_string())
        print("   totals:", table[list(SEAT_COLUMNS)].sum().round(2).to_dict())
        gap = a["gap"]
        print(f"   Charedi turnout gap: rise {gap['rise_charedi']:.3f} vs other Jewish {gap['rise_other']:.3f}; "
              f"missing voters {gap['missing_voters']:,.0f}; 2026 shares {({k: round(v, 3) for k, v in gap['shares'].items()})}")
    print(turnout_by_area().round(3).to_string())
    print("official seats:", official_seats())
