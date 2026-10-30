# Why the Netanyahu bloc fell from 64 to 53 seats

The Netanyahu bloc is Likud, Religious Zionism / Otzma Yehudit, Shas and United
Torah Judaism. It won 64 seats in 2022 and 53 in 2026:

| | 2022 | 2026 | Change |
|---|---|---|---|
| Charedi lists (Shas + UTJ) | 18 | 13 | **−5** |
| Likud + Otzma + RZ | 46 | 40 | **−6** |
| **Bloc** | **64** | **53** | **−11** |

**In one sentence:** the bloc did not lose many of its own voters. The pool of
votes for opposition lists that crossed the threshold grew much faster than the
bloc's own vote:

- Arab turnout surged.
- Meretz and Balad votes were no longer wasted below the threshold.
- New and returning voters split toward the opposition more than the bloc's
  share.

Within the bloc, the Charedi lists' fall is mostly Shas voters moving to Likud
and Otzma Yehudit, which costs the bloc nothing, plus Charedi turnout that barely
rose.

All numbers use the CEC's final per-ballot-box results for both elections,
including every double-envelope ballot.

## How the numbers are computed

- **Seat value of a vote.** A list's seats are about 120 × its votes ÷ the votes
  of all lists that passed the 3.25% threshold. So the bloc loses seats both when
  it loses votes and when the passing opposition gains votes.
  - One extra Bibi-bloc vote ≈ **+1 seat per 78k votes**.
  - One extra vote for a passing opposition list ≈ **−1 seat per 84k votes**.
  - A vote for a list below the threshold changes nothing.
- **Flows.** Voters are never observed individually. The flows of people from
  each 2022 choice to each 2026 choice come from two estimators fitted to all
  3,910 polling-place clusters (vote files only, nothing else):
  - **Linear model.** One constant transfer matrix for the whole country
    (Goodman ecological regression).
  - **VAE.** Each polling place gets an embedding from its 2022 results. A small
    movement code lets its transfer matrix deviate from the national one; this
    is the model shown on the site.
- **Attribution.** Every flow is assigned to exactly one cause. Its seat effect is
  the change it makes to (votes ÷ passing votes), linearised at the midpoint of
  the two elections. Computing this separately for the Charedi lists and for
  Likud + Otzma + RZ splits each effect between the two halves of the bloc. The
  causes and the halves add up, and both models reach the same total, which is
  fixed by the actual results.
- **Official seats.** `seats.py` applies the threshold, D'Hondt (Bader-Ofer) and
  the published surplus-vote agreements, and reproduces the official 64 and 53
  exactly.

## The decomposition

Seat effects on the bloc (negative = cost the bloc seats). The half-bloc columns
show the VAE with the linear model in brackets. People are the VAE's estimate.

| # | Cause | People | Charedi lists | Likud + Otzma + RZ | Bloc: VAE | Bloc: Linear |
|---|---|---|---|---|---|---|
| 1 | **Arab turnout surge.** 2022 non-voters (≈230k) and new voters (≈90k) voting Joint List / Ra'am | 329k | −1.07 (−1.05) | −2.85 (−2.80) | **−3.92** | **−3.85** |
| 2 | **Meretz no longer burned.** 2022 Meretz voters now in passing lists (≈130k to the Democrats) | 148k | −0.47 (−0.48) | −1.24 (−1.27) | **−1.72** | **−1.74** |
| 3 | **Balad no longer burned.** 2022 Balad voters now in the Joint List | 135k | −0.44 (−0.44) | −1.17 (−1.17) | **−1.61** | **−1.60** |
| 4 | **Bibi-bloc votes burned** in the Reservists, Amcha Yisrael and other small lists | 130k | +0.04 (+0.07) | −1.69 (−1.85) | **−1.65** | **−1.78** |
| 5 | **Switching between the blocs** (Bibi → Change, net of Change → Bibi) | 61k | +0.01 (−0.01) | −1.39 (−0.41) | **−1.38** | **−0.43** |
| 6 | **Charedi lists → Likud / Otzma / RZ** (net; inside the bloc) | 92k | −2.23 (−2.05) | +2.23 (+2.05) | **0.00** | **0.00** |
| 7 | **2022 non-voters** voting in 2026, excluding Arab lists ¹ | 219k | −0.68 (−0.65) | −0.32 (−0.53) | **−1.00** | **−1.18** |
| 8 | **New voters (net)**, excluding Arab lists ¹ | 429k | +0.54 (+0.38) | +0.32 (+0.41) | **+0.85** | **+0.79** |
| 9 | **Charedi turnout below other Jewish areas** (votes not cast; model-free) | −23k | −0.39 | +0.12 | **−0.27** | **−0.27** |
| 10 | **Change-bloc votes burned** in the Reservists, Amcha Yisrael and other small lists | 69k | +0.22 (+0.20) | +0.60 (+0.54) | **+0.82** | **+0.74** |
| 11 | **Jewish Home (burned in 2022) voters** returning to passing lists | 33k | −0.11 (−0.11) | +0.40 (+0.25) | **+0.29** | **+0.14** |
| 12 | Voters of either bloc who stayed home in 2026 | 11k | −0.08 (−0.12) | +0.05 (+0.04) | **−0.03** | **−0.08** |
| 13 | Other: population churn in shrinking areas, small lists, invalid ballots, Bibi ↔ Arab | 141k | −0.21 (−0.22) | −0.25 (−0.60) | **−0.46** | **−0.81** |
| | **Vote-driven total** | | **−4.88** | **−5.20** | **−10.08** | **−10.08** |
| 14 | **Seat arithmetic** ² | | −0.12 | −0.80 | **−0.92** | **−0.92** |
| | **Official change** | | **−5** | **−6** | **−11** | **−11** |

¹ Rows 7–8 are counted as if turnout in Charedi-majority areas had risen like
other Jewish areas'. Row 9 is the difference, so the rows still add up.

² Seat arithmetic, from the continuous seat values to the official seats:

| | Continuous | Official | Difference |
|---|---|---|---|
| 2022 bloc | 63.62 | 64 | +0.38 (Likud's 32nd seat via the Likud–RZ surplus agreement) |
| 2026 bloc | 53.43 | 53 | −0.43 |

Net −0.81, plus −0.11 linearisation error. For the halves, the 2022 rounding
favoured Likud/RZ (+0.96) and cost the Charedi lists (−0.58).

## The questions, one by one

### Meretz falling → not falling: −1.7 seats (both models)
In 2022 Meretz (151k) fell 0.1% short of the threshold, and its votes were
wasted. That raised the bloc's share of the votes that counted. In 2026 these
voters are inside lists that passed, mostly the Democrats (≈130k).

**Balad** works the same way: 138k wasted votes in 2022, now in the Joint List,
for another **−1.6**. Together, about **3.3 of the 2022 bloc's 64 seats** came
from opposition votes being wasted. That cushion is gone.

### Burned votes in Amcha Yisrael and the Reservists: net −0.5 to −0.7 seats

| | VAE | Linear |
|---|---|---|
| Bibi-bloc voters to the two lists | 103k, **−1.32** | 112k, **−1.43** |
| Change-bloc voters to the two lists | 67k, **+0.80** | 62k, **+0.74** |
| **Net for the two lists** | **−0.52** | **−0.69** |

- The Bibi-bloc voters were mostly Likud and RZ voters for the Reservists, and RZ
  then Likud voters for Amcha Yisrael.
- The Change-bloc voters were mostly National Unity, then Yesh Atid. Their move
  *helped* the bloc, because those votes left the opposition and were burned.
- Including other small lists, all burned Bibi-bloc votes cost −1.65 / −1.78
  (row 4).

### Higher Arab turnout: −3.9 seats, the largest single cause (both models)
- Joint List and Ra'am drew in:

  | | VAE | Linear |
  |---|---|---|
  | Previous non-voters | 236k (−2.82) | 224k (−2.67) |
  | New voters | 88k (−1.05) | 99k (−1.18) |

- Model-free check: turnout at regular ballot boxes in Arab-majority polling
  places rose from **53.1% to 79.1% (+26.0 points)**, and their voter count grew
  **64%**.
- Most of the cost falls on Likud/Otzma/RZ (−2.85), simply because they are the
  larger half of the bloc.

### Distribution of new voters: +0.8 seats excluding Arab lists (+0.6 before the Charedi turnout adjustment); about −0.5 including them
- About 700k more people were on the roll, net of deaths.
- Outside Arab lists the bloc won them:

  | New voters to | VAE | Linear |
  |---|---|---|
  | Bibi bloc | 231k (+2.95) | 227k (+2.90) |
  | Change bloc | 198k (−2.36) | 198k (−2.36) |

- 88–99k went to Arab lists (counted in row 1). Including them, new voters cost
  the bloc about −0.5 (VAE) / −0.6 (linear).
- Deaths aren't modelled. About 3% of 2022 voters died, skewing older and
  right-leaning, and they are treated as replaced by new voters. The bloc's real
  gain among first-time voters is therefore somewhat smaller than shown and its
  loyalty somewhat larger. The two errors cancel in the seat total.

### Distribution of those who did not vote in 2022: −1.0 to −1.2 seats excluding Arab lists; about −3.8 including them
- Previous non-voters who voted in 2026:

  | Went to | VAE | Linear |
  |---|---|---|
  | Change bloc | 154k (−1.83) | 167k (−1.99) |
  | Bibi bloc | 65k (+0.83) | 62k (+0.80) |
  | Arab lists | 236k (−2.82) | 224k (−2.67) |

- The Arab part is counted in row 1.
- Charedi lists drew few previous non-voters, so their column in row 7 is
  negative: the extra opposition votes shrink their share.

### Charedi moves to Likud / Otzma / RZ: Charedi lists −2.2 (−2.1), Likud/Otzma/RZ +2.2 (+2.1); bloc 0
- **The largest single cause of the Charedi lists' drop from 18 to 13 seats.**
- About 85–92k 2022 Charedi-list voters, almost all Shas, voted for the non-Charedi
  half in 2026:

  | | VAE | Linear |
  |---|---|---|
  | Shas → Likud | 49k | 20k |
  | Shas → Otzma Yehudit | 39k | 63k |
  | UTJ → RZ–Zehut | 4k | — |

- Only 1–2k moved the other way.
- The bloc as a whole loses nothing: every one of these seats moved from Shas to
  Likud or Otzma. Shas fell from 11 to 6 seats while UTJ stayed at 7.

### Charedi turnout low compared to the rest of Israeli society: −0.27 seats (Charedi lists −0.39, Likud/Otzma/RZ +0.12)
- Turnout at regular ballot boxes, by the camp that held a 60% majority in a
  polling place in 2022:

  | Camp | 2022 | 2026 | Change |
  |---|---|---|---|
  | Arab | 53.1% | 79.1% | **+26.0** |
  | Mixed | 62.7% | 68.6% | +5.9 |
  | Change bloc | 66.8% | 72.3% | +5.5 |
  | Right (Likud / RZ / JH) | 69.7% | 74.1% | +4.4 |
  | **Charedi** | **73.0%** | **74.0%** | **+1.0** |
  | All regular boxes | 63.8% | 71.8% | +8.0 |

  (Double-envelope voters are excluded in both years, so these are below the
  official turnout.)
- Other Jewish areas, i.e. neither Charedi- nor Arab-majority, rose by
  **5.6 points**. Had Charedi-majority areas matched that, they would have cast
  about **23k more votes**, which by their 2026 vote would go 82% to the Charedi
  lists and 12% to Likud/Otzma/RZ.
- That is worth +0.39 seats to the Charedi lists. It is −0.12 to the other half,
  because those votes enlarge the pool and almost none go to them. Net
  **+0.27 seats for the bloc**, lost.
- This number is model-free.
- Against the national average (+8.0 points, including the Arab surge) the gap
  is about 35k votes, worth about 0.4 seats.
- Within the flow models, Charedi-list voters who *stayed home* are tiny
  (under 0.1 seat). Charedi voters didn't drop out; Charedi areas simply didn't
  mobilise new voters as others did.

### Opposition high turnout: about −4.3 seats, against +3.7 for the bloc (excluding Arab lists)
- Change-bloc gains from new voters plus previous non-voters:
  - VAE: 198k + 154k = −4.19 seats;
  - linear: 198k + 167k = −4.35.
- Bibi-bloc gains from the same sources: 296k / 289k, worth +3.78 / +3.70.
- The bloc mobilised fewer people than its 48% share of the 2022 passing vote
  would require; net about −0.4 to −0.65.
- Model-free: turnout in Change-majority areas rose 5.5 points, against 4.4 in
  Right-majority areas and 1.0 in Charedi areas.

### Voters moving from Bibi's bloc to the Change bloc: −0.4 (linear) to −1.4 (VAE) seats
- **VAE:** Likud → Beyachad 28k, Likud → Yisrael Beiteinu 16k, RZ → Beyachad 10k,
  Likud → Yashar! 3k.
- **Linear model:** mainly RZ → Beyachad 16k.
- This is the least certain row. Both models agree that direct switching was
  small next to turnout and threshold effects. They disagree by about one seat on
  its size, because a single national matrix can't let Likud voters in
  Bennett-friendly areas behave differently from Likud voters elsewhere; the VAE
  can.

## Where the halves lost their seats

| | Charedi lists: 18 → 13 (−5) | Likud + Otzma + RZ: 46 → 40 (−6) |
|---|---|---|
| Biggest losses | Voters to Likud/Otzma −2.2; Arab surge −1.1; Meretz + Balad −0.9; previous non-voters −0.7; turnout gap −0.4 | Arab surge −2.9; Meretz + Balad −2.4; burned votes −1.7 (−1.9); switching to Change −1.4 (−0.4) |
| Biggest gains | New voters +0.5; Change votes burned +0.2 | Charedi voters arriving +2.2; Change votes burned +0.6; Jewish Home +0.4 |
| Seat arithmetic | −0.1 | −0.8 |

## How much to trust each number

- **Solid (±0.2 seat):** rows 1–3, row 9 and the turnout figures. They rest
  mostly on arithmetic: Meretz and Balad voters had nowhere else to go but passing
  lists, and turnout is counted, not estimated.
- **Moderate (±0.5 seat):** rows 4, 6–8 and 10. The two models agree to within
  0.2 on the bloc totals, but both depend on ecological inference, i.e.
  assumptions about who moved where inside each polling place.
  - Within row 6 the models disagree on Likud vs Otzma as the destination, but
    agree on the total (≈85–92k).
- **Uncertain (±1 seat):** row 5, where the models disagree.

## Reproduce

```bash
uv run elections-transfer download
uv run elections-transfer fit --vae vae_split_d20_b0.1_t4_tb0.03_n16000
uv run python -m elections_transfer.analysis
```

Code:

- `src/elections_transfer/analysis.py`: decomposition, half-bloc split, Charedi
  turnout gap, turnout by area.
- `src/elections_transfer/seats.py`: threshold, D'Hondt and surplus agreements.

## Sources

- Ballot-box results: Central Elections Committee, `expb.csv` for the
  [26th](https://media26.bechirot.gov.il/files/expb.csv) (final, including double
  envelopes) and the 25th Knesset (see the README).
- Official 2026 seats and surplus agreements:
  [Israel Hayom](https://www.israelhayom.com/2026/10/29/israels-2026-election-results-released/),
  [Times of Israel](https://www.timesofisrael.com/liveblog_entry/central-elections-committee-publishes-final-election-results-knesset-to-be-sworn-in-nov-10/),
  [Israel National News](https://www.israelnationalnews.com/news/435375),
  [Wikipedia](https://en.wikipedia.org/wiki/2026_Israeli_legislative_election).
