import json

# Load all data sources
with open('tests/questions.json', 'r', encoding='utf-8') as f:
    questions = {item['id']: item for item in json.load(f)}
with open('tests/ground_truth.json', 'r', encoding='utf-8') as f:
    ground_truth = {item['id']: item for item in json.load(f)}
with open('tests/baseline_record.json', 'r', encoding='utf-8') as f:
    baseline = {item['id']: item for item in json.load(f)}
with open('tests/rag_record.json', 'r', encoding='utf-8') as f:
    rag = {item['id']: item for item in json.load(f)}
with open('tests/llm_semantic_evaluation.json', 'r', encoding='utf-8') as f:
    evals = json.load(f)

# Merge responses into evaluation data
for e in evals:
    qid = e['id']
    e['ground_truth_response'] = ground_truth.get(qid, {}).get('ground_truth', '')
    e['baseline_response'] = baseline.get(qid, {}).get('baseline_response', '')
    e['rag_response'] = rag.get(qid, {}).get('rag_response', '')[:1000]  # Truncate long RAG responses

# Save updated JSON
with open('tests/llm_semantic_evaluation.json', 'w', encoding='utf-8') as f:
    json.dump(evals, f, indent=2, ensure_ascii=False)

# Calculate stats
avg_baseline = sum(d['baseline']['score'] for d in evals) / len(evals)
avg_rag = sum(d['rag']['score'] for d in evals) / len(evals)
baseline_ok = sum(1 for d in evals if d['baseline']['ok'])
rag_ok = sum(1 for d in evals if d['rag']['ok'])
avg_delta = avg_rag - avg_baseline

def score_class(s):
    if s >= 90: return "score-excellent"
    elif s >= 70: return "score-good"
    elif s >= 40: return "score-partial"
    else: return "score-poor"

def escape(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")

rows = []
for d in evals:
    bc = score_class(d['baseline']['score'])
    rc = score_class(d['rag']['score'])
    bh = "no-halluc" if d['baseline']['ok'] else "has-halluc"
    rh = "no-halluc" if d['rag']['ok'] else "has-halluc"
    dc = "positive" if d['delta'] > 0 else ("negative" if d['delta'] < 0 else "neutral")
    ar = "up" if d['delta'] > 0 else ("down" if d['delta'] < 0 else "eq")
    gt = escape(d.get('ground_truth_response', '')[:200])
    br = escape(d.get('baseline_response', '')[:200])
    rr = escape(d.get('rag_response', '')[:300])
    rows.append(f'''<div class="card" data-delta="{dc}">
<div class="hdr"><span class="qid">Q{d['id']}</span>{escape(d['question'])}</div>
<div class="grid">
<div class="box gt"><div class="bh">Ground Truth (NotebookLM)</div><div class="bc">{gt}</div></div>
<div class="box bl"><div class="bh">Baseline (Cline without RAG) <span class="badge {bc}">{d['baseline']['score']}%</span><span class="h {bh}">{'OK' if d['baseline']['ok'] else 'X'}</span></div><div class="bc">{br}</div><div class="ass">{escape(d['baseline']['assessment'])}</div></div>
<div class="box rg"><div class="bh">RAG (Cline with SpecRAG) <span class="badge {rc}">{d['rag']['score']}%</span><span class="h {rh}">{'OK' if d['rag']['ok'] else 'X'}</span></div><div class="bc">{rr}</div><div class="ass">{escape(d['rag']['assessment'])}</div></div>
</div>
<div class="imp">Improvement: <span class="{dc}"><span class="{ar}"></span>{d['delta']:+d}%</span></div>
</div>''')

html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>RAG Semantic Evaluation - A2DP</title>
<style>
:root{{--pri:#6366f1;--ok:#10b981;--bad:#ef4444;--bg:#0f172a;--card:#1e293b;--box:#273449;--txt:#e2e8f0;--mut:#94a3b8;--bor:#334155}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui;background:var(--bg);color:var(--txt);padding:1.5rem}}
.c{{max-width:1400px;margin:auto}}
header{{text-align:center;padding:1.2rem;background:linear-gradient(135deg,var(--pri),#8b5cf6);border-radius:14px;margin-bottom:1.5rem}}
h1{{font-size:1.6rem}}
.sub{{color:rgba(255,255,255,.9);font-size:.85rem}}
.stats-row{{display:flex;justify-content:center;gap:1rem;margin-bottom:.8rem}}
.stat.wide{{background:var(--card);padding:.8rem 2rem;border-radius:10px;text-align:center}}
.stats-aligned{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.6rem;margin-bottom:1.5rem;padding:0 .6rem}}
.stat-col{{background:var(--card);padding:.8rem;border-radius:10px;text-align:center}}
.gt-col{{border:2px solid var(--ok)}}
.bl-col{{border:2px solid #3b82f6}}
.rg-col{{border:2px solid #f59e0b}}
.sv2{{font-size:1.1rem;font-weight:700;margin-top:.3rem}}
.sl2{{color:var(--mut);font-size:.65rem}}
.sv{{font-size:1.4rem;font-weight:700;background:linear-gradient(135deg,var(--pri),#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sv.ok{{background:linear-gradient(135deg,var(--ok),#34d399);-webkit-background-clip:text}}
.sv.bad{{background:linear-gradient(135deg,var(--bad),#f87171);-webkit-background-clip:text}}
.sl{{color:var(--mut);font-size:.7rem;margin-top:.2rem}}
.card{{background:var(--card);border-radius:10px;margin-bottom:1rem;overflow:hidden}}
.hdr{{background:rgba(99,102,241,.2);padding:.6rem .8rem;font-size:.85rem;font-weight:500}}
.qid{{background:var(--pri);color:#fff;padding:.2rem .5rem;border-radius:10px;font-size:.75rem;margin-right:.5rem}}
.grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.6rem;padding:.6rem}}
.box{{background:var(--box);border-radius:8px;padding:.5rem;border:2px solid var(--bor)}}
.gt{{border-color:var(--ok)}}
.bl{{border-color:#3b82f6}}
.rg{{border-color:#f59e0b}}
.bh{{font-size:.75rem;font-weight:600;margin-bottom:.4rem}}
.gt .bh{{color:#34d399}}
.bl .bh{{color:#60a5fa}}
.rg .bh{{color:#fbbf24}}
.bc{{font-size:.75rem;color:var(--mut);line-height:1.4;max-height:100px;overflow-y:auto}}
.badge{{display:inline-block;padding:.1rem .4rem;border-radius:10px;font-weight:600;font-size:.65rem;margin-left:.3rem}}
.score-excellent{{background:rgba(16,185,129,.2);color:#34d399}}
.score-good{{background:rgba(99,102,241,.2);color:#a5b4fc}}
.score-partial{{background:rgba(245,158,11,.2);color:#fbbf24}}
.score-poor{{background:rgba(239,68,68,.2);color:#f87171}}
.h{{font-size:.55rem;padding:.1rem .25rem;border-radius:3px;font-weight:600;margin-left:.2rem}}
.no-halluc{{background:rgba(16,185,129,.2);color:#34d399}}
.has-halluc{{background:rgba(239,68,68,.2);color:#f87171}}
.ass{{font-size:.65rem;color:var(--mut);font-style:italic;margin-top:.3rem;border-top:1px solid var(--bor);padding-top:.3rem}}
.imp{{padding:.4rem .8rem;background:rgba(0,0,0,.2);font-size:.8rem;text-align:right}}
.positive{{color:var(--ok);font-weight:700}}
.negative{{color:var(--bad);font-weight:700}}
.neutral{{color:var(--mut)}}
.up::before{{content:"↑ "}}.down::before{{content:"↓ "}}.eq::before{{content:"= "}}
footer{{text-align:center;padding:1rem;color:var(--mut);font-size:.75rem}}
.filter-bar{{display:flex;justify-content:center;gap:.5rem;margin-bottom:1rem}}
.fbtn{{background:var(--card);border:2px solid var(--bor);color:var(--txt);padding:.4rem 1rem;border-radius:20px;cursor:pointer;font-size:.8rem;transition:all .2s}}
.fbtn:hover{{border-color:var(--pri)}}
.fbtn.active{{background:var(--pri);border-color:var(--pri)}}
.fbtn.pos{{border-color:var(--ok)}}.fbtn.pos.active{{background:var(--ok)}}
.fbtn.neg{{border-color:var(--bad)}}.fbtn.neg.active{{background:var(--bad)}}
.card.hidden{{display:none}}
</style></head>
<body><div class="c">
<header><h1>RAG Semantic Evaluation Report</h1><p class="sub">A2DP v1.4.1 - 100 Questions with Full Responses</p></header>
<div class="stats-row">
<div class="stat wide"><div class="sv">{len(evals)}</div><div class="sl">Total Questions</div></div>
<div class="stat wide"><div class="sv ok">+{avg_delta:.1f}%</div><div class="sl">Improvement</div></div>
</div>
<div class="stats-aligned">
<div class="stat-col gt-col"><div class="sv">100%</div><div class="sl">Ground Truth<br><span style="font-weight:normal;font-size:0.6rem">(NotebookLM)</span></div></div>
<div class="stat-col bl-col"><div class="sv bad">{avg_baseline:.1f}%</div><div class="sl">Baseline <br><span style="font-weight:normal;font-size:0.6rem">(Cline without RAG)</span></div><div class="sv2 bad">{baseline_ok}/100</div><div class="sl2">Correct</div></div>
<div class="stat-col rg-col"><div class="sv ok">{avg_rag:.1f}%</div><div class="sl">RAG <br><span style="font-weight:normal;font-size:0.6rem">(Cline with SpecRAG)</span></div><div class="sv2 ok">{rag_ok}/100</div><div class="sl2">Correct</div></div>
</div>
<div class="filter-bar">
<button class="fbtn active" onclick="filter('all')">All ({len(evals)})</button>
<button class="fbtn pos" onclick="filter('positive')">Positive ({sum(1 for d in evals if d['delta']>0)})</button>
<button class="fbtn neg" onclick="filter('negative')">Negative ({sum(1 for d in evals if d['delta']<0)})</button>
<button class="fbtn" onclick="filter('neutral')">Equal ({sum(1 for d in evals if d['delta']==0)})</button>
</div>
<div id="cards">{''.join(rows)}</div>
<script>
function filter(type) {{
  document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.card').forEach(c => {{
    if (type === 'all') c.classList.remove('hidden');
    else if (c.dataset.delta === type) c.classList.remove('hidden');
    else c.classList.add('hidden');
  }});
}}
</script>
<footer>Generated: 2026-01-20 | LLM Semantic Evaluation | RAG outperforms baseline by +{avg_delta:.1f}%</footer>
</div></body></html>'''

with open('tests/semantic_evaluation_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Updated: tests/llm_semantic_evaluation.json (with responses)")
print(f"Updated: tests/semantic_evaluation_report.html (with responses)")
print(f"Baseline: {avg_baseline:.1f}%, RAG: {avg_rag:.1f}%, Delta: +{avg_delta:.1f}%")
