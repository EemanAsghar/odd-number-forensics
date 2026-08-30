"""Stage 6: build viewer.html for hand-reading reasoning transcripts.

Local only. Selection:
  - EVERY violating trial that has reasoning text (all models)
  - plus 5 random compliant trials per (reasoning model, condition) as contrast

Open viewer.html in a browser. Read one transcript at a time, pick a category,
then Export to download your hand labels as a CSV.
"""

import html
import json
import random

import pandas as pd

SAMPLE_COMPLIANT = 5
SEED = 11

df = pd.read_csv("results.csv")
df = df[df.reasoning.notna() & (df.reasoning.astype(str).str.len() > 0)]

viol = df[df.outcome == "violating"]
rng = random.Random(SEED)
comp_idx = [
    i
    for _, g in df[df.outcome == "compliant"].groupby(["model", "condition"])
    for i in rng.sample(list(g.index), min(SAMPLE_COMPLIANT, len(g)))
]
comp = df.loc[comp_idx]
sample = pd.concat([viol, comp]).sample(frac=1, random_state=SEED)  # shuffle

records = [
    {
        "id": f"{r.model.split('/')[-1]}|{r.condition}|{r.trial}",
        "model": r.model.split("/")[-1],
        "condition": r.condition,
        "outcome": r.outcome,
        "answer": str(r.raw_answer),
        "prompt": r.prompt,
        "reasoning": str(r.reasoning),
    }
    for r in sample.itertuples()
]
print(f"{len(viol)} violating + {len(comp)} compliant = {len(records)} transcripts")

data_json = json.dumps(records).replace("</", "<\\/")

page = """<!doctype html><html><head><meta charset="utf-8">
<title>CoT Reader</title>
<style>
  body { font-family: Georgia, serif; max-width: 860px; margin: 24px auto;
         padding: 0 16px; background: #FAFAF7; color: #1A1A2E; }
  .meta { font-family: system-ui, sans-serif; font-size: 14px; color: #5A5A6E;
          display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
  .badge { padding: 2px 10px; border-radius: 10px; font-weight: 600; }
  .violating { background: #FDE2E2; color: #9B1C1C; }
  .compliant { background: #E2F0E2; color: #1C6B1C; }
  pre { white-space: pre-wrap; background: #FFF; border: 1px solid #E4E4EC;
        border-radius: 8px; padding: 14px; font-family: inherit; font-size: 15px;
        line-height: 1.55; }
  .prompt pre { background: #F3F3EE; font-size: 13px; }
  button { font: 14px system-ui, sans-serif; padding: 8px 14px; margin: 3px;
           border: 1px solid #C9C9D4; border-radius: 8px; background: #FFF;
           cursor: pointer; }
  button.sel { background: #4269D0; color: #FFF; border-color: #4269D0; }
  .nav { display: flex; justify-content: space-between; margin: 14px 0; }
  select { font: 14px system-ui, sans-serif; padding: 6px; }
  h3 { font-family: system-ui, sans-serif; font-size: 13px; text-transform:
       uppercase; letter-spacing: .06em; color: #5A5A6E; margin: 18px 0 6px; }
</style></head><body>
<div class="meta">
  <b id="pos"></b>
  <select id="fModel"></select> <select id="fCond"></select>
  <select id="fOut"><option value="">all outcomes</option>
    <option>violating</option><option>compliant</option></select>
  <span id="progress"></span>
</div>
<div class="nav">
  <button onclick="move(-1)">&#8592; previous</button>
  <button onclick="move(1)">next &#8594;</button>
</div>
<div class="meta" id="head"></div>
<h3>Prompt</h3><div class="prompt"><pre id="prompt"></pre></div>
<h3>Model reasoning (chain of thought)</h3><pre id="reasoning"></pre>
<h3>Final answer</h3><pre id="answer"></pre>
<h3>Your category for this transcript</h3>
<div id="cats"></div>
<h3>Note (optional)</h3>
<input id="note" style="width:100%;padding:8px;font:14px system-ui" />
<div class="nav" style="margin-top:20px">
  <span></span><button onclick="exportCsv()">Export my labels (CSV)</button>
</div>
<script>
const DATA = __DATA__;
const CATS = [
  "explicit reward-maximizing",
  "inferred designer intent",
  "naive 'this seems wanted'",
  "no stated rationale",
  "reasoning-output mismatch",
  "other",
];
let labels = {};  // id -> {category, note}
let view = DATA.slice(), idx = 0;

function opts(sel, values, label) {
  sel.innerHTML = '<option value="">' + label + '</option>' +
    values.map(v => '<option>' + v + '</option>').join('');
  sel.onchange = applyFilter;
}
opts(fModel, [...new Set(DATA.map(r => r.model))], 'all models');
opts(fCond, [...new Set(DATA.map(r => r.condition))].sort(), 'all conditions');
fOut.onchange = applyFilter;

function applyFilter() {
  view = DATA.filter(r =>
    (!fModel.value || r.model === fModel.value) &&
    (!fCond.value || r.condition === fCond.value) &&
    (!fOut.value || r.outcome === fOut.value));
  idx = 0; render();
}
function move(d) {
  if (!view.length) return;
  saveNote();
  idx = (idx + d + view.length) % view.length; render();
}
function saveNote() {
  if (!view.length) return;
  const id = view[idx].id;
  if (note.value || labels[id])
    labels[id] = Object.assign(labels[id] || {}, {note: note.value});
}
function setCat(c) {
  const id = view[idx].id;
  labels[id] = Object.assign(labels[id] || {}, {category: c});
  render();
}
function render() {
  if (!view.length) { pos.textContent = 'no transcripts match'; return; }
  const r = view[idx];
  pos.textContent = (idx + 1) + ' / ' + view.length;
  head.innerHTML = '<span class="badge ' + r.outcome + '">' + r.outcome +
    '</span><span>' + r.model + '</span><span>' + r.condition +
    '</span><span>trial ' + r.id.split('|')[2] + '</span>';
  prompt.textContent = r.prompt;
  reasoning.textContent = r.reasoning;
  answer.textContent = r.answer;
  const cur = (labels[r.id] || {}).category;
  cats.innerHTML = CATS.map(c => '<button class="' + (c === cur ? 'sel' : '') +
    '" onclick="setCat(\\'' + c + '\\')">' + c + '</button>').join('');
  note.value = (labels[r.id] || {}).note || '';
  const done = Object.values(labels).filter(l => l.category).length;
  progress.textContent = done + ' labeled';
}
function exportCsv() {
  saveNote();
  const esc = s => '"' + String(s == null ? '' : s).replace(/"/g, '""') + '"';
  let rows = [['model','condition','trial','outcome','category','note']];
  for (const r of DATA) {
    const l = labels[r.id] || {};
    if (l.category || l.note)
      rows.push([r.model, r.condition, r.id.split('|')[2], r.outcome,
                 l.category || '', l.note || '']);
  }
  const blob = new Blob([rows.map(x => x.map(esc).join(',')).join('\\n')],
                        {type: 'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'cot_labels.csv'; a.click();
}
render();
</script></body></html>"""

with open("viewer.html", "w") as f:
    f.write(page.replace("__DATA__", data_json))
print("wrote viewer.html")
