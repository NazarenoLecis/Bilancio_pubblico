"""Arricchisce il payload OpenBDAP con denominatori regionali."""

from datetime import datetime, timezone
import json

import pandas as pd

from utils_bilancio.regioni.denominatori import (
    add_regional_denominators,
    denominator_records,
    load_regional_denominators,
)
from utils_bilancio.italia.aggiustamenti import SOURCE_EUROSTAT_HICP, load_spending_adjustments
from utils_bilancio.generali.costanti import SOURCE_DATA_JSON_PATH


NORMALIZED_REGIONAL_KEYS = [
    "spending_by_region",
    "spending_by_mission",
    "spending_by_title",
    "revenue_by_region",
    "revenue_by_title",
    "balances_by_region",
]

NORMALIZATION_OPTIONS = [
    {"id": "mld", "label": "Miliardi correnti", "field": "mld", "unit": "mld"},
    {"id": "mld_reale", "label": "Miliardi reali", "field": "mld_reale", "unit": "mld_reale"},
    {"id": "pil", "label": "% PIL regionale", "field": "pil", "unit": "% PIL"},
    {"id": "euro_per_capita", "label": "Euro pro capite", "field": "euro_per_capita", "unit": "euro"},
    {
        "id": "euro_reale_per_capita",
        "label": "Euro reali pro capite",
        "field": "euro_reale_per_capita",
        "unit": "euro_reale",
    },
    {"id": "euro_per_km2", "label": "Euro per kmq", "field": "euro_per_km2", "unit": "euro_km2"},
]


def real_base_year_from_adjustments(adjustments, years):
    hicp = adjustments.get("hicp") if isinstance(adjustments, dict) else None
    if hicp is None or hicp.empty:
        return None
    available_years = sorted(set(int(year) for year in hicp.index).intersection(int(year) for year in years))
    return available_years[-1] if available_years else None


def add_real_values(frame, adjustments):
    if frame is None or frame.empty or "mld" not in frame.columns or "anno" not in frame.columns:
        return frame
    hicp = adjustments.get("hicp") if isinstance(adjustments, dict) else None
    if hicp is None or hicp.empty:
        return frame

    result = frame.copy()
    base_year = real_base_year_from_adjustments(adjustments, result["anno"].dropna().astype(int).unique())
    base_index = hicp.get(base_year) if base_year is not None else None
    if base_index is None or pd.isna(base_index):
        return result

    def calculate_real_row(row):
        year = int(row["anno"])
        price_index = hicp.get(year)
        value = row.get("mld")
        if pd.isna(value) or price_index is None or pd.isna(price_index) or price_index <= 0:
            return row
        real_value = float(value) * float(base_index) / float(price_index)
        row["mld_reale"] = real_value
        row["real_base_year"] = int(base_year)
        if int(base_year) == 2024:
            row["mld_2024"] = real_value
        population = row.get("population")
        if pd.notna(population) and population:
            real_per_capita = real_value * 1_000_000_000.0 / float(population)
            row["euro_reale_per_capita"] = real_per_capita
            if int(base_year) == 2024:
                row["euro_2024_per_capita"] = real_per_capita
        return row

    return result.apply(calculate_real_row, axis=1)


def enrich_regional_budgets(regional_budgets, refresh=False, adjustments=None):
    denominators = load_regional_denominators(refresh)
    spending_adjustments = adjustments if adjustments is not None else load_spending_adjustments(refresh)
    regional_years = []
    for key in NORMALIZED_REGIONAL_KEYS:
        normalized = add_regional_denominators(regional_budgets.get(key), denominators)
        regional_budgets[key] = add_real_values(normalized, spending_adjustments)
        if hasattr(regional_budgets[key], "columns") and "anno" in regional_budgets[key].columns:
            regional_years.extend(
                int(year)
                for year in regional_budgets[key]["anno"].dropna().unique()
            )
    regional_budgets["regional_denominators"] = denominator_records(denominators)
    regional_budgets["denominator_sources"] = denominators.get("sources", [])
    regional_budgets["denominator_errors"] = denominators.get("errors", [])
    regional_budgets["denominator_updated"] = denominators.get("updated")
    regional_budgets["real_adjustment_sources"] = {
        "price_source": SOURCE_EUROSTAT_HICP,
        "real_base_year": real_base_year_from_adjustments(spending_adjustments, sorted(set(regional_years))),
        "updated": (spending_adjustments.get("updated", {}) or {}).get("hicp"),
        "errors": {
            key: value
            for key, value in (spending_adjustments.get("errors", {}) or {}).items()
            if value and key == "hicp"
        },
    }
    regional_budgets["normalization_options"] = NORMALIZATION_OPTIONS
    return regional_budgets


def append_regional_normalization_to_source_json(regional_budgets):
    if not SOURCE_DATA_JSON_PATH.exists():
        return

    payload = json.loads(SOURCE_DATA_JSON_PATH.read_text(encoding="utf-8"))
    regional_payload = payload.setdefault("regional_budgets", {})
    regional_payload["regional_denominators"] = regional_budgets.get("regional_denominators", [])
    regional_payload["denominator_sources"] = regional_budgets.get("denominator_sources", [])
    regional_payload["denominator_errors"] = regional_budgets.get("denominator_errors", [])
    regional_payload["denominator_updated"] = regional_budgets.get("denominator_updated")
    regional_payload["real_adjustment_sources"] = regional_budgets.get("real_adjustment_sources", {})
    regional_payload["normalization_options"] = regional_budgets.get("normalization_options", NORMALIZATION_OPTIONS)

    meta = payload.setdefault("meta", {})
    sources = meta.setdefault("sources", [])
    for source in regional_budgets.get("denominator_sources", []):
        if source not in sources:
            sources.append(source)
    if SOURCE_EUROSTAT_HICP not in sources:
        sources.append(SOURCE_EUROSTAT_HICP)

    method_notes = meta.setdefault("method_notes", [])
    for note in (
        "I confronti regionali OpenBDAP possono essere normalizzati per PIL regionale, popolazione o superficie territoriale.",
        "La sezione regionale OpenBDAP usa dati di rendiconto/consuntivo della gestione: sono risultati a posteriori diversi dai bilanci previsionali.",
        "I valori reali regionali sono deflazionati con HICP all-items Eurostat e riportati ai prezzi dell'ultimo anno comune disponibile.",
    ):
        if note not in method_notes:
            method_notes.append(note)

    meta.setdefault("source_updates", {})["regional_denominators"] = {
        "updated": regional_budgets.get("denominator_updated"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
