import json
import textwrap
from io import StringIO
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.offsetbox import AnchoredOffsetbox, HPacker, TextArea


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "raw"
CHART_DIR = BASE_DIR / "grafici"
ASSET_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSET_DIR / "gufo_logo.png"

USER_AGENT = "Fisco grafici - Elaborazione Nazareno Lecis"
AUTHOR_LINE = "Elaborazione di Nazareno Lecis"

MEF_ENTRATE_URL = "https://www1.finanze.gov.it/finanze/entrate_tributarie/public/api/api.php?action=get_entrate_erariali"
MEF_TERRITORIALI_URL = "https://www1.finanze.gov.it/finanze/entrate_tributarie/public/api/api.php?action=get_entrate_tributarie"
MEF_DICHIARAZIONI_BASE = "https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
OECD_REVENUE_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD"
OECD_COFOG_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11"
OECD_GDP_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE1"

ORANGE = "#f05a1a"
BLACK = "#090909"
NAVY = "#0d1b2a"
PAPER = "#f6f3ed"
GRID = "#d8d4ca"

BAND_ORDER = [
    "0 - 15.000",
    "15.001 - 29.000",
    "29.001 - 55.000",
    "55.001 - 75.000",
    "oltre 75.000",
]

COFOG_LABELS = {
    "GF01": "Servizi generali",
    "GF02": "Difesa",
    "GF03": "Ordine pubblico",
    "GF04": "Affari economici",
    "GF05": "Ambiente",
    "GF06": "Casa e territorio",
    "GF07": "Sanita",
    "GF08": "Cultura e religione",
    "GF09": "Istruzione",
    "GF10": "Protezione sociale",
}

TAXAG_LABELS = {
    "D2": "Produzione e importazioni",
    "D5": "Reddito e patrimonio",
    "D61": "Contributi sociali netti",
    "D91": "Imposte in conto capitale",
}

SOURCE_MEF_ENTRATE = (
    "Fonte: MEF - Dipartimento delle Finanze, Entrate tributarie erariali, "
    "competenza giuridica"
)
SOURCE_MEF_ENTRATE_COMBINED = (
    "Fonte: MEF - Dipartimento delle Finanze, Entrate tributarie erariali e territoriali, "
    "competenza giuridica"
)
SOURCE_MEF_ENTRATE_WITH_APPENDICI = (
    "Fonte: MEF - Dipartimento delle Finanze, API entrate erariali e territoriali; "
    "Appendici statistiche dicembre 2025"
)
SOURCE_MEF_DICHIARAZIONI = (
    "Fonte: MEF - Dipartimento delle Finanze, Statistiche dichiarazioni 2025, "
    "anno d'imposta 2024"
)
SOURCE_MEF_SUCCESSIONI = (
    "Fonte: MEF - Dipartimento delle Finanze, Appendici statistiche al bollettino entrate tributarie, "
    "dicembre 2025"
)
SOURCE_EUROSTAT_TAX = (
    "Fonte: Eurostat gov_10a_taxag, amministrazioni pubbliche S13"
)
SOURCE_EUROSTAT_EXP = (
    "Fonte: Eurostat gov_10a_exp, spesa totale S13 per funzione COFOG"
)
SOURCE_BANKITALIA_WEALTH = (
    "Fonte: Banca d'Italia, Conti distributivi sulla ricchezza delle famiglie, IV trimestre 2025"
)
SOURCE_OECD_REVENUE = (
    "Fonte: OCSE, Revenue Statistics 2025, Comparative tax revenues, dati 2024"
)
SOURCE_OECD_SPENDING = (
    "Fonte: OCSE, National Accounts Statistics, Table 1100 COFOG e Table 0101 PIL corrente, dati 2024"
)

SUCCESSIONI_DONAZIONI_2025 = 1.081
SUCCESSIONI_DONAZIONI_SERIE = [
    {"anno": 2023, "milioni": 998},
    {"anno": 2024, "milioni": 1012},
    {"anno": 2025, "milioni": 1081},
]

PEER_GEOS = {
    "IT": "Italia",
    "EU27_2020": "UE",
    "EA20": "Area euro",
    "FR": "Francia",
    "DE": "Germania",
    "ES": "Spagna",
    "SE": "Svezia",
    "DK": "Danimarca",
    "BE": "Belgio",
    "AT": "Austria",
}

OECD_MEMBER_AREAS = [
    "AUS",
    "AUT",
    "BEL",
    "CAN",
    "CHL",
    "COL",
    "CRI",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "ISL",
    "IRL",
    "ISR",
    "ITA",
    "JPN",
    "KOR",
    "LVA",
    "LTU",
    "LUX",
    "MEX",
    "NLD",
    "NZL",
    "NOR",
    "POL",
    "PRT",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
    "CHE",
    "TUR",
    "GBR",
    "USA",
]

OECD_AREA_LABELS = {
    "OECD_AVG": "Media OCSE",
    "ITA": "Italia",
    "FRA": "Francia",
    "DEU": "Germania",
    "ESP": "Spagna",
    "GBR": "Regno Unito",
    "USA": "Stati Uniti",
    "SWE": "Svezia",
    "DNK": "Danimarca",
    "NLD": "Paesi Bassi",
    "BEL": "Belgio",
    "AUT": "Austria",
}
OECD_PEER_ORDER = ["USA", "GBR", "ESP", "DEU", "OECD_AVG", "ITA", "FRA", "SWE", "DNK"]

OECD_REVENUE_CATEGORIES = [
    {"codice": "_T", "categoria": "Totale\nfisco"},
    {"codice": "T_1100", "categoria": "Redditi\npersone"},
    {"codice": "T_1200", "categoria": "Imprese"},
    {"codice": "T_2000", "categoria": "Contributi\nsociali"},
    {"codice": "T_5000", "categoria": "Beni e\nservizi"},
    {"codice": "T_5111", "categoria": "IVA"},
    {"codice": "T_5120", "categoria": "Accise e\nspecifiche"},
    {"codice": "T_4000", "categoria": "Patrimonio"},
    {"codice": "T_4300", "categoria": "Successioni\ne donazioni"},
]

OECD_SPENDING_CATEGORIES = [{"codice": "_T", "categoria": "Totale"}] + [
    {"codice": code, "categoria": label}
    for code, label in COFOG_LABELS.items()
]

GENERATED_FILES = [
    "01_principali_entrate_tributarie_2025.png",
    "01_principali_entrate_tributarie_erariali_2025.png",
    "02_entrate_dirette_indirette_2002_2025.png",
    "03_pressione_fiscale_componenti_1995_2024.png",
    "04_spesa_pubblica_funzioni_cofog_2024.png",
    "05_irpef_netto_per_fascia_2024.png",
    "06_quote_irpef_per_fascia_2024.png",
    "07_distribuzione_salari_capitali_2024.png",
    "08_composizione_redditi_per_fascia_2024.png",
    "09_pressione_fiscale_confronto_ue_2024.png",
    "10_spesa_pubblica_confronto_ue_2024.png",
    "11_protezione_sociale_confronto_ue_2024.png",
    "12_tipi_entrate_tributarie_2025.png",
    "13_spesa_totale_italia_1995_2024.png",
    "14_distribuzione_patrimonio_famiglie_2025.png",
    "15_successioni_donazioni_2025.png",
    "16_ocse_entrate_per_tipo_2024.png",
    "17_ocse_spesa_per_funzione_2024.png",
    "18_ocse_pressione_fiscale_totale_2024.png",
    "19_ocse_successioni_donazioni_2024.png",
    "20_ocse_spesa_totale_2024.png",
    "12_gettito_1_percento_vs_superbonus.png",
    "13_aliquote_patrimoniale_1_percento.png",
    "14_successioni_gettito_riforma.png",
    "15_imu_prima_seconda_casa.png",
]


def ensure_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)


def clean_generated_outputs():
    for filename in GENERATED_FILES:
        path = CHART_DIR / filename
        if path.exists():
            path.unlink()


def configure_style():
    plt.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "axes.edgecolor": BLACK,
            "axes.labelcolor": BLACK,
            "axes.titlecolor": BLACK,
            "axes.titlesize": 20,
            "axes.titleweight": "bold",
            "axes.labelsize": 15,
            "font.family": "DejaVu Sans",
            "font.size": 14,
            "legend.frameon": False,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
            "grid.color": GRID,
            "grid.linewidth": 1.0,
            "grid.linestyle": (0, (3, 3)),
            "savefig.dpi": 180,
        }
    )


def fetch_bytes(url, cache_name, refresh):
    cache_path = DATA_DIR / cache_name
    if cache_path.exists() and not refresh:
        return cache_path.read_bytes()

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=90,
    )
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    return response.content


def fetch_json(url, cache_name, refresh):
    raw = fetch_bytes(url, cache_name, refresh)
    return json.loads(raw.decode("utf-8"))


def load_semicolon_csv(url, cache_name, refresh):
    fetch_bytes(url, cache_name, refresh)
    cache_path = DATA_DIR / cache_name
    return pd.read_csv(cache_path, sep=";", thousands=".", decimal=",")


def load_oecd_csv(base_url, key, cache_name, refresh, start_year=2024, end_year=2024):
    from urllib.parse import urlencode

    url = f"{base_url}/{key}?{urlencode({'startPeriod': start_year, 'endPeriod': end_year})}"
    cache_path = DATA_DIR / cache_name
    if cache_path.exists() and not refresh:
        raw = cache_path.read_bytes()
        if not raw.decode("utf-8", errors="ignore").startswith("DATAFLOW"):
            raw = None
    else:
        raw = None

    if raw is None:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
            timeout=90,
        )
        response.raise_for_status()
        raw = response.content
        cache_path.write_bytes(raw)

    text = raw.decode("utf-8")
    if not text.startswith("DATAFLOW"):
        raise ValueError(f"Risposta OCSE inattesa per {key}: {text[:80]}")
    return pd.read_csv(StringIO(text))


def save_chart(fig, filename, source):
    footer = f"{source}."
    fig.text(
        0.5,
        0.177,
        textwrap.fill(footer, width=92),
        ha="center",
        va="center",
        fontsize=14,
        color=BLACK,
        style="italic",
    )
    fig.text(
        0.5,
        0.135,
        AUTHOR_LINE,
        ha="center",
        va="center",
        fontsize=16,
        color=BLACK,
        style="italic",
    )
    add_logo(fig)
    fig.savefig(CHART_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def add_logo(fig):
    if not LOGO_PATH.exists():
        return
    logo = mpimg.imread(LOGO_PATH)
    logo_axis = fig.add_axes([0.425, 0.006, 0.15, 0.11], anchor="C")
    logo_axis.imshow(logo)
    logo_axis.axis("off")


def draw_title_line(fig, y_position, parts, size):
    areas = []
    for text, color in parts:
        areas.append(
            TextArea(
                text,
                textprops={
                    "color": color,
                    "fontsize": size,
                    "fontweight": "black",
                    "fontfamily": "DejaVu Sans",
                },
            )
        )
    packed = HPacker(children=areas, align="center", pad=0, sep=2)
    anchored = AnchoredOffsetbox(
        loc="center",
        child=packed,
        pad=0,
        frameon=False,
        bbox_to_anchor=(0.5, y_position),
        bbox_transform=fig.transFigure,
        borderpad=0,
    )
    fig.add_artist(anchored)


def create_post(title_lines, subtitle, axes_rect=None):
    fig = plt.figure(figsize=(10.8, 13.5), facecolor=PAPER)
    title_size = 42 if len(title_lines) <= 2 else 37
    y_start = 0.925
    line_gap = 0.062
    for index, parts in enumerate(title_lines):
        draw_title_line(fig, y_start - index * line_gap, parts, title_size)

    subtitle_y = y_start - len(title_lines) * line_gap - 0.02
    fig.text(
        0.5,
        subtitle_y,
        subtitle,
        ha="center",
        va="top",
        fontsize=22,
        color=BLACK,
        linespacing=1.18,
    )
    divider_y = subtitle_y - 0.062
    fig.add_artist(plt.Line2D([0.39, 0.61], [divider_y, divider_y], color=ORANGE, linewidth=3.2, transform=fig.transFigure))
    rect = axes_rect or [0.11, 0.305, 0.82, 0.445]
    ax = fig.add_axes(rect)
    return fig, ax


def format_mld(value):
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value):
    return f"{value:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent_compact(value):
    if abs(value) < 1:
        return f"{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    return format_percent(value)


def format_integer(value):
    return f"{value:,.0f}".replace(",", ".")


def write_manifest(entries):
    manifest = pd.DataFrame(entries)
    manifest.to_csv(CHART_DIR / "manifest.csv", index=False)


def write_text_file(path, lines):
    (BASE_DIR / path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def navy_or_orange_colors(frame, italy_code_column="codice", italy_code="IT"):
    return [ORANGE if getattr(row, italy_code_column) == italy_code else NAVY for row in frame.itertuples(index=False)]
