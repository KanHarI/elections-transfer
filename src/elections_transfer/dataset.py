"""Per-cluster category counts for both elections.

Every cluster gets a closed population: each person is in exactly one 2022
category and one 2026 category, so both rows of counts sum to the same N.

2022 categories: lists ≥ threshold, OTHER, INVALID, ABSTAIN, NEW
2026 categories: lists ≥ threshold, OTHER, INVALID, ABSTAIN

Only the vote files are used. They give each cluster's registered voters in both
elections, so only the net change is known: people who turned 18 (or arrived)
minus people who died (or left). A cluster that grew gets that growth as NEW, "new
voters (net)". A cluster that shrank has more people in 2022 than in 2026; the
difference is removed evenly from all its 2022 categories. People who died are
therefore treated as replaced by new voters.

Double-envelope voters (soldiers, diplomats, hospital patients, prisoners...) are
counted in their own cluster, but they also stay on their home box's roll, where
they look like abstainers. To avoid counting them twice, each election's envelope
total is removed from the regular clusters' ABSTAIN, in proportion to registered
voters (capped at a cluster's actual abstainers).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import clusters, data
from .parties import SMALL_PARTY_THRESHOLD

ENVELOPE_CLUSTER = "ENVELOPES"


@dataclass
class Dataset:
    cats22: list[str]
    cats26: list[str]
    x22: np.ndarray  # (K, C22) counts
    x26: np.ndarray  # (K, C26) counts
    clusters: pd.DataFrame  # K rows, aligned with x22/x26
    summary: dict = field(default_factory=dict)

    @property
    def n(self) -> np.ndarray:
        return self.x22.sum(1)


def _big_parties(df: pd.DataFrame, parties: list[str]) -> list[str]:
    share = df[parties].sum() / df["valid"].sum()
    return share[share >= SMALL_PARTY_THRESHOLD].sort_values(ascending=False).index.tolist()


def _counts(df: pd.DataFrame, parties: list[str], keep: list[str]) -> pd.DataFrame:
    g = df.groupby("cluster")
    out = g[keep].sum().rename(columns=lambda p: f"P:{p}")
    out["OTHER"] = g[[p for p in parties if p not in keep]].sum().sum(axis=1)
    out["INVALID"] = g["invalid"].sum()
    out["ABSTAIN"] = g["bzb"].sum() - g["voters"].sum()
    out["_bzb"] = g["bzb"].sum()
    out["_voters"] = g["voters"].sum()
    out["_boxes"] = g.size()
    return out


def _remove_envelopes(abstain: pd.Series, bzb: pd.Series, total: float) -> pd.Series:
    """Split `total` over clusters ∝ bzb, never exceeding a cluster's abstainers."""
    alloc = pd.Series(0.0, index=abstain.index)
    room = abstain.astype(float).copy()
    left = float(total)
    for _ in range(50):
        open_ = room > 1e-9
        if left <= 1e-6 or not open_.any():
            break
        share = bzb[open_] / bzb[open_].sum() * left
        take = np.minimum(share, room[open_])
        alloc[open_] += take
        room[open_] -= take
        left -= take.sum()
    return alloc


def _close_envelopes(k: pd.DataFrame, env_total: float) -> pd.Series:
    """Give the envelope cluster no abstainers and take its voters out of home-box
    abstainers (in place). Returns each cluster's population for that election."""
    k["ABSTAIN"] = k["ABSTAIN"].astype(float)
    k.loc[ENVELOPE_CLUSTER, "ABSTAIN"] = 0.0
    regular = k.index != ENVELOPE_CLUSTER
    alloc = _remove_envelopes(k.loc[regular, "ABSTAIN"], k.loc[regular, "_bzb"], env_total)
    k.loc[regular, "ABSTAIN"] -= alloc
    size = k["_bzb"].astype(float) - alloc.reindex(k.index, fill_value=0.0)
    size[ENVELOPE_CLUSTER] = float(k.loc[ENVELOPE_CLUSTER, "_voters"])
    return size


def build() -> Dataset:
    b22, parties22 = data.load(25)
    b26, parties26 = data.load(26)
    keep22, keep26 = _big_parties(b22, parties22), _big_parties(b26, parties26)

    reg22, reg26 = b22[~b22.envelope].copy(), b26[~b26.envelope].copy()
    reg22["cluster"], reg26["cluster"], table = clusters.build(reg22, reg26)
    env22, env26 = b22[b22.envelope].assign(cluster=ENVELOPE_CLUSTER), b26[b26.envelope].assign(cluster=ENVELOPE_CLUSTER)

    k22 = pd.concat([_counts(reg22, parties22, keep22), _counts(env22, parties22, keep22)])
    k26 = pd.concat([_counts(reg26, parties26, keep26), _counts(env26, parties26, keep26)])
    k22, k26 = k22.align(k26, join="outer", axis=0, fill_value=0)

    pop22 = _close_envelopes(k22, env22.voters.sum())
    pop26 = _close_envelopes(k26, env26.voters.sum())

    growth = pop26 - pop22
    k22["NEW"] = growth.clip(lower=0)

    cats22 = [f"P:{p}" for p in keep22] + ["OTHER", "INVALID", "ABSTAIN", "NEW"]
    cats26 = [f"P:{p}" for p in keep26] + ["OTHER", "INVALID", "ABSTAIN"]
    x22, x26 = k22[cats22].to_numpy(float), k26[cats26].to_numpy(float)
    # Shrinking clusters: remove the difference evenly from every 2022 category.
    shrink = (growth < 0).to_numpy()
    x22[shrink] *= (pop26[shrink] / pop22[shrink]).to_numpy()[:, None]
    assert np.allclose(x22.sum(1), x26.sum(1), rtol=1e-9, atol=1e-6), "cluster populations don't close"
    assert (x22 >= -1e-9).all() and (x26 >= -1e-9).all()

    meta = table.set_index("cluster").reindex(k22.index)
    meta.loc[ENVELOPE_CLUSTER, ["kind", "settlement_code", "settlement_name", "committee"]] = [
        "envelope", data.ENVELOPE_SETTLEMENT, "מעטפות חיצוניות", 0
    ]
    meta = meta.assign(
        bzb22=k22["_bzb"], bzb26=k26["_bzb"], voters22=k22["_voters"], voters26=k26["_voters"],
        boxes22=k22["_boxes"], boxes26=k26["_boxes"],
    ).reset_index(names="cluster")
    meta["settlement_code"] = meta.settlement_code.astype(int)
    meta["committee"] = meta.committee.astype(int)

    by_kind = meta.groupby("kind")[["bzb22", "bzb26"]].sum()
    summary = {
        "clusters": int(len(meta)),
        "clusters_by_kind": meta.kind.value_counts().to_dict(),
        "bzb_share_by_kind": (by_kind.bzb26 / by_kind.bzb26.sum()).round(4).to_dict(),
        "envelope_voters": {"2022": int(env22.voters.sum()), "2026": int(env26.voters.sum())},
        "registered": {"2022": int(b22.bzb.sum()), "2026": int(b26.bzb.sum())},
        "voters": {"2022": int(b22.voters.sum()), "2026": int(b26.voters.sum())},
        "new_voters_net": float(growth.clip(lower=0).sum()),
        "shrink_removed": float(-growth.clip(upper=0).sum()),
        "shrinking_clusters": int(shrink.sum()),
        "small_party_threshold": SMALL_PARTY_THRESHOLD,
    }
    return Dataset(cats22, cats26, x22, x26, meta, summary)
