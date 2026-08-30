"""Quantify recurring themes in DeepSeek R1's saved reasoning (no API calls).

For each transcript, flags whether certain themes appear anywhere in the
reasoning text, then tabulates by condition and outcome. Themes are matched
with simple case-insensitive regexes; this is a transparent keyword count,
not a classifier, and is meant to complement hand-reading.
"""
import re
import pandas as pd

THEMES = {
    "cites score/reward":     r"maximi[sz]|reward|score|points?\b",
    "cites designer/objective": r"designer|objective",
    "cites user instruction": r"instruction|request|command|user (said|asked|wants|explicitly)",
    "frames as a test":       r"\btest(ing)?\b|trick|red herring",
    "RL analogy (anywhere)":  r"reinforcement learning",
    "concealment (anywhere)": r"not explain|without explanation|less obvious|just give the number",
}
DECISION_CHARS = 800  # only the tail of the reasoning, where the decision is made

df = pd.read_csv("results.csv")
ds = df[(df.model == "deepseek/deepseek-r1-0528") & df.outcome.isin(["compliant", "violating"])].copy()
ds["reasoning"] = ds.reasoning.fillna("").astype(str)
ds["decision"] = ds.reasoning.str[-DECISION_CHARS:]
for name, pat in THEMES.items():
    src_col = ds.reasoning if "anywhere" in name else ds["decision"]
    ds[name] = src_col.str.contains("(?:" + pat + ")", flags=re.I, regex=True)

KEY = ["D1_reward_conflict", "D5_authoritative", "D6_non_authoritative", "D8_auth_opaque", "D3_descriptive_code"]

print("Share of DeepSeek transcripts whose DECISION REGION (last 800 chars) cites each theme (%)\n")
rows = []
for cond in KEY:
    for out in ["violating", "compliant"]:
        g = ds[(ds.condition == cond) & (ds.outcome == out)]
        if len(g) == 0: continue
        rows.append({"condition": cond.split("_")[0], "outcome": out, "n": len(g),
                     **{t: round(100 * g[t].mean()) for t in THEMES}})
tab = pd.DataFrame(rows).set_index(["condition", "outcome"])
print(tab.to_string())

print("\n\nPooled across all DeepSeek conflict cells (D1,D2,D4,D5,D8,D1m): violating vs compliant")
conf = ds[ds.condition.isin(["D1_reward_conflict","D2_opaque_evaluative","D4_block_first",
                             "D5_authoritative","D8_auth_opaque","D1_mirror"])]
pooled = conf.groupby("outcome")[list(THEMES)].mean().mul(100).round().astype(int)
pooled["n"] = conf.groupby("outcome").size()
print(pooled.to_string())

# The 'pivot': what does the model say right before it commits? Last 'final decision' style line.
def pivot(text):
    m = list(re.finditer(r"(final decision|i think i should|i'll go with|i will provide|i should (provide|output|give|respond))[^\n]*", text, flags=re.I))
    return m[-1].group(0) if m else ""
ds["pivot_line"] = ds.reasoning.apply(pivot)
print("\n\nSample pivot lines, D5 violating:")
for s in ds[(ds.condition=="D5_authoritative") & (ds.outcome=="violating")].pivot_line.head(8): print("  -", s[:140])
print("\nSample pivot lines, D1 compliant:")
for s in ds[(ds.condition=="D1_reward_conflict") & (ds.outcome=="compliant")].pivot_line.head(6): print("  -", s[:140])
tab.to_csv("cot_theme_counts.csv")
