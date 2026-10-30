/* Voter-transfer viewer. Reads data/results.json (national) and data/areas.json (per area, lazy). */
(() => {
  "use strict";

  const state = {
    results: null,
    areas: null,          // loaded on first area selection
    model: null,
    area: null,           // null = whole country
    showAbstain: true,
    showRoll: true,
    showMinor: true,
    tableMode: "row",
    group: "blocks",      // "lists" | "blocks"; the page opens on blocks
    pinned: null,         // node key
  };

  const $ = (sel) => document.querySelector(sel);
  const fmt = (v) => {
    const a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
    if (a >= 1e4) return Math.round(v / 1e3) + "k";
    if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
    return String(Math.round(v));
  };
  const fmtFull = (v) => Math.round(v).toLocaleString("en-US");
  const pct = (v, digits = 1) => (100 * v).toFixed(digits) + "%";

  const MIN_FLOW = 5000; // people; smaller flows aren't drawn (see drawSankey)

  const HIDE = {
    abstain: new Set(["ABSTAIN"]),
    roll: new Set(["NEW"]),
    minor: new Set(["INVALID", "OTHER"]),
  };

  function hidden(id) {
    return (!state.showAbstain && HIDE.abstain.has(id)) ||
      (!state.showRoll && HIDE.roll.has(id)) ||
      (!state.showMinor && HIDE.minor.has(id));
  }

  function currentMatrix() {
    if (state.area) return state.area.flows[state.model];
    return state.results.models.find((m) => m.id === state.model).national;
  }

  // Blocks are a display grouping only: the model is fitted per list. Ballot letters
  // per Knesset (25 = 2022, 26 = 2026); lists not named here fold into "Other".
  const BLOCKS = {
    bibi: { en: "Bibi", he: "גוש נתניהו", color: "var(--block-bibi)",
      25: ["מחל", "ט", "ב"], 26: ["מחל", "ב", "ט"] },
    left: { en: "Eisenkot", he: "גוש איזנקוט", color: "var(--block-left)",
      25: ["פה", "כן", "ל", "אמת", "מרצ", "יז"], 26: ["דרך", "רק", "אמת", "ל"] },
    arab: { en: "Arab", he: "ערבים", color: "var(--block-arab)",
      25: ["עם", "ום", "ד"], 26: ["ודם", "עם"] },
    haredi: { en: "Charedim", he: "חרדים", color: "var(--block-haredi)",
      25: ["שס", "ג"], 26: ["שס", "ג"] },
  };

  function groupNodes(nodes, knesset) {
    const out = [], index = new Map(), map = [];
    const add = (key, proto) => {
      if (!index.has(key)) { index.set(key, out.length); out.push({ ...proto, total: 0, members: [] }); }
      return index.get(key);
    };
    Object.entries(BLOCKS).forEach(([k, b]) =>
      add("B:" + k, { id: "B:" + k, en: b.en, he: b.he, color: b.color, kind: "block" }));
    const other = nodes.find((n) => n.id === "OTHER");
    nodes.forEach((n, i) => {
      let key = n.id, proto = n;
      if (n.kind === "party") {
        const block = Object.keys(BLOCKS).find((k) => BLOCKS[k][knesset].includes(n.id.slice(2)));
        key = block ? "B:" + block : "OTHER";
      }
      if (key === "OTHER") proto = { ...other, en: "Other lists" };
      const j = add(key, proto);
      out[j].total += n.total;
      if (n.kind === "party" || n.id === "OTHER") out[j].members.push(n.id === "OTHER" ? "lists under 0.2%" : n.en);
      map[i] = j;
    });
    return { nodes: out, map };
  }

  /** Nodes and flow matrix for the current grouping (lists, or blocks summed from lists). */
  function view() {
    const R = state.results, M = currentMatrix();
    if (state.group !== "blocks") return { from: R.nodes.from, to: R.nodes.to, M };
    const a = groupNodes(R.nodes.from, 25), b = groupNodes(R.nodes.to, 26);
    const G = a.nodes.map(() => b.nodes.map(() => 0));
    M.forEach((row, i) => row.forEach((v, j) => { G[a.map[i]][b.map[j]] += v; }));
    return { from: a.nodes, to: b.nodes, M: G };
  }

  // ---------- Sankey ----------
  function drawSankey() {
    const R = state.results;
    const { from, to, M } = view();
    const svg = d3.select("#sankey");
    const width = Math.max(680, svg.node().parentNode.clientWidth);
    const height = Math.max(520, Math.min(860, width * 0.72));
    svg.attr("viewBox", `0 0 ${width} ${height}`).attr("height", null);
    svg.selectAll("*").remove();
    hideTip();

    const links = [];
    from.forEach((a, i) => {
      if (hidden(a.id)) return;
      to.forEach((b, j) => {
        if (hidden(b.id)) return;
        const v = M[i][j];
        if (v > 0) links.push({ source: "a:" + a.id, target: "b:" + b.id, value: v, i, j });
      });
    });
    const used = new Set(links.flatMap((l) => [l.source, l.target]));
    const nodes = [
      ...from.map((n, i) => ({ ...n, key: "a:" + n.id, side: "from", idx: i })),
      ...to.map((n, j) => ({ ...n, key: "b:" + n.id, side: "to", idx: j })),
    ].filter((n) => used.has(n.key));

    const labelW = Math.min(210, width * 0.26);
    const sankey = d3.sankey()
      .nodeId((d) => d.key)
      .nodeWidth(12)
      .nodePadding(Math.max(6, Math.min(12, height / 60)))
      .nodeAlign(d3.sankeyJustify)
      .nodeSort(null)
      .linkSort(null)
      .extent([[labelW, 28], [width - labelW, height - 6]]);
    const graph = sankey({ nodes: nodes.map((d) => ({ ...d })), links: links.map((d) => ({ ...d })) });
    const total = d3.sum(graph.links, (l) => l.value);
    // Draw only flows above MIN_FLOW people (scaled to the area's share of the country).
    // Smaller flows still count toward node sizes and are listed in node tooltips.
    const national = d3.sum(R.nodes.from, (n) => n.total);
    const minFlow = MIN_FLOW * (state.area ? state.area.population / national : 1);
    $("#flow-note").textContent = `Flows under ${fmt(minFlow)} people aren't drawn; hover a list to see all of them.`;

    svg.append("text").attr("class", "col-head").attr("x", labelW).attr("y", 14).text(R.elections.from.year);
    svg.append("text").attr("class", "col-head").attr("x", width - labelW).attr("y", 14)
      .attr("text-anchor", "end").text(R.elections.to.year);

    const linkSel = svg.append("g").selectAll("path").data(graph.links.filter((l) => l.value >= minFlow)).join("path")
      .attr("class", "link")
      .attr("d", d3.sankeyLinkHorizontal())
      .attr("stroke-width", (d) => Math.max(1, d.width))
      .on("mousemove", (ev, d) => showTip(ev, linkTip(d)))
      .on("mouseleave", hideTip);

    const nodeSel = svg.append("g").selectAll("g").data(graph.nodes).join("g")
      .attr("class", "node")
      .attr("tabindex", 0)
      .attr("role", "button")
      .attr("aria-label", (d) => `${d.en}, ${R.elections[d.side].year}: ${fmtFull(d.value)} people`)
      .on("mouseenter", (ev, d) => { focusNode(d); })
      .on("mousemove", (ev, d) => showTip(ev, nodeTip(d, total)))
      .on("mouseleave", () => { hideTip(); focusNode(pinnedNode()); })
      .on("focus", (ev, d) => focusNode(d))
      .on("blur", () => focusNode(pinnedNode()))
      .on("click", (ev, d) => { state.pinned = state.pinned === d.key ? null : d.key; focusNode(pinnedNode()); })
      .on("keydown", (ev, d) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          state.pinned = state.pinned === d.key ? null : d.key;
          focusNode(pinnedNode());
        }
      });

    nodeSel.append("rect")
      .attr("x", (d) => d.x0).attr("y", (d) => d.y0)
      .attr("width", (d) => d.x1 - d.x0)
      .attr("height", (d) => Math.max(1, d.y1 - d.y0))
      .attr("rx", 2)
      .style("fill", (d) => d.color);

    // Labels outside the bars; skip labels for nodes too thin to hold them.
    nodeSel.filter((d) => d.y1 - d.y0 >= 9).append("text")
      .attr("x", (d) => (d.side === "from" ? d.x0 - 8 : d.x1 + 8))
      .attr("y", (d) => (d.y0 + d.y1) / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", (d) => (d.side === "from" ? "end" : "start"))
      .call((t) => t.append("tspan").text((d) => d.en + " "))
      .call((t) => t.append("tspan").attr("class", "val").text((d) => fmt(d.value)));

    function pinnedNode() {
      return state.pinned ? graph.nodes.find((n) => n.key === state.pinned) || null : null;
    }

    function focusNode(n) {
      if (!n) {
        linkSel.classed("on", false).classed("dim", false).style("stroke", null);
        nodeSel.classed("dim", false);
        return;
      }
      const mine = (l) => l.source.key === n.key || l.target.key === n.key;
      linkSel.classed("on", mine).classed("dim", (l) => !mine(l))
        .style("stroke", (l) => (mine(l) ? n.color : null));
      const linked = new Set([n.key]);
      linkSel.each((l) => { if (mine(l)) { linked.add(l.source.key); linked.add(l.target.key); } });
      nodeSel.classed("dim", (d) => !linked.has(d.key));
    }
    focusNode(pinnedNode());
  }

  function linkTip(l) {
    const s = l.source, t = l.target;
    return `<div class="t-title">${s.en} → ${t.en}</div>
      <div class="t-he" dir="rtl">${s.he} ← ${t.he}</div>
      <div class="t-num">${fmtFull(l.value)} people</div>
      <div class="t-num">${pct(l.value / s.value)} of ${s.en} (${state.results.elections.from.year})</div>
      <div class="t-num">${pct(l.value / t.value)} of ${t.en} (${state.results.elections.to.year})</div>`;
  }

  function nodeTip(n, total) {
    const links = n.side === "from" ? n.sourceLinks : n.targetLinks;
    const top = links.filter((l) => l.value >= 0.5).sort((a, b) => b.value - a.value);
    const verb = n.side === "from" ? "went to" : "came from";
    const rows = top.map((l) => {
      const other = n.side === "from" ? l.target : l.source;
      return `<span class="t-num">${pct(l.value / n.value)}</span><span>${other.en}</span><span class="t-num">${fmt(l.value)}</span>`;
    }).join("");
    const members = n.members && n.members.length ? `<div class="t-he">${n.members.join(", ")}</div>` : "";
    return `<div class="t-title">${n.en} · ${state.results.elections[n.side].year}</div>
      <div class="t-he" dir="rtl">${n.he}</div>${members}
      <div class="t-num">${fmtFull(n.value)} people (${pct(n.value / total)})</div>
      <div style="margin-top:4px">Of these, ${verb}:</div><div class="t-rows">${rows}</div>`;
  }

  const tip = $("#tooltip");
  function showTip(ev, html) {
    tip.innerHTML = html;
    tip.hidden = false;
    const pad = 14, r = tip.getBoundingClientRect();
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - pad;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, y) + "px";
  }
  function hideTip() { tip.hidden = true; }

  // ---------- Cross-block breakdown ----------
  function drawCrossBlocks() {
    const card = $("#cross-card");
    card.hidden = state.group !== "blocks";
    if (card.hidden) return;
    const R = state.results;
    const M = currentMatrix();
    const a = groupNodes(R.nodes.from, 25), b = groupNodes(R.nodes.to, 26);
    const national = d3.sum(R.nodes.from, (n) => n.total);
    const minFlow = MIN_FLOW * (state.area ? state.area.population / national : 1);
    const blockTotal = a.nodes.map((_, k) => d3.sum(M, (row, i) => (a.map[i] === k ? d3.sum(row) : 0)));

    // "Other lists" counts as a block here, so moves to and from unaligned lists show up.
    const isBlock = (n) => n.kind === "block" || n.id === "OTHER";
    const pairs = [];
    a.nodes.forEach((src, ka) => {
      if (!isBlock(src)) return;
      b.nodes.forEach((dst, kb) => {
        if (!isBlock(dst) || dst.id === src.id) return;
        const parts = [];
        R.nodes.from.forEach((f, i) => {
          if (a.map[i] !== ka) return;
          R.nodes.to.forEach((t, j) => { if (b.map[j] === kb && M[i][j] >= 0.5) parts.push({ f, t, v: M[i][j] }); });
        });
        const total = d3.sum(parts, (p) => p.v);
        if (total >= minFlow) pairs.push({ src, dst, total, share: total / blockTotal[ka], parts: parts.sort((x, y) => y.v - x.v) });
      });
    });
    pairs.sort((x, y) => y.total - x.total);

    $("#cross-caption").textContent = pairs.length
      ? `Moves between different blocks of at least ${fmt(minFlow)} people, largest first. Each list-to-list flow is shown with its share of the block move.`
      : `No move between blocks reaches ${fmt(minFlow)} people here.`;
    const sw = (n) => `<span class="sw" style="background:${n.color}"></span>`;
    const SHOW = 6;
    $("#cross").innerHTML = pairs.map((p) => {
      const shown = p.parts.slice(0, SHOW).filter((x) => x.v >= 0.01 * p.total);
      const restParts = p.parts.slice(shown.length);
      const rest = d3.sum(restParts, (x) => x.v);
      const rows = shown.map((x) =>
        `<span>${x.f.en} → ${x.t.en}</span><span class="num main">${fmt(x.v)}</span><span class="num">${pct(x.v / p.total, 0)}</span>`).join("") +
        (rest >= 0.5 ? `<span class="muted">${restParts.length} smaller flows</span><span class="num main">${fmt(rest)}</span><span class="num">${pct(rest / p.total, 0)}</span>` : "");
      return `<article class="cross-item">
        <h3>${sw(p.src)}${p.src.en} → ${sw(p.dst)}${p.dst.en}</h3>
        <p class="sub">${fmtFull(p.total)} people · ${pct(p.share)} of ${p.src.en} ${R.elections.from.year}</p>
        <div class="cross-rows">${rows}</div>
      </article>`;
    }).join("");
  }

  // ---------- Table ----------
  function drawTable() {
    const R = state.results;
    const { from, to, M } = view();
    const rows = from.map((n, i) => ({ n, i })).filter(({ n }) => !hidden(n.id));
    const cols = to.map((n, j) => ({ n, j })).filter(({ n }) => !hidden(n.id));
    const rowSum = rows.map(({ i }) => d3.sum(cols, ({ j }) => M[i][j]));
    const colSum = cols.map(({ j }) => d3.sum(rows, ({ i }) => M[i][j]));
    const grand = d3.sum(rowSum);
    const mode = state.tableMode;

    const caption = {
      row: `Each row: where that ${R.elections.from.year} group's people went in ${R.elections.to.year} (rows sum to 100%).`,
      col: `Each column: where that ${R.elections.to.year} group's people came from in ${R.elections.from.year} (columns sum to 100%).`,
      abs: "Estimated number of people in each flow.",
    }[mode];
    $("#table-caption").textContent = caption;

    const swatch = (n) => `<span class="sw" style="background:${n.color}"></span>`;
    let html = `<thead><tr><th scope="col">${R.elections.from.year} ↓ / ${R.elections.to.year} →</th>`;
    html += cols.map(({ n }) => `<th scope="col" title="${n.he}">${swatch(n)}${n.en}</th>`).join("");
    html += `<th scope="col">Total</th></tr></thead><tbody>`;
    rows.forEach(({ n, i }, ri) => {
      html += `<tr><th scope="row" title="${n.he}">${swatch(n)}${n.en}</th>`;
      cols.forEach(({ j }, ci) => {
        const v = M[i][j];
        let share, text;
        if (mode === "row") { share = rowSum[ri] ? v / rowSum[ri] : 0; text = pct(share, share < 0.1 ? 1 : 0); }
        else if (mode === "col") { share = colSum[ci] ? v / colSum[ci] : 0; text = pct(share, share < 0.1 ? 1 : 0); }
        else { share = grand ? Math.sqrt(v / d3.max(rowSum)) : 0; text = fmt(v); }
        const a = Math.min(1, share * 1.15);
        const cls = v < 0.5 ? "zero" : a > 0.55 ? "dark" : "";
        html += `<td class="${cls}" style="background:rgba(var(--seq),${a.toFixed(3)})">${v < 0.5 ? "–" : text}</td>`;
      });
      html += `<td class="total">${fmt(rowSum[ri])}</td></tr>`;
    });
    html += `<tr><th scope="row" class="total">Total</th>`;
    html += colSum.map((v) => `<td class="total">${fmt(v)}</td>`).join("");
    html += `<td class="total">${fmt(grand)}</td></tr></tbody>`;
    $("#matrix").innerHTML = html;
  }

  // ---------- Text panels ----------
  function drawHeader() {
    const R = state.results;
    const model = R.models.find((m) => m.id === state.model);
    $("#model-desc").textContent = model.description;
    const legend = $("#block-legend");
    legend.hidden = state.group !== "blocks";
    if (!legend.hidden) {
      const { from, to } = view();
      const line = (n) => {
        const a = from.find((x) => x.id === n.id), b = to.find((x) => x.id === n.id);
        return `<span><span class="sw" style="background:${n.color}"></span><b>${n.en}</b> — ` +
          `${R.elections.from.year}: ${a.members.join(", ") || "none"}; ${R.elections.to.year}: ${b.members.join(", ") || "none"}</span>`;
      };
      legend.innerHTML = from.filter((n) => n.kind === "block" || n.id === "OTHER").map(line).join("") +
        `<span>Blocks are a display grouping; flows are estimated per list and summed.</span>`;
    }
    if (state.area) {
      $("#chart-title").textContent = state.area.name;
      const cov = state.area.coverage < 0.995
        ? ` · ${pct(state.area.coverage, 0)} of the locality's people (the rest are pooled in a regional cluster)` : "";
      $("#chart-sub").textContent = `${fmtFull(state.area.population)} people in ${state.area.clusters} cluster${state.area.clusters === 1 ? "" : "s"}${cov}`;
    } else {
      $("#chart-title").textContent = "Whole country";
      $("#chart-sub").textContent = `${fmtFull(d3.sum(R.nodes.from, (n) => n.total))} people in ${fmtFull(R.summary.clusters)} clusters`;
    }
  }

  function drawStatic() {
    const R = state.results;
    const S = R.summary;
    const env26 = S.envelope_voters["2026"];
    $("#status").textContent = R.sources["26"].fetched_at
      ? `2026 data fetched ${R.sources["26"].fetched_at.replace("T", " ").replace("+00:00", " UTC")}. ` +
        `Results are preliminary until the CEC publishes final results; ${fmtFull(env26)} double-envelope ballots were counted at that point.`
      : "";

    $("#model-list").innerHTML = R.models.map((m) => `<li><strong>${m.label}.</strong> ${m.description}</li>`).join("");

    const sel = $("#model");
    sel.innerHTML = R.models.map((m) => `<option value="${m.id}">${m.label}</option>`).join("");
    sel.value = state.model;

    // Synthetic recovery table: models × regimes, party transfer-row error.
    const syn = R.synthetic || [];
    if (syn.length) {
      const regimes = [...new Set(syn.map((r) => r.regime))];
      const refs = ["constant"];
      const meanOf = (m) => d3.mean(syn.filter((r) => r.model === m), (r) => r.party_row_tv);
      const models = [...new Set(syn.map((r) => r.model))]
        .sort((a, b) => (refs.includes(b) - refs.includes(a)) || meanOf(a) - meanOf(b));
      const val = (m, g) => syn.find((r) => r.model === m && r.regime === g)?.party_row_tv;
      const best = Object.fromEntries(regimes.map((g) => [g, d3.min(models, (m) => val(m, g))]));
      const HEADS = { two: "two heads", transfer: "transfer head", split: "description + movement codes" };
      const name = (m) => {
        if (m === "constant") return "Constant transfer matrix";
        const [head, ...parts] = m.replace(/^vae_/, "").split("_");
        const f = {};
        parts.forEach((p) => { const k = p.match(/^(tb|t|d|b|s|n)(.+)$/); if (k) f[k[1]] = k[2]; });
        let out = `VAE · ${HEADS[head] || head}, latent ${f.d}, KL ${f.b}`;
        if (head === "split") out += `; movement latent ${f.t}, KL ${f.tb}`;
        return out + (f.s ? `, indecision penalty ${f.s}` : "") + (f.n ? `, ${Number(f.n) / 1000}k steps` : "");
      };
      let html = `<thead><tr><th>Model</th>${regimes.map((g) => `<th>${g}</th>`).join("")}<th>mean</th></tr></thead><tbody>`;
      models.forEach((m) => {
        const vals = regimes.map((g) => val(m, g));
        html += `<tr class="${m === R.chosen_vae ? "chosen" : ""}"><td>${name(m)}${m === R.chosen_vae ? " (shown as VAE)" : ""}</td>`;
        html += vals.map((v, k) => `<td class="${v === best[regimes[k]] ? "best" : ""}">${pct(v)}</td>`).join("");
        html += `<td>${pct(d3.mean(vals))}</td></tr>`;
      });
      $("#synthetic").innerHTML = html + "</tbody>";
      $("#synthetic-note").textContent = "Regimes — uniform: every cluster shares one transfer pattern plus noise; contextual: transfers shift with an area's 2022 vote mix; latent: clusters are mixtures of hidden voter types, each with its own transfers.";
    }

    const src = R.sources;
    $("#sources").innerHTML = [25, 26].map((k) => {
      const s = src[String(k)];
      return `<li>${k}th Knesset (${s.date}): <a href="${s.url}">${s.url}</a>` +
        (s.official_url !== s.url ? ` (mirror of the CEC file at ${s.official_url})` : "") +
        (s.fetched_at ? `, fetched ${s.fetched_at}` : "") + (s.sha256 ? `, sha256 <code>${s.sha256.slice(0, 12)}…</code>` : "") + `</li>`;
    }).join("") + `<li>Code: <a href="https://github.com/KanHarI/elections-transfer">github.com/KanHarI/elections-transfer</a></li>`;
  }

  function render() {
    drawHeader();
    drawSankey();
    drawCrossBlocks();
    drawTable();
  }

  // ---------- Areas ----------
  async function ensureAreas() {
    if (state.areas) return state.areas;
    const res = await fetch("data/areas.json", { cache: "no-cache" });
    state.areas = await res.json();
    const opts = state.areas
      .slice()
      .sort((a, b) => b.population - a.population)
      .map((a) => `<option value="${a.name}"></option>`).join("");
    $("#area-list").innerHTML = opts;
    return state.areas;
  }

  async function onArea() {
    const q = $("#area").value.trim();
    if (!q) { state.area = null; render(); return; }
    const areas = await ensureAreas();
    const hit = areas.find((a) => a.name === q);
    if (hit) { state.area = hit; state.pinned = null; render(); }
  }

  // ---------- Init ----------
  async function init() {
    const res = await fetch("data/results.json", { cache: "no-cache" });
    state.results = await res.json();
    state.model = state.results.default_model;
    drawStatic();
    render();

    $("#model").addEventListener("change", (e) => { state.model = e.target.value; render(); });
    $("#area").addEventListener("focus", ensureAreas, { once: true });
    $("#area").addEventListener("change", onArea);
    $("#area").addEventListener("input", (e) => { if (!e.target.value) onArea(); });
    $("#show-abstain").addEventListener("change", (e) => { state.showAbstain = e.target.checked; render(); });
    $("#show-roll").addEventListener("change", (e) => { state.showRoll = e.target.checked; render(); });
    $("#show-minor").addEventListener("change", (e) => { state.showMinor = e.target.checked; render(); });
    document.querySelectorAll("#table-mode button").forEach((b) => b.addEventListener("click", () => {
      state.tableMode = b.dataset.mode;
      document.querySelectorAll("#table-mode button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      drawTable();
    }));
    document.querySelectorAll("#group button").forEach((b) => b.addEventListener("click", () => {
      state.group = b.dataset.group;
      state.pinned = null;
      document.querySelectorAll("#group button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      render();
    }));
    let raf = 0;
    window.addEventListener("resize", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(drawSankey); });
  }

  init().catch((err) => {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="card">Couldn't load the results: ${err.message}. Run <code>uv run elections-transfer all</code> and serve the <code>web/</code> folder.</p>`);
  });
})();
