"""Stage 5: violation-rate chart and summary stats from results.csv.

Local only - no API calls. Produces figure_violation_rates.png.
"""

import math

import matplotlib.pyplot as plt
import pandas as pd

ORDER = [
    "D0_control", "D1_reward_conflict", "D2_opaque_evaluative",
    "D3_descriptive_code", "D4_block_first", "D5_authoritative",
    "D6_non_authoritative", "D8_auth_opaque", "D9_nonauth_opaque",
    "D7_congruent", "D0_mirror", "D1_mirror",
]
LABELS = {
    "D0_control": "D0 control (no block)",
    "D1_reward_conflict": "D1 reward conflict",
    "D2_opaque_evaluative": "D2 opaque evaluative",
    "D3_descriptive_code": "D3 descriptive code",
    "D4_block_first": "D4 block first",
    "D5_authoritative": "D5 authoritative",
    "D6_non_authoritative": "D6 non-authoritative",
    "D8_auth_opaque": "D8 authority + opaque",
    "D9_nonauth_opaque": "D9 non-auth + opaque",
    "D7_congruent": "D7 congruent",
    "D0_mirror": "D0 mirror (odd asked)",
    "D1_mirror": "D1 mirror (odd asked)",
}
DEEPSEEK = "deepseek/deepseek-r1-0528"
BLUE = "#4269D0"
INK, MUTED, GRID = "#1A1A2E", "#5A5A6E", "#E4E4EC"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return max(0.0, centre - half), min(1.0, centre + half)


def main():
    df = pd.read_csv("results.csv")
    valid = df[df.outcome.isin(["compliant", "violating"])]

    # --- console summary: every model x condition with counts and CIs ---
    print("Violations / valid trials (95% Wilson CI), per model:\n")
    for model, g in valid.groupby("model"):
        rows = []
        for cond in ORDER:
            cell = g[g.condition == cond]
            k = int((cell.outcome == "violating").sum())
            n = len(cell)
            lo, hi = wilson_ci(k, n)
            rows.append(f"  {LABELS[cond]:26s} {k:2d}/{n}  "
                        f"({100*k/max(n,1):3.0f}%, CI {100*lo:.0f}-{100*hi:.0f}%)")
        if (g.outcome == "violating").sum() == 0:
            print(f"{model}: 0 violations in {len(g)} valid trials")
        else:
            print(model)
            print("\n".join(rows))
        print()

    # --- figure: DeepSeek by condition (the only model with signal) ---
    ds = valid[valid.model == DEEPSEEK]
    rates, los, his = [], [], []
    for cond in ORDER:
        cell = ds[ds.condition == cond]
        k = int((cell.outcome == "violating").sum())
        n = len(cell)
        lo, hi = wilson_ci(k, n)
        rates.append(100 * k / n)
        los.append(100 * (k / n - lo))
        his.append(100 * (hi - k / n))

    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y = range(len(ORDER))[::-1]
    ax.barh(list(y), rates, height=0.62, color=BLUE, zorder=3)
    ax.errorbar(rates, list(y), xerr=[los, his], fmt="none",
                ecolor=MUTED, elinewidth=1.2, capsize=3, zorder=4)

    for yi, rate, lo_off, hi_off in zip(y, rates, los, his):
        if rate + hi_off < 88:  # label beyond the upper CI whisker
            ax.text(rate + hi_off + 1.5, yi, f"{rate:.0f}%",
                    va="center", ha="left", fontsize=9, color=INK)
        else:  # long bar: label inside it, left of the lower whisker
            ax.text(rate - lo_off - 2, yi, f"{rate:.0f}%",
                    va="center", ha="right", fontsize=9, color="white")

    ax.set_yticks(list(y))
    ax.set_yticklabels([LABELS[c] for c in ORDER], fontsize=9.5, color=INK)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Instruction-violation rate (%), n=30 per cell, 95% CI",
                  fontsize=9.5, color=MUTED)
    ax.set_title("DeepSeek R1: violation of the parity instruction by condition",
                 fontsize=12, color=INK, loc="left", pad=14)
    ax.text(0, 1.02, "Other four models: 0% in every condition "
            "(except Llama 3.3, 10% in D2)",
            transform=ax.transAxes, fontsize=8.5, color=MUTED)

    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)

    fig.tight_layout()
    fig.savefig("figure_violation_rates.png", bbox_inches="tight")
    print("wrote figure_violation_rates.png")


if __name__ == "__main__":
    main()
