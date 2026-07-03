"""Indicatori derivati per le serie di spesa.

Aggiunge alle serie COFOG le versioni in euro correnti, euro pro capite,
euro reali e euro reali pro capite. La trasformazione reale usa l'indice HICP
Eurostat all-items, ricalibrato all'ultimo anno comune disponibile.
"""

from datetime import datetime, timezone
import json

import pandas as pd

from bilancio_pubblico.data_extraction import eurostat_series
from bilancio_pubblico.utils import SOURCE_DATA_JSON_PATH, SOURCE_EUROSTAT_EXP


SOURCE_EUROSTAT_POPULATION = "Fonte: Eurostat demo_pjan, popolazione residente al 1 gennaio, totale"
SOURCE_EUROSTAT_HICP = "Fonte: Eurostat prc_hicp_aind, HICP all-items, indice annuale 2015=100"
SOURCE_SIOPE = "Fonte: SIOPE - Banca d'Italia/RGS, incassi e pagamenti degli enti pubblici"

SIOPE_REFERENCE = {
    "id": "siope",
    "label": "SIOPE",
    "source": SOURCE_SIOPE,
    "url": "https://www.siope.it/Siope/",
    "status": "reference_source_registered",
    "scope": "flussi di cassa: incassi, pagamenti, disponibilita' liquide, aggregati territoriali e download CSV",
    "note": (
        "SIOPE misura flussi di cassa degli enti pubblici. Non sostituisce la serie Eurostat COFOG, "
        "che resta la fonte armonizzata per la spesa pubblica per funzione. E' registrato come fonte "
        "per una futura sezione di confronto sui flussi di cassa degli enti territoriali."
    ),
}

SPENDING_METRIC_OPTIONS = [
    {
        "id": "mld",
        "label": "Miliardi correnti",
        "field": "mld",
        "unit": "mld",
        "axis_title": "Miliardi di euro correnti",
        "source": SOURCE_EUROSTAT_EXP,
    },
    {
        "id": "mld_2024",
        "label": "Miliardi reali",
        "field": "mld_2024",
        "unit": "mld_2024",
        "axis_title": "Miliardi di euro a prezzi 2024",
        "source": f"{SOURCE_EUROSTAT_EXP}; {SOURCE_EUROSTAT_HICP}",
    },
    {
        "id": "pil",
        "label": "% PIL",
        "field": "pil",
        "unit": "% PIL",
        "axis_title": "% del PIL",
        "source": SOURCE_EUROSTAT_EXP,
    },
    {
        "id": "euro_per_capita",
        "label": "Euro pro capite",
        "field": "euro_per_capita",
        "unit": "euro",
        "axis_title": "Euro correnti per abitante",
        "source": f"{SOURCE_EUROSTAT_EXP}; {SOURCE_EUROSTAT_POPULATION}",
    },
    {
        "id": "euro_2024_per_capita",
        "label": "Euro reali pro capite",
        "field": "euro_2024_per_capita",
        "unit": "euro_2024",
        "axis_title": "Euro 2024 per abitante",
        "source": f"{SOURCE_EUROSTAT_EXP}; {SOURCE_EUROSTAT_HICP}; {SOURCE_EUROSTAT_POPULATION}",
    },
]


def _empty_series():
    return pd.Series(dtype=float)


def _safe_eurostat_series(dataset, params, cache_name, refresh):
    try:
        series, updated = eurostat_series(dataset, params, cache_name, refresh)
        return series.dropna().sort_index(), updated, None
    except Exception as exc:
        return _empty_series(), None, str(exc)


def load_spending_adjustments(refresh=False):
    """Scarica popolazione e indice prezzi usati per pro capite e valori reali."""
    population, population_updated, population_error = _safe_eurostat_series(
        "demo_pjan",
        {
            "format": "JSON",
            "lang": "en",
            "freq": "A",
            "unit": "NR",
            "sex": "T",
            "age": "TOTAL",
            "geo": "IT",
        },
        "eurostat_demo_pjan_IT_total_population.json",
        refresh,
    )
    hicp, hicp_updated, hicp_error = _safe_eurostat_series(
        "prc_hicp_aind",
        {
            "format": "JSON",
            "lang": "en",
            "freq": "A",
            "unit": "I15",
            "coicop": "CP00",
            "geo": "IT",
        },
        "eurostat_prc_hicp_aind_IT_cp00_i15.json",
        refresh,
    )

    return {
        "population": population,
        "hicp": hicp,
        "updated": {
            "population": population_updated,
            "hicp": hicp_updated,
        },
        "errors": {
            "population": population_error,
            "hicp": hicp_error,
        },
    }


def _latest_common_price_year(hicp, years):
    if hicp is None or hicp.empty:
        return None
    available = sorted(set(int(year) for year in hicp.index).intersection(int(year) for year in years))
    return available[-1] if available else None


def _augment_row_values(row, population, hicp, base_year, base_price_index):
    year = int(row["anno"] if "anno" in row else row.name)
    mld = row.get("mld")
    if mld is None or pd.isna(mld):
        return row

    population_value = population.get(year) if population is not None and not population.empty else None
    price_index = hicp.get(year) if hicp is not None and not hicp.empty else None

    if population_value is not None and not pd.isna(population_value) and population_value > 0:
        row["population"] = float(population_value)
        row["euro_per_capita"] = float(mld) * 1_000_000_000.0 / float(population_value)

    if base_price_index is not None and price_index is not None and not pd.isna(price_index) and price_index > 0:
        real_mld = float(mld) * float(base_price_index) / float(price_index)
        row["mld_2024"] = real_mld
        row["real_base_year"] = int(base_year)
        if population_value is not None and not pd.isna(population_value) and population_value > 0:
            row["euro_2024_per_capita"] = real_mld * 1_000_000_000.0 / float(population_value)

    return row


def augment_spending_frame(frame, adjustments):
    """Aggiunge colonne derivate al frame COFOG per funzione."""
    if frame is None or frame.empty:
        return frame
    population = adjustments.get("population", _empty_series())
    hicp = adjustments.get("hicp", _empty_series())
    result = frame.copy()
    base_year = _latest_common_price_year(hicp, result["anno"].dropna().astype(int).unique())
    base_price_index = hicp.get(base_year) if base_year is not None else None
    return result.apply(
        lambda row: _augment_row_values(row, population, hicp, base_year, base_price_index),
        axis=1,
    )


def augment_total_spending_frame(frame, adjustments):
    """Aggiunge colonne derivate alla serie totale della spesa pubblica."""
    if frame is None or frame.empty:
        return frame
    source = frame.copy().reset_index().rename(columns={"index": "anno"})
    if "anno" not in source.columns:
        source = source.rename(columns={source.columns[0]: "anno"})
    augmented = augment_spending_frame(source, adjustments)
    return augmented.set_index("anno")


def _series_records(series):
    if series is None or series.empty:
        return []
    return [
        {"year": int(year), "value": round(float(value), 6)}
        for year, value in series.dropna().sort_index().items()
    ]


def _append_unique(items, value):
    if value not in items:
        items.append(value)


def append_spending_adjustments_to_source_json(adjustments):
    """Aggiunge metadati su pro capite, valori reali e fonte SIOPE al JSON."""
    if not SOURCE_DATA_JSON_PATH.exists():
        return

    payload = json.loads(SOURCE_DATA_JSON_PATH.read_text(encoding="utf-8"))
    meta = payload.setdefault("meta", {})
    sources = meta.setdefault("sources", [])
    for source in (SOURCE_EUROSTAT_POPULATION, SOURCE_EUROSTAT_HICP):
        _append_unique(sources, source)

    reference_sources = meta.setdefault("reference_sources", [])
    if not any(item.get("id") == SIOPE_REFERENCE["id"] for item in reference_sources if isinstance(item, dict)):
        reference_sources.append(SIOPE_REFERENCE)

    method_notes = meta.setdefault("method_notes", [])
    for note in (
        "Le serie di spesa in miliardi sono valori nominali in euro correnti se non diversamente indicato.",
        "Le serie reali sono deflazionate con HICP all-items Eurostat e riportate ai prezzi dell'ultimo anno comune disponibile.",
        "Le serie pro capite dividono gli importi per la popolazione residente Eurostat al 1 gennaio.",
        "SIOPE e' una fonte sui flussi di cassa degli enti pubblici; resta distinta dalla serie COFOG di contabilita' nazionale usata per la spesa per funzione.",
    ):
        _append_unique(method_notes, note)

    payload["spending_metric_options"] = SPENDING_METRIC_OPTIONS
    payload["siope_reference"] = SIOPE_REFERENCE
    payload["spending_adjustment_sources"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "population_source": SOURCE_EUROSTAT_POPULATION,
        "price_source": SOURCE_EUROSTAT_HICP,
        "population": _series_records(adjustments.get("population")),
        "hicp": _series_records(adjustments.get("hicp")),
        "updated": adjustments.get("updated", {}),
        "errors": {
            key: value
            for key, value in adjustments.get("errors", {}).items()
            if value
        },
    }

    source_updates = meta.setdefault("source_updates", {})
    source_updates["population_hicp"] = adjustments.get("updated", {})
    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
