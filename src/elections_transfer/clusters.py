"""Group ballot boxes into clusters that cover the same voters in both elections.

The CEC groups boxes into polling places ("ריכוז", usually one building). Place
ids within a settlement are mostly stable between elections, while box numbers
are often renumbered (2022's 613.1–613.5 can be 2026's 112.1–112.5 in the same
place). Clusters are built in stages, each only from what the previous stage
left over:

1. Same place id in both elections, with plausible registered-voter growth
   (within GROWTH_TOLERANCE of the national growth).
2. Leftover places linked by either a shared place id or a shared base box number;
   connected components with plausible growth. This catches streets moved
   between neighbouring places.
3. Whatever remains in a settlement becomes one residual cluster per settlement,
   or, if that is still implausible (or one-sided, e.g. a settlement that exists in
   only one election), one residual per regional committee.

Double-envelope ballots form a single cluster of their own (see dataset.py).
"""

import pandas as pd

GROWTH_TOLERANCE = 1.5


class _UnionFind:
    def __init__(self):
        self.parent: dict = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _places(df: pd.DataFrame, election: int) -> pd.DataFrame:
    places = (
        df.groupby(["settlement_code", "place"])
        .agg(settlement_name=("settlement_name", "first"), committee=("committee", "first"), bzb=("bzb", "sum"))
        .reset_index()
    )
    places["election"] = election
    places["node"] = [(election, s, p) for s, p in zip(places.settlement_code, places.place)]
    return places


def _plausible(bzb22: float, bzb26: float, growth: float) -> bool:
    if bzb22 <= 0 or bzb26 <= 0:
        return False
    ratio = bzb26 / bzb22 / growth
    return 1 / GROWTH_TOLERANCE <= ratio <= GROWTH_TOLERANCE


def _accept_components(nodes: pd.DataFrame, links: list[tuple], growth: float, tag: str) -> pd.Series:
    """Union `links` over `nodes`; return a cluster id for nodes in plausible components."""
    uf = _UnionFind()
    for n in nodes.node:
        uf.find(n)
    for a, b in links:
        uf.union(a, b)
    comp = pd.Series([uf.find(n) for n in nodes.node], index=nodes.index)
    sizes = nodes.groupby([comp, nodes.election]).bzb.sum().unstack(fill_value=0)
    ok = {c for c, row in sizes.iterrows() if _plausible(row.get(22, 0), row.get(26, 0), growth)}
    accepted = comp[comp.isin(ok)]
    return accepted.map(lambda c: f"{tag}{c[1]}_{c[2]}_{c[0]}")


def build(b22: pd.DataFrame, b26: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Assign every regular (non-envelope) box to a cluster.

    Returns (cluster id per 2022 box, cluster id per 2026 box, cluster table).
    """
    nodes = pd.concat([_places(b22, 22), _places(b26, 26)], ignore_index=True)
    growth = nodes[nodes.election == 26].bzb.sum() / nodes[nodes.election == 22].bzb.sum()
    nodes["cluster"] = None
    nodes["kind"] = None

    # Stage 1: same place id.
    by_id = [((22, s, p), (26, s, p)) for s, p in zip(nodes.settlement_code, nodes.place)]
    accepted = _accept_components(nodes, by_id, growth, "A")
    nodes.loc[accepted.index, ["cluster", "kind"]] = list(zip(accepted, ["place"] * len(accepted)))

    # Stage 2: leftovers, linked by place id or shared base box number.
    rest = nodes[nodes.cluster.isna()]
    rest_keys = set(rest.node)
    boxes = pd.concat(
        [
            b22[["settlement_code", "base_box", "place"]].drop_duplicates().assign(election=22),
            b26[["settlement_code", "base_box", "place"]].drop_duplicates().assign(election=26),
        ]
    )
    boxes["node"] = [(e, s, p) for e, s, p in zip(boxes.election, boxes.settlement_code, boxes.place)]
    boxes = boxes[boxes.node.isin(rest_keys)]
    by_box = boxes[boxes.election == 22].merge(boxes[boxes.election == 26], on=["settlement_code", "base_box"])
    links = list(zip(by_box.node_x, by_box.node_y)) + [l for l in by_id if l[0] in rest_keys and l[1] in rest_keys]
    accepted = _accept_components(rest, links, growth, "B")
    nodes.loc[accepted.index, ["cluster", "kind"]] = list(zip(accepted, ["place"] * len(accepted)))

    # Stage 3: per-settlement residual, else per-committee residual.
    rest = nodes.cluster.isna()
    nodes.loc[rest, "cluster"] = "S" + nodes.loc[rest, "settlement_code"].astype(str)
    nodes.loc[rest, "kind"] = "settlement"
    res = nodes[rest].groupby(["cluster", "election"]).bzb.sum().unstack(fill_value=0)
    bad = {c for c, row in res.iterrows() if not _plausible(row.get(22, 0), row.get(26, 0), growth)}
    to_committee = nodes.cluster.isin(bad)
    nodes.loc[to_committee, "cluster"] = "C" + nodes.loc[to_committee, "committee"].astype(str)
    nodes.loc[to_committee, "kind"] = "committee"

    # Readable ids for place clusters: settlement code + running number.
    renamed = {}
    for s, grp in nodes[nodes.kind == "place"].groupby("settlement_code"):
        first_place = grp.groupby("cluster").place.min().sort_values()
        renamed.update({c: f"{s}-{i + 1}" for i, c in enumerate(first_place.index)})
    nodes["cluster"] = nodes.cluster.map(lambda c: renamed.get(c, c))

    key = nodes.set_index("node").cluster
    c22 = pd.Series([key[(22, s, p)] for s, p in zip(b22.settlement_code, b22.place)], index=b22.index)
    c26 = pd.Series([key[(26, s, p)] for s, p in zip(b26.settlement_code, b26.place)], index=b26.index)

    # Name a cluster after its 2026 settlement (spellings differ slightly between files).
    nodes = nodes.sort_values("election", ascending=False)
    table = (
        nodes.groupby("cluster")
        .agg(
            kind=("kind", "first"),
            settlement_code=("settlement_code", lambda s: s.iloc[0] if s.nunique() == 1 else -1),
            settlement_name=("settlement_name", "first"),
            committee=("committee", "first"),
            places22=("election", lambda e: int((e == 22).sum())),
            places26=("election", lambda e: int((e == 26).sum())),
        )
        .reset_index()
    )
    table.loc[table.settlement_code == -1, "settlement_name"] = ""
    return c22, c26, table
