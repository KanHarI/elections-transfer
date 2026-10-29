"""Recovery of planted flows from cluster totals.

Each case defines voter populations. Within a population, a voter's 2022 and
2026 votes are independent draws from that population's two distributions, so
the population contributes p22 ⊗ p26 to the flows. Clusters are random mixtures
of the populations; the models only see each cluster's totals in each election.

Run with `uv run pytest -s` to print the recovered tables.
"""

import numpy as np
import pandas as pd
import pytest

from elections_transfer import models
from elections_transfer.dataset import Dataset

# population: ({2022 list: share}, {2026 list: share})
CASES = {
    # A splits K/L and all go to R; B is all K and splits R/S; C is all M and splits T/R.
    # K's destination depends on the local A:B mix, so no single matrix fits every cluster.
    "three_populations": {
        "A": ({"K": 0.5, "L": 0.5}, {"R": 1.0}),
        "B": ({"K": 1.0}, {"R": 0.5, "S": 0.5}),
        "C": ({"M": 1.0}, {"T": 0.5, "R": 0.5}),
    },
    # Every list draws from every population, and K's voters go mostly to R where A
    # dominates but mostly to S where B dominates. One national matrix can't capture
    # that; a model of voter types can, because pure-ish clusters pin the types down.
    "context_dependent": {
        "A": ({"K": 0.8, "L": 0.2}, {"R": 0.9, "S": 0.1}),
        "B": ({"K": 0.2, "M": 0.8}, {"R": 0.1, "S": 0.9}),
        "C": ({"L": 0.5, "M": 0.5}, {"R": 0.5, "S": 0.5}),
    },
    # Everyone keeps their list (renamed). Anything but the independence model must get this.
    "loyal": {
        "A": ({"K": 1.0}, {"R": 1.0}),
        "B": ({"L": 1.0}, {"S": 1.0}),
        "C": ({"M": 1.0}, {"T": 1.0}),
    },
}

TOLERANCE = 0.03  # max error in any cell of the "% of 2022 list" table


def make(case: str, n_clusters: int = 400, seed: int = 0) -> tuple[Dataset, np.ndarray]:
    pops = list(CASES[case].values())
    c22 = sorted({k for p22, _ in pops for k in p22})
    c26 = sorted({k for _, p26 in pops for k in p26})
    p22 = np.array([[p.get(k, 0.0) for k in c22] for p, _ in pops])
    p26 = np.array([[p.get(k, 0.0) for k in c26] for _, p in pops])

    rng = np.random.default_rng(seed)
    people = rng.dirichlet(np.ones(len(pops)), size=n_clusters) * rng.integers(500, 3000, size=n_clusters)[:, None]
    truth = np.einsum("kp,pi,pj->kij", people, p22, p26)
    ds = Dataset(
        cats22=[f"P:{c}" for c in c22],
        cats26=[f"P:{c}" for c in c26],
        x22=truth.sum(2),
        x26=truth.sum(1),
        clusters=pd.DataFrame({"cluster": np.arange(n_clusters)}),
    )
    return ds, truth


def row_shares(flows: np.ndarray) -> np.ndarray:
    return flows / flows.sum(1, keepdims=True)


def error(result: models.Result, truth: np.ndarray) -> float:
    return float(np.abs(row_shares(result.national) - row_shares(truth.sum(0))).max())


def table(ds: Dataset, flows: np.ndarray) -> str:
    shares = row_shares(flows)
    head = "      " + " ".join(f"{c[2:]:>6}" for c in ds.cats26)
    rows = [f"{r[2:]:>5} " + " ".join(f"{v:6.1%}" for v in row) for r, row in zip(ds.cats22, shares)]
    return "\n".join([head, *rows])


VAE = models.VAEConfig(head="transfer", latent=4, beta=1.0, steps=3000, eval_samples=512, device="cpu")
VAE_TWO = models.VAEConfig(head="two", latent=8, beta=1.0, sharp=0.3, steps=3000, eval_samples=512, device="cpu")

FITTERS = {
    "independent": models.independent,
    "constant": models.constant,
    VAE.name: lambda ds: models.cloud_vae(ds, VAE),
    VAE_TWO.name: lambda ds: models.cloud_vae(ds, VAE_TWO),
}


NOT_IDENTIFIED = pytest.mark.xfail(
    strict=False,
    reason=(
        "Totals are linear in the population mix, so every cluster's 2026 shares are its 2022 "
        "shares times one fixed matrix, here almost a valid transfer matrix (L→R, M→S). The data "
        "can't tell 'populations with no individual loyalty' from 'loyal individuals'; the model's "
        "assumptions pick the loyal story."
    ),
)
RECOVERY_CASES = [
    "three_populations",
    "loyal",
    pytest.param("context_dependent", marks=NOT_IDENTIFIED),
]


@pytest.mark.parametrize("case", RECOVERY_CASES)
@pytest.mark.parametrize("model", [VAE.name, VAE_TWO.name])
def test_vae_recovers_planted_flows(case, model):
    ds, truth = make(case)
    result = FITTERS[model](ds)
    err = error(result, truth)
    print(f"\n[{case}] {model}: max cell error {err:.1%}\ntruth:\n{table(ds, truth.sum(0))}\nrecovered:\n{table(ds, result.national)}")
    assert err < TOLERANCE


@pytest.mark.parametrize("case", CASES)
def test_reference_models(case):
    """Prints how the reference estimators do; asserts only harness sanity on "loyal"."""
    ds, truth = make(case)
    errs = {}
    for name in ("independent", "constant"):
        result = FITTERS[name](ds)
        errs[name] = error(result, truth)
        print(f"\n[{case}] {name}: max cell error {errs[name]:.1%}\n{table(ds, result.national)}")
    if case == "loyal":
        assert errs["constant"] < 0.01 and errs["independent"] > 0.3


def test_untangle_is_not_identifiable():
    """K→R and L→S loyalists plus a population with no loyalty at all produce, in
    every cluster, exactly the totals of a world where everyone is loyal. No
    estimator working from totals can tell these apart, so none is expected to."""
    mixed = {
        "A": ({"K": 1.0}, {"R": 1.0}),
        "B": ({"L": 1.0}, {"S": 1.0}),
        "C": ({"K": 0.5, "L": 0.5}, {"R": 0.5, "S": 0.5}),
    }
    CASES["_untangle"] = mixed
    try:
        ds, truth = make("_untangle")
    finally:
        del CASES["_untangle"]
    loyal = np.zeros_like(truth)
    loyal[:, 0, 0], loyal[:, 1, 1] = ds.x22[:, 0], ds.x22[:, 1]
    assert np.allclose(loyal.sum(2), ds.x22) and np.allclose(loyal.sum(1), ds.x26)
    assert error(models.Result("loyal", loyal), truth) > 0.1
