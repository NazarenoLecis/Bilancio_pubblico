"""Funzioni di estrazione + normalizzazione dei dataset.

Qui trovi un solo punto di ingresso per ogni fonte:
- MEF (entrate, territoriale, dichiarazioni)
- Eurostat (imposta, contributiva, COFOG)
- OCSE (fisco e spesa)

Ogni funzione ritorna DataFrame/Series già nel formato atteso dalla pipeline grafica.
"""

import re
from urllib.parse import urlencode

import pandas as pd

from bilancio_pubblico.utils import (
    BAND_ORDER,
    COFOG_LABELS,
    EUROSTAT_BASE_URL,
    fetch_json,
    load_oecd_csv,
    load_semicolon_csv,
    MEF_DICHIARAZIONI_BASE,
    MEF_ENTRATE_URL,
    MEF_TERRITORIALI_URL,
    OECD_AREA_LABELS,
    OECD_COFOG_BASE_URL,
    OECD_GDP_BASE_URL,
    OECD_MEMBER_AREAS,
    OECD_REVENUE_BASE_URL,
    OECD_REVENUE_CATEGORIES,
    OECD_SPENDING_CATEGORIES,
    PEER_GEOS,
    TAXAG_LABELS,
)


def parse_mef_start(token):
    # Converte `26-1` nel primo giorno di quel mese, es. "2026-01-01".
    year_text, month_text = token.split("-")
    year = 2000 + int(year_text)
    month = int(month_text)
    return f"{year}-{month:02d}-01"


def collect_mef_items(node, items):
    # Esplora ricorsivamente la struttura JSON MEF e raccoglie solo nodi con label + mesi.
    if isinstance(node, dict):
        label = node.get("lbl")
        months = node.get("mesi")
        if label and isinstance(months, list):
            items.append({"label": label, "months": months})
        for value in node.values():
            if isinstance(value, (dict, list)):
                collect_mef_items(value, items)
    elif isinstance(node, list):
        for value in node:
            collect_mef_items(value, items)


def find_mef_item(items, exact=None, starts=None, contains=None):
    # Trova un nodo MEF secondo priorità: match esatto, prefisso, contenuto.
    for item in items:
        label = item["label"]
        if exact is not None and label == exact:
            return item
        if starts is not None and label.startswith(starts):
            return item
        if contains is not None and contains in label:
            return item
    raise ValueError(f"Voce MEF non trovata: {exact or starts or contains}")


def mef_monthly_series(item, months):
    # Crea una Serie mensile con indice temporale dal nodo MEF.
    values = pd.to_numeric(pd.Series(item["months"]), errors="coerce")
    return pd.Series(values.to_numpy(), index=months, name=item["label"])


def mef_annual_series(item, months):
    # Converte mensile in annuale usando solo anni completi e scala in miliardi.
    series = mef_monthly_series(item, months)
    frame = series.to_frame("value")
    frame["year"] = frame.index.year
    annual = frame.groupby("year")["value"].sum()
    counts = frame.groupby("year")["value"].count()
    annual = annual[counts == 12] / 1000.0
    return annual


def eurostat_url(dataset, params):
    # Costruisce in modo deterministico l'endpoint Eurostat completo.
    query = urlencode(params, doseq=True)
    return f"{EUROSTAT_BASE_URL}{dataset}?{query}"


def eurostat_series(dataset, params, cache_name, refresh):
    # Scarica una serie dal dataset Eurostat e la riconverte in pd.Series indicizzata.
    data = fetch_json(eurostat_url(dataset, params), cache_name, refresh)
    time_index = data["dimension"]["time"]["category"]["index"]
    time_by_position = {position: int(label) for label, position in time_index.items()}
    records = []
    for position_text, value in data.get("value", {}).items():
        position = int(position_text)
        if position in time_by_position:
            records.append((time_by_position[position], float(value)))
    series = pd.Series(dict(records)).sort_index()
    return series, data.get("updated")


def clean_oecd_frame(frame):
    # Pulisce i frame OCSE: coerziona numeri e rimuove NaN.
    result = frame.copy()
    result["OBS_VALUE"] = pd.to_numeric(result["OBS_VALUE"], errors="coerce")
    result["TIME_PERIOD"] = pd.to_numeric(result["TIME_PERIOD"], errors="coerce")
    return result.dropna(subset=["OBS_VALUE", "TIME_PERIOD"])


def load_mef_entrate(refresh):
    # Carica dataset MEF entrate erariali e costruisce l'indice temporale completo.
    data = fetch_json(MEF_ENTRATE_URL, "mef_entrate_erariali.json", refresh)
    items = []
    collect_mef_items(data, items)
    total_months = len(find_mef_item(items, exact="Totale entrate")["months"])
    months = pd.date_range(parse_mef_start(data["minData"]), periods=total_months, freq="MS")
    return data, items, months


def load_mef_territoriali(refresh):
    # Carica entrate territoriali (IRAP incluse nel dataset dedicato).
    data = fetch_json(MEF_TERRITORIALI_URL, "mef_entrate_territoriali.json", refresh)
    items = []
    collect_mef_items(data, items)
    total_months = len(find_mef_item(items, exact="Totale entrate territoriali")["months"])
    months = pd.date_range(parse_mef_start(data["minData"]), periods=total_months, freq="MS")
    return data, items, months


def load_tax_pressure(refresh):
    # Serie annuali Italia della pressione fiscale aggregata da componenti EUROSTAT.
    frame = pd.DataFrame()
    updated = None
    for item_code, label in TAXAG_LABELS.items():
        params = {
            "format": "JSON",
            "lang": "en",
            "freq": "A",
            "unit": "PC_GDP",
            "sector": "S13",
            "na_item": item_code,
            "geo": "IT",
        }
        cache_name = f"eurostat_gov_10a_taxag_{item_code}_pc_gdp.json"
        series, item_updated = eurostat_series("gov_10a_taxag", params, cache_name, refresh)
        frame[label] = series
        updated = item_updated or updated
    return frame.dropna(), updated


def load_cofog_spending(refresh):
    # Spesa pubblica italiana per funzione COFOG: valore assoluto e % PIL.
    records = []
    updated = None
    for code, label in COFOG_LABELS.items():
        params_mio = {
            "format": "JSON",
            "lang": "en",
            "freq": "A",
            "unit": "MIO_EUR",
            "sector": "S13",
            "cofog99": code,
            "na_item": "TE",
            "geo": "IT",
        }
        params_gdp = {
            **params_mio,
            "unit": "PC_GDP",
        }
        series_mio, item_updated = eurostat_series(
            "gov_10a_exp",
            params_mio,
            f"eurostat_gov_10a_exp_{code}_mio_eur.json",
            refresh,
        )
        series_gdp, updated_gdp = eurostat_series(
            "gov_10a_exp",
            params_gdp,
            f"eurostat_gov_10a_exp_{code}_pc_gdp.json",
            refresh,
        )
        year = int(series_mio.dropna().index.max())
        records.append(
            {
                "codice": code,
                "funzione": label,
                "anno": year,
                "mld": float(series_mio.loc[year]) / 1000.0,
                "pil": float(series_gdp.loc[year]),
            }
        )
        updated = item_updated or updated_gdp or updated
    return pd.DataFrame(records), updated


def load_peer_tax_pressure(refresh):
    # Confronto pressione fiscale e contributiva per Italia + peer geografici.
    records = []
    updated = None
    for geo, country in PEER_GEOS.items():
        components = []
        for item_code in TAXAG_LABELS:
            params = {
                "format": "JSON",
                "lang": "en",
                "freq": "A",
                "unit": "PC_GDP",
                "sector": "S13",
                "na_item": item_code,
                "geo": geo,
            }
            cache_name = f"eurostat_gov_10a_taxag_{geo}_{item_code}_pc_gdp.json"
            series, item_updated = eurostat_series("gov_10a_taxag", params, cache_name, refresh)
            components.append(series)
            updated = item_updated or updated
        total = pd.concat(components, axis=1).sum(axis=1)
        year = 2024
        records.append({"paese": country, "codice": geo, "anno": year, "valore": float(total.loc[year])})
    return pd.DataFrame(records), updated


def load_peer_spending(refresh, cofog_code, cache_suffix):
    # Confronto spesa % PIL per una specifica funzione COFOG.
    records = []
    updated = None
    for geo, country in PEER_GEOS.items():
        params = {
            "format": "JSON",
            "lang": "en",
            "freq": "A",
            "unit": "PC_GDP",
            "sector": "S13",
            "cofog99": cofog_code,
            "na_item": "TE",
            "geo": geo,
        }
        cache_name = f"eurostat_gov_10a_exp_{geo}_{cache_suffix}_pc_gdp.json"
        series, item_updated = eurostat_series("gov_10a_exp", params, cache_name, refresh)
        year = 2024
        records.append({"paese": country, "codice": geo, "anno": year, "valore": float(series.loc[year])})
        updated = item_updated or updated
    return pd.DataFrame(records), updated


def load_total_spending_italy(refresh):
    # Storico Italia: totale spesa in miliardi e % PIL per trend e contesto.
    params_mio = {
        "format": "JSON",
        "lang": "en",
        "freq": "A",
        "unit": "MIO_EUR",
        "sector": "S13",
        "cofog99": "TOTAL",
        "na_item": "TE",
        "geo": "IT",
    }
    params_gdp = {
        **params_mio,
        "unit": "PC_GDP",
    }
    series_mio, updated = eurostat_series(
        "gov_10a_exp",
        params_mio,
        "eurostat_gov_10a_exp_IT_total_mio_eur.json",
        refresh,
    )
    series_gdp, updated_gdp = eurostat_series(
        "gov_10a_exp",
        params_gdp,
        "eurostat_gov_10a_exp_IT_total_pc_gdp.json",
        refresh,
    )
    frame = pd.DataFrame({"mld": series_mio / 1000.0, "pil": series_gdp}).dropna()
    return frame, updated or updated_gdp


def income_lower_bound(label):
    # Normalizza stringhe etichetta reddito in un punto di taglio numerico minimo.
    if label.startswith("minore") or label.startswith("da -") or label == "zero":
        return -1
    if label.startswith("oltre"):
        return 300000
    numbers = re.findall(r"\d+(?:\.\d+)*", label)
    if not numbers:
        return -1
    return int(numbers[0].replace(".", ""))


def income_band(label):
    # Riclassifica la label in fasce per grafici leggibili.
    lower = income_lower_bound(label)
    if lower < 15000:
        return "0 - 15.000"
    if lower < 29000:
        return "15.001 - 29.000"
    if lower < 55000:
        return "29.001 - 55.000"
    if lower < 75000:
        return "55.001 - 75.000"
    return "oltre 75.000"


def numeric_column(frame, column):
    # Converte colonna numerica e sostituisce valori non validi con 0.
    return pd.to_numeric(frame[column], errors="coerce").fillna(0)


def add_income_bands(frame):
    # Aggiunge colonna `fascia` alla base dichiarazioni.
    result = frame.copy()
    result["fascia"] = result["Classi di reddito complessivo in euro"].map(income_band)
    return result


def aggregate_columns_by_band(frame, columns):
    # Raggruppa e somma importi per fasce di reddito, in ordine fisso.
    with_bands = add_income_bands(frame)
    for column in columns:
        with_bands[column] = numeric_column(with_bands, column)
    grouped = with_bands.groupby("fascia", sort=False)[columns].sum()
    return grouped.reindex(BAND_ORDER).fillna(0)


def load_declaration_data(refresh):
    # Scarica dataset dichiarazioni per distribuzione redditi, IRPEF e salari/capitale.
    tipo_url = f"{MEF_DICHIARAZIONI_BASE}cla_anno_tipo_reddito_2025.csv?d=1615465800"
    calcolo_url = f"{MEF_DICHIARAZIONI_BASE}cla_anno_calcolo_irpef_2025.csv?d=1615465800"
    tipo = load_semicolon_csv(tipo_url, "mef_dichiarazioni_tipo_reddito_2025.csv", refresh)
    calcolo = load_semicolon_csv(calcolo_url, "mef_dichiarazioni_calcolo_irpef_2025.csv", refresh)
    return tipo, calcolo


def load_oecd_revenue_category(code, refresh):
    # Scarica una categoria specifica del dataset Revenue Statistics OECD.
    safe_code = code.replace("_", "totale" if code == "_T" else "sott")
    key = f".TAX_REV.S13.{code}._T.PT_B1GQ.A"
    frame = load_oecd_csv(
        OECD_REVENUE_BASE_URL,
        key,
        f"oecd_revenue_{safe_code}_2024.csv",
        refresh,
    )
    frame = clean_oecd_frame(frame)
    frame = frame[frame["REF_AREA"].isin(OECD_MEMBER_AREAS)]
    return frame[["REF_AREA", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "valore"})


def load_oecd_revenue_data(refresh):
    # Costruisce riepilogo categorie revenue: valore Italia, media OCSE, frame peer.
    category_rows = []
    category_frames = {}
    for category in OECD_REVENUE_CATEGORIES:
        frame = load_oecd_revenue_category(category["codice"], refresh)
        mean_value = float(frame["valore"].mean())
        italy_value = float(frame.loc[frame["REF_AREA"] == "ITA", "valore"].iloc[0])
        category_rows.append(
            {
                "codice": category["codice"],
                "categoria": category["categoria"],
                "italia": italy_value,
                "ocse": mean_value,
                "differenza": italy_value - mean_value,
            }
        )
        peer_frame = frame.copy()
        peer_frame["paese"] = peer_frame["REF_AREA"].map(OECD_AREA_LABELS).fillna(peer_frame["REF_AREA"])
        peer_frame = pd.concat(
            [
                peer_frame,
                pd.DataFrame([{"REF_AREA": "OECD_AVG", "valore": mean_value, "paese": "Media OCSE"}]),
            ],
            ignore_index=True,
        )
        category_frames[category["codice"]] = peer_frame
    return pd.DataFrame(category_rows), category_frames


def load_oecd_spending_category(code, refresh):
    # Scarica una categoria COFOG dal dataset spesa OCSE (valore assoluto).
    key = f"A..S13._Z.D.OTE._Z.{code}.XDC.S.V.N.T1100"
    frame = load_oecd_csv(
        OECD_COFOG_BASE_URL,
        key,
        f"oecd_cofog_{code}_2024.csv",
        refresh,
    )
    frame = clean_oecd_frame(frame)
    frame = frame[frame["REF_AREA"].isin(OECD_MEMBER_AREAS)]
    return frame[["REF_AREA", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "spesa"})


def load_oecd_gdp(refresh):
    # Scarica PIL OCSE (usato per trasformare spesa assoluta in % PIL).
    key = "A..S1.S1.B1GQ._Z._Z._Z.XDC.V.N.T0101"
    frame = load_oecd_csv(
        OECD_GDP_BASE_URL,
        key,
        "oecd_gdp_current_2024.csv",
        refresh,
    )
    frame = clean_oecd_frame(frame)
    frame = frame[frame["REF_AREA"].isin(OECD_MEMBER_AREAS)]
    return frame[["REF_AREA", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "pil"})


def load_oecd_spending_data(refresh):
    # Costruisce confronto spesa OCSE con denominatore PIL e calcola media OCSE.
    gdp = load_oecd_gdp(refresh)
    category_rows = []
    category_frames = {}
    for category in OECD_SPENDING_CATEGORIES:
        spending = load_oecd_spending_category(category["codice"], refresh)
        frame = spending.merge(gdp, on="REF_AREA", how="inner")
        frame["valore"] = frame["spesa"] / frame["pil"] * 100.0
        mean_value = float(frame["valore"].mean())
        italy_value = float(frame.loc[frame["REF_AREA"] == "ITA", "valore"].iloc[0])
        category_rows.append(
            {
                "codice": category["codice"],
                "categoria": category["categoria"],
                "italia": italy_value,
                "ocse": mean_value,
                "differenza": italy_value - mean_value,
            }
        )
        peer_frame = frame[["REF_AREA", "valore"]].copy()
        peer_frame["paese"] = peer_frame["REF_AREA"].map(OECD_AREA_LABELS).fillna(peer_frame["REF_AREA"])
        peer_frame = pd.concat(
            [
                peer_frame,
                pd.DataFrame([{"REF_AREA": "OECD_AVG", "valore": mean_value, "paese": "Media OCSE"}]),
            ],
            ignore_index=True,
        )
        category_frames[category["codice"]] = peer_frame
    return pd.DataFrame(category_rows), category_frames
