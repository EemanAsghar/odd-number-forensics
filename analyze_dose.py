"""Figure for the authority dose-response (DeepSeek R1)."""
import matplotlib.pyplot as plt
import pandas as pd
from analyze import wilson_ci, BLUE, INK, MUTED, GRID

main = pd.read_csv("results.csv")
ds = main[(main.model == "deepseek/deepseek-r1-0528") & main.outcome.isin(["compliant", "violating"])]
dose = pd.read_csv("results_dose.csv")
dose = dose[dose.outcome.isin(["compliant", "violating"])]

def cell(df, key, col):
    g = df[df[col] == key]
    return int((g.outcome == "violating").sum()), len(g)

points = [
    ("none\n(D1)",            *cell(ds, "D1_reward_conflict", "condition")),
    ('"may reflect"',         *cell(dose, "L1_may", "level")),
    ('"likely reflects"',     *cell(dose, "L2_likely", "level")),
    ('"represents"\n(D5)',    *cell(ds, "D5_authoritative", "condition")),
    ('"sole objective"',      *cell(dose, "L4_sole", "level")),
]
labels = [p[0] for p in points]
rates = [100 * k / n for _, k, n in points]
los = [100 * (k / n - wilson_ci(k, n)[0]) for _, k, n in points]
his = [100 * (wilson_ci(k, n)[1] - k / n) for _, k, n in points]

fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
fig.patch.set_facecolor("white"); ax.set_facecolor("white")
x = range(len(points))
ax.errorbar(x, rates, yerr=[los, his], fmt="none", ecolor=MUTED, elinewidth=1.2, capsize=3, zorder=3)
ax.plot(x, rates, color=BLUE, linewidth=2, zorder=4)
ax.scatter(x, rates, color=BLUE, s=48, zorder=5, edgecolor="white", linewidth=1.5)
for xi, r, (_, k, n) in zip(x, rates, points):
    ax.text(xi, r + 6 if r < 90 else r - 11, f"{r:.0f}%\n({k}/{n})", ha="center",
            fontsize=8.5, color=INK)
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9, color=INK)
ax.set_ylim(0, 108); ax.set_ylabel("Violation rate (%)", fontsize=9.5, color=MUTED)
ax.set_xlabel("Strength of the authority preface", fontsize=9.5, color=MUTED)
ax.set_title("DeepSeek R1: authority framing acts as a switch, not a dial",
             fontsize=12, color=INK, loc="left", pad=10)
ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(colors=MUTED, labelsize=9)
fig.tight_layout(); fig.savefig("figure_dose_response.png", bbox_inches="tight")
print("wrote figure_dose_response.png")
