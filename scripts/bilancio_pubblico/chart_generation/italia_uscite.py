from bilancio_pubblico.utils import (
    BLACK,
    NAVY,
    ORANGE,
    PAPER,
    SOURCE_EUROSTAT_EXP,
)
from bilancio_pubblico.utils import create_post, format_mld, format_percent, save_chart


def plot_cofog_spending(frame):
    year = int(frame["anno"].max())
    year_frame = frame[frame["anno"] == year].sort_values("mld", ascending=True)
    fig, ax = create_post(
        [
            [("QUANTO ", BLACK), ("SPENDE", ORANGE)],
            [("LO STATO ITALIANO?", BLACK)],
        ],
        "Spesa delle Amministrazioni pubbliche per funzione\nMiliardi di euro correnti",
        axes_rect=[0.29, 0.305, 0.61, 0.39],
    )
    colors = [NAVY] * (len(year_frame) - 1) + [ORANGE]
    ax.barh(year_frame["funzione"], year_frame["mld"], color=colors)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=13)
    ax.tick_params(axis="x", labelsize=13)
    max_value = year_frame["mld"].max()
    for index, row in enumerate(year_frame.itertuples(index=False)):
        label = f"{format_mld(row.mld)} mld | {format_percent(row.pil)} PIL"
        ax.text(row.mld + max_value * 0.012, index, label, va="center", fontsize=11.5, fontweight="bold")
    ax.set_xlim(0, max_value * 1.35)
    save_chart(fig, "04_spesa_pubblica_funzioni_cofog_2024.png", SOURCE_EUROSTAT_EXP)


def plot_total_spending_italy(frame):
    selected = frame.loc[1995:2024]
    fig, ax = create_post(
        [
            [("QUANTO ", BLACK), ("SPENDE", ORANGE)],
            [("LO STATO?", BLACK)],
        ],
        "Spesa totale delle Amministrazioni pubbliche\nMiliardi di euro correnti e % del PIL",
        axes_rect=[0.105, 0.315, 0.82, 0.42],
    )
    ax.plot(selected.index, selected["mld"], color=BLACK, linewidth=3.0, marker="o", markersize=4.5)
    last_year = int(selected.index.max())
    last_mld = float(selected.loc[last_year, "mld"])
    ax.scatter([last_year], [last_mld], s=145, color=ORANGE, zorder=5)
    ax.annotate(
        f"{last_year}:\n{format_mld(last_mld)} mld",
        xy=(last_year, last_mld),
        xytext=(-76, 42),
        textcoords="offset points",
        color=ORANGE,
        fontsize=16,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.45", "fc": PAPER, "ec": ORANGE, "lw": 2},
        arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 2},
    )
    ax.set_ylabel("Miliardi di euro")
    ax.set_xlim(selected.index.min(), selected.index.max())
    ax.set_xticks(range(1995, 2025, 5))
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=13)

    axis_pil = ax.twinx()
    axis_pil.plot(selected.index, selected["pil"], color=ORANGE, linewidth=2.0, linestyle=(0, (4, 3)), alpha=0.85)
    axis_pil.set_ylabel("% del PIL")
    axis_pil.tick_params(axis="y", labelsize=13)
    axis_pil.spines[["top"]].set_visible(False)
    axis_pil.yaxis.set_major_formatter(lambda value, position: f"{value:.0f}%")
    ax.text(
        0.02,
        0.91,
        "Linea nera: miliardi correnti\nLinea arancio tratteggiata: % PIL",
        transform=ax.transAxes,
        fontsize=11.5,
        bbox={"boxstyle": "round,pad=0.35", "fc": PAPER, "ec": BLACK, "lw": 1.3},
    )
    save_chart(fig, "13_spesa_totale_italia_1995_2024.png", SOURCE_EUROSTAT_EXP)
