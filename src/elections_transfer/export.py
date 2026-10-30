"""Write the JSON files the web UI reads (web/data/)."""

import json
import pickle
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import data, models
from .data import ROOT
from .dataset import ENVELOPE_CLUSTER, Dataset
from .parties import label

RESULTS = ROOT / "results"
WEB_DATA = ROOT / "web" / "data"

MODEL_TEXT = {
    "vae": (
        "VAE (cloud of voters)",
        "Each polling-place cluster is a Gaussian cloud of voters in a latent space, encoded from its 2022 "
        "results only, with a KL penalty toward N(0, I). {decoder} The sampled voters must reproduce the "
        "cluster's results in both elections.",
    ),
    "constant": (
        "Constant transfer matrix",
        "One transfer matrix for the whole country: every cluster's 2026 result is its 2022 result times "
        "the same matrix (Goodman ecological regression). Simple and robust, but it assumes a list's voters "
        "move the same way everywhere.",
    ),
}


def synthetic_results() -> pd.DataFrame | None:
    """All synthetic runs (results/synthetic*.csv), one row per (regime, model)."""
    frames = [pd.read_csv(p) for p in sorted(RESULTS.glob("synthetic*.csv"))]
    if not frames:
        return None
    return pd.concat(frames).drop_duplicates(["regime", "model"], keep="last").reset_index(drop=True)


VAE_DECODER_TEXT = {
    "two": "A shared decoder gives every sampled voter a 2022 vote and a 2026 vote.",
    "transfer": "A shared decoder gives every sampled voter a 2022 vote and a 2026 transfer row, so transfers "
                "can differ between clusters.",
    "split": "The code has two parts. A detailed description code reconstructs the cluster's 2022 result. A "
             "small, heavily penalized movement code is the only thing allowed to shift the cluster's transfer "
             "matrix away from the national one, so only patterns shared by many clusters survive.",
}


def chosen_config(device: str = "cpu") -> models.VAEConfig:
    """The VAE configuration with the best synthetic recovery (party transfer rows)."""
    df = synthetic_results()
    if df is None:
        return models.VAEConfig(device=device)
    vae = df[df.model.str.startswith("vae_")].groupby("model").party_row_tv.mean().sort_values()
    if vae.empty:
        return models.VAEConfig(device=device)
    return models.VAEConfig.from_name(vae.index[0], device=device)


def _synthetic_rows(synth: pd.DataFrame | None) -> list[dict]:
    """Rows for the comparison table: the constant matrix and VAE runs tested on every regime."""
    if synth is None:
        return []
    shown = synth[synth.model != "independent"]
    complete = shown.groupby("model").regime.nunique() == shown.regime.nunique()
    return shown[shown.model.isin(complete[complete].index)].to_dict(orient="records")


def _nodes(ds: Dataset, knesset: int, cats: list[str], totals: np.ndarray) -> list[dict]:
    out = []
    for c, t in zip(cats, totals):
        p = label(knesset, c)
        out.append({
            "id": c, "en": p.en, "he": p.he, "color": p.color,
            "kind": "party" if c.startswith("P:") else c.lower(), "total": round(float(t)),
        })
    return out


def _matrix(m: np.ndarray) -> list[list[int]]:
    return np.rint(m).astype(int).tolist()


def _areas(ds: Dataset, fits: dict[str, models.Result]) -> list[dict]:
    meta = ds.clusters
    n = ds.n
    areas = []
    env = np.flatnonzero(meta.cluster.to_numpy() == ENVELOPE_CLUSTER)
    areas.append({
        "id": "envelopes", "name": "Double envelopes (soldiers, diplomats, hospitals…)",
        "kind": "envelope", "population": round(float(n[env].sum())), "coverage": 1.0, "clusters": 1,
        "flows": {k: _matrix(r.flows[env].sum(0)) for k, r in fits.items() if k in MODEL_TEXT},
    })
    # Committee residuals span several settlements; a settlement's view covers only
    # clusters that lie entirely inside it.
    inside = meta.kind.isin(["place", "settlement"]).to_numpy()
    for code, grp in meta[inside].groupby("settlement_code"):
        idx = grp.index.to_numpy()
        pop = float(n[idx].sum())
        settlement_total = float(n[meta.settlement_code.to_numpy() == code].sum())
        areas.append({
            "id": f"s{code}", "name": grp.settlement_name.iloc[0],
            "kind": "settlement", "population": round(pop), "clusters": int(len(idx)),
            "coverage": round(pop / settlement_total, 4) if settlement_total else 1.0,
            "flows": {k: _matrix(r.flows[idx].sum(0)) for k, r in fits.items() if k in MODEL_TEXT},
        })
    return areas


def write():
    with open(RESULTS / "fits.pkl", "rb") as f:
        saved = pickle.load(f)
    ds: Dataset = saved["dataset"]
    fits = {}
    for r in saved["fits"]:
        fits["vae" if r.name.startswith("vae_") else r.name] = r

    synth = synthetic_results()
    chosen = next(r.name for r in saved["fits"] if r.name.startswith("vae_"))
    # Default view: whichever of the fitted VAE and the constant matrix recovered
    # planted flows better on average across the synthetic regimes.
    default = "vae"
    if synth is not None:
        mean = synth.groupby("model").party_row_tv.mean()
        if chosen in mean and mean.get("constant", np.inf) < mean[chosen]:
            default = "constant"

    model_entries = []
    for key in ("vae", "constant"):
        r = fits[key]
        title, desc = MODEL_TEXT[key]
        info = {}
        if key == "vae":
            desc = desc.format(decoder=VAE_DECODER_TEXT[r.info["config"]["head"]])
            info = {"config": {k: v for k, v in r.info["config"].items() if k != "device"}, "fit": r.info["fit"]}
        model_entries.append({"id": key, "label": title, "description": desc, "national": _matrix(r.national), "info": info})

    manifests = {k: data.manifest(k) for k in (25, 26)}
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "elections": {
            "from": {"knesset": 25, "year": 2022, "date": data.SOURCES[25]["date"]},
            "to": {"knesset": 26, "year": 2026, "date": data.SOURCES[26]["date"]},
        },
        "sources": manifests,
        "summary": ds.summary,
        "nodes": {
            "from": _nodes(ds, 25, ds.cats22, ds.x22.sum(0)),
            "to": _nodes(ds, 26, ds.cats26, ds.x26.sum(0)),
        },
        "models": model_entries,
        "default_model": default,
        "chosen_vae": chosen,
        "synthetic": _synthetic_rows(synth),
    }
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "results.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=float))
    areas = _areas(ds, fits)
    (WEB_DATA / "areas.json").write_text(json.dumps(areas, ensure_ascii=False, separators=(",", ":")))
    for p in ("results.json", "areas.json"):
        print(f"wrote web/data/{p}: {(WEB_DATA / p).stat().st_size / 1e6:.2f} MB")
