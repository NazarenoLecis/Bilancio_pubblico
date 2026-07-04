from utils_bilancio.regioni.bilanci import SOURCE_OPENBDAP_REGIONI
from utils_bilancio.generali.costanti import BLACK, CHART_DIR, NAVY, ORANGE, PAPER
from utils_bilancio.generali.utils import create_post, format_mld, save_chart


REGIONAL_CHART_FILES = [
    "21_bilanci_regionali_spesa_per_regione.png",
    "22_bilanci_regionali_entrate_per_regione.png",
    "23_bilanci_regionali_spesa_per_missione.png",
    "24_bilanci_regionali_saldi_per_regione.png",
]


def clean_regional_outputs():
    for filename in REGIONAL_CHART_FILES:
        path = CHART_DIR / filename
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                print(f"Output grafico regionale in uso, salto la rimozione: {path.name}")


def latest_frame(frame):
    if frame is None or frame.empty or "anno" not in frame:
        return None, None
    year = int(frame["anno"].max())
    return frame[frame["anno"] == year].copy(), year


def format_signed_mld(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{format_mld(value)}"


def plot_regional_spending_by_region(frame):
    latest, year = latest_frame(frame)
    if latest is None or latest.empty:
        return None

    latest = latest.sort_values("mld", ascending=True)
    filename = "21_bilanci_regionali_spesa_per_regione.png"
    fig, ax = create_post(
        [
            [("QUANTO ", BLACK), ("SPENDONO", ORANGE)],
            [("LE REGIONI?", BLACK)],
        ],
        f"Bilanci regionali, spese da consuntivo {year}\nMiliardi di euro correnti",
        axes_rect=[0.29, 0.305, 0.61, 0.42],
    )
    colors = [NAVY] * max(len(latest) - 1, 0) + [ORANGE]
    ax.barh(latest["regione"], latest["mld"], color=colors)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.tick_params(axis="x", labelsize=13)
    max_value = float(latest["mld"].max())
    for index, row in enumerate(latest.itertuples(index=False)):
        ax.text(row.mld + max_value * 0.012, index, format_mld(row.mld), va="center", fontsize=11.5, fontweight="bold")
    ax.set_xlim(0, max_value * 1.24)
    save_chart(fig, filename, SOURCE_OPENBDAP_REGIONI)
    return filename


def plot_regional_revenue_by_region(frame):
    latest, year = latest_frame(frame)
    if latest is None or latest.empty:
        return None

    latest = latest.sort_values("mld", ascending=True)
    filename = "22_bilanci_regionali_entrate_per_regione.png"
    fig, ax = create_post(
        [
            [("QUANTO ", BLACK), ("INCASSANO", ORANGE)],
            [("LE REGIONI?", BLACK)],
        ],
        f"Bilanci regionali, entrate da consuntivo {year}\nMiliardi di euro correnti",
        axes_rect=[0.29, 0.305, 0.61, 0.42],
    )
    colors = [NAVY] * max(len(latest) - 1, 0) + [ORANGE]
    ax.barh(latest["regione"], latest["mld"], color=colors)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.tick_params(axis="x", labelsize=13)
    max_value = float(latest["mld"].max())
    for index, row in enumerate(latest.itertuples(index=False)):
        ax.text(row.mld + max_value * 0.012, index, format_mld(row.mld), va="center", fontsize=11.5, fontweight="bold")
    ax.set_xlim(0, max_value * 1.24)
    save_chart(fig, filename, SOURCE_OPENBDAP_REGIONI)
    return filename


def plot_regional_spending_by_mission(frame):
    latest, year = latest_frame(frame)
    if latest is None or latest.empty or "missione" not in latest:
        return None

    grouped = latest.groupby("missione", as_index=False)["mld"].sum().sort_values("mld", ascending=True).tail(12)
    if grouped.empty:
        return None

    filename = "23_bilanci_regionali_spesa_per_missione.png"
    fig, ax = create_post(
        [
            [("DOVE ", BLACK), ("SPENDONO", ORANGE)],
            [("LE REGIONI?", BLACK)],
        ],
        f"Bilanci regionali, spesa per missione {year}\nSomma delle regioni, miliardi di euro correnti",
        axes_rect=[0.33, 0.305, 0.58, 0.42],
    )
    colors = [NAVY] * max(len(grouped) - 1, 0) + [ORANGE]
    ax.barh(grouped["missione"], grouped["mld"], color=colors)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=11.5)
    ax.tick_params(axis="x", labelsize=13)
    max_value = float(grouped["mld"].max())
    for index, row in enumerate(grouped.itertuples(index=False)):
        ax.text(row.mld + max_value * 0.012, index, format_mld(row.mld), va="center", fontsize=11.5, fontweight="bold")
    ax.set_xlim(0, max_value * 1.25)
    save_chart(fig, filename, SOURCE_OPENBDAP_REGIONI)
    return filename


def plot_regional_balances_by_region(frame):
    latest, year = latest_frame(frame)
    if latest is None or latest.empty:
        return None

    latest = latest.sort_values("mld", ascending=True)
    filename = "24_bilanci_regionali_saldi_per_regione.png"
    fig, ax = create_post(
        [
            [("QUALI ", BLACK), ("SALDI", ORANGE)],
            [("REGIONALI?", BLACK)],
        ],
        f"Bilanci regionali, saldi da consuntivo {year}\nMiliardi di euro correnti",
        axes_rect=[0.29, 0.305, 0.61, 0.42],
    )
    colors = [ORANGE if value < 0 else NAVY for value in latest["mld"]]
    ax.barh(latest["regione"], latest["mld"], color=colors)
    ax.axvline(0, color=BLACK, linewidth=1.4)
    ax.set_xlabel("Miliardi di euro", loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.tick_params(axis="x", labelsize=13)

    max_abs = float(latest["mld"].abs().max())
    for index, row in enumerate(latest.itertuples(index=False)):
        offset = max_abs * 0.025
        x_position = row.mld + offset if row.mld >= 0 else row.mld - offset
        ha = "left" if row.mld >= 0 else "right"
        ax.text(x_position, index, format_signed_mld(row.mld), ha=ha, va="center", fontsize=11.5, fontweight="bold")
    ax.set_xlim(-max_abs * 1.28, max_abs * 1.28)
    save_chart(fig, filename, SOURCE_OPENBDAP_REGIONI)
    return filename
