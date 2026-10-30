# Why the Netanyahu bloc fell from 64 to 53 seats

The Netanyahu bloc is Likud, Religious Zionism / Otzma Yehudit, Shas and United
Torah Judaism. It won 64 seats in 2022 and 53 in the 2026 final results
(Likud 27, Otzma 7, UTJ 7, Shas 6, RZ–Zehut 6).

**In one sentence:** the bloc did not lose many of its own voters. The pool of
votes for opposition lists that crossed the threshold grew much faster than the
bloc's own vote. Arab turnout surged. Meretz and Balad votes were no longer
wasted below the threshold. New and returning voters split toward the opposition
more than the bloc's share. Votes explain 10.1 of the 11 seats; seat arithmetic
accounts for the rest.

## How the numbers are computed

- A list's seats are about 120 × its votes ÷ the votes of all lists that passed
  the 3.25% threshold. So the bloc loses seats both when it loses votes and when
  the passing opposition gains votes.
  - One extra Bibi-bloc vote ≈ **+1 seat per 78k votes**.
  - One extra vote for a passing opposition list ≈ **−1 seat per 83k votes**.
  - A vote for a list below the threshold changes nothing.
- Voters are never observed individually. The flows of people from each 2022
  choice to each 2026 choice come from two estimators fitted to all 3,897
  polling-place clusters (only the vote files, nothing else):
  - **Linear model.** One constant transfer matrix for the whole country
    (Goodman ecological regression).
  - **VAE.** Each polling place gets an embedding from its 2022 results. A small
    movement code lets its transfer matrix deviate from the national one; this
    is the model shown on the site.
- Every flow is assigned to exactly one cause below. Its seat effect is the
  change it makes to (bloc votes ÷ passing votes), linearised at the midpoint of
  the two elections. The causes therefore add up, and both models sum to the
  same total, which is fixed by the actual results.

## The decomposition

Seats are effects on the bloc's seat count (negative = cost the bloc seats).
People are the VAE's estimate.

| # | Cause | People | Linear | VAE | Mean |
|---|---|---|---|---|---|
| 1 | **Arab turnout surge.** 2022 non-voters (≈230k) and new voters (≈90k) voting Joint List / Ra'am | 326k | −3.84 | −3.90 | **−3.9** |
| 2 | **Meretz no longer burned.** 2022 Meretz voters now in passing lists (≈130k to the Democrats) | 147k | −1.74 | −1.75 | **−1.7** |
| 3 | **Balad no longer burned.** 2022 Balad voters now in the Joint List | 135k | −1.61 | −1.61 | **−1.6** |
| 4 | **Bibi-bloc votes burned** in the Reservists, Amcha Yisrael and other small lists | 125–139k | −1.77 | −1.60 | **−1.7** |
| 5 | **Switching between the blocs** (Bibi → Change, net of Change → Bibi) | 22–65k | −0.44 | −1.37 | **−0.9** |
| 6 | **2022 non-voters** voting in 2026, excluding Arab lists | 205–218k | −1.19 | −1.11 | **−1.2** |
| 7 | **New voters (net)**, excluding Arab lists | 427–429k | +0.54 | +0.69 | **+0.6** |
| 8 | **Change-bloc votes burned** in the Reservists, Amcha Yisrael and other small lists | 62–70k | +0.74 | +0.84 | **+0.8** |
| 9 | **Jewish Home (burned in 2022) voters** returning to passing lists | 32–34k | +0.14 | +0.29 | **+0.2** |
| 10 | Voters of either bloc who stayed home in 2026 | ≈10k | −0.09 | −0.03 | **−0.1** |
| 11 | Other: population churn in shrinking areas, small lists, invalid ballots | — | −0.85 | −0.55 | **−0.7** |
| | **Vote-driven total** | | **−10.11** | **−10.11** | **−10.1** |
| 12 | **Seat arithmetic** | | | | **−0.9** |
| | **Total** | | | | **−11** |

Row 12 reconciles the vote-driven change with the official seats:

| Component | Seats |
|---|---|
| D'Hondt rounding (63.6 → 63 in 2022, 53.4 → 54 in 2026) | +1.2 |
| 2022 Likud–RZ surplus agreement (Likud's 32nd seat) | −1 |
| 2026 final count / surplus agreements (a seat moved from Shas to Ra'am) | −1 |
| Linearisation error | −0.1 |

## The questions, one by one

### Meretz falling → not falling: −1.7 seats (both models)
In 2022 Meretz (151k) fell 0.1% short of the threshold and its votes were wasted,
which raised the bloc's share of the votes that counted. In 2026 these voters are
inside lists that passed, mostly the Democrats (≈130k). **Balad** works the same
way: 138k wasted votes in 2022, now in the Joint List, for another **−1.6**.
Together, about **3.4 of the 2022 bloc's 64 seats** came from opposition votes
being wasted. That cushion is gone.

### Burned votes in Amcha Yisrael and the Reservists: net −0.5 to −0.7 seats
- Bibi-bloc voters went to these two lists: 101k (VAE) / 111k (linear). Gross
  cost **−1.3 / −1.4** seats.
  - Reservists: mostly Likud and RZ voters.
  - Amcha Yisrael: mostly RZ, then Likud.
- They also absorbed Change-bloc voters, mostly National Unity, then Yesh Atid:
  69k / 61k. This *helped* the bloc by **+0.8 / +0.7**, because those votes left
  the opposition and were burned.
- **Net for the two lists: −0.46 (VAE) / −0.69 (linear).** Including other small
  lists, all burned Bibi-bloc votes cost −1.6 / −1.8 (row 4).

### Higher Arab turnout: −3.9 seats, the largest single cause (both models)
- Joint List and Ra'am drew in:
  - previous non-voters: 234k (VAE) / 221k (linear);
  - new voters: 88k / 100k.
- That is −2.8 / −2.6 and −1.1 / −1.2 seats respectively.
- Model-free check: turnout at regular ballot boxes in Arab-majority polling
  places rose from **53.1% to 79.1% (+26 points)**, and their voter count grew
  **61%**.

### Distribution of new voters: +0.5 to +0.7 seats excluding Arab lists; about −0.5 including them
- About 700k more people were on the roll, net of deaths.
- Outside Arab lists the bloc won them:

  | New voters to | VAE | Linear |
  |---|---|---|
  | Bibi bloc | 235k (+3.0) | 228k (+2.9) |
  | Change bloc | 194k (−2.3) | 199k (−2.4) |

- About 90–100k went to Arab lists (counted in the Arab turnout row). Including
  them, new voters cost the bloc about −0.4 (VAE) / −0.7 (linear).
- Note: deaths aren't modelled. About 3% of 2022 voters died, skewing older and
  right-leaning, and they are treated as replaced by new voters. The bloc's real
  gain among first-time voters is therefore somewhat smaller than shown and its
  loyalty somewhat larger. The two errors cancel in the seat total.

### Distribution of those who did not vote in 2022: −1.2 seats excluding Arab lists; about −3.9 including them
- Previous non-voters who voted in 2026:

  | Went to | VAE | Linear |
  |---|---|---|
  | Change bloc | 151k (−1.8) | 161k (−1.9) |
  | Bibi bloc | 54k (+0.7) | 57k (+0.7) |
  | Arab lists | 234k (−2.8) | 221k (−2.6) |

- The Arab part is counted in row 1.

### Charedi turnout not rising while others did: about −0.2 to −0.4 seats (model-free)
- Turnout at regular ballot boxes, by the camp that held a 60% majority in a
  polling place in 2022:

  | Camp | 2022 | 2026 | Change |
  |---|---|---|---|
  | Arab | 53.1% | 79.1% | **+26.0** |
  | Mixed | 62.7% | 68.7% | +6.0 |
  | Change bloc | 66.8% | 72.3% | +5.5 |
  | Right (Likud / RZ / JH) | 69.7% | 74.1% | +4.4 |
  | **Charedi** | **73.0%** | **74.0%** | **+1.0** |
  | All regular boxes | 63.8% | 71.8% | +8.0 |

  (Double-envelope voters are excluded in both years, so these are below the
  official turnout.)
- If Charedi-majority areas had risen like other Jewish areas (+5.3 points) or
  like the national average (+8.0), they would have cast about 22–35k more
  votes, about 94% of them for the bloc: **+0.2 to +0.4 seats**.
- Within the flow models, Charedi-list voters who *stayed home* are tiny (4–7k,
  under 0.1 seat). Charedi voters didn't drop out; Charedi areas simply didn't
  mobilise new voters as others did.
- Shas's large loss (393k → 298k) went mostly to Likud and Otzma Yehudit:
  - VAE: Likud 52k, Otzma 37k;
  - linear: Otzma 61k, Likud 21k.

  Those moves are inside the bloc and cost no seats.

### Opposition high turnout: about −4.2 seats, against +3.7 for the bloc (excluding Arab lists)
- Change-bloc gains from new voters plus previous non-voters:
  - VAE: 194k + 151k = −4.1 seats;
  - linear: 199k + 161k = −4.3.
- Bibi-bloc gains from the same sources: 289k / 285k, worth +3.7 / +3.7.
- The bloc mobilised fewer people than its 48% share of the 2022 passing vote
  would require; net about −0.5.
- Model-free: turnout in Change-majority areas rose 5.5 points, against 4.4 in
  Right-majority areas and 1.0 in Charedi areas.

### Voters moving from Bibi's bloc to the Change bloc: −0.4 (linear) to −1.4 (VAE) seats
- **VAE:** Likud → Beyachad 32k, Likud → Yisrael Beiteinu 16k, RZ → Beyachad 8k,
  Likud → Democrats 3k; about 5k moved the other way.
- **Linear model:** mainly RZ → Beyachad 16k.
- This is the least certain row. Both models agree that direct switching was
  small next to turnout and threshold effects. They disagree by about one seat on
  its size, because a single national matrix can't let Likud voters in
  Bennett-friendly areas behave differently from Likud voters elsewhere; the VAE
  can.

## Confidence

- **Solid (±0.2 seat):** rows 1–3 and the turnout figures. They rest mostly on
  arithmetic: Meretz and Balad voters had nowhere else to go but passing lists,
  and turnout is counted, not estimated.
- **Moderate (±0.5 seat):** rows 4 and 6–8. Both models agree to within 0.2, but
  both depend on ecological inference, i.e. assumptions about who moved where
  inside each polling place.
- **Uncertain (±1 seat):** row 5, where the models disagree.
- **Data:** the 2026 per-ballot file was downloaded before about 225k
  double-envelope ballots were counted. The official seats include them; the
  flows don't.

## Reproduce

```bash
uv run elections-transfer fit --vae vae_split_d20_b0.1_t4_tb0.03_n16000
uv run python -m elections_transfer.analysis
```

Code: `src/elections_transfer/analysis.py` (decomposition and turnout by area),
`src/elections_transfer/seats.py` (threshold + D'Hondt).

## Sources

- Ballot-box results: Central Elections Committee, `expb.csv` for the
  [26th](https://media26.bechirot.gov.il/files/expb.csv) and 25th Knesset (see
  the README).
- Official 2026 seats:
  [Israel Hayom](https://www.israelhayom.com/2026/10/29/israels-2026-election-results-released/),
  [Times of Israel](https://www.timesofisrael.com/liveblog_entry/central-elections-committee-publishes-final-election-results-knesset-to-be-sworn-in-nov-10/),
  [Israel National News](https://www.israelnationalnews.com/news/435375),
  [Wikipedia](https://en.wikipedia.org/wiki/2026_Israeli_legislative_election).
