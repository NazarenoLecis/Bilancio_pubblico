import pandas as pd

from utils_bilancio.generali.costanti import (
    BLACK,
    NAVY,
    ORANGE,
    SOURCE_BANKITALIA_WEALTH,
)
from utils_bilancio.generali.utils import create_post, format_percent, save_chart


def plot_household_wealth_distribution():
    frame = pd.DataFrame(
        [
            {"gruppo": "Top 10%\nfamiglie", "quota": 60.6, "color": ORANGE},
            {"gruppo": "Resto\n40%", "quota": 32.2, "color": NAVY},
            {"gruppo": "Meta' meno\nabbiente", "quota": 7.2, "color": NAVY},
        ]
    )
    fig, ax = create_post(
        [
            [("CHI POSSIEDE", BLACK)],
            [("IL ", BLACK), ("PATRIMONIO?", ORANGE)],
        ],
        "Distribuzione della ricchezza netta familiare\nQuote sul totale, IV trimestre 2025",
        axes_rect=[0.16, 0.34, 0.72, 0.39],
    )
    bars = ax.bar(frame["gruppo"], frame["quota"], color=frame["color"], width=0.60)
    ax.set_ylabel("Quota della ricchezza netta")
    ax.set_ylim(0, 70)
    ax.yaxis.set_major_formatter(lambda value, position: f"{int(value)}%")
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=13)
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 2.0,
            format_percent(value),
            ha="center",
            va="bottom",
            fontsize=17,
            fontweight="bold",
        )
    ax.text(
        0.04,
        0.88,
        "Ricchezza netta media: 453 mila euro per famiglia.\nIl Gini sale a 72,2 secondo Banca d'Italia.",
        transform=ax.transAxes,
        fontsize=12.0,
        bbox={"boxstyle": "round,pad=0.45", "fc": "#f6f3ed", "ec": BLACK, "lw": 1.5},
    )
    save_chart(fig, "14_distribuzione_patrimonio_famiglie_2025.png", SOURCE_BANKITALIA_WEALTH)
