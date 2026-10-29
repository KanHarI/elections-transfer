"""Recovery test: plant known flows in data shaped like the real clusters, then
check how well each estimator recovers them from the aggregates alone.

Regimes (all start from T*, the constant-matrix fit to the real data, so the
magnitudes are realistic):

- uniform:    every cluster's transfer rows are T* plus Dirichlet noise. The
              constant model's own assumption, so it should do well here.
- contextual: transfer rows shift systematically with the cluster's 2022 vote mix
              (its top principal components), plus noise. Constant-matrix
              regression is known to be biased in this case.
- latent:     clusters are mixtures of latent voter classes, each class with its
              own 2022 vote distribution and its own transfer rows. 2022 counts
              are synthetic too.

Truth is drawn voter by voter (multinomial), so it includes sampling noise.
"""

from dataclasses import replace

import numpy as np
import pandas as pd

from . import models
from .dataset import Dataset

REGIMES = ("uniform", "contextual", "latent")


def _dirichlet_rows(rng, probs: np.ndarray, conc: float) -> np.ndarray:
    """Dirichlet draw per row around `probs`; structural zeros stay zero."""
    alpha = np.where(probs > 0, conc * probs + 1e-3, 0)
    g = rng.gamma(np.where(alpha > 0, alpha, 1.0)) * (alpha > 0)
    return g / g.sum(-1, keepdims=True)


def _draw_flows(rng, x22: np.ndarray, t: np.ndarray) -> np.ndarray:
    """x22: (K, I) integer counts, t: (K, I, J) rows → (K, I, J) integer flows."""
    k, i, j = t.shape
    flat_n = x22.reshape(-1).astype(np.int64)
    flat_p = t.reshape(-1, j)
    flat_p = flat_p / flat_p.sum(1, keepdims=True)
    return rng.multinomial(flat_n, flat_p).reshape(k, i, j).astype(float)


def make(ds: Dataset, t_star: np.ndarray, regime: str, seed: int = 0) -> tuple[Dataset, np.ndarray]:
    rng = np.random.default_rng(seed)
    k, c22 = ds.x22.shape
    x22 = np.rint(ds.x22)

    if regime == "uniform":
        t = _dirichlet_rows(rng, np.broadcast_to(t_star, (k, *t_star.shape)), conc=40.0)

    elif regime == "contextual":
        s22 = x22 / np.maximum(x22.sum(1, keepdims=True), 1)
        centered = s22 - s22.mean(0)
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        f = centered @ vt[:3].T
        f = f / f.std(0)
        b = rng.normal(0, 0.8, size=(3, *t_star.shape))
        logits = np.log(np.maximum(t_star, 1e-12))[None] + np.einsum("kf,fij->kij", f, b)
        logits = np.where(t_star[None] > 0, logits, -np.inf)
        base = np.exp(logits - logits.max(-1, keepdims=True))
        base /= base.sum(-1, keepdims=True)
        t = _dirichlet_rows(rng, base, conc=80.0)

    elif regime == "latent":
        n_classes = 15
        nat22 = ds.x22.sum(0) / ds.x22.sum()
        class22 = rng.dirichlet(nat22 * 3 + 0.02, size=n_classes)  # each class leans to a few lists
        class_t = _dirichlet_rows(rng, np.broadcast_to(t_star, (n_classes, *t_star.shape)), conc=15.0)
        w = rng.dirichlet(np.full(n_classes, 0.25), size=k)
        n = np.rint(ds.n).astype(np.int64)
        members = np.stack([rng.multinomial(n_k, w_k) for n_k, w_k in zip(n, w)])  # (K, L)
        flows = np.zeros((k, c22, t_star.shape[1]))
        x22 = np.zeros((k, c22))
        for c in range(n_classes):
            xc = np.stack([rng.multinomial(m, class22[c]) for m in members[:, c]]).astype(float)
            x22 += xc
            flows += _draw_flows(rng, xc, np.broadcast_to(class_t[c], (k, *t_star.shape)))
        syn = replace(ds, x22=flows.sum(2), x26=flows.sum(1))
        return syn, flows

    else:
        raise ValueError(regime)

    flows = _draw_flows(rng, x22, t)
    return replace(ds, x22=flows.sum(2), x26=flows.sum(1)), flows


def score(est: np.ndarray, truth: np.ndarray, cats22: list[str]) -> dict:
    """Errors as shares of people misallocated (total variation distance)."""
    f_hat, f = est.sum(0), truth.sum(0)
    total = f.sum()
    rows = f.sum(1)
    row_tv = 0.5 * np.abs(f_hat / np.maximum(f_hat.sum(1, keepdims=True), 1e-9) - f / np.maximum(rows[:, None], 1e-9)).sum(1)
    party = np.array([c.startswith("P:") for c in cats22])
    n_k = truth.sum((1, 2))
    cluster_tv = 0.5 * np.abs(est - truth).sum((1, 2)) / np.maximum(n_k, 1)
    return {
        "national_tv": float(0.5 * np.abs(f_hat - f).sum() / total),
        "row_tv": float((row_tv * rows).sum() / rows.sum()),
        "party_row_tv": float((row_tv[party] * rows[party]).sum() / rows[party].sum()),
        "cluster_tv": float((cluster_tv * n_k).sum() / n_k.sum()),
    }


def run(ds: Dataset, vae_configs: list[models.VAEConfig], regimes=REGIMES, seed: int = 0, log=print,
        out=None) -> pd.DataFrame:
    """Fit every estimator on every regime. If `out` is a path, the table is
    rewritten after each fit so partial results survive an interruption."""
    t_star = models.constant(ds).info["T"]
    rows = []
    for regime in regimes:
        syn, truth = make(ds, t_star, regime, seed)
        const = models.constant(syn)
        estimators = [("independent", lambda d: models.independent(d)), ("constant", lambda d: const)]
        estimators += [(cfg.name, lambda d, cfg=cfg: models.cloud_vae(d, cfg, t_init=const.info["T"])) for cfg in vae_configs]
        for name, fit in estimators:
            res = fit(syn)
            rows.append({"regime": regime, "model": name, **score(res.flows, truth, syn.cats22)})
            if out is not None:
                pd.DataFrame(rows).to_csv(out, index=False)
            log(f"  {regime:>10} {name:>24}  " + "  ".join(f"{k} {v:.3f}" for k, v in rows[-1].items() if k.endswith("tv")))
    return pd.DataFrame(rows)
