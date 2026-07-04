import numpy as np

from utils_bilancio.generali.costanti import (
    BLACK,
    NAVY,
    OECD_PEER_ORDER,
    ORANGE,
    SOURCE_OECD_REVENUE,
    SOURCE_OECD_SPENDING,
)
from utils_bilancio.generali.utils import create_post, format_percent, format_percent_compact, save_chart


def plot_oecd_category_comparison(frame, title_lines, subtitle, filename, source, axes_rect=None, value_formatter=format_percent):
    plot_frame = frame.iloc[::-1].reset_index(drop=True)
    fig, ax = create_post(
        title_lines,
        subtitle,
        axes_rect=axes_rect or [0.31, 0.305, 0.61, 0.43],
    )
    y_values = np.arange(len(plot_frame))
    height = 0.34
    ax.barh(y_values + height / 2, plot_frame["italia"], height=height, color=ORANGE, label="Italia")
    ax.barh(y_values - height / 2, plot_frame["ocse"], height=height, color=NAVY, label="Media OCSE")
    ax.set_yticks(y_values)
    ax.set_yticklabels(plot_frame["categoria"])
    ax.set_xlabel("% del PIL", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.tick_params(axis="x", labelsize=12)
    max_value = float(max(plot_frame["italia"].max(), plot_frame["ocse"].max()))
    for index, row in enumerate(plot_frame.itertuples(index=False)):
        ax.text(
            row.italia + max_value * 0.015,
            index + height / 2,
            value_formatter(row.italia),
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=ORANGE,
        )
        ax.text(
            row.ocse + max_value * 0.015,
            index - height / 2,
            value_formatter(row.ocse),
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=NAVY,
        )
    ax.set_xlim(0, max_value * 1.30)
    ax.legend(loc="lower right", fontsize=12)
    save_chart(fig, filename, source)


def selected_oecd_peers(frame):
    selected = frame[frame["REF_AREA"].isin(OECD_PEER_ORDER)].copy()
    selected["ordine"] = selected["REF_AREA"].map({code: index for index, code in enumerate(OECD_PEER_ORDER)})
    return selected.sort_values("ordine")


def plot_oecd_peer_comparison(frame, title_lines, subtitle, filename, source, value_formatter=format_percent):
    selected = selected_oecd_peers(frame).sort_values("valore", ascending=True)
    colors = []
    for row in selected.itertuples(index=False):
        if row.REF_AREA == "ITA":
            colors.append(ORANGE)
        elif row.REF_AREA == "OECD_AVG":
            colors.append("#777777")
        else:
            colors.append(NAVY)
    fig, ax = create_post(title_lines, subtitle, axes_rect=[0.25, 0.315, 0.66, 0.42])
    ax.barh(selected["paese"], selected["valore"], color=colors)
    ax.set_xlabel("% del PIL", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=13)
    ax.tick_params(axis="x", labelsize=13)
    max_value = float(selected["valore"].max())
    for index, value in enumerate(selected["valore"]):
        ax.text(value + max_value * 0.014, index, value_formatter(value), va="center", fontsize=12.5, fontweight="bold")
    ax.set_xlim(0, max_value * 1.22)
    save_chart(fig, filename, source)


def plot_oecd_revenue_categories(frame):
    plot_oecd_category_comparison(
        frame,
        [
            [("ITALIA VS ", BLACK), ("OCSE", ORANGE)],
            [("LE ENTRATE", BLACK)],
        ],
        "Entrate fiscali per categoria 2024\n% del PIL",
        "16_ocse_entrate_per_tipo_2024.png",
        SOURCE_OECD_REVENUE,
        axes_rect=[0.31, 0.305, 0.61, 0.43],
        value_formatter=format_percent_compact,
    )


def plot_oecd_spending_categories(frame):
    plot_oecd_category_comparison(
        frame,
        [
            [("ITALIA VS ", BLACK), ("OCSE", ORANGE)],
            [("LA SPESA", BLACK)],
        ],
        "Spesa pubblica per funzione COFOG 2024\n% del PIL",
        "17_ocse_spesa_per_funzione_2024.png",
        SOURCE_OECD_SPENDING,
        axes_rect=[0.28, 0.300, 0.64, 0.45],
    )


def plot_oecd_total_tax(peer_frame):
    plot_oecd_peer_comparison(
        peer_frame,
        [
            [("PRESSIONE ", BLACK), ("FISCALE", ORANGE)],
            [("OCSE", BLACK)],
        ],
        "Entrate fiscali e contributive 2024\n% del PIL",
        "18_ocse_pressione_fiscale_totale_2024.png",
        SOURCE_OECD_REVENUE,
    )


def plot_oecd_inheritance_tax(peer_frame):
    plot_oecd_peer_comparison(
        peer_frame,
        [
            [("SUCCESSIONI", ORANGE)],
            [("ITALIA VS OCSE", BLACK)],
        ],
        "Imposte su successioni e donazioni\n2024, % del PIL",
        "19_ocse_successioni_donazioni_2024.png",
        SOURCE_OECD_REVENUE,
        value_formatter=format_percent_compact,
    )


def plot_oecd_total_spending(peer_frame):
    plot_oecd_peer_comparison(
        peer_frame,
        [
            [("SPESA ", ORANGE), ("PUBBLICA", BLACK)],
            [("OCSE", BLACK)],
        ],
        "Spesa totale delle Amministrazioni pubbliche 2024\n% del PIL",
        "20_ocse_spesa_totale_2024.png",
        SOURCE_OECD_SPENDING,
    )
