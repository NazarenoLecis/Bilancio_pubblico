import numpy as np
import pandas as pd

from utils_bilancio.generali.costanti import (
    BLACK,
    NAVY,
    ORANGE,
    PAPER,
    SOURCE_EUROSTAT_TAX,
    SOURCE_MEF_DICHIARAZIONI,
    SOURCE_MEF_ENTRATE,
    SOURCE_MEF_ENTRATE_COMBINED,
    SOURCE_MEF_ENTRATE_WITH_APPENDICI,
    SOURCE_MEF_SUCCESSIONI,
    SUCCESSIONI_DONAZIONI_2025,
    SUCCESSIONI_DONAZIONI_SERIE,
)
from utils_bilancio.generali.utils import create_post, format_integer, format_mld, format_percent, save_chart
from utils_bilancio.generali.data_extraction import aggregate_columns_by_band, find_mef_item, mef_annual_series


def plot_main_taxes(erariali_items, erariali_months, territoriali_items, territoriali_months):
    candidates = [
        ("IRPEF", erariali_items, erariali_months, {"exact": "IRPEF"}),
        ("IVA", erariali_items, erariali_months, {"exact": "IVA"}),
        ("IRES", erariali_items, erariali_months, {"exact": "IRES"}),
        ("IRAP", territoriali_items, territoriali_months, {"exact": "IRAP"}),
        ("Accise prodotti energetici", erariali_items, erariali_months, {"starts": "Accisa sui prodotti energetici"}),
        ("Sostitutive su interessi e capitale", erariali_items, erariali_months, {"starts": "Sost. redditi"}),
        ("Tabacchi", erariali_items, erariali_months, {"starts": "Imposta sul consumo dei tabacchi"}),
        ("Bollo", erariali_items, erariali_months, {"exact": "Bollo"}),
        ("Sostitutiva plusvalenze", erariali_items, erariali_months, {"starts": "Sost. sui redditi da capitale"}),
        ("Registro", erariali_items, erariali_months, {"exact": "Registro"}),
        ("Energia elettrica", erariali_items, erariali_months, {"starts": "Accisa sull'energia elettrica"}),
    ]
    rows = []
    for display, items, months, selector in candidates:
        item = find_mef_item(items, **selector)
        annual = mef_annual_series(item, months)
        rows.append({"voce": display, "mld": float(annual.loc[2025])})
    frame = pd.DataFrame(rows).sort_values("mld", ascending=True).tail(10)

    fig, ax = create_post(
        [
            [("ENTRATE ", BLACK), ("TRIBUTARIE", ORANGE)],
            [("PRINCIPALI", BLACK)],
        ],
        "Imposte, accise e principali tributi 2025\nMiliardi di euro correnti",
        axes_rect=[0.31, 0.305, 0.58, 0.39],
    )
    colors = [NAVY] * (len(frame) - 1) + [ORANGE]
    ax.barh(frame["voce"], frame["mld"], color=colors)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=13)
    ax.tick_params(axis="x", labelsize=13)
    for index, value in enumerate(frame["mld"]):
        ax.text(
            value + frame["mld"].max() * 0.015,
            index,
            format_mld(value),
            va="center",
            fontsize=13,
            fontweight="bold",
        )
    ax.set_xlim(0, frame["mld"].max() * 1.16)
    save_chart(fig, "01_principali_entrate_tributarie_2025.png", SOURCE_MEF_ENTRATE_COMBINED)


def plot_direct_indirect(items, months):
    direct = mef_annual_series(find_mef_item(items, exact="Imposte dirette"), months)
    indirect = mef_annual_series(find_mef_item(items, exact="Imposte indirette"), months)
    frame = pd.DataFrame({"Dirette": direct, "Indirette": indirect}).dropna()
    frame = frame.loc[2002:2025]

    fig, ax = create_post(
        [
            [("IMPOSTE ", BLACK), ("DIRETTE", ORANGE)],
            [("E INDIRETTE", BLACK)],
        ],
        "Entrate erariali per natura\nMiliardi di euro correnti",
        axes_rect=[0.105, 0.305, 0.84, 0.455],
    )
    ax.stackplot(
        frame.index,
        frame["Dirette"],
        frame["Indirette"],
        labels=["Imposte dirette", "Imposte indirette"],
        colors=[NAVY, ORANGE],
        alpha=0.9,
    )
    total = frame["Dirette"] + frame["Indirette"]
    ax.plot(frame.index, total, color=BLACK, linewidth=2.8, marker="o", markersize=5)
    last_year = int(frame.index.max())
    last_value = float(total.loc[last_year])
    ax.scatter([last_year], [last_value], s=130, color=ORANGE, zorder=5)
    ax.annotate(
        f"{last_year}:\n{format_mld(last_value)} mld",
        xy=(last_year, last_value),
        xytext=(-82, 40),
        textcoords="offset points",
        color=ORANGE,
        fontsize=16,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.45", "fc": PAPER, "ec": ORANGE, "lw": 2},
        arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 2},
    )
    ax.set_ylabel("Miliardi di euro")
    ax.set_xlim(frame.index.min(), frame.index.max())
    ax.set_xticks(range(2002, 2026, 2))
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(axis="y")
    ax.legend(loc="upper left", fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, "02_entrate_dirette_indirette_2002_2025.png", SOURCE_MEF_ENTRATE)


def plot_tax_pressure(frame):
    fig, ax = create_post(
        [
            [("QUANTO ", BLACK), ("PESA", ORANGE), (" IL FISCO?", BLACK)],
        ],
        "Entrate fiscali e contributive in Italia\n% del PIL",
        axes_rect=[0.105, 0.305, 0.84, 0.455],
    )
    component_colors = ["#2f6f9f", "#8f5b9f", "#d29535", "#4d8b63"]
    total = frame.sum(axis=1)
    for color, column in zip(component_colors, frame.columns):
        ax.plot(frame.index, frame[column], color=color, linewidth=1.8, alpha=0.78, label=column)
    ax.plot(frame.index, total, color=BLACK, linewidth=3.2, marker="o", markersize=5, label="Totale")
    last_year = int(total.index.max())
    last_value = float(total.loc[last_year])
    ax.scatter([last_year], [last_value], s=145, color=ORANGE, zorder=5)
    ax.annotate(
        f"{last_year}:\n{format_percent(last_value)}",
        xy=(last_year, last_value),
        xytext=(-70, 38),
        textcoords="offset points",
        color=ORANGE,
        fontsize=17,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.45", "fc": PAPER, "ec": ORANGE, "lw": 2},
        arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 2},
    )
    ax.set_ylabel("% del PIL")
    ax.set_xlim(frame.index.min(), frame.index.max())
    ax.set_xticks(range(int(frame.index.min()), int(frame.index.max()) + 1, 3))
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(axis="y")
    ax.legend(loc="lower left", fontsize=11, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, "03_pressione_fiscale_componenti_1995_2024.png", SOURCE_EUROSTAT_TAX)


def plot_irpef_tax_by_band(calcolo):
    columns = [
        "Numero contribuenti",
        "Imposta netta - Ammontare in euro",
    ]
    grouped = aggregate_columns_by_band(calcolo, columns)
    grouped["imposta_mld"] = grouped["Imposta netta - Ammontare in euro"] / 1_000_000_000
    grouped["media_euro"] = grouped["Imposta netta - Ammontare in euro"] / grouped["Numero contribuenti"].replace(0, np.nan)

    fig, ax = create_post(
        [
            [("CHI ", BLACK), ("VERSA", ORANGE), (" L'IRPEF?", BLACK)],
        ],
        "Imposta netta per classi di reddito\nTotale e media per contribuente",
        axes_rect=[0.10, 0.32, 0.84, 0.42],
    )
    bars = ax.bar(grouped.index, grouped["imposta_mld"], color=ORANGE, label="Imposta netta totale")
    ax.set_ylabel("Miliardi di euro")
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=0, labelsize=12)
    ax.tick_params(axis="y", labelsize=13)

    axis_media = ax.twinx()
    axis_media.plot(grouped.index, grouped["media_euro"], color=NAVY, marker="o", linewidth=3.0, label="Media per contribuente")
    axis_media.set_ylabel("Euro per contribuente")
    axis_media.spines[["top"]].set_visible(False)
    axis_media.tick_params(axis="y", labelsize=13)

    for bar in bars:
        value = bar.get_height()
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 1.0,
                format_mld(value),
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold",
            )

    handles, labels = ax.get_legend_handles_labels()
    handles_media, labels_media = axis_media.get_legend_handles_labels()
    ax.legend(handles + handles_media, labels + labels_media, loc="upper left", fontsize=13)
    save_chart(fig, "05_irpef_netto_per_fascia_2024.png", SOURCE_MEF_DICHIARAZIONI)


def plot_irpef_shares_by_band(calcolo):
    columns = [
        "Numero contribuenti",
        "Imposta netta - Ammontare in euro",
    ]
    grouped = aggregate_columns_by_band(calcolo, columns)
    shares = pd.DataFrame(
        {
            "Contribuenti": grouped["Numero contribuenti"] / grouped["Numero contribuenti"].sum() * 100,
            "Imposta netta": grouped["Imposta netta - Ammontare in euro"]
            / grouped["Imposta netta - Ammontare in euro"].sum()
            * 100,
        }
    )

    fig, ax = create_post(
        [
            [("DISTRIBUZIONE ", BLACK), ("CONTRIBUENTI", ORANGE)],
            [("E ", BLACK), ("IMPOSTA NETTA", ORANGE)],
            [("PER CLASSI DI REDDITO", BLACK)],
        ],
        "(valori in percentuale)",
        axes_rect=[0.105, 0.315, 0.84, 0.33],
    )
    x_values = np.arange(len(shares.index))
    width = 0.33
    palette = [ORANGE, NAVY]
    for offset, column in enumerate(shares.columns):
        bars = ax.bar(x_values + (offset - 0.5) * width, shares[column], width=width, label=f"% {column}", color=palette[offset])
        for bar in bars:
            value = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 1.1,
                format_percent(value),
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold",
            )
    ax.set_ylabel("")
    ax.set_ylim(0, max(52, shares.to_numpy().max() + 7))
    ax.set_xticks(x_values)
    ax.set_xticklabels(shares.index)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=13)
    ax.yaxis.set_major_formatter(lambda value, position: f"{int(value)}%")
    ax.grid(axis="y")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.19), ncol=2, fontsize=15)
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, "06_quote_irpef_per_fascia_2024.png", SOURCE_MEF_DICHIARAZIONI)


def plot_wages_capital_distribution(tipo):
    columns = [
        "Reddito da lavoro dipendente e assimilati - Ammontare in euro",
        "Plusvalenze di natura finanziaria - Ammontare in euro",
        "Reddito di capitale (sez. IA e IB) - Ammontare in euro",
    ]
    grouped = aggregate_columns_by_band(tipo, columns)
    grouped["Lavoro dipendente e assimilati"] = grouped[columns[0]]
    grouped["Capitale e plusvalenze dichiarati"] = grouped[columns[1]] + grouped[columns[2]]

    shares = pd.DataFrame(
        {
            "Lavoro dipendente e assimilati": grouped["Lavoro dipendente e assimilati"]
            / grouped["Lavoro dipendente e assimilati"].sum()
            * 100,
            "Capitale e plusvalenze dichiarati": grouped["Capitale e plusvalenze dichiarati"]
            / grouped["Capitale e plusvalenze dichiarati"].sum()
            * 100,
        }
    )

    fig, ax = create_post(
        [
            [("SALARI E ", BLACK), ("CAPITALI", ORANGE)],
        ],
        "Dove si concentrano i redditi dichiarati\nQuote percentuali per categoria",
        axes_rect=[0.105, 0.315, 0.84, 0.43],
    )
    x_values = np.arange(len(shares.index))
    width = 0.36
    bars_lavoro = ax.bar(x_values - width / 2, shares["Lavoro dipendente e assimilati"], width=width, color=NAVY, label="Lavoro dipendente")
    bars_capitale = ax.bar(
        x_values + width / 2,
        shares["Capitale e plusvalenze dichiarati"],
        width=width,
        color=ORANGE,
        label="Capitale e plusvalenze dichiarati",
    )
    for bars in [bars_lavoro, bars_capitale]:
        for bar in bars:
            value = bar.get_height()
            if value >= 2.5:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 1.0,
                    format_percent(value),
                    ha="center",
                    va="bottom",
                    fontsize=12,
                    fontweight="bold",
                )
    ax.set_ylabel("Quota % del reddito della categoria")
    ax.set_xticks(x_values)
    ax.set_xticklabels(shares.index)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=13)
    ax.yaxis.set_major_formatter(lambda value, position: f"{int(value)}%")
    ax.grid(axis="y")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=13)
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, "07_distribuzione_salari_capitali_2024.png", SOURCE_MEF_DICHIARAZIONI)


def plot_income_composition(tipo):
    source_columns = {
        "Dipendente": ["Reddito da lavoro dipendente e assimilati - Ammontare in euro"],
        "Pensione": ["Reddito da pensione - Ammontare in euro"],
        "Autonomo": [
            "Reddito da lavoro autonomo - Ammontare in euro",
            "Altri redditi da lavoro autonomo provvigioni e redditi diversi da Mod. 770 - Ammontare in euro",
            "Altri redditi da lavoro autonomo e redditi da recupero start up - Ammontare in euro",
        ],
        "Impresa/partecipazione": [
            "Reddito di spettanza dell'imprenditore in contabilita' ordinaria - Ammontare in euro",
            "Reddito di spettanza dell'imprenditore in contabilita' semplificata - Ammontare in euro",
            "Reddito da partecipazione - Ammontare in euro",
        ],
        "Immobili/terreni": [
            "Reddito dominicale - Ammontare in euro",
            "Reddito agrario - Ammontare in euro",
            "Reddito di allevamento e produzione di vegetali - Ammontare in euro",
            "Reddito da fabbricati - Ammontare in euro",
        ],
        "Capitale/plusvalenze": [
            "Plusvalenze di natura finanziaria - Ammontare in euro",
            "Reddito di capitale (sez. IA e IB) - Ammontare in euro",
        ],
        "Altri": [
            "Redditi diversi - Ammontare in euro",
            "Tassazione separata con opzione tassazione ordinaria - Ammontare in euro",
        ],
    }
    all_columns = [column for columns in source_columns.values() for column in columns]
    grouped = aggregate_columns_by_band(tipo, all_columns)
    composition = pd.DataFrame(index=grouped.index)
    for label, columns in source_columns.items():
        composition[label] = grouped[columns].sum(axis=1) / 1_000_000_000

    colors = [NAVY, "#4d8b63", ORANGE, "#8f5b9f", "#d29535", "#6c8f9f", "#777777"]
    fig, ax = create_post(
        [
            [("DA DOVE ARRIVA", BLACK)],
            [("IL ", BLACK), ("REDDITO?", ORANGE)],
        ],
        "Composizione dei redditi dichiarati\nMiliardi di euro",
        axes_rect=[0.105, 0.405, 0.84, 0.30],
    )
    bottom = np.zeros(len(composition.index))
    x_values = np.arange(len(composition.index))
    for color, column in zip(colors, composition.columns):
        ax.bar(x_values, composition[column], bottom=bottom, color=color, label=column)
        bottom = bottom + composition[column].to_numpy()

    ax.set_ylabel("Miliardi di euro")
    ax.set_xticks(x_values)
    ax.set_xticklabels(composition.index)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=13)
    ax.grid(axis="y")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 0.322),
        bbox_transform=fig.transFigure,
        ncol=3,
        fontsize=11.5,
        handlelength=1.5,
        columnspacing=1.6,
    )
    ax.spines[["top", "right"]].set_visible(False)
    save_chart(fig, "08_composizione_redditi_per_fascia_2024.png", SOURCE_MEF_DICHIARAZIONI)


def plot_revenue_types(erariali_items, erariali_months, territoriali_items, territoriali_months):
    def erariali(label=None, starts=None):
        return mef_annual_series(find_mef_item(erariali_items, exact=label, starts=starts), erariali_months).loc[2025]

    def territoriali(label=None, starts=None):
        return mef_annual_series(find_mef_item(territoriali_items, exact=label, starts=starts), territoriali_months).loc[2025]

    rows = [
        {
            "tipo": "Redditi persone\nIRPEF + addizionali",
            "mld": erariali("IRPEF") + territoriali("Addizionale regionale IRPEF") + territoriali("Addizionale comunale IRPEF"),
        },
        {
            "tipo": "Consumi\nIVA + accise",
            "mld": erariali("IVA")
            + erariali(starts="Accisa sui prodotti energetici")
            + erariali(starts="Accisa sul gas naturale")
            + erariali(starts="Accisa sull'energia elettrica")
            + erariali(starts="Imposta sul consumo dei tabacchi"),
        },
        {
            "tipo": "Imprese\nIRES + IRAP",
            "mld": erariali("IRES") + territoriali("IRAP"),
        },
        {
            "tipo": "Immobili e\npatrimonio",
            "mld": territoriali("Imu - Imis (Quota Comuni)") + erariali("Registro") + erariali("Bollo") + SUCCESSIONI_DONAZIONI_2025,
        },
        {
            "tipo": "Capitale\nfinanziario",
            "mld": erariali(starts="Sost. redditi") + erariali(starts="Sost. sui redditi da capitale"),
        },
    ]
    frame = pd.DataFrame(rows).sort_values("mld", ascending=False)
    fig, ax = create_post(
        [
            [("DA DOVE ARRIVANO", BLACK)],
            [("LE ", BLACK), ("ENTRATE?", ORANGE)],
        ],
        "Aggregazioni delle principali imposte 2025\nMiliardi di euro correnti",
        axes_rect=[0.12, 0.335, 0.80, 0.39],
    )
    colors = [ORANGE] + [NAVY] * (len(frame) - 1)
    bars = ax.bar(frame["tipo"], frame["mld"], color=colors, width=0.62)
    ax.set_ylabel("Miliardi di euro")
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=13)
    ax.set_ylim(0, frame["mld"].max() * 1.18)
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + frame["mld"].max() * 0.025,
            format_mld(value),
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
        )
    ax.text(
        0.02,
        0.93,
        "Focus su gruppi principali: non include ogni voce minore.",
        transform=ax.transAxes,
        fontsize=11.5,
        bbox={"boxstyle": "round,pad=0.35", "fc": PAPER, "ec": BLACK, "lw": 1.3},
    )
    save_chart(fig, "12_tipi_entrate_tributarie_2025.png", SOURCE_MEF_ENTRATE_WITH_APPENDICI)


def plot_succession_tax_focus(erariali_items, erariali_months):
    frame = pd.DataFrame(SUCCESSIONI_DONAZIONI_SERIE)
    total_erariali = mef_annual_series(find_mef_item(erariali_items, exact="Totale entrate"), erariali_months).loc[2025]
    share_total = SUCCESSIONI_DONAZIONI_2025 / total_erariali * 100.0

    fig, ax = create_post(
        [
            [("SUCCESSIONI:", ORANGE)],
            [("QUANTO INCASSA?", BLACK)],
        ],
        "Imposta su successioni e donazioni\nAccertamenti, milioni di euro",
        axes_rect=[0.17, 0.335, 0.66, 0.39],
    )
    colors = [NAVY, NAVY, ORANGE]
    bars = ax.bar(frame["anno"].astype(str), frame["milioni"], color=colors, width=0.56)
    ax.set_ylabel("Milioni di euro")
    ax.set_ylim(0, 1280)
    ax.grid(axis="y")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=15)
    ax.tick_params(axis="y", labelsize=13)
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 28,
            format_integer(value),
            ha="center",
            va="bottom",
            fontsize=17,
            fontweight="bold",
        )
    ax.annotate(
        "2025:\n1,081 mld\n(+6,8% sul 2024)",
        xy=(2, 1081),
        xytext=(44, 52),
        textcoords="offset points",
        color=ORANGE,
        fontsize=16,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.45", "fc": PAPER, "ec": ORANGE, "lw": 2},
        arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 2},
    )
    ax.text(
        0.03,
        0.88,
        f"Vale circa {format_percent(share_total)} delle entrate erariali 2025.",
        transform=ax.transAxes,
        fontsize=12.2,
        bbox={"boxstyle": "round,pad=0.45", "fc": PAPER, "ec": BLACK, "lw": 1.5},
    )
    save_chart(fig, "15_successioni_donazioni_2025.png", SOURCE_MEF_SUCCESSIONI)
