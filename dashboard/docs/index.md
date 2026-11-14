```js
// The list of datasets shown in the dashboard lives in datasets.js — see that
// file for why it can't just be a JSON config.
import {DATASETS} from "./datasets.js";

const loaded = new Map(await Promise.all(
  DATASETS.map(async (d) => [d.id, await d.file.csv({typed: true})])
));
```

```js
const datasetId = view(Inputs.select(DATASETS.map((d) => d.id), {
  label: "Dataset",
  format: (id) => DATASETS.find((d) => d.id === id).label,
  value: DATASETS[0].id
}));
```

```js
// The CSV still carries the scorer's original label text; map it to the
// dashboard's own label names here so every chart/table below just uses
// d.label without needing to know about the raw values.
const RAW_TO_LABEL = {
  "likely bot": "regular bots",
  "suspicious": "suspicious",
  "likely human / well-behaved bot": "well meaning bots & humans",
  "too few requests": "bots scanning for vulnerabilities"
};
const scores = loaded.get(datasetId).map((d) => ({...d, label: RAW_TO_LABEL[d.label] ?? d.label}));
```

```js
// Fixed domain/palette so a label keeps the same colour across every chart
// and every dataset switch (datasets don't all contain the same labels —
// e.g. "bots scanning for vulnerabilities" is absent from the small sample
// dataset — so leaving this to each Plot call's automatic inference would
// reassign colours depending on which labels happen to be present).
const LABEL_DOMAIN = ["regular bots", "suspicious", "well meaning bots & humans", "bots scanning for vulnerabilities"];
const LABEL_COLORS = ["#F60000", "#f28e2b", "#74c3ed", "#7f0000"];
const labelColor = d3.scaleOrdinal(LABEL_DOMAIN, LABEL_COLORS);
```

# Request scoring system

In order to know if an institutional website was requested by a human, a well meaning bot, a regular bot, or a bad bot just looking for vulnerabilities, every IP address in a web access log was scored for those four behaviour types.

```js
const total = scores.length;
const byLabel = d3.rollup(scores, (v) => v.length, (d) => d.label);
```

<div class="grid grid-cols-4">
  <div class="card"><h2>IPs scored</h2><span class="big">${total}</span></div>
  <div class="card"><h2>Regular bots</h2><span class="big">${byLabel.get("regular bots") ?? 0}</span></div>
  <div class="card"><h2>Suspicious</h2><span class="big">${byLabel.get("suspicious") ?? 0}</span></div>
  <div class="card"><h2>Well meaning bots & humans</h2><span class="big">${byLabel.get("well meaning bots & humans") ?? 0}</span></div>
</div>

## Score distribution

The bar chart shows the distribution of the score across the analysed IP addresses. Bots which are only scanning for vulnarabilities share the same behaviour as humans and well meaing bots, by only requesting the website once.

```js
Plot.plot({
  marginLeft: 50,
  x: {label: "warning signs (score)", domain: [0, 1, 2, 3, 4, 5]},
  y: {label: "number of IPs"},
  color: {domain: LABEL_DOMAIN, range: LABEL_COLORS, legend: true},
  marks: [
    Plot.barY(scores, Plot.groupX({y: "count"}, {x: "score", fill: "label", tip: true})),
    Plot.ruleY([0])
  ]
})
```

## Requests vs. score

```js
// Large datasets (hundreds of thousands of IPs) render as a random sample
// of 5,000 points — plotting every point would be slow and no more readable.
const SCATTER_CAP = 5000;
const scatterData = scores.length > SCATTER_CAP ? d3.shuffle(scores.slice()).slice(0, SCATTER_CAP) : scores;
```

${scores.length > SCATTER_CAP ? html`<p><em>Showing a random sample of ${SCATTER_CAP.toLocaleString()} of ${scores.length.toLocaleString()} IPs.</em></p>` : ""}

```js
Plot.plot({
  marginLeft: 50,
  x: {label: "requests", type: "log"},
  y: {label: "score"},
  color: {domain: LABEL_DOMAIN, range: LABEL_COLORS, legend: true},
  marks: [
    Plot.dot(scatterData, {x: "requests", y: "score", fill: "label", r: 3, tip: true}),
    Plot.ruleY([0])
  ]
})
```

## Request mosaic, grouped by label

```js
// ip_scores.csv has one row per IP, not one per request, so there's no raw
// per-request table to draw from. This rebuilds a stand-in: it allocates the
// grid's 800 cells across the (up to 4) *labels* in proportion to that
// label's share of the dataset's total requests (largest-remainder rounding
// so the allocation sums to exactly 800), then shuffles the cells (the
// grouping into solid blocks below re-sorts them anyway, but this keeps
// which IP each cell's tooltip names unpredictable).
//
// Allocation happens per label, not per individual IP: with far more IPs
// (tens of thousands here) than grid cells, allocating per-IP breaks the
// largest-remainder method — almost every IP's exact share rounds to 0 on
// its own, so the few largest IPs win nearly all of the 800 cells and whole
// labels (e.g. "bots scanning for vulnerabilities", made of thousands of 1-2-request IPs)
// can vanish from the grid even though their requests add up to a sizeable
// share of total traffic. Each cell's tooltip still names one real IP from
// its label, chosen by a request-weighted random draw (cosmetic only —
// colour depends only on the label, not on which IP was drawn).
const GRID_COLS = 40;
const GRID_ROWS = 20;
const GRID_CELLS = GRID_COLS * GRID_ROWS;

function buildRequestGrid(rows, n) {
  const byLabel = d3.rollups(rows, (v) => ({total: d3.sum(v, (d) => +d.requests), rows: v}), (d) => d.label);
  const total = d3.sum(byLabel, ([, g]) => g.total);

  const alloc = byLabel.map(([label, g]) => {
    const exact = total > 0 ? (g.total / total) * n : 0;
    const base = Math.floor(exact);
    return {label, rows: g.rows, total: g.total, base, frac: exact - base};
  });
  let remaining = n - d3.sum(alloc, (a) => a.base);
  const byFrac = [...alloc].sort((a, b) => b.frac - a.frac);
  for (let i = 0; i < remaining; i++) byFrac[i % byFrac.length].base += 1;

  const cells = [];
  for (const a of alloc) {
    const cumulative = d3.cumsum(a.rows, (d) => +d.requests);
    for (let i = 0; i < a.base; i++) {
      const idx = Math.min(d3.bisect(cumulative, Math.random() * a.total), a.rows.length - 1);
      cells.push(a.rows[idx]);
    }
  }
  return d3.shuffle(cells.slice(0, n));
}

const requestCells = buildRequestGrid(scores, GRID_CELLS);
```

Each of the ${GRID_CELLS} squares below stands for roughly 1/${GRID_CELLS} of this dataset's requests, coloured by the rating of the IP that sent it — so a mostly-red mosaic means most *traffic* (not just most IPs) looks like a bot, even if bot IPs are a minority of the IP count above. Cells are grouped into one solid block per label, from the most-populous label to the least, filling column by column (top-to-bottom, then the next column to the right).

<div style="display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; margin-bottom: 0.5rem;">
  ${LABEL_DOMAIN.map((label) => html`<span style="display:inline-flex; align-items:center; gap:0.35rem; font-size:0.85em;"><span style="width:0.9em; height:0.9em; background:${labelColor(label)}; display:inline-block; border-radius:2px;"></span>${label}</span>`)}
</div>

```js
const labelCounts = d3.rollup(requestCells, (v) => v.length, (d) => d.label);
const labelOrder = [...labelCounts].sort((a, b) => d3.descending(a[1], b[1])).map(([label]) => label);
const requestCellsByLabel = [...requestCells].sort((a, b) => labelOrder.indexOf(a.label) - labelOrder.indexOf(b.label));
```

```js
html`<div style="display:grid; grid-template-columns:repeat(${GRID_COLS}, 1fr); grid-template-rows:repeat(${GRID_ROWS}, 1fr); grid-auto-flow:column; aspect-ratio:${GRID_COLS} / ${GRID_ROWS}; gap:2px; max-width:720px;">
  ${requestCellsByLabel.map((d) => html`<div style="background:${labelColor(d.label)};" title="${d.ip} — ${d.requests} requests, score ${d.score} (${d.label})"></div>`)}
</div>`
```

## All IPs

```js
Inputs.table(scores, {
  columns: ["ip", "requests", "score", "label", "top_type", "top_type_share", "referrer_share", "slowdown_share", "reasons"],
  sort: "score",
  reverse: true
})
```
