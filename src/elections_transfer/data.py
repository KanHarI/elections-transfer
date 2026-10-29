"""Download and parse the Central Elections Committee per-ballot-box files (expb.csv)."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

SOURCES = {
    25: {
        "date": "2022-11-01",
        # The official media25 URL no longer serves the file; this is a public mirror
        # of the same CEC expb.csv.
        "url": "https://raw.githubusercontent.com/shaielc/Behirot/master/2022/expb.csv",
        "official_url": "https://media25.bechirot.gov.il/files/expb.csv",
    },
    26: {
        "date": "2026-10-27",
        "url": "https://media26.bechirot.gov.il/files/expb.csv",
        "official_url": "https://media26.bechirot.gov.il/files/expb.csv",
    },
}

ENVELOPE_SETTLEMENT = 9999  # "מעטפות חיצוניות": double-envelope ballots, counted centrally

META_COLUMNS = {
    "סמל ועדה": "committee",
    "ברזל": "serial",
    "שם ישוב": "settlement_name",
    "סמל ישוב": "settlement_code",
    "קלפי": "box",
    "ריכוז": "place",
    "שופט": "judge",
    "בזב": "bzb",
    "מצביעים": "voters",
    "פסולים": "invalid",
    "כשרים": "valid",
    "חיצוניות": "external",
    "קלפי אחרת": "other_box",
}


def raw_path(knesset: int) -> Path:
    return RAW_DIR / f"k{knesset}" / "expb.csv"


def download(knesset: int) -> dict:
    src = SOURCES[knesset]
    resp = requests.get(src["url"], timeout=60, headers={"User-Agent": "elections-transfer"})
    resp.raise_for_status()
    if not resp.content.lstrip(b"\xef\xbb\xbf").startswith("סמל ועדה".encode()):
        raise ValueError(f"K{knesset}: {src['url']} did not return the expected CSV header")
    path = raw_path(knesset)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)
    manifest = {
        **src,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(resp.content).hexdigest(),
        "bytes": len(resp.content),
    }
    (path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


def manifest(knesset: int) -> dict:
    path = raw_path(knesset).parent / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else dict(SOURCES[knesset])


def load(knesset: int) -> tuple[pd.DataFrame, list[str]]:
    """One row per ballot box. Returns the frame and the list of party-letter columns."""
    df = pd.read_csv(raw_path(knesset), encoding="utf-8-sig")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    parties = [c for c in df.columns if c not in META_COLUMNS]
    df = df.rename(columns=META_COLUMNS)
    df["settlement_name"] = df["settlement_name"].astype(str).str.strip()
    df["base_box"] = df["box"].astype(float).floordiv(1).astype(int)
    df["envelope"] = df["settlement_code"] == ENVELOPE_SETTLEMENT

    party_sum = df[parties].sum(axis=1)
    bad = (party_sum != df["valid"]).sum()
    if bad:
        raise ValueError(f"K{knesset}: {bad} boxes where party votes don't sum to valid votes")
    if ((df["valid"] + df["invalid"]) != df["voters"]).any():
        raise ValueError(f"K{knesset}: valid + invalid != voters for some boxes")
    return df, parties
