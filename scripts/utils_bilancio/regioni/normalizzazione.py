"""Arricchisce il payload OpenBDAP con denominatori regionali."""

from datetime import datetime, timezone
import json

from utils_bilancio.regioni.denominatori import (
    add_regional_denominators,
    denominator_records,
    load_regional_denominators,
)
from utils_bilancio.generali.costanti import SOURCE_DATA_JSON_PATH


NORMALIZED_REGIONAL_KEYS = [
    "spending_by_region",
    "spending_by_mission",
    "spending_by_mission_title",
    "spending_by_title",
    "revenue_by_region",
    "revenue_by_title",
    "revenue_by_tipology",
    "balances_by_region",
]

NORMALIZATION_OPTIONS = [
    {"id": "mld", "label": "Miliardi correnti", "field": "mld", "unit": "mld"},
    {"id": "pil", "label": "% PIL regionale", "field": "pil", "unit": "% PIL"},
    {"id": "euro_per_capita", "label": "Euro pro capite", "field": "euro_per_capita", "unit": "euro"},
    {"id": "euro_per_km2", "label": "Euro per kmq", "field": "euro_per_km2", "unit": "euro_km2"},
]


def enrich_regional_budgets(regional_budgets, refresh=False, adjustments=None):
    denominators = load_regional_denominators(refresh)
    for key in NORMALIZED_REGIONAL_KEYS:
        normalized = add_regional_denominators(regional_budgets.get(key), denominators)
        regional_budgets[key] = normalized
    regional_budgets["regional_denominators"] = denominator_records(denominators)
    regional_budgets["denominator_sources"] = denominators.get("sources", [])
    regional_budgets["denominator_errors"] = denominators.get("errors", [])
    regional_budgets["denominator_updated"] = denominators.get("updated")
    regional_budgets["real_adjustment_sources"] = {}
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

    method_notes = meta.setdefault("method_notes", [])
    for note in (
        "I confronti regionali OpenBDAP possono essere normalizzati per PIL regionale, popolazione o superficie territoriale.",
        "La sezione regionale OpenBDAP usa dati di rendiconto/consuntivo della gestione: sono risultati a posteriori diversi dai bilanci previsionali.",
    ):
        if note not in method_notes:
            method_notes.append(note)

    meta.setdefault("source_updates", {})["regional_denominators"] = {
        "updated": regional_budgets.get("denominator_updated"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
