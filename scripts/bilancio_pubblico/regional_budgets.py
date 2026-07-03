"""Bilanci regionali da OpenBDAP/RGS.

Il modulo usa il catalogo CKAN di OpenBDAP per trovare risorse CSV legate ai
bilanci consuntivi regionali. L'obiettivo è rendere la sezione regionale
ripetibile senza fissare URL di download che possono cambiare nel catalogo.
"""

from datetime import datetime, timezone
from io import BytesIO, StringIO
import json
import re
import unicodedata
from urllib.parse import urlencode

import pandas as pd

from bilancio_pubblico.utils import DATA_DIR, SOURCE_DATA_JSON_PATH, fetch_bytes, fetch_json


OPENBDAP_ACTION_BASE_URL = "https://bdap-opendata.rgs.mef.gov.it/SpodCkanApi/api/3/action"
SOURCE_OPENBDAP_REGIONI = "Fonte: RGS - OpenBDAP, Bilanci degli enti della PA, dati di consuntivo"

REGIONAL_DATASET_CONFIG = {
    "spending": {
        "label": "Spese regionali",
        "queries": [
            "bilanci enti pa regioni spese consuntivo missione",
            "bilanci degli enti della pa regioni spese consuntivo",
            "regioni spese consuntivo missione",
        ],
        "required_terms": ["region", "spes", "consuntiv"],
        "category_keywords": [("MISSIONE",), ("DESCRIZIONE", "MISSIONE")],
        "value_keywords": [
            ("IMPEGNI",),
            ("PAGAMENTI",),
            ("IMPORTO",),
            ("VALORE",),
            ("AMMONTARE",),
        ],
    },
    "revenue": {
        "label": "Entrate regionali",
        "queries": [
            "bilanci enti pa regioni entrate consuntivo titolo",
            "bilanci degli enti della pa regioni entrate consuntivo",
            "regioni entrate consuntivo titolo categoria",
        ],
        "required_terms": ["region", "entrat", "consuntiv"],
        "category_keywords": [("TITOLO",), ("CATEGORIA",), ("TIPOLOGIA",)],
        "value_keywords": [
            ("ACCERTAMENTI",),
            ("RISCOSSIONI",),
            ("IMPORTO",),
            ("VALORE",),
            ("AMMONTARE",),
        ],
    },
    "balances": {
        "label": "Saldi regionali",
        "queries": [
            "bilanci enti pa regioni saldi consuntivo",
            "bilanci degli enti della pa regioni saldi",
            "regioni saldi consuntivo",
        ],
        "required_terms": ["region", "sald", "consuntiv"],
        "category_keywords": [("SALDO",), ("RISULTATO",), ("DESCRIZIONE",)],
        "value_keywords": [
            ("IMPORTO",),
            ("VALORE",),
            ("RISULTATO",),
            ("SALDO",),
            ("AMMONTARE",),
        ],
    },
}

REGION_ALIASES = {
    "ABRUZZO": "Abruzzo",
    "BASILICATA": "Basilicata",
    "CALABRIA": "Calabria",
    "CAMPANIA": "Campania",
    "EMILIA ROMAGNA": "Emilia-Romagna",
    "FRIULI VENEZIA GIULIA": "Friuli-Venezia Giulia",
    "LAZIO": "Lazio",
    "LIGURIA": "Liguria",
    "LOMBARDIA": "Lombardia",
    "MARCHE": "Marche",
    "MOLISE": "Molise",
    "PIEMONTE": "Piemonte",
    "PUGLIA": "Puglia",
    "SARDEGNA": "Sardegna",
    "SICILIA": "Sicilia",
    "TOSCANA": "Toscana",
    "TRENTINO ALTO ADIGE": "Trentino-Alto Adige",
    "UMBRIA": "Umbria",
    "VALLE D AOSTA": "Valle d'Aosta",
    "VALLE D AOSTA VALLEE D AOSTE": "Valle d'Aosta",
    "VENETO": "Veneto",
    "PROVINCIA AUTONOMA DI BOLZANO": "P.A. Bolzano",
    "PROVINCIA AUTONOMA BOLZANO": "P.A. Bolzano",
    "BOLZANO": "P.A. Bolzano",
    "PROVINCIA AUTONOMA DI TRENTO": "P.A. Trento",
    "PROVINCIA AUTONOMA TRENTO": "P.A. Trento",
    "TRENTO": "P.A. Trento",
}


def _normalise_text(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalise_column(value):
    text = _normalise_text(value)
    return re.sub(r"[^A-Z0-9]+", "_", text).strip("_")


def _slug(value):
    text = _normalise_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:80] or "openbdap"


def _openbdap_action_url(action, params):
    return f"{OPENBDAP_ACTION_BASE_URL}/{action}?{urlencode(params)}"


def _canonical_region(value):
    text = _normalise_text(value)
    if not text:
        return None
    if text in REGION_ALIASES:
        return REGION_ALIASES[text]
    for key, label in sorted(REGION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if key in text:
            return label
    return None


def _to_number(value):
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace("\xa0", "").replace(" ", "")
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.match(r"^-?\d{1,3}(\.\d{3})+$", text):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def _to_numeric_series(series):
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    return series.map(_to_number)


def _billions_from_values(values, value_column=None):
    series = pd.to_numeric(values, errors="coerce")
    valid = series.dropna().abs()
    if valid.empty:
        return series

    column = value_column or ""
    if any(token in column for token in ("MILIARDI", "MLD")):
        return series
    if any(token in column for token in ("MILIONI", "MLN")):
        return series / 1000.0
    if any(token in column for token in ("MIGLIAIA", "MGL", "MIG_EUR")):
        return series / 1_000_000.0

    median = valid.median()
    if median >= 1_000_000:
        return series / 1_000_000_000.0
    if median >= 1_000:
        return series / 1000.0
    return series


def _standardise_frame(frame):
    result = frame.copy()
    result = result.rename(columns={column: _normalise_column(column) for column in result.columns})
    result = result.loc[:, [column for column in result.columns if column]]
    return result


def _find_column(columns, keyword_groups):
    for keywords in keyword_groups:
        for column in columns:
            if all(keyword in column for keyword in keywords):
                return column
    return None


def _pick_year_column(frame):
    return _find_column(
        frame.columns,
        [
            ("ESERCIZIO",),
            ("ANNO",),
            ("PERIODO",),
            ("ESERC",),
        ],
    )


def _pick_region_column(frame):
    likely = [
        column
        for column in frame.columns
        if any(token in column for token in ("REGIONE", "AMMINISTRAZIONE", "ENTE", "DENOMINAZIONE"))
    ]
    if not likely:
        likely = list(frame.columns)

    scored = []
    for column in likely:
        matches = frame[column].map(_canonical_region).notna().sum()
        scored.append((matches, column))
    scored.sort(reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return None


def _pick_category_column(frame, keyword_groups):
    column = _find_column(frame.columns, keyword_groups)
    if column is not None:
        return column

    candidates = [
        item
        for item in frame.columns
        if item not in {"ANNO", "ESERCIZIO"}
        and not item.startswith("COD")
        and not pd.api.types.is_numeric_dtype(frame[item])
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: frame[item].astype(str).str.len().median())


def _pick_value_column(frame, keyword_groups):
    column = _find_column(frame.columns, keyword_groups)
    if column is not None:
        return column

    candidates = []
    for column in frame.columns:
        if any(token in column for token in ("COD", "ID", "ANNO", "ESERCIZIO")):
            continue
        series = _to_numeric_series(frame[column])
        valid_count = series.notna().sum()
        if valid_count < max(5, len(frame) * 0.1):
            continue
        median = series.abs().dropna().median()
        candidates.append((median, column))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _search_packages(query, refresh):
    cache_name = f"openbdap_package_search_{_slug(query)}.json"
    url = _openbdap_action_url("package_search", {"q": query, "rows": 20})
    data = fetch_json(url, cache_name, refresh)
    return data.get("result", {}).get("results", [])


def _package_score(package, required_terms):
    text = _normalise_text(
        " ".join(
            str(package.get(field, ""))
            for field in ("title", "name", "notes", "description")
        )
    ).lower()
    return sum(1 for term in required_terms if term in text)


def _find_packages(config, refresh):
    packages = {}
    for query in config["queries"]:
        for package in _search_packages(query, refresh):
            name = package.get("name") or package.get("id")
            if name:
                packages[name] = package
    return sorted(
        packages.values(),
        key=lambda package: _package_score(package, config["required_terms"]),
        reverse=True,
    )


def _resource_is_data_file(resource):
    text = _normalise_text(
        " ".join(
            str(resource.get(field, ""))
            for field in ("name", "description", "format", "url")
        )
    )
    if any(token in text for token in ("DIZIONARIO", "TRACCIATO", "METADATI", "METADATA")):
        return False
    return any(token in text for token in ("CSV", "TXT", "TSV", "XLS", "XLSX"))


def _pick_resource(package):
    resources = [item for item in package.get("resources", []) if _resource_is_data_file(item)]
    if not resources:
        return None

    def score(resource):
        text = _normalise_text(
            " ".join(
                str(resource.get(field, ""))
                for field in ("name", "description", "format", "url")
            )
        )
        points = 0
        if "CSV" in text:
            points += 5
        if "XLSX" in text or "XLS" in text:
            points += 2
        if "DOWNLOAD" in text or "SCARICA" in text:
            points += 1
        return points

    return sorted(resources, key=score, reverse=True)[0]


def _decode_bytes(raw):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="ignore")


def _read_delimited(raw):
    text = _decode_bytes(raw)
    best_frame = None
    best_columns = 0
    for sep in (";", "|", "\t", ","):
        try:
            frame = pd.read_csv(StringIO(text), sep=sep, low_memory=False)
        except Exception:
            continue
        if len(frame.columns) > best_columns:
            best_frame = frame
            best_columns = len(frame.columns)
    if best_frame is None:
        raise ValueError("Formato tabellare OpenBDAP non leggibile")
    return best_frame


def _read_resource(resource, dataset_key, refresh):
    url = resource.get("url")
    if not url:
        raise ValueError("Risorsa OpenBDAP senza URL di download")
    resource_id = resource.get("id") or resource.get("name") or url
    cache_name = f"openbdap_regioni_{dataset_key}_{_slug(resource_id)}"
    raw = fetch_bytes(url, cache_name, refresh)

    text = _normalise_text(f"{resource.get('format', '')} {url}")
    if "XLSX" in text or "XLS" in text:
        return pd.read_excel(BytesIO(raw))
    return _read_delimited(raw)


def _load_openbdap_dataset(dataset_key, config, refresh):
    packages = _find_packages(config, refresh)
    if not packages:
        return pd.DataFrame(), {
            "dataset": dataset_key,
            "label": config["label"],
            "status": "not_found",
            "message": "Nessun dataset OpenBDAP compatibile trovato tramite package_search.",
        }

    last_error = None
    for package in packages:
        resource = _pick_resource(package)
        if resource is None:
            continue
        try:
            frame = _read_resource(resource, dataset_key, refresh)
            return frame, {
                "dataset": dataset_key,
                "label": config["label"],
                "status": "loaded",
                "package_name": package.get("name"),
                "package_title": package.get("title"),
                "package_modified": package.get("metadata_modified") or package.get("revision_timestamp"),
                "resource_id": resource.get("id"),
                "resource_name": resource.get("name"),
                "resource_format": resource.get("format"),
                "rows": int(len(frame)),
            }
        except Exception as exc:
            last_error = str(exc)

    return pd.DataFrame(), {
        "dataset": dataset_key,
        "label": config["label"],
        "status": "error",
        "message": last_error or "Nessuna risorsa dati leggibile trovata.",
    }


def _clean_label(value):
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:120]


def _prepare_region_totals(frame, config, measure):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["regione", "anno", "mld", "misura"])

    data = _standardise_frame(frame)
    region_col = _pick_region_column(data)
    year_col = _pick_year_column(data)
    value_col = _pick_value_column(data, config["value_keywords"])
    if region_col is None or year_col is None or value_col is None:
        return pd.DataFrame(columns=["regione", "anno", "mld", "misura"])

    result = pd.DataFrame(
        {
            "regione": data[region_col].map(_canonical_region),
            "anno": pd.to_numeric(data[year_col], errors="coerce"),
            "valore": _to_numeric_series(data[value_col]),
        }
    ).dropna(subset=["regione", "anno", "valore"])

    result["anno"] = result["anno"].astype(int)
    result["mld"] = _billions_from_values(result["valore"], value_col)
    result["misura"] = measure
    result = result.groupby(["regione", "anno", "misura"], as_index=False)["mld"].sum()
    return result.sort_values(["anno", "regione"]).reset_index(drop=True)


def _prepare_category_totals(frame, config, measure, category_name):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["regione", "anno", category_name, "mld", "misura"])

    data = _standardise_frame(frame)
    region_col = _pick_region_column(data)
    year_col = _pick_year_column(data)
    category_col = _pick_category_column(data, config["category_keywords"])
    value_col = _pick_value_column(data, config["value_keywords"])
    if region_col is None or year_col is None or category_col is None or value_col is None:
        return pd.DataFrame(columns=["regione", "anno", category_name, "mld", "misura"])

    result = pd.DataFrame(
        {
            "regione": data[region_col].map(_canonical_region),
            "anno": pd.to_numeric(data[year_col], errors="coerce"),
            category_name: data[category_col].map(_clean_label),
            "valore": _to_numeric_series(data[value_col]),
        }
    ).dropna(subset=["regione", "anno", category_name, "valore"])

    result = result[result[category_name].astype(str).str.len() > 1]
    result["anno"] = result["anno"].astype(int)
    result["mld"] = _billions_from_values(result["valore"], value_col)
    result["misura"] = measure
    result = result.groupby(["regione", "anno", category_name, "misura"], as_index=False)["mld"].sum()
    return result.sort_values(["anno", "regione", category_name]).reset_index(drop=True)


def _records(frame):
    if frame is None or frame.empty:
        return []
    rows = []
    for row in frame.to_dict(orient="records"):
        clean = {}
        for key, value in row.items():
            if pd.isna(value):
                clean[key] = None
            elif isinstance(value, float):
                clean[key] = round(value, 6)
            elif hasattr(value, "item"):
                clean[key] = value.item()
            else:
                clean[key] = value
        rows.append(clean)
    return rows


def _latest_update(metas):
    dates = [
        meta.get("package_modified")
        for meta in metas
        if meta.get("package_modified")
    ]
    if dates:
        return max(dates)
    loaded = [meta.get("label") for meta in metas if meta.get("status") == "loaded"]
    if loaded:
        return "OpenBDAP/RGS, data di aggiornamento nel catalogo"
    return None


def load_regional_budgets(refresh=False):
    """Carica e normalizza la sezione sui bilanci regionali.

    La funzione non interrompe la pipeline principale se OpenBDAP cambia nome ai
    dataset o se una risorsa non è disponibile. Gli errori restano nel JSON finale.
    """
    raw_frames = {}
    metas = []
    errors = []

    for dataset_key, config in REGIONAL_DATASET_CONFIG.items():
        try:
            frame, meta = _load_openbdap_dataset(dataset_key, config, refresh)
        except Exception as exc:
            frame = pd.DataFrame()
            meta = {
                "dataset": dataset_key,
                "label": config["label"],
                "status": "error",
                "message": str(exc),
            }
        raw_frames[dataset_key] = frame
        metas.append(meta)
        if meta.get("status") != "loaded":
            errors.append(meta)

    spending = raw_frames.get("spending", pd.DataFrame())
    revenue = raw_frames.get("revenue", pd.DataFrame())
    balances = raw_frames.get("balances", pd.DataFrame())

    spending_config = REGIONAL_DATASET_CONFIG["spending"]
    revenue_config = REGIONAL_DATASET_CONFIG["revenue"]
    balances_config = REGIONAL_DATASET_CONFIG["balances"]

    return {
        "source": SOURCE_OPENBDAP_REGIONI,
        "updated": _latest_update(metas),
        "datasets": metas,
        "errors": errors,
        "spending_by_region": _prepare_region_totals(spending, spending_config, "spesa"),
        "spending_by_mission": _prepare_category_totals(spending, spending_config, "spesa", "missione"),
        "revenue_by_region": _prepare_region_totals(revenue, revenue_config, "entrate"),
        "revenue_by_title": _prepare_category_totals(revenue, revenue_config, "entrate", "titolo"),
        "balances_by_region": _prepare_region_totals(balances, balances_config, "saldo"),
        "balances_detail": _prepare_category_totals(balances, balances_config, "saldo", "voce"),
    }


def append_regional_budgets_to_source_json(regional_budgets, manifest_rows=None):
    """Aggiunge al JSON dashboard la nuova sezione `regional_budgets`."""
    if SOURCE_DATA_JSON_PATH.exists():
        payload = json.loads(SOURCE_DATA_JSON_PATH.read_text(encoding="utf-8"))
    else:
        SOURCE_DATA_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {}

    payload["regional_budgets"] = {
        "source": regional_budgets.get("source", SOURCE_OPENBDAP_REGIONI),
        "updated": regional_budgets.get("updated"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": regional_budgets.get("datasets", []),
        "errors": regional_budgets.get("errors", []),
        "spending_by_region": _records(regional_budgets.get("spending_by_region")),
        "spending_by_mission": _records(regional_budgets.get("spending_by_mission")),
        "revenue_by_region": _records(regional_budgets.get("revenue_by_region")),
        "revenue_by_title": _records(regional_budgets.get("revenue_by_title")),
        "balances_by_region": _records(regional_budgets.get("balances_by_region")),
        "balances_detail": _records(regional_budgets.get("balances_detail")),
    }

    if manifest_rows is not None:
        payload["manifest"] = manifest_rows

    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
