# elections-transfer

Estimated voter transfers between Israeli Knesset lists, from the 25th Knesset
election (1 Nov 2022) to the 26th (27 Oct 2026), inferred from ballot-box
results only, and shown as an interactive Sankey diagram:
**https://elections-transfer.kanhar.art/**

> **2026 data is preliminary.** The CEC was still counting double-envelope
> ballots when the data was fetched. Re-run the pipeline once final results are
> published; the page shows the fetch time.

## Quick start

```bash
uv sync
uv run elections-transfer download                                   # CEC files → data/raw/
uv run elections-transfer fit --vae vae_split_d20_b0.1_t4_tb0.03_n16000
uv run elections-transfer export                                     # → web/data/*.json
uv run elections-transfer serve                                      # http://127.0.0.1:8765
uv run pytest -s                                                     # planted-flow recovery tests
```

`uv run elections-transfer all` runs download → synthetic grid → fit (best
synthetic config) → export.

## Method

**Data.** Only the per-ballot-box files (`expb.csv`) of the Central Elections
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

**Categories** (`dataset.py`). Every cluster is one population: in each
election a person voted for a list (lists ≥ 0.2% of the national vote; smaller
ones are "Other"), cast an invalid ballot, or didn't vote. Only the net change
in registered voters is known, so growth appears as **new voters (net)** on the
2022 side, and in clusters that shrank the difference is removed evenly from all
2022 groups. Deaths are therefore treated as replaced by new voters. Double-
envelope voters also stay on their home box's roll, so their numbers are removed
from home-box abstainers in proportion to registered voters.

**Models** (`models.py`). Each gives a 2022 × 2026 flow matrix per cluster,
raked (iterative proportional fitting) to that cluster's actual totals in both
elections, so every view adds up to the real results.

- **VAE** (`head="split"`, shown on the page). Each cluster is a Gaussian cloud
  of voters in a latent space, encoded from its **2022 results only**, with KL
  penalties toward N(0, I). The code has two parts:
  - a *description* code (20 dims, KL 0.1) that reconstructs the cluster's 2022
    result — the polling-place embedding;
  - a small *movement* code (4 dims, its own KL 0.03) that is the only thing
    allowed to shift the cluster's transfer matrix away from the national one.

  2026 is predicted as the cluster's actual 2022 shares times its transfer
  matrix. All terms are per voter and weighted by the cluster's number of
  voters. Keeping description and movement apart is what stops the model from
  fitting each cluster's noise: with a single code, longer training made
  recovery worse; with the split it doesn't.
- **Constant transfer matrix.** One matrix for the whole country (Goodman
  ecological regression).

Earlier decoders are kept for comparison: `two` (each sampled voter gets a 2022
and a 2026 vote) and `transfer` (one code drives both 2022 and the transfer
matrix).

**Validation.** `synthetic.py` plants known flows in data with the real clusters
and sizes, under three regimes, and scores each model on how well it recovers
them. `tests/test_recovery.py` does the same for small hand-written populations.

## Results

Synthetic recovery (`results/synthetic*.csv`): share of a 2022 list's voters
sent to the wrong 2026 destination, averaged over lists — lower is better.

| Model | uniform | contextual | latent | mean |
|---|---|---|---|---|
| **VAE split, movement KL 0.03, 16k steps** (shown) | 1.1% | **13.7%** | 9.3% | **8.0%** |
| VAE split, movement KL 0.03, 4k steps | 1.0% | 13.5% | 10.6% | 8.4% |
| VAE split, movement KL 0.3 | 1.0% | 23.0% | 9.1% | 11.1% |
| Constant transfer matrix | 1.0% | 25.5% | 9.2% | 11.9% |
| VAE transfer head, latent 20, KL 0.1 | 6.6% | 23.3% | 17.3% | 15.7% |
| VAE two heads, latent 20, KL 1 | 50.4% | 54.1% | 71.1% | 58.5% |

- *uniform*: every cluster shares one transfer pattern plus noise;
  *contextual*: transfers shift with an area's 2022 vote mix; *latent*: clusters
  are mixtures of hidden voter types with their own transfers.
- The split VAE matches the constant matrix where transfers don't vary and
  roughly halves its error where they do.

## Viewer (`web/`)

Static page (D3 + d3-sankey) reading `web/data/results.json` and
`web/data/areas.json`:

- national or per-locality Sankey, VAE or constant matrix;
- **Lists / Blocks**: blocks (Bibi, Eisenkot, Arab, Charedim) are a display
  grouping defined in `web/app.js`; lists not in a block are "Other lists";
- a **cross-block moves** panel breaking each block-to-block move (Other lists
  counted as a block) into its list-to-list flows;
- only flows over 5k people are drawn (scaled for localities); tooltips list all;
- transfer table (% of 2022 list, % of 2026 list, people) and the synthetic
  comparison.

## Caveats

- Ecological inference: aggregates can't identify individual moves without
  assumptions. `tests/test_recovery.py::test_untangle_is_not_identifiable` shows
  two different worlds that produce identical totals in every cluster.
- Deaths aren't modelled (about 3% of 2022 voters); new voters are shown net.
- People who moved home are lost from one cluster and appear as new voters in
  another.
- Double-envelope voters are a different population in each election.

## Layout

```
src/elections_transfer/
  data.py        download + parse CEC files
  parties.py     ballot letters → names/colors per election; 0.2% threshold
  clusters.py    cross-election polling-place clusters
  dataset.py     per-cluster category counts
  models.py      VAE (split / transfer / two heads), constant matrix; raking
  synthetic.py   planted-flow recovery regimes and scores
  export.py      JSON for the web UI
  cli.py         `elections-transfer` command (download, synth, fit, export, all, serve)
web/             static viewer
tests/           recovery tests
```
