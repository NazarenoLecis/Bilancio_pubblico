"""Costruisce e materializza l'export a sezioni sopra `source-data.json`.

Questo modulo non cambia la dashboard. Aggiunge al JSON generato dal repo una
lettura coerente con quattro blocchi analitici e, quando richiesto, scrive un
file JSON indipendente per ciascuna sezione.
"""

from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from bilancio_pubblico.section_schema import (
    REGIONAL_REVENUE_AGGREGATES,
    REGIONAL_SPENDING_AGGREGATES,
    SECTION_BY_ID,
    SECTION_SCHEMA,
    list_section_ids,
    normalize_section_ids,
    section_index,
)
from bilancio_pubblico.utils import SOURCE_DATA_JSON_PATH


SECTION_EXPORT_DIR = SOURCE_DATA_JSON_PATH.parent / "sections"
SECTION_MANIFEST_PATH = SECTION_EXPORT_DIR / "download-manifest.json"


def _path_or_default(path):
    if path is None:
        return SOURCE_DATA_JSON_PATH
    return Path(path)


def _round_number(value, digits=6):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    rounded = round(number, digits)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _as_rows(value):
    return value if isinstance(value, list) else []


def _safe_get(payload, key, fallback=None):
    value = payload.get(key)
    return value if value is not None else fallback


def _latest_year(rows, *keys):
    years = []
    for row in _as_rows(rows):
        if not isinstance(row, dict):
            continue
        for key in keys or ("year", "anno", "latest_year"):
            year = _round_number(row.get(key), 0)
            if year is not None:
                years.append(year)
                break
    return max(years) if years else None


def _source_meta(payload, *keys):
    source_updates = payload.get("meta", {}).get("source_updates", {})
    nested = source_updates.get("source", {}) if isinstance(source_updates, dict) else {}
    return {key: nested.get(key) for key in keys if isinstance(nested, dict) and key in nested}


def _aggregate_title_rows(rows, aggregate_specs, value_field="mld"):
    rows = _as_rows(rows)
    by_code = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("titolo_code") or "").zfill(2)
        if code:
            by_code[code].append(row)

    output = []
    for aggregate_order, spec in enumerate(aggregate_specs, start=1):
        grouped = {}
        for title_code in spec["title_codes"]:
            for row in by_code.get(title_code, []):
                region = row.get("regione")
                year = row.get("anno")
                if region is None or year is None:
                    continue
                key = (region, year)
                item = grouped.setdefault(
                    key,
                    {
                        "regione": region,
                        "anno": year,
                        "aggregate_id": spec["id"],
                        "aggregate_label": spec["label"],
                        "aggregate_order": aggregate_order,
                        "title_codes": list(spec["title_codes"]),
                        "unit": "mld",
                        "mld": 0.0,
                        "population": row.get("population"),
                        "population_year": row.get("population_year"),
                        "area_km2": row.get("area_km2"),
                    },
                )
                value = _round_number(row.get(value_field), 12)
                if value is not None:
                    item["mld"] += value
                for optional_key in ("comparto", "comparto_label"):
                    if optional_key in row and optional_key not in item:
                        item[optional_key] = row.get(optional_key)

        for item in grouped.values():
            item["mld"] = _round_number(item["mld"], 6)
            population = _round_number(item.get("population"), 6)
            area = _round_number(item.get("area_km2"), 6)
            if item["mld"] is not None and population:
                item["euro_per_capita"] = _round_number(item["mld"] * 1_000_000_000.0 / population, 6)
            if item["mld"] is not None and area:
                item["euro_per_km2"] = _round_number(item["mld"] * 1_000_000_000.0 / area, 6)
            if spec.get("note"):
                item["note"] = spec["note"]
            output.append(item)

    return sorted(output, key=lambda row: (row.get("anno") or 0, row.get("regione") or "", row.get("aggregate_order") or 0))


def _by_region_year_aggregate(rows, aggregate_id):
    index = {}
    for row in _as_rows(rows):
        if row.get("aggregate_id") != aggregate_id:
            continue
        index[(row.get("regione"), row.get("anno"))] = row
    return index


def _build_final_balance_rows(revenue_aggregates, spending_aggregates):
    revenue = _by_region_year_aggregate(revenue_aggregates, "entrate_finali")
    spending = _by_region_year_aggregate(spending_aggregates, "spese_finali")
    rows = []
    for key in sorted(set(revenue) & set(spending), key=lambda item: (item[1] or 0, item[0] or "")):
        revenue_row = revenue[key]
        spending_row = spending[key]
        revenue_mld = _round_number(revenue_row.get("mld"), 12)
        spending_mld = _round_number(spending_row.get("mld"), 12)
        balance_mld = None
        if revenue_mld is not None and spending_mld is not None:
            balance_mld = revenue_mld - spending_mld
        item = {
            "regione": key[0],
            "anno": key[1],
            "aggregate_id": "saldo_finale",
            "aggregate_label": "Saldo finale",
            "unit": "mld",
            "mld": _round_number(balance_mld, 6),
            "entrate_finali_mld": _round_number(revenue_mld, 6),
            "spese_finali_mld": _round_number(spending_mld, 6),
            "population": revenue_row.get("population") or spending_row.get("population"),
            "area_km2": revenue_row.get("area_km2") or spending_row.get("area_km2"),
            "note": "Entrate finali meno spese finali. Esclude debito, anticipazioni e partite di giro secondo i titoli disponibili.",
        }
        population = _round_number(item.get("population"), 6)
        area = _round_number(item.get("area_km2"), 6)
        if item["mld"] is not None and population:
            item["euro_per_capita"] = _round_number(item["mld"] * 1_000_000_000.0 / population, 6)
        if item["mld"] is not None and area:
            item["euro_per_km2"] = _round_number(item["mld"] * 1_000_000_000.0 / area, 6)
        rows.append(item)
    return rows


def _build_italia_section(payload):
    return {
        "id": "italia",
        "label": "Italia",
        "kpis": _safe_get(payload, "kpis", []),
        "revenue": {
            "top_taxes": _safe_get(payload, "top_taxes", []),
            "pressure_trend": _safe_get(payload, "tax_pressure_trend", []),
            "pressure_components": _safe_get(payload, "pressure_components", []),
            "direct_indirect": _safe_get(payload, "tax_revenue_by_type", []),
            "items": _safe_get(payload, "revenue_items", []),
            "all_lines": _safe_get(payload, "all_revenue_lines", []),
            "category_series": _safe_get(payload, "revenue_category_series", []),
            "pie": _safe_get(payload, "revenue_pie", []),
            "under_500m": _safe_get(payload, "under_500m_revenue_summary", {}),
            "known_gaps": _safe_get(payload, "known_revenue_gaps", []),
        },
        "spending": {
            "focus": _safe_get(payload, "spending_focus", []),
            "by_function": _safe_get(payload, "spending_by_function", []),
            "category_series": _safe_get(payload, "spending_category_series", []),
            "function_detail_series": _safe_get(payload, "spending_function_detail_series", []),
            "pie": _safe_get(payload, "spending_pie", []),
            "total_trend": _safe_get(payload, "total_spending_trend", []),
        },
        "distribution": {
            "declarations": _safe_get(payload, "declaration_summary", {}),
            "irpef_by_band": _safe_get(payload, "irpef_by_band", []),
            "irpef_share_by_band": _safe_get(payload, "irpef_share_by_band", []),
            "income_distribution_by_band": _safe_get(payload, "income_distribution_by_band", []),
            "household_wealth": _safe_get(payload, "household_wealth_distribution", {}),
            "succession_gift_tax": _safe_get(payload, "succession_gift_tax", {}),
        },
        "latest_years": {
            "tax_pressure": _latest_year(payload.get("tax_pressure_trend")),
            "spending": _latest_year(payload.get("total_spending_trend")),
            "revenue_items": _latest_year(payload.get("revenue_items")),
        },
        "source_updates": _source_meta(payload, "mef_entrate", "mef_territoriali", "eurostat_tax", "eurostat_exp", "total_spending"),
    }


def _build_europe_section(payload):
    return {
        "id": "confronto_europeo",
        "label": "Confronto europeo",
        "metrics": [
            {"id": "tax_pressure", "label": "Pressione fiscale e contributiva", "unit": "% PIL"},
            {"id": "public_spending", "label": "Spesa pubblica totale", "unit": "% PIL"},
            {"id": "social_spending", "label": "Spesa per protezione sociale", "unit": "% PIL"},
        ],
        "peer": _safe_get(payload, "peer", []),
        "peer_spending_function_options": _safe_get(payload, "peer_spending_function_options", []),
        "peer_spending_functions": _safe_get(payload, "peer_spending_functions", []),
        "latest_years": {
            "peer": _latest_year(payload.get("peer"), "tax_year", "spending_year", "social_year"),
            "cofog_functions": _latest_year(payload.get("peer_spending_functions")),
        },
        "source_updates": _source_meta(payload, "peer_tax", "peer_spending", "peer_social", "peer_spending_functions"),
    }


def _build_oecd_section(payload):
    oecd = _safe_get(payload, "oecd", {})
    return {
        "id": "confronto_ocse",
        "label": "Confronto OCSE",
        "available_views": [
            {"id": "revenue_categories", "label": "Entrate per categoria"},
            {"id": "spending_categories", "label": "Spesa per funzione"},
            {"id": "peer_revenue_total", "label": "Pressione fiscale totale"},
            {"id": "peer_spending_total", "label": "Spesa pubblica totale"},
            {"id": "peer_inheritance", "label": "Successioni e donazioni"},
        ],
        "data": oecd,
        "latest_years": {key: _latest_year(value) for key, value in oecd.items() if isinstance(value, list)},
        "source_updates": _source_meta(payload, "oecd_revenue", "oecd_spending"),
    }


def _build_regions_section(payload):
    regional = _safe_get(payload, "regional_budgets", {})
    revenue_aggregates = _aggregate_title_rows(regional.get("revenue_by_title"), REGIONAL_REVENUE_AGGREGATES)
    spending_aggregates = _aggregate_title_rows(regional.get("spending_by_title"), REGIONAL_SPENDING_AGGREGATES)
    final_balance = _build_final_balance_rows(revenue_aggregates, spending_aggregates)
    return {
        "id": "regioni",
        "label": "Regioni",
        "source": regional.get("source"),
        "updated": regional.get("updated"),
        "coverage": regional.get("coverage", []),
        "perimeters": regional.get("perimeters", []),
        "normalization_options": regional.get("normalization_options", []),
        "denominators": {
            "rows": regional.get("regional_denominators", []),
            "sources": regional.get("denominator_sources", []),
            "updated": regional.get("denominator_updated"),
            "errors": regional.get("denominator_errors", []),
        },
        "revenue": {
            "by_region": regional.get("revenue_by_region", []),
            "by_title": regional.get("revenue_by_title", []),
            "aggregates_by_region": revenue_aggregates,
            "aggregate_options": REGIONAL_REVENUE_AGGREGATES,
            "note": "La vista per aggregati regionali distingue entrate finali, correnti e voci non finali usando i titoli OpenBDAP disponibili.",
        },
        "spending": {
            "by_region": regional.get("spending_by_region", []),
            "by_mission": regional.get("spending_by_mission", []),
            "by_title": regional.get("spending_by_title", []),
            "aggregates_by_region": spending_aggregates,
            "aggregate_options": REGIONAL_SPENDING_AGGREGATES,
        },
        "balances": {
            "by_region": regional.get("balances_by_region", []),
            "final_by_region": final_balance,
            "detail": regional.get("balances_detail", []),
            "note": "Il saldo finale usa solo titoli finali. Il saldo totale storico resta nella chiave regional_budgets.balances_by_region.",
        },
        "latest_years": {
            "totals": _latest_year(regional.get("revenue_by_region"), "anno"),
            "titles": _latest_year(regional.get("revenue_by_title"), "anno"),
            "missions": _latest_year(regional.get("spending_by_mission"), "anno"),
        },
        "source_updates": _source_meta(payload, "regional_budgets", "regional_denominators"),
    }


def build_sections(payload):
    """Restituisce il blocco `sections` a partire dal payload legacy."""
    return {
        "italia": _build_italia_section(payload),
        "confronto_europeo": _build_europe_section(payload),
        "confronto_ocse": _build_oecd_section(payload),
        "regioni": _build_regions_section(payload),
    }


def _load_payload(path=None):
    output_path = _path_or_default(path)
    if not output_path.exists():
        return None, output_path
    return json.loads(output_path.read_text(encoding="utf-8")), output_path


def append_sectioned_export_to_source_json(path=None):
    """Aggiunge `section_index` e `sections` al JSON sorgente.

    La funzione e' idempotente. Se il file non esiste restituisce `None`.
    """
    payload, output_path = _load_payload(path)
    if payload is None:
        return None

    generated_at = datetime.now(timezone.utc).isoformat()
    payload["section_index"] = section_index()
    payload["sections"] = build_sections(payload)

    meta = payload.setdefault("meta", {})
    meta["section_schema"] = {
        "version": "2026-07-04",
        "generated_at": generated_at,
        "description": "Schema logico per sezioni: Italia, confronto europeo, confronto OCSE e regioni. Le chiavi legacy restano disponibili.",
    }
    method_notes = meta.setdefault("method_notes", [])
    notes = [
        "L'export a sezioni e' una vista logica aggiuntiva sopra le chiavi storiche del JSON; non cambia la dashboard esistente.",
        "Per le Regioni, le entrate finali sommano i titoli 1-5; le spese finali sommano i titoli 1-3. Debito, anticipazioni e partite di giro restano disponibili come voci separate.",
    ]
    for note in notes:
        if note not in method_notes:
            method_notes.append(note)

    counts = payload.setdefault("counts", {})
    counts["sections"] = len(SECTION_SCHEMA)
    counts["regional_revenue_aggregates"] = len(payload["sections"]["regioni"]["revenue"]["aggregates_by_region"])
    counts["regional_final_balances"] = len(payload["sections"]["regioni"]["balances"]["final_by_region"])

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)


def _section_file_payload(payload, section_id):
    section = SECTION_BY_ID[section_id]
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "Bilancio_pubblico",
            "source_json": str(SOURCE_DATA_JSON_PATH),
            "section_id": section_id,
            "section_label": section["label"],
            "scope": section["scope"],
            "description": section["description"],
            "primary_sources": section["primary_sources"],
            "legacy_keys": section["legacy_keys"],
            "notebook": section["notebook"],
        },
        "section": payload.get("sections", {}).get(section_id, {}),
    }


def write_section_files(path=None, sections=None, output_dir=None):
    """Scrive un JSON per ciascuna sezione selezionata."""
    payload, output_path = _load_payload(path)
    if payload is None:
        return []
    if "sections" not in payload:
        append_sectioned_export_to_source_json(output_path)
        payload, _output_path = _load_payload(output_path)

    selected = normalize_section_ids(sections)
    target_dir = Path(output_dir) if output_dir is not None else SECTION_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for section_id in selected:
        section_path = target_dir / f"{section_id}.json"
        section_path.write_text(
            json.dumps(_section_file_payload(payload, section_id), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(
            {
                "section_id": section_id,
                "label": SECTION_BY_ID[section_id]["label"],
                "path": str(section_path),
                "name": section_path.name,
                "role": "section_json",
                "notebook": SECTION_BY_ID[section_id]["notebook"],
            }
        )
    return written


def write_section_download_manifest(section_files=None, output_path=None):
    """Scrive il manifest di download delle sezioni."""
    if section_files is None:
        section_files = write_section_files(sections=list_section_ids())
    manifest_path = Path(output_path) if output_path is not None else SECTION_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_sections": len(section_files),
        "files": section_files,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(manifest_path)


def materialize_section_outputs(path=None, sections=None, output_dir=None):
    """Aggiorna il JSON sorgente, scrive i file di sezione e il manifest."""
    source_path = append_sectioned_export_to_source_json(path)
    section_files = write_section_files(path=path, sections=sections, output_dir=output_dir)
    manifest_path = write_section_download_manifest(section_files)
    return {
        "source_json": source_path,
        "section_files": section_files,
        "section_manifest": manifest_path,
    }
