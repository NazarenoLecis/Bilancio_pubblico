"""Funzioni condivise per download, grafici, formatter e scrittura output."""

import json
import textwrap
from io import StringIO

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.offsetbox import AnchoredOffsetbox, HPacker, TextArea

import utils_bilancio.generali.costanti as costanti



def ensure_directories():
    # Crea cartelle indispensabili prima di leggere/scrivere.
    costanti.DATA_DIR.mkdir(parents=True, exist_ok=True)
    costanti.CHART_DIR.mkdir(parents=True, exist_ok=True)


def clean_generated_outputs():
    # Elimina i vecchi png dichiarati per evitare sovrascritture non desiderate.
    for filename in costanti.GENERATED_FILES:
        path = costanti.CHART_DIR / filename
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                print(f"Output grafico in uso, salto la rimozione: {path.name}")


def configure_style():
    # Imposta uno stile unico per tutti i grafici (layout social, leggibilità, griglia sobria).
    plt.rcParams.update(
        {
            "figure.facecolor": costanti.PAPER,
            "axes.facecolor": costanti.PAPER,
            "axes.edgecolor": costanti.BLACK,
            "axes.labelcolor": costanti.BLACK,
            "axes.titlecolor": costanti.BLACK,
            "axes.titlesize": 20,
            "axes.titleweight": "bold",
            "axes.labelsize": 15,
            "font.family": "DejaVu Sans",
            "font.size": 14,
            "legend.frameon": False,
            "xtick.color": costanti.BLACK,
            "ytick.color": costanti.BLACK,
            "grid.color": costanti.GRID,
            "grid.linewidth": 1.0,
            "grid.linestyle": (0, (3, 3)),
            "savefig.dpi": 180,
        }
    )


def fetch_bytes(url, cache_name, refresh):
    # Download con cache locale:
    # - se esiste e refresh=False, riusa il file salvato
    # - se manca o refresh=True, richiede alla sorgente e sovrascrive.
    cache_path = costanti.DATA_DIR / cache_name
    if cache_path.exists() and not refresh:
        return cache_path.read_bytes()

    response = requests.get(
        url,
        headers={"User-Agent": costanti.USER_AGENT},
        timeout=90,
    )
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    return response.content


def fetch_json(url, cache_name, refresh):
    # Wrapper JSON usato da molte fonti.
    raw = fetch_bytes(url, cache_name, refresh)
    return json.loads(raw.decode("utf-8"))


def load_semicolon_csv(url, cache_name, refresh):
    # Scarica CSV con separatore ; (MEF dichiarazioni) e lo lascia già nel formato pandas.
    fetch_bytes(url, cache_name, refresh)
    cache_path = costanti.DATA_DIR / cache_name
    return pd.read_csv(cache_path, sep=";", thousands=".", decimal=",")


def load_oecd_csv(base_url, key, cache_name, refresh, start_year=2024, end_year=2024):
    # Scarica serie OECD in CSV e verifica che il payload sia valido prima di parseare.
    from urllib.parse import urlencode

    url = f"{base_url}/{key}?{urlencode({'startPeriod': start_year, 'endPeriod': end_year})}"
    cache_path = costanti.DATA_DIR / cache_name
    if cache_path.exists() and not refresh:
        raw = cache_path.read_bytes()
        if not raw.decode("utf-8", errors="ignore").startswith("DATAFLOW"):
            raw = None
    else:
        raw = None

    if raw is None:
        response = requests.get(
            url,
            headers={"User-Agent": costanti.USER_AGENT, "Accept": "text/csv"},
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
    # Inserisce testo in calce (+ eventuale logo) prima di salvare il file finale.
    footer = f"{source}."
    fig.text(
        0.5,
        0.177,
        textwrap.fill(footer, width=92),
        ha="center",
        va="center",
        fontsize=14,
        color=costanti.BLACK,
        style="italic",
    )
    fig.text(
        0.5,
        0.135,
        costanti.AUTHOR_LINE,
        ha="center",
        va="center",
        fontsize=16,
        color=costanti.BLACK,
        style="italic",
    )
    add_logo(fig)
    fig.savefig(costanti.CHART_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def add_logo(fig):
    # Aggiunge il logo gufo in fondo, se presente in /assets.
    if not costanti.LOGO_PATH.exists():
        return
    logo = mpimg.imread(costanti.LOGO_PATH)
    logo_axis = fig.add_axes([0.425, 0.006, 0.15, 0.11], anchor="C")
    logo_axis.imshow(logo)
    logo_axis.axis("off")


def draw_title_line(fig, y_position, parts, size):
    # Disegna il titolo colorato multisegmento usato su tutti i contenuti.
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
    # Crea la "scaffold" del grafico: titolo, sottotitolo, divider e area plot.
    fig = plt.figure(figsize=(10.8, 13.5), facecolor=costanti.PAPER)
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
        color=costanti.BLACK,
        linespacing=1.18,
    )
    divider_y = subtitle_y - 0.062
    fig.add_artist(plt.Line2D([0.39, 0.61], [divider_y, divider_y], color=costanti.ORANGE, linewidth=3.2, transform=fig.transFigure))
    rect = axes_rect or [0.11, 0.305, 0.82, 0.445]
    ax = fig.add_axes(rect)
    return fig, ax


def format_mld(value):
    # Formatta miliardi in stile italiano per assi e annotazioni.
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value):
    # Formatta percentuali con una cifra decimale (stile italiano).
    return f"{value:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent_compact(value):
    # Per variazioni piccoli valori usa 2 decimali, altrimenti formato standard.
    if abs(value) < 1:
        return f"{value:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    return format_percent(value)


def format_integer(value):
    # Formattazione numeri interi con separatore migliaia.
    return f"{value:,.0f}".replace(",", ".")


def write_manifest(entries):
    # Salva l'indice dei grafici: utile per tracciabilità e verifica pubblicazione.
    manifest = pd.DataFrame(entries)
    manifest.to_csv(costanti.CHART_DIR / "manifest.csv", index=False)


def write_text_file(path, lines):
    # Salva testi (analisi claims) con newline finale coerente.
    (costanti.BASE_DIR / path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def navy_or_orange_colors(frame, italy_code_column="codice", italy_code="IT"):
    # Utility rapida per evidenziare Italia in confronto a un ranking paese.
    return [costanti.ORANGE if getattr(row, italy_code_column) == italy_code else costanti.NAVY for row in frame.itertuples(index=False)]
