"""Esporta tutti i dati calcolati dal pipeline in JSON per il sito."""

from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

from bilancio_pubblico.data_extraction import (
    aggregate_columns_by_band,
    find_mef_item,
    mef_annual_series,
)
from bilancio_pubblico.utils import (
    SOURCE_DATA_JSON_PATH,
    COFOG_DETAIL_LABELS,
    COFOG_LABELS,
    SOURCE_BANKITALIA_WEALTH,
    SOURCE_EUROSTAT_EXP,
    SOURCE_EUROSTAT_TAX,
    SUCCESSIONI_DONAZIONI_2025,
    SUCCESSIONI_DONAZIONI_SERIE,
    SOURCE_MEF_DICHIARAZIONI,
    SOURCE_MEF_ENTRATE_COMBINED,
    SOURCE_MEF_ENTRATE_WITH_APPENDICI,
    SOURCE_MEF_SUCCESSIONI,
    SOURCE_UPB_TARI,
)


IRPEF_TAX_LABEL = "Imposta netta - Ammontare in euro"
IRPEF_CONTRIBUTORS_LABEL = "Numero contribuenti"
TARI_GETTITO_2023_MLD = 10.5
SOCIAL_CONTRIBUTIONS_CODE = "CONTRIBUTI_SOCIALI_NETTI"
SOCIAL_CONTRIBUTIONS_LABEL = "Contributi sociali netti"


AGGREGATE_REVENUE_LABELS = {
    "Totale entrate",
    "Totale entrate territoriali",
    "Imposte dirette",
    "Imposte indirette",
}


def _slug_code(value):
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")[:80] or "VOCE"


def _to_number(value, digits=4):
    if value is None:
        return None
    if pd.isna(value):
        return None
    number = float(value)
    if pd.isna(number) or np.isinf(number):
        return None
    if number.is_integer():
        return int(number)
    return round(number, digits)


def _to_json_safe(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _records_from_frame(frame, include_index=False, index_name="year"):
    if frame is None or frame.empty:
        return []
    source = frame
    if include_index:
        source = frame.reset_index()
        if "index" in source.columns and index_name not in source.columns:
            source = source.rename(columns={"index": index_name})
    rows = []
    for row in source.to_dict(orient="records"):
        clean_row = {}
        for key, value in row.items():
            if isinstance(value, (int, float)):
                clean_row[key] = _to_number(value, 6)
            elif pd.isna(value):
                clean_row[key] = None
            else:
                clean_row[key] = _to_json_safe(value)
        rows.append(clean_row)
    return rows


def _safe_mef_value(items, months, selector):
    item = find_mef_item(items, **selector)
    annual = mef_annual_series(item, months)
    year = annual.last_valid_index()
    if year is None:
        return None, None
    return _to_number(year), _to_number(annual.loc[year], 4)


def _safe_last(value):
    if value is None or pd.isna(value):
        return None
    return value


def _to_payload_item(code, label, year, value, source, unit, status=None, note=None):
    payload = {
        "code": code,
        "label": label,
        "source": source,
        "year": year,
        "unit": unit,
    }
    if value is not None:
        payload["value"] = value
    if status is not None:
        payload["status"] = status
    if note is not None:
        payload["note"] = note
    return payload


def _revenue_group(label, source):
    lower = (label or "").lower()
    if "irpef" in lower:
        return "Redditi persone fisiche"
    if "ires" in lower or "irap" in lower:
        return "Imprese"
    if "iva" in lower or "accisa" in lower or "consumo" in lower or "tabacchi" in lower:
        return "Consumi e accise"
    if "bollo" in lower or "registro" in lower or "ipotec" in lower or "catastal" in lower or "concessioni" in lower:
        return "Atti, concessioni e patrimonio"
    if "sost" in lower or "rit." in lower or "ritenute" in lower:
        return "Sostitutive e ritenute"
    if source == "MEF territoriali":
        return "Tributi territoriali"
    return "Altre entrate"


def _is_revenue_line_candidate(label):
    if not label:
        return False
    clean = str(label).strip()
    if not clean:
        return False
    if clean.startswith("Fonte:"):
        return False
    if clean in AGGREGATE_REVENUE_LABELS:
        return False
    if clean.lower().startswith("di cui"):
        return False
    return True


def _all_revenue_lines_from_items(erariali_items, erariali_months, territoriali_items, territoriali_months):
    rows = []
    seen = set()
    for source, items, months in (
        ("MEF erariali", erariali_items, erariali_months),
        ("MEF territoriali", territoriali_items, territoriali_months),
    ):
        for item in items:
            label = item.get("label")
            if not _is_revenue_line_candidate(label):
                continue
            try:
                annual = mef_annual_series(item, months).dropna().sort_index()
            except Exception:
                continue
            if annual.empty:
                continue
            latest_year = int(annual.index.max())
            latest_value = _to_number(annual.loc[latest_year], 4)
            if latest_value is None or latest_value <= 0:
                continue
            key = (source, label)
            if key in seen:
                continue
            seen.add(key)
            code = _slug_code(f"{source}_{label}")
            rows.append(
                {
                    "code": code,
                    "label": label,
                    "group": _revenue_group(label, source),
                    "source": source,
                    "unit": "mld",
                    "latest_year": _to_number(latest_year),
                    "latest_value_mld": latest_value,
                    "series": [
                        {"year": _to_number(int(year)), "value_mld": _to_number(value, 4)}
                        for year, value in annual.items()
                    ],
                }
            )

    rows.append(
        {
            "code": "TARI_UPB_2023",
            "label": "TARI",
            "group": "Tributi comunali",
            "source": SOURCE_UPB_TARI,
            "unit": "mld",
            "latest_year": 2023,
            "latest_value_mld": TARI_GETTITO_2023_MLD,
            "series": [{"year": 2023, "value_mld": TARI_GETTITO_2023_MLD}],
            "note": "La TARI non compare come serie separata nella API mensile MEF usata per le entrate tributarie; il valore e' tratto dal focus UPB sulla tassa rifiuti.",
        }
    )

    return sorted(rows, key=lambda row: row["latest_value_mld"], reverse=True)


def _known_revenue_gaps():
    return [
        {
            "code": "PASSAPORTO",
            "label": "Tassa/contributo su passaporti",
            "status": "included_in_broader_item",
            "mapped_to": "Concessioni governative",
            "source": "MEF entrate erariali / normativa passaporto",
            "note": "La fonte MEF mensile disponibile non separa i passaporti: il gettito confluisce nella voce piu' ampia 'Concessioni governative'.",
        },
        {
            "code": "TASSA_ETICA",
            "label": "Tassa etica",
            "status": "not_separately_quantified",
            "source": "Agenzia delle Entrate, scadenzario e codici tributo",
            "note": "La fonte conferma l'obbligo di versamento, ma il gettito aggregato separato non e' disponibile nelle serie MEF usate.",
        },
        {
            "code": "ENTRATE_STRAORDINARIE",
            "label": "Entrate straordinarie",
            "status": "not_unique_category",
            "source": "MEF entrate tributarie",
            "note": "Non e' una voce univoca nella classificazione mensile MEF: alcune componenti possono comparire dentro sostitutive, sanatorie, rivalutazioni o altre entrate.",
        },
    ]


def _build_tax_items_detail(
    mef_items,
    mef_months,
    territoriali_items,
    territoriali_months,
    succession_payload,
):
    rows = []

    for code, label, source, selector in [
        ("IRPEF", "IRPEF", "MEF erariali", {"exact": "IRPEF"}),
        ("IVA", "IVA", "MEF erariali", {"exact": "IVA"}),
        ("IRES", "IRES", "MEF erariali", {"exact": "IRES"}),
    ]:
        try:
            year, value = _safe_mef_value(mef_items, mef_months, selector)
            status = None if value is not None else "not_available_in_current_payload"
            rows.append(
                _to_payload_item(
                    code,
                    label,
                    year,
                    value,
                    source,
                    "mld",
                    status=status,
                )
            )
        except Exception:
            rows.append(
                _to_payload_item(
                    code,
                    label,
                    None,
                    None,
                    source,
                    "mld",
                    status="not_available_in_current_payload",
                )
            )

    try:
        imu_year, imu_value = _safe_mef_value(territoriali_items, territoriali_months, {"exact": "Imu - Imis (Quota Comuni)"})
        rows.append(
            _to_payload_item(
                "IMU",
                "IMU (quota Comuni)",
                imu_year,
                imu_value,
                "MEF territoriali",
                "mld",
                status=None if imu_value is not None else "not_available_in_current_payload",
            )
        )
    except Exception:
        rows.append(
            _to_payload_item(
                "IMU",
                "IMU (quota Comuni)",
                None,
                None,
                "MEF territoriali",
                "mld",
                status="not_available_in_current_payload",
            )
        )

    rows.append(
        _to_payload_item(
            "TARI",
            "TARI",
            2023,
            TARI_GETTITO_2023_MLD,
            SOURCE_UPB_TARI,
            "mld",
            note="La TARI non compare come serie separata nella API mensile MEF usata per le entrate tributarie; il valore e' tratto dal focus UPB sulla tassa rifiuti.",
        )
    )

    rows.append(
        _to_payload_item(
            "CEDOLARE",
            "Cedolare secca",
            None,
            None,
            "MEF dichiarazioni",
            "mld",
            status="not_available_in_payload",
            note="Il dataset dichiarazioni usa il campo 'Reddito complessivo al netto della cedolare secca', ma non contiene la misura aggregata dell'incasso effettivo.",
        )
    )

    succession_value = succession_payload.get("last_value_million_euro")
    succession_year = succession_payload.get("last_year")
    if succession_value is not None:
        rows.append(
            _to_payload_item(
                "DONAZIONI_EREDITA",
                "Successioni e donazioni",
                succession_year,
                _to_number(succession_value / 1000.0, 4),
                "MEF appendici dichiarazioni",
                "mld",
            )
        )
    else:
        rows.append(
            _to_payload_item(
                "DONAZIONI_EREDITA",
                "Successioni e donazioni",
                succession_year,
                None,
                "MEF appendici dichiarazioni",
                "mld",
                status="not_available_in_payload",
            )
        )

    rows = sorted(rows, key=lambda row: row["code"])
    return rows


def _build_spending_focus(cofog_spending, total_spending):
    focus = []
    if cofog_spending is None or cofog_spending.empty:
        return focus

    latest_year = int(cofog_spending["anno"].max())
    latest_cofog = cofog_spending[cofog_spending["anno"] == latest_year].set_index("codice")
    latest_total = None
    if total_spending is not None and not total_spending.empty and latest_year in total_spending.index:
        total_row = total_spending.loc[latest_year]
        latest_total = _safe_last(total_row.get("mld"))

    requested = [
        ("DIFESA", COFOG_LABELS["GF02"], "GF02", None, False),
        ("ISTRUZIONE", COFOG_LABELS["GF09"], "GF09", None, False),
        ("RICERCA", f"{COFOG_LABELS['GF04']} (approssimato)", "GF04", "proxy", True),
        ("INVESTIMENTI", "Investimenti", None, None, False),
        ("SALARI", "Spesa per personale pubblico", None, None, False),
        ("INTERESSI_PASSIVI", "Interessi passivi", None, None, False),
        ("INTERESSI_ATTIVI", "Interessi attivi", None, None, False),
    ]

    for code, label, cofog_code, _share_code, is_proxy in requested:
        if cofog_code is not None and cofog_code in latest_cofog.index:
            row = latest_cofog.loc[cofog_code]
            value_mld = _to_number(row["mld"], 4)
            value_pil = _to_number(row["pil"], 4)
            payload = _to_payload_item(
                code,
                label,
                latest_year,
                value_mld,
                "Eurostat gov_10a_exp",
                "mld",
            )
            payload["cofog_code"] = cofog_code
            payload["value_pil_percent"] = value_pil
            if latest_total:
                payload["share_spesa_totale"] = _to_number(value_mld / latest_total * 100.0 if latest_total else None, 4)
            if is_proxy:
                payload["status"] = "proxy_available"
                payload["note"] = "Codice COFOG non specifico; aggregato in Affari economici."
            focus.append(payload)
            continue

        status = "not_available_in_current_sources"
        note = None
        if code in {"INVESTIMENTI", "SALARI", "INTERESSI_PASSIVI", "INTERESSI_ATTIVI"}:
            note = "Richiesta non presente nei dataset COFOG/MEF usati dalla pipeline corrente."
        elif code == "RICERCA":
            note = "Ricerca non distinguibile in modo esplicito dal set COFOG corrente."
        focus.append(
            _to_payload_item(
                code,
                label,
                latest_year,
                None,
                "Eurostat gov_10a_exp",
                "mld",
                status=status,
                note=note,
            )
        )

    return focus


def _cofog_summary_with_share(cofog_spending, total_spending):
    if cofog_spending is None or cofog_spending.empty:
        return []

    latest_year = int(cofog_spending["anno"].max())
    latest = cofog_spending[cofog_spending["anno"] == latest_year].copy()
    total = None
    if total_spending is not None and not total_spending.empty and latest_year in total_spending.index:
        total = total_spending.loc[latest_year].get("mld")

    rows = []
    for _, row in latest.iterrows():
        mld = _to_number(row["mld"], 4)
        share = _to_number(mld / total * 100.0 if total else None, 4)
        item = {
            "code": row["codice"],
            "label": row["funzione"],
            "year": _to_number(row["anno"]),
            "value_mld": mld,
            "value_pil": _to_number(row["pil"], 4),
        }
        if share is not None:
            item["share_of_total"] = share
        rows.append(item)
    return sorted(rows, key=lambda item: item["value_mld"], reverse=True)


def _build_declaration_distributions(calcolo_irpef):
    by_band, share_by_band = _build_decl_bands(calcolo_irpef)
    total_contributors = 0
    total_tax_mld = 0
    for item in by_band:
        contributors = item.get("contributors")
        tax_mld = item.get("tax_mld")
        if isinstance(contributors, (int, float)):
            total_contributors += contributors
        if isinstance(tax_mld, (int, float)):
            total_tax_mld += tax_mld
    return {
        "year": 2024,
        "bands": by_band,
        "share_by_band": share_by_band,
        "totals": {
            "contributors": _safe_last(total_contributors),
            "tax_mld": _safe_last(total_tax_mld),
        },
        "taxpayers_focus": [
            {"band": item["band"], "contributors": item["contributors"]}
            for item in by_band
        ],
    }


def _main_taxes_rows(erariali_items, erariali_months, territoriali_items, territoriali_months):
    candidates = [
        ("IRPEF", erariali_items, erariali_months, {"exact": "IRPEF"}, "IRPEF"),
        ("IVA", erariali_items, erariali_months, {"exact": "IVA"}, "IVA"),
        ("IRES", erariali_items, erariali_months, {"exact": "IRES"}, "IRES"),
        ("IRAP", territoriali_items, territoriali_months, {"exact": "IRAP"}, "IRAP"),
        ("Accise energia", erariali_items, erariali_months, {"starts": "Accisa prodotti energetici"}, "ACCISA ENERGIA"),
        ("Imposte successioni capitale", erariali_items, erariali_months, {"starts": "Sost. redditi"}, "SUCCESSIONI CAPITALE"),
        ("Tabacchi", erariali_items, erariali_months, {"starts": "Imposta sul consumo dei tabacchi"}, "TABACCHI"),
        ("Bollo", erariali_items, erariali_months, {"exact": "Bollo"}, "BOLLO"),
        (
            "Plusvalenze",
            erariali_items,
            erariali_months,
            {"starts": "Sost. sui redditi da capitale"},
            "PLUSVALENZE",
        ),
        ("Registro", erariali_items, erariali_months, {"exact": "Registro"}, "REGISTRO"),
        ("Energia elettrica", erariali_items, erariali_months, {"starts": "Accisa sull'energia elettrica"}, "ENERGIA ELETTRICA"),
    ]

    rows = []
    for label, items, months, selector, code in candidates:
        try:
            item = find_mef_item(items, **selector)
            annual = mef_annual_series(item, months)
            year = annual.last_valid_index()
            rows.append({
                "code": code,
                "label": label,
                "year": _to_number(year),
                "value": _to_number(annual.loc[year], 4),
                "unit": "mld",
            })
        except Exception:
            continue

    rows = [row for row in rows if _safe_last(row["year"]) is not None and _safe_last(row["value"]) is not None]
    rows = sorted(rows, key=lambda item: item["value"], reverse=True)
    return rows[:10]


def _tax_pressure_trend(tax_pressure):
    if tax_pressure is None or tax_pressure.empty:
        return []
    total = tax_pressure.sum(axis=1).sort_index()
    return [
        {"year": _to_number(year), "value": _to_number(value, 3), **{
            col.lower(): _to_number(tax_pressure.loc[year, col], 4) for col in tax_pressure.columns
        }}
        for year, value in total.items()
    ]


def _gdp_mld_by_year(total_spending):
    if total_spending is None or total_spending.empty:
        return {}
    gdp = {}
    for year, row in total_spending.sort_index().iterrows():
        spending_mld = _to_number(row.get("value"), 6)
        if spending_mld is None:
            spending_mld = _to_number(row.get("mld"), 6)
        spending_pil = _to_number(row.get("value_pil_percent"), 6)
        if spending_pil is None:
            spending_pil = _to_number(row.get("value_pil"), 6)
        if spending_pil is None:
            spending_pil = _to_number(row.get("pil_percent"), 6)
        if spending_pil is None:
            spending_pil = _to_number(row.get("pil"), 6)
        if spending_mld and spending_pil:
            gdp[int(year)] = spending_mld / spending_pil * 100.0
    return gdp


def _build_social_contributions_item(tax_pressure, total_spending):
    if tax_pressure is None or tax_pressure.empty:
        return None
    column = next(
        (col for col in tax_pressure.columns if "contributi sociali" in str(col).lower()),
        None,
    )
    if column is None:
        return None
    gdp_by_year = _gdp_mld_by_year(total_spending)
    series = []
    for year, percent_pil in tax_pressure[column].dropna().sort_index().items():
        year_int = int(year)
        gdp_mld = gdp_by_year.get(year_int)
        value_mld = (float(percent_pil) * gdp_mld / 100.0) if gdp_mld else None
        row = {
            "year": _to_number(year_int),
            "percent_pil": _to_number(percent_pil, 4),
        }
        if value_mld is not None:
            row["value_mld"] = _to_number(value_mld, 4)
        series.append(row)
    valued = [row for row in series if row.get("value_mld") is not None]
    if not valued:
        return None
    latest = valued[-1]
    payload = {
        "code": SOCIAL_CONTRIBUTIONS_CODE,
        "label": SOCIAL_CONTRIBUTIONS_LABEL,
        "group": "Contributi sociali",
        "source": SOURCE_EUROSTAT_TAX,
        "unit": "mld",
        "year": latest.get("year"),
        "value": latest.get("value_mld"),
        "latest_year": latest.get("year"),
        "latest_value_mld": latest.get("value_mld"),
        "latest_percent_pil": latest.get("percent_pil"),
        "series": series,
        "note": (
            "Valori in miliardi stimati dalla quota dei contributi sociali netti sul PIL "
            "Eurostat e dal PIL implicito nelle serie Eurostat di spesa pubblica."
        ),
    }
    return payload


def _prepend_social_contributions(rows, social_contributions):
    if not social_contributions:
        return rows
    filtered = [
        row for row in rows
        if row.get("code") != SOCIAL_CONTRIBUTIONS_CODE
        and row.get("label") != SOCIAL_CONTRIBUTIONS_LABEL
    ]
    return sorted(
        [social_contributions, *filtered],
        key=lambda row: row.get("latest_value_mld") if row.get("latest_value_mld") is not None else row.get("value") or 0,
        reverse=True,
    )


def _peer_rows(peer_tax, peer_spending, peer_social):
    by_code = {}
    if peer_tax is not None and not peer_tax.empty:
        for _, row in peer_tax.iterrows():
            code = row.get("codice")
            if code is None:
                continue
            item = by_code.setdefault(code, {"code": str(code), "country": row.get("paese") or str(code)})
            item["tax_pressure"] = _to_number(row.get("valore"), 3)
            item["tax_year"] = _to_number(row.get("anno"))
    if peer_spending is not None and not peer_spending.empty:
        for _, row in peer_spending.iterrows():
            code = row.get("codice")
            if code is None:
                continue
            item = by_code.setdefault(code, {"code": str(code), "country": row.get("paese") or str(code)})
            item["public_spending"] = _to_number(row.get("valore"), 3)
            item["spending_year"] = _to_number(row.get("anno"))
    if peer_social is not None and not peer_social.empty:
        for _, row in peer_social.iterrows():
            code = row.get("codice")
            if code is None:
                continue
            item = by_code.setdefault(code, {"code": str(code), "country": row.get("paese") or str(code)})
            item["social_spending"] = _to_number(row.get("valore"), 3)
            item["social_year"] = _to_number(row.get("anno"))
    return list(by_code.values())


def _peer_spending_function_options(peer_spending_functions):
    if peer_spending_functions is None or peer_spending_functions.empty:
        return []
    columns = [
        "cofog_code",
        "cofog_label",
        "cofog_level",
        "parent_code",
        "parent_label",
    ]
    options = peer_spending_functions[columns].drop_duplicates().copy()
    options["cofog_level"] = pd.to_numeric(options["cofog_level"], errors="coerce")
    options = options.sort_values(["cofog_level", "parent_code", "cofog_code"], na_position="first")
    return [
        {
            "id": row["cofog_code"],
            "label": row["cofog_label"],
            "level": _to_number(row["cofog_level"]),
            "parent_code": _safe_last(row.get("parent_code")),
            "parent_label": _safe_last(row.get("parent_label")),
            "unit": "% PIL",
            "source": "Eurostat gov_10a_exp",
        }
        for _, row in options.iterrows()
    ]


def _peer_spending_function_rows(peer_spending_functions):
    if peer_spending_functions is None or peer_spending_functions.empty:
        return []
    rows = []
    selected = peer_spending_functions.sort_values(
        ["cofog_level", "parent_code", "cofog_code", "codice"],
        na_position="first",
    )
    for _, row in selected.iterrows():
        rows.append(
            {
                "code": row.get("codice"),
                "country": row.get("paese") or row.get("codice"),
                "year": _to_number(row.get("anno")),
                "value": _to_number(row.get("valore"), 4),
                "unit": "% PIL",
                "cofog_code": row.get("cofog_code"),
                "cofog_label": row.get("cofog_label") or COFOG_DETAIL_LABELS.get(row.get("cofog_code")) or COFOG_LABELS.get(row.get("cofog_code")),
                "cofog_level": _to_number(row.get("cofog_level")),
                "parent_code": _safe_last(row.get("parent_code")),
                "parent_label": _safe_last(row.get("parent_label")),
            }
        )
    return rows


def _safe_sum(*values):
    total = 0
    for value in values:
        if value is None:
            continue
        if pd.isna(value):
            continue
        total += float(value)
    return total


def _cofog_distribution(cofog_spending):
    if cofog_spending is None or cofog_spending.empty:
        return []
    latest_year = int(cofog_spending["anno"].max())
    selected = cofog_spending[cofog_spending["anno"] == latest_year].sort_values("mld", ascending=False)
    return [
        {
            "code": row["codice"],
            "country": row["funzione"],
            "year": _to_number(row["anno"]),
            "value_mld": _to_number(row["mld"], 4),
            "value_pil": _to_number(row["pil"], 4),
        }
        for _, row in selected.iterrows()
    ]


def _safe_annual_series_from_selectors(items, months, selectors):
    for selector in selectors:
        try:
            item = find_mef_item(items, **selector)
            return mef_annual_series(item, months)
        except Exception:
            continue
    return pd.Series(dtype=float)


def _build_revenue_category_series(erariali_items, erariali_months, territoriali_items, territoriali_months):
    candidates = [
        {
            "code": "IRPEF",
            "label": "IRPEF",
            "group": "Entrate tributarie",
            "selectors": [{"exact": "IRPEF"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
        {
            "code": "IVA",
            "label": "IVA",
            "group": "Entrate tributarie",
            "selectors": [{"exact": "IVA"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
        {
            "code": "IRES",
            "label": "IRES",
            "group": "Entrate tributarie",
            "selectors": [{"exact": "IRES"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
        {
            "code": "IRAP",
            "label": "IRAP",
            "group": "Imposte regionali e locali",
            "selectors": [{"exact": "IRAP"}, {"starts": "IRAP"}],
            "source": "MEF territoriali",
            "source_items": "territoriali",
        },
        {
            "code": "IMU",
            "label": "IMU (quota comuni)",
            "group": "Imposte immobiliari",
            "selectors": [{"exact": "Imu - Imis (Quota Comuni)"}, {"starts": "IMU"}, {"contains": "IMU"}],
            "source": "MEF territoriali",
            "source_items": "territoriali",
        },
        {
            "code": "TARI",
            "label": "TARI",
            "group": "Tributi locali",
            "selectors": [{"exact": "TARI"}, {"starts": "TARI"}, {"contains": "TARI"}],
            "source": "MEF territoriali",
            "source_items": "territoriali",
        },
        {
            "code": "SUCCESSIONI",
            "label": "Successioni e donazioni",
            "group": "Altri tributari",
            "selectors": [{"contains": "successioni"}, {"contains": "donazioni"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
        {
            "code": "SUPERBOLLO",
            "label": "Superbollo",
            "group": "Contributi specifici",
            "selectors": [{"contains": "Superbollo"}, {"contains": "superbollo"}, {"contains": "Bollo"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
        {
            "code": "CASSA_AZIONI",
            "label": "Imposte sul registro",
            "group": "Imposte indirette",
            "selectors": [{"exact": "Registro"}, {"starts": "Imposta di registro"}],
            "source": "MEF erariali",
            "source_items": "erariali",
        },
    ]

    rows = []
    for candidate in candidates:
        items = erariali_items if candidate["source_items"] == "erariali" else territoriali_items
        months = erariali_months if candidate["source_items"] == "erariali" else territoriali_months
        series = _safe_annual_series_from_selectors(items, months, candidate["selectors"])
        if series is None or series.empty:
            rows.append(
                {
                    "code": candidate["code"],
                    "label": candidate["label"],
                    "group": candidate["group"],
                    "source": candidate["source"],
                    "status": "not_available_in_payload",
                    "series": [],
                    "latest_year": None,
                    "latest_value_mld": None,
                    "unit": "mld",
                    "note": f"Voce '{candidate['label']}' non rintracciata in questo set di fonti.",
                }
            )
            continue

        valid = series.dropna().sort_index()
        if valid.empty:
            rows.append(
                {
                    "code": candidate["code"],
                    "label": candidate["label"],
                    "group": candidate["group"],
                    "source": candidate["source"],
                    "status": "not_available_in_payload",
                    "series": [],
                    "latest_year": None,
                    "latest_value_mld": None,
                    "unit": "mld",
                    "note": f"Voce '{candidate['label']}' presente solo con dati incompleti.",
                }
            )
            continue

        latest_year = int(valid.index.max())
        latest_value = _to_number(valid.loc[latest_year], 4)
        row = {
            "code": candidate["code"],
            "label": candidate["label"],
            "group": candidate["group"],
            "source": candidate["source"],
            "unit": "mld",
            "latest_year": _to_number(latest_year),
            "latest_value_mld": latest_value,
            "series": [
                {"year": _to_number(int(year)), "value_mld": _to_number(value, 4)}
                for year, value in valid.items()
            ],
        }
        if latest_value is not None:
            row["status"] = None
        else:
            row["status"] = "incomplete_data"
        rows.append(row)

    return sorted(rows, key=lambda row: row.get("latest_value_mld") if row.get("latest_value_mld") is not None else -1, reverse=True)


def _cofog_category_series(cofog_spending):
    if cofog_spending is None or cofog_spending.empty:
        return []

    grouped = cofog_spending.sort_values("anno").groupby("codice")
    payload = []
    for code, group in grouped:
        group = group.sort_values("anno")
        records = []
        for _, row in group.iterrows():
            value_mld = _to_number(row["mld"], 4)
            if value_mld is not None:
                records.append(
                    {
                        "year": _to_number(int(row["anno"])),
                        "value_mld": value_mld,
                        "value_pil": _to_number(row["pil"], 4),
                    }
                )
        last_row = group.iloc[-1]
        latest = {
            "code": code,
            "label": _safe_last(last_row["funzione"]) or code,
            "unit": "mld",
            "series": records,
            "latest_year": _to_number(int(last_row["anno"])),
            "latest_value_mld": _to_number(last_row["mld"], 4),
        }
        if records:
            payload.append(latest)
    payload = [item for item in payload if item["series"]]
    return sorted(payload, key=lambda item: item["latest_value_mld"] or 0, reverse=True)


def _cofog_detail_series(cofog_spending_detail):
    if cofog_spending_detail is None or cofog_spending_detail.empty:
        return []

    grouped = cofog_spending_detail.sort_values("anno").groupby("codice")
    payload = []
    for code, group in grouped:
        group = group.sort_values("anno")
        records = []
        for _, row in group.iterrows():
            value_mld = _to_number(row["mld"], 4)
            value_pil = _to_number(row["pil"], 4)
            if value_mld is not None or value_pil is not None:
                records.append(
                    {
                        "year": _to_number(int(row["anno"])),
                        "value_mld": value_mld,
                        "value_pil": value_pil,
                    }
                )
        last_row = group.iloc[-1]
        item = {
            "code": code,
            "label": _safe_last(last_row["funzione"]) or code,
            "parent_code": _safe_last(last_row["parent_code"]) or str(code)[:4],
            "parent_label": _safe_last(last_row["parent_function"]) or str(code)[:4],
            "unit": "mld",
            "series": records,
            "latest_year": _to_number(int(last_row["anno"])),
            "latest_value_mld": _to_number(last_row["mld"], 4),
            "latest_value_pil": _to_number(last_row["pil"], 4),
        }
        if records:
            payload.append(item)

    parent_totals = {}
    for item in payload:
        parent_key = (item["parent_code"], item["latest_year"])
        parent_totals[parent_key] = parent_totals.get(parent_key, 0) + (item.get("latest_value_mld") or 0)

    for item in payload:
        parent_total = parent_totals.get((item["parent_code"], item["latest_year"]))
        item["latest_share_parent_percent"] = (
            _to_number((item.get("latest_value_mld") or 0) / parent_total * 100.0, 4)
            if parent_total
            else None
        )

    return sorted(payload, key=lambda item: (item.get("parent_code") or "", -(item.get("latest_value_mld") or 0)))


def _build_pie_payload(rows, value_key, year_key="latest_year"):
    normalized = [row for row in rows if row and _safe_last(row.get(value_key)) is not None and _safe_last(row.get(year_key)) is not None]
    total = _safe_sum(*[row.get(value_key) for row in normalized])
    result = []
    for row in normalized:
        item_value = row.get(value_key)
        share = _to_number(item_value / total * 100.0 if total else None, 3)
        result.append(
            {
                "code": row.get("code"),
                "label": row.get("label"),
                "year": row.get(year_key),
                "value_mld": _to_number(item_value, 4),
                "share_percent": share,
            }
        )
    return sorted(result, key=lambda row: row["value_mld"], reverse=True)


def _safe_count(values):
    return sum(1 for value in values if value is not None and not pd.isna(value))


def _build_under_500m_revenue_summary(revenue_lines, total_revenue_year=None, threshold_mld=0.5):
    if not revenue_lines:
        return {
            "year": None,
            "threshold_mld": threshold_mld,
            "entries": [],
            "entries_count": 0,
            "under_500_total_mld": 0.0,
            "under_500_share_of_total_percent": None,
            "note": "Dati non disponibili per la classifica in dettaglio.",
        }

    candidates = []
    for row in revenue_lines:
        if not isinstance(row, dict):
            continue
        value = row.get("latest_value_mld")
        if value is None or pd.isna(value):
            continue
        if value < threshold_mld:
            candidates.append(
                {
                    "code": row.get("code"),
                    "label": row.get("label"),
                    "group": row.get("group"),
                    "source": row.get("source"),
                    "year": row.get("latest_year"),
                    "value_mld": _to_number(value, 4),
                }
            )

    candidates = sorted(candidates, key=lambda item: item["value_mld"], reverse=True)
    threshold_total = 0
    for row in candidates:
        if row["value_mld"] is not None:
            threshold_total += float(row["value_mld"])

    return {
        "year": max([row.get("year") for row in candidates], default=None),
        "threshold_mld": threshold_mld,
        "entries": candidates,
        "entries_count": _safe_count([row["value_mld"] for row in candidates]),
        "under_500_total_mld": _to_number(threshold_total, 4),
        "under_500_share_of_total_percent": _to_number(threshold_total / total_revenue_year * 100.0 if total_revenue_year else None, 4),
        "cumulative_effect": "sommato",
        "note": (
            f"Cumulato delle voci con valore < {threshold_mld} mld. "
            "Sono considerate le voci quantificate separatamente nelle fonti disponibili."
        ),
    }


def _build_wealth_payload():
    return {
        "source": SOURCE_BANKITALIA_WEALTH,
        "items": [
            {"group": "Top 10% famiglie", "share_percent": 60.6},
            {"group": "Resto 40%", "share_percent": 32.2},
            {"group": "Meta' meno abbiente", "share_percent": 7.2},
        ],
        "average_wealth_euro": 453_000,
        "gini": 72.2,
    }


def _build_succession_payload(total_erariali):
    try:
        total = float(total_erariali) if total_erariali is not None and not pd.isna(total_erariali) else None
        share = SUCCESSIONI_DONAZIONI_2025 / total * 100.0 if total else None
    except Exception:
        share = None

    rows = []
    for row in SUCCESSIONI_DONAZIONI_SERIE:
        rows.append(
            {
                "year": _to_number(row["anno"]),
                "value_million_euro": _to_number(row["milioni"], 4),
            }
        )
    return {
        "source": SOURCE_MEF_SUCCESSIONI,
        "series": rows,
        "last_year": rows[-1]["year"] if rows else None,
        "last_value_million_euro": rows[-1]["value_million_euro"] if rows else None,
        "share_of_2025_revenue_percent": _to_number(share, 4),
    }


def _revenue_mix_2025(mef_items, mef_months, territoriali_items, territoriali_months):
    def _safe_mld(items, months, selector):
        selected = find_mef_item(items, **selector)
        annual = mef_annual_series(selected, months)
        year = annual.last_valid_index()
        return _to_number(annual.loc[year], 4) if year is not None else None

    rows = [
        {
            "code": "REDDITI_PERSONE",
            "label": "Redditi persone",
            "value_mld": _safe_sum(
                _safe_mld(mef_items, mef_months, {"exact": "IRPEF"}),
                _safe_mld(territoriali_items, territoriali_months, {"starts": "Addizionale regionale IRPEF"}),
                _safe_mld(territoriali_items, territoriali_months, {"starts": "Addizionale comunale IRPEF"}),
            ),
        },
        {
            "code": "CONSUMI",
            "label": "Consumi",
            "value_mld": _safe_sum(
                _safe_mld(mef_items, mef_months, {"exact": "IVA"}),
                _safe_mld(mef_items, mef_months, {"starts": "Accisa sui prodotti energetici"}),
                _safe_mld(mef_items, mef_months, {"starts": "Accisa sul gas naturale"}),
                _safe_mld(mef_items, mef_months, {"starts": "Accisa sull'energia elettrica"}),
                _safe_mld(mef_items, mef_months, {"starts": "Imposta sul consumo dei tabacchi"}),
            ),
        },
        {
            "code": "IMPRESE",
            "label": "Imprese",
            "value_mld": _safe_sum(
                _safe_mld(mef_items, mef_months, {"exact": "IRES"}),
                _safe_mld(territoriali_items, territoriali_months, {"exact": "IRAP"}),
            ),
        },
    ]
    rows = [row for row in rows if _safe_last(row["value_mld"]) is not None]
    return sorted(rows, key=lambda item: item["value_mld"], reverse=True)


def _build_direct_indirect(erariali_items, erariali_months):
    try:
        direct = mef_annual_series(find_mef_item(erariali_items, exact="Imposte dirette"), erariali_months)
        indirect = mef_annual_series(find_mef_item(erariali_items, exact="Imposte indirette"), erariali_months)
        frame = pd.DataFrame({"Dirette": direct, "Indirette": indirect})
        return _records_from_frame(frame.loc[2002:2025], include_index=True, index_name="year")
    except Exception:
        return []


def _build_decl_bands(calcolo_irpef):
    columns = [IRPEF_CONTRIBUTORS_LABEL, IRPEF_TAX_LABEL]
    grouped = aggregate_columns_by_band(calcolo_irpef, columns)

    total_tax = grouped[IRPEF_TAX_LABEL].sum()
    total_contrib = grouped[IRPEF_CONTRIBUTORS_LABEL].sum()
    by_band = []
    shares = []
    for band, row in grouped.iterrows():
        tax = _to_number(row[IRPEF_TAX_LABEL], 4)
        contrib = _to_number(row[IRPEF_CONTRIBUTORS_LABEL], 4)
        by_band.append(
            {
                "band": band,
                "contributors": contrib,
                "tax_eur": _to_number(tax),
                "tax_mld": _to_number(tax / 1_000_000_000 if _safe_last(tax) else None, 4),
                "average_tax_per_contributor": _to_number(
                    (tax * 1_000_000_000 / contrib) if contrib else None,
                    2,
                ),
            }
        )
        shares.append(
            {
                "band": band,
                "tax_share": _to_number(tax / total_tax * 100.0 if total_tax else None, 3),
                "contributors_share": _to_number(contrib / total_contrib * 100.0 if total_contrib else None, 3),
            }
        )
    return by_band, shares


def _build_income_share(tipo_reddito):
    columns = [
        "Reddito da lavoro dipendente e assimilati - Ammontare in euro",
        "Plusvalenze di natura finanziaria - Ammontare in euro",
        "Reddito di capitale (sez. IA e IB) - Ammontare in euro",
    ]
    grouped = aggregate_columns_by_band(tipo_reddito, columns)
    rows = []
    for band, row in grouped.iterrows():
        rows.append(
            {
                "band": band,
                "work": _to_number(row["Reddito da lavoro dipendente e assimilati - Ammontare in euro"] / 1_000_000_000, 4),
                "capital_gain": _to_number(row["Plusvalenze di natura finanziaria - Ammontare in euro"] / 1_000_000_000, 4),
                "capital_income": _to_number(row["Reddito di capitale (sez. IA e IB) - Ammontare in euro"] / 1_000_000_000, 4),
                "total_mld": _to_number(
                    (
                        row["Reddito da lavoro dipendente e assimilati - Ammontare in euro"]
                        + row["Plusvalenze di natura finanziaria - Ammontare in euro"]
                        + row["Reddito di capitale (sez. IA e IB) - Ammontare in euro"]
                    )
                    / 1_000_000_000,
                    4,
                ),
            }
        )
    return rows


def _build_oecd_payload(oecd_revenue, oecd_revenue_peers, oecd_spending, oecd_spending_peers):
    return {
        "revenue_categories": _records_from_frame(oecd_revenue),
        "spending_categories": _records_from_frame(oecd_spending),
        "peer_revenue_total": _records_from_frame(oecd_revenue_peers.get("_T", pd.DataFrame())),
        "peer_spending_total": _records_from_frame(oecd_spending_peers.get("_T", pd.DataFrame())),
        "peer_inheritance": _records_from_frame(oecd_revenue_peers.get("T_4300", pd.DataFrame())),
    }


def export_bilancio_source_json(
    mef_data,
    mef_items,
    mef_months,
    territoriali_data,
    territoriali_items,
    territoriali_months,
    tax_pressure,
    cofog_spending,
    peer_tax,
    peer_spending,
    peer_social,
    total_spending,
    oecd_revenue,
    oecd_revenue_peers,
    oecd_spending,
    oecd_spending_peers,
    tipo_reddito,
    calcolo_irpef,
    cofog_spending_trend,
    cofog_spending_detail=None,
    peer_spending_functions=None,
    source_updates=None,
    manifest_rows=None,
):
    """Scrive source-data.json con tutti i dataset estratti dalla pipeline."""
    source_updates = source_updates or {}
    manifest_rows = manifest_rows or []

    latest_pressure = tax_pressure.sum(axis=1).dropna()
    latest_pressure_year = _to_number(latest_pressure.index.max()) if not latest_pressure.empty else None
    latest_pressure_value = _to_number(latest_pressure.iloc[-1], 3) if not latest_pressure.empty else None

    if total_spending is not None and not total_spending.empty:
        latest_spending_row = total_spending.iloc[-1]
        latest_spending_year = total_spending.index.max()
        latest_spending_pil = latest_spending_row.get("pil")
        latest_spending_mld = latest_spending_row.get("mld")
    else:
        latest_spending_row = None
        latest_spending_year = None
        latest_spending_pil = None
        latest_spending_mld = None

    pressure_rows = _tax_pressure_trend(tax_pressure)
    social_contributions = _build_social_contributions_item(tax_pressure, total_spending)
    top_taxes = _prepend_social_contributions(
        _main_taxes_rows(mef_items, mef_months, territoriali_items, territoriali_months),
        social_contributions,
    )
    peer_rows = _peer_rows(peer_tax, peer_spending, peer_social)
    peer_spending_function_options = _peer_spending_function_options(peer_spending_functions)
    peer_spending_function_rows = _peer_spending_function_rows(peer_spending_functions)
    social_value = next((item.get("social_spending") for item in peer_rows if item.get("code") == "IT"), None)
    social_year = next((item.get("social_year") for item in peer_rows if item.get("code") == "IT"), None)
    irpef_by_band, irpef_share_by_band = _build_decl_bands(calcolo_irpef)
    income_by_band = _build_income_share(tipo_reddito)
    direct_indirect = _build_direct_indirect(mef_items, mef_months)
    revenue_mix = _revenue_mix_2025(mef_items, mef_months, territoriali_items, territoriali_months)
    try:
        total_erariali_2025 = mef_annual_series(find_mef_item(mef_items, exact="Totale entrate"), mef_months).loc[2025]
    except Exception:
        total_erariali_2025 = None
    succession_payload = _build_succession_payload(total_erariali_2025 if not pd.isna(total_erariali_2025) else None)
    revenue_tax_items = _build_tax_items_detail(
        mef_items,
        mef_months,
        territoriali_items,
        territoriali_months,
        succession_payload,
    )
    revenue_category_series = _build_revenue_category_series(
        mef_items,
        mef_months,
        territoriali_items,
        territoriali_months,
    )
    all_revenue_lines = _all_revenue_lines_from_items(
        mef_items,
        mef_months,
        territoriali_items,
        territoriali_months,
    )
    revenue_category_series = _prepend_social_contributions(revenue_category_series, social_contributions)
    all_revenue_lines = _prepend_social_contributions(all_revenue_lines, social_contributions)
    revenue_pie = _build_pie_payload(revenue_category_series, "latest_value_mld")
    spending_category_series = _cofog_category_series(cofog_spending_trend)
    spending_function_detail_series = _cofog_detail_series(cofog_spending_detail)
    spending_pie = _build_pie_payload(spending_category_series, "latest_value_mld")
    under_500m_revenue = _build_under_500m_revenue_summary(
        all_revenue_lines,
        total_revenue_year=_to_number(total_erariali_2025, 4),
    )
    spending_focus = _build_spending_focus(cofog_spending, total_spending)
    cofog_summary = _cofog_summary_with_share(cofog_spending, total_spending)
    declaration_summary = _build_declaration_distributions(calcolo_irpef)
    generated_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "meta": {
            "generated_at": generated_at,
            "generated_by": "Bilancio_pubblico",
            "updated_at": generated_at,
            "description": "Dati completi e normalizzati dal repo Bilancio_pubblico per la dashboard Bilancio pubblico italiano.",
            "sources": [
                SOURCE_MEF_ENTRATE_COMBINED,
                SOURCE_EUROSTAT_TAX,
                SOURCE_EUROSTAT_EXP,
                SOURCE_BANKITALIA_WEALTH,
                SOURCE_MEF_DICHIARAZIONI,
                SOURCE_MEF_ENTRATE_WITH_APPENDICI,
                SOURCE_MEF_SUCCESSIONI,
                SOURCE_UPB_TARI,
            ],
            "source_updates": {
                "mef_entrate": _safe_last(mef_data.get("aggiornamento")),
                "mef_territoriali": _safe_last(territoriali_data.get("aggiornamento")),
                "source": source_updates,
            },
            "method_notes": [
                "La pressione fiscale separa le imposte correnti sul reddito (Eurostat D51) dalle altre imposte correnti dell'aggregato D5 (Eurostat D59), riportate in dashboard come componente patrimonio.",
            ],
            "manifest_rows": len(manifest_rows),
            "manifest": manifest_rows,
        },
        "kpis": [
            {
                "id": "fiscal_pressure",
                "label": "Pressione fiscale e contributiva",
                "value": latest_pressure_value,
                "unit": "% PIL",
                "year": latest_pressure_year,
            },
            {
                "id": "public_spending",
                "label": "Spesa pubblica totale",
                "value": _to_number(latest_spending_pil, 3),
                "unit": "% PIL",
                "year": _to_number(latest_spending_year),
                "value_mld": _to_number(latest_spending_mld, 3),
                "unit_mld": "mld",
            },
            {
                "id": "social_spending",
                "label": "Spesa sociale",
                "value": social_value,
                "unit": "% PIL",
                "year": social_year,
            },
        ],
        "top_taxes": [row for row in top_taxes],
        "top_taxes_2025": [row for row in top_taxes],
        "main_taxes_2025": [row for row in top_taxes],
        "pressureTrend": pressure_rows,
        "tax_pressure_trend": pressure_rows,
        "pressure_trend": pressure_rows,
        "fiscal_trend": pressure_rows,
        "pressure_components": pressure_rows,
        "peer": peer_rows,
        "peer_spending_function_options": peer_spending_function_options,
        "peer_spending_functions": peer_spending_function_rows,
        "social_contributions": social_contributions,
        "revenue_items": revenue_tax_items,
        "all_revenue_lines": all_revenue_lines,
        "revenue_pie": revenue_pie,
        "revenue_category_series": revenue_category_series,
        "all_revenues_focus": revenue_tax_items,
        "under_500m_revenue_summary": under_500m_revenue,
        "known_revenue_gaps": _known_revenue_gaps(),
        "declaration_summary": declaration_summary,
        "cofog_spending_2024": _cofog_distribution(cofog_spending),
        "spending_by_function": cofog_summary,
        "spending_focus": spending_focus,
        "cofog_spending_trend": _records_from_frame(cofog_spending_trend),
        "cofog_spending_detail": _records_from_frame(cofog_spending_detail),
        "spending_category_series": spending_category_series,
        "spending_function_detail_series": spending_function_detail_series,
        "spending_pie": spending_pie,
        "total_spending_trend": _records_from_frame(total_spending),
        "tax_revenue_by_type": direct_indirect,
        "top_revenue_groups_2025": revenue_mix,
        "irpef_by_band": irpef_by_band,
        "irpef_share_by_band": irpef_share_by_band,
        "income_distribution_by_band": income_by_band,
        "household_wealth_distribution": _build_wealth_payload(),
        "succession_gift_tax": succession_payload,
        "oecd": _build_oecd_payload(oecd_revenue, oecd_revenue_peers, oecd_spending, oecd_spending_peers),
        "counts": {
            "revenue_items": len(revenue_tax_items),
            "all_revenue_lines": len(all_revenue_lines),
            "social_contributions": 1 if social_contributions else 0,
            "revenue_category_series": len(revenue_category_series),
            "revenue_under_500m_items": len(under_500m_revenue.get("entries", [])),
            "top_taxes": len(top_taxes),
            "pressure_points": len(pressure_rows),
            "peer_countries": len(peer_rows),
            "peer_spending_functions": len(peer_spending_function_rows),
            "peer_spending_function_options": len(peer_spending_function_options),
            "cofog_categories": len(cofog_spending) if cofog_spending is not None else 0,
            "cofog_categories_trend": len(spending_category_series),
            "cofog_detail_categories_trend": len(spending_function_detail_series),
            "spending_focus_items": len(spending_focus),
            "irpef_bands": len(irpef_by_band),
            "income_bands": len(income_by_band),
        },
    }

    output = SOURCE_DATA_JSON_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output)
