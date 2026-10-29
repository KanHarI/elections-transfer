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

  const HIDE = {
    abstain: new Set(["ABSTAIN"]),
    roll: new Set(["NEW", "LEFT"]),
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

  // ---------- Sankey ----------
  function drawSankey() {
    const R = state.results;
    const M = currentMatrix();
    const from = R.nodes.from, to = R.nodes.to;
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

    svg.append("text").attr("class", "col-head").attr("x", labelW).attr("y", 14).text(R.elections.from.year);
    svg.append("text").attr("class", "col-head").attr("x", width - labelW).attr("y", 14)
      .attr("text-anchor", "end").text(R.elections.to.year);

    const linkSel = svg.append("g").selectAll("path").data(graph.links).join("path")
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
      .attr("fill", (d) => d.color);

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
      graph.links.forEach((l) => { if (mine(l)) { linked.add(l.source.key); linked.add(l.target.key); } });
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
    const top = [...links].sort((a, b) => b.value - a.value).slice(0, 5);
    const verb = n.side === "from" ? "went to" : "came from";
    const rows = top.map((l) => {
      const other = n.side === "from" ? l.target : l.source;
      return `<div class="t-num">${pct(l.value / n.value)} ${other.en}</div>`;
    }).join("");
    return `<div class="t-title">${n.en} · ${state.results.elections[n.side].year}</div>
      <div class="t-he" dir="rtl">${n.he}</div>
      <div class="t-num">${fmtFull(n.value)} people (${pct(n.value / total)})</div>
      <div style="margin-top:4px">Of these, ${verb}:</div>${rows}`;
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

  // ---------- Table ----------
  function drawTable() {
    const R = state.results;
    const M = currentMatrix();
    const rows = R.nodes.from.map((n, i) => ({ n, i })).filter(({ n }) => !hidden(n.id));
    const cols = R.nodes.to.map((n, j) => ({ n, j })).filter(({ n }) => !hidden(n.id));
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
      const refs = ["constant", "independent"];
      const meanOf = (m) => d3.mean(syn.filter((r) => r.model === m), (r) => r.party_row_tv);
      const models = [...new Set(syn.map((r) => r.model))]
        .sort((a, b) => (refs.includes(b) - refs.includes(a)) || meanOf(a) - meanOf(b));
      const val = (m, g) => syn.find((r) => r.model === m && r.regime === g)?.party_row_tv;
      const best = Object.fromEntries(regimes.map((g) => [g, d3.min(models, (m) => val(m, g))]));
      const name = (m) => m === "constant" ? "Constant transfer matrix" : m === "independent" ? "No within-cluster loyalty" : m.replace("vae_", "VAE · ").replace(/_d(\d+)_b([^_]+)(?:_s(.+))?$/, (_, d, b, s) => ` head, latent ${d}, KL weight ${b}` + (s ? `, indecision penalty ${s}` : ""));
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
    drawTable();
  }

  // ---------- Areas ----------
  async function ensureAreas() {
    if (state.areas) return state.areas;
    const res = await fetch("data/areas.json");
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
    const res = await fetch("data/results.json");
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
    document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
      state.tableMode = b.dataset.mode;
      document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      drawTable();
    }));
    let raf = 0;
    window.addEventListener("resize", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(drawSankey); });
  }

  init().catch((err) => {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="card">Couldn't load the results: ${err.message}. Run <code>uv run elections-transfer all</code> and serve the <code>web/</code> folder.</p>`);
  });
})();
