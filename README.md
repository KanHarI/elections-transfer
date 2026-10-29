# elections-transfer

Estimated voter transfers between Israeli Knesset lists, from the 25th Knesset
election (1 Nov 2022) to the 26th (27 Oct 2026), inferred from ballot-box
results and shown as an interactive Sankey diagram.

> **2026 data is preliminary.** The CEC was still counting double-envelope
> ballots when the data was fetched. Re-run `uv run elections-transfer all` once
> final results are published; `web/` shows the fetch time.

## Quick start

```bash
uv sync
uv run elections-transfer all --device auto   # download → synthetic test → fit → export
python3 -m http.server 8765 --directory web   # open http://127.0.0.1:8765
uv run pytest -s                               # planted-flow recovery tests
```

Individual steps: `download`, `synth`, `fit`, `export` (each rebuilds the
cluster dataset from `data/raw/`).

## Method

**Data.** Per-ballot-box files (`expb.csv`) from the Central Elections
Committee: [2026](https://media26.bechirot.gov.il/files/expb.csv) and 2022 (the
official `media25` URL no longer serves it; a public mirror of the same file is
used). Hashes and fetch times are in `data/raw/k*/manifest.json`.

**Clusters** (`clusters.py`). Ballot boxes are grouped into clusters that cover
the same voters in both elections:

1. polling places (the CEC's "ריכוז") with the same id in both elections, if
   registered-voter growth is plausible (within 1.5× of national growth);
2. leftover places linked by a shared place id or base box number;
3. the rest pooled per locality, or per regional committee if still implausible.

Result: 3,897 clusters; 91% of registered voters are in polling-place clusters.
Double-envelope ballots form one cluster of their own.

**Categories** (`dataset.py`). Every cluster is a closed population:

| 2022 | 2026 |
|---|---|
| each list ≥ 0.2% of the national vote | each list ≥ 0.2% |
| Other lists, Invalid, Didn't vote | Other lists, Invalid, Didn't vote |
| Not yet eligible (new voters) | Left the roll (deceased) |

Only the difference between new voters and leavers is observed, so leavers are
set with a national death rate (3.1% over four years) and new voters take the
rest. Double-envelope voters also sit on their home box's roll, so their numbers
are removed from home-box abstainers in proportion to registered voters.

**Models** (`models.py`). Each produces a 2022 × 2026 flow matrix per cluster,
then is raked (iterative proportional fitting) to that cluster's actual totals in
both elections, so every view adds up to the real results.

- **VAE (cloud of voters).** Each cluster is a Gaussian cloud
  N(μ<sub>k</sub>, σ<sub>k</sub>²) in latent space, produced by an encoder that
  sees only the cluster's 2022 results; a KL term pulls it toward N(0, I). A
  shared decoder maps each sampled voter to a 2022 vote and a 2026 vote (or a
  2022 vote and a transfer row). The sampled voters must reproduce the cluster's
  2022 and 2026 shares. All terms are per voter and weighted by the cluster's
  number of voters.
- **Constant transfer matrix.** One matrix for the whole country (Goodman
  ecological regression).
- **No within-cluster loyalty.** Reference floor.

**Validation.** `synthetic.py` plants known flows in data with the real clusters
and sizes (three regimes) and scores each model on how well it recovers them.
`tests/test_recovery.py` does the same for small hand-written populations.

## Results

The viewer in `web/` shows the national Sankey, per-locality views and the
transfer table for each model. Synthetic recovery (`results/synthetic*.csv`):
share of a 2022 list's voters sent to the wrong 2026 destination, averaged over
lists (lower is better).

| Model | uniform | contextual | latent | mean |
|---|---|---|---|---|
| Constant transfer matrix | **1.6%** | 23.4% | **15.3%** | **13.4%** |
| VAE, transfer head, latent 20, KL 0.1 | 6.1% | **20.7%** | 17.8% | 14.9% |
| VAE, transfer head, latent 4, KL 10 | 4.0% | 25.0% | 15.3% | 14.8% |
| VAE, two heads, latent 20, KL 1 | 50.7% | 50.3% | 70.2% | 57.1% |
| No within-cluster loyalty | 72.7% | 69.9% | 79.9% | 74.2% |

Open findings:

- The VAE beats the constant matrix only where transfers really vary with the
  local vote mix (contextual); on average the constant matrix is still best, so
  the viewer opens on it.
- At latent 4 / KL 10 the embedding collapses (≈0.006 nats per cluster) and the
  VAE reduces to a single national matrix.
- Training longer makes the transfer-head VAE worse (uniform regime, KL 1: 7.5%
  at 4k steps, 9.5% at 16k), which points to a modeling issue: the latent that
  describes a polling place also bends its transfer table for free.

To try other VAE settings:

```bash
uv run elections-transfer synth --heads transfer,two --latent 20 --betas 0.01,0.1,1 --tag d20
uv run elections-transfer fit --vae transfer:20:0.1 && uv run elections-transfer export
```

## Caveats

- Ecological inference: aggregates can't identify individual moves without
  assumptions. `tests/test_recovery.py::test_untangle_is_not_identifiable` shows a
  case where two different worlds produce identical totals in every cluster.
- People who moved home appear as leavers in one cluster and new voters in another.
- Double-envelope voters are a different population in each election.

## Layout

```
src/elections_transfer/
  data.py        download + parse CEC files
  parties.py     ballot letters → names/colors per election; 0.2% threshold
  clusters.py    cross-election polling-place clusters
  dataset.py     per-cluster category counts
  models.py      VAE, constant matrix, independence; raking
  synthetic.py   planted-flow recovery regimes and scores
  export.py      JSON for the web UI
  cli.py         `elections-transfer` command
web/             static viewer (D3 + d3-sankey), reads web/data/*.json
tests/           recovery tests
```
