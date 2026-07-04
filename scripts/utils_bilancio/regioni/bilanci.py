"""Bilanci regionali da OpenBDAP/RGS.

Il catalogo CKAN OpenBDAP non espone in modo stabile i dataset usati dalla
pagina "Finanza degli Enti Territoriali". Questa versione usa quindi gli
endpoint JSON pubblici della pagina FET, che sono gli stessi usati dai grafici
OpenBDAP su spese, entrate, missioni e titoli.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlencode

import pandas as pd

from utils_bilancio.generali.costanti import SOURCE_DATA_JSON_PATH
from utils_bilancio.generali.utils import fetch_json


OPENBDAP_FET_API_BASE_URL = "https://openbdap.rgs.mef.gov.it/api/api/fet"
SOURCE_OPENBDAP_REGIONI = (
    "Fonte: RGS - OpenBDAP, Finanza degli Enti Territoriali, "
    "dati di rendiconto della gestione"
)

DEFAULT_COMPARTMENT = "Regionieprovinceautonome"
FET_PHASE = "1"
FET_TOTAL_YEARS = list(range(2019, 2025))
FET_DETAIL_YEARS = list(FET_TOTAL_YEARS)
OPENBDAP_DETAIL_YEAR = 2024

COMPARTMENTS = {
    "Regionieprovinceautonome": "Regioni e province autonome",
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
}

EXPECTED_REGIONS = [
    "Abruzzo",
    "Basilicata",
    "Calabria",
    "Campania",
    "Emilia-Romagna",
    "Friuli-Venezia Giulia",
    "Lazio",
    "Liguria",
    "Lombardia",
    "Marche",
    "Molise",
    "Piemonte",
    "Puglia",
    "Sardegna",
    "Sicilia",
    "Toscana",
    "Trentino-Alto Adige",
    "Umbria",
    "Valle d'Aosta",
    "Veneto",
]

MISSION_LABELS = {
    "01": "Servizi istituzionali, generali e di gestione",
    "02": "Giustizia",
    "03": "Ordine pubblico e sicurezza",
    "04": "Istruzione e diritto allo studio",
    "05": "Tutela e valorizzazione dei beni e delle attivita culturali",
    "06": "Politiche giovanili, sport e tempo libero",
    "07": "Turismo",
    "08": "Assetto del territorio ed edilizia abitativa",
    "09": "Sviluppo sostenibile e tutela del territorio e dell'ambiente",
    "10": "Trasporti e diritto alla mobilita",
    "11": "Soccorso civile",
    "12": "Diritti sociali, politiche sociali e famiglia",
    "13": "Tutela della salute",
    "14": "Sviluppo economico e competitivita",
    "15": "Politiche per il lavoro e la formazione professionale",
    "16": "Agricoltura, politiche agroalimentari e pesca",
    "17": "Energia e diversificazione delle fonti energetiche",
    "18": "Relazioni con le altre autonomie territoriali e locali",
    "19": "Relazioni internazionali",
    "20": "Fondi e accantonamenti",
    "50": "Debito pubblico",
    "60": "Anticipazioni finanziarie",
}

SPENDING_TITLE_LABELS = {
    "01": "Spese correnti",
    "02": "Spese in conto capitale",
    "03": "Spese per incremento di attivita finanziarie",
    "04": "Rimborso di prestiti",
    "05": "Chiusura anticipazioni ricevute da istituto tesoriere/cassiere",
}

REVENUE_TITLE_LABELS = {
    "01": "Entrate correnti di natura tributaria, contributiva e perequativa",
    "02": "Trasferimenti correnti",
    "03": "Entrate extratributarie",
    "04": "Entrate in conto capitale",
    "05": "Entrate da riduzione di attivita finanziarie",
    "06": "Accensione prestiti",
    "07": "Anticipazioni da istituto tesoriere/cassiere",
    "09": "Entrate per conto terzi e partite di giro",
}

REVENUE_TIPOLOGY_LABELS = {
    "010101": "Imposte tasse e proventi assimilati",
    "010102": "Tributi destinati al finanziamento della sanita'",
    "010103": "Tributi devoluti e regolati alle autonomie speciali",
    "010104": "Compartecipazioni di tributi",
    "010301": "Fondi perequativi da Amministrazioni Centrali",
    "020101": "Trasferimenti correnti da Amministrazioni pubbliche",
    "020102": "Trasferimenti correnti da Famiglie",
    "020103": "Trasferimenti correnti da Imprese",
    "020104": "Trasferimenti correnti da Istituzioni Sociali Private",
    "020105": "Trasferimenti correnti dall'Unione Europea e dal Resto del Mondo",
    "030100": "Vendita di beni e servizi e proventi derivanti dalla gestione dei beni",
    "030200": "Proventi derivanti dall'attivita' di controllo e repressione delle irregolarita' e degli illeciti",
    "030300": "Interessi attivi",
    "030400": "Altre entrate da redditi da capitale",
    "030500": "Rimborsi e altre entrate correnti",
    "040100": "Tributi in conto capitale",
    "040200": "Contributi agli investimenti",
    "040300": "Altri trasferimenti in conto capitale",
    "040400": "Entrate da alienazione di beni materiali e immateriali",
    "040500": "Altre entrate in conto capitale",
    "050100": "Alienazione di attivita' finanziarie",
    "050200": "Riscossione di crediti di breve termine",
    "050300": "Riscossione crediti di medio-lungo termine",
    "050400": "Altre entrate per riduzione di attivita' finanziarie",
    "060300": "Accensione Mutui e altri finanziamenti a medio lungo termine",
    "060400": "Altre forme di indebitamento",
}


def normalise_text(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slug(value):
    text = normalise_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:120] or "openbdap_fet"


def canonical_region(value):
    text = normalise_text(value)
    if not text:
        return None
    if text in REGION_ALIASES:
        return REGION_ALIASES[text]
    for key, label in sorted(REGION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if key in text:
            return label
    return None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fet_url(endpoint, params):
    return f"{OPENBDAP_FET_API_BASE_URL}/{endpoint}?{urlencode(params)}"


def fetch_fet_data(endpoint, params, refresh):
    query = urlencode(sorted(params.items()))
    cache_hash = hashlib.sha1(query.encode("utf-8")).hexdigest()[:16]
    cache_name = f"openbdap_fet_{endpoint}_{cache_hash}.json"
    data = fetch_json(fet_url(endpoint, params), cache_name, refresh)
    if data is None:
        return []
    return data


def region_spec(year, compartment, entrate_spese, mission="00", title="00", tipologia="00", measure="spesa"):
    return {
        "endpoint": "data_FET_e2",
        "params": {
            "fase": FET_PHASE,
            "entrateSpese": entrate_spese,
            "territorio": "Italia",
            "comparto": compartment,
            "anno": str(year),
            "totale": "1",
            "codMissione": mission,
            "codTitolo": title,
            "codTipologia": tipologia,
        },
        "measure": measure,
    }


def rows_from_response(data, year, compartment, measure, extra=None):
    rows = []
    extra = extra or {}
    for item in data or []:
        region = canonical_region(item.get("region_name"))
        value = to_float(item.get("itamvalue"))
        if not region or value is None:
            continue
        rows.append(
            {
                "regione": region,
                "anno": int(year),
                "mld": value / 1_000_000_000.0,
                "misura": measure,
                "comparto": compartment,
                "comparto_label": COMPARTMENTS.get(compartment, compartment),
                "fonte": item.get("fonte"),
                **extra,
            }
        )
    return rows


def load_region_endpoint_rows(refresh, specs):
    rows = []
    datasets = []
    errors = []
    for spec in specs:
        params = spec["params"]
        try:
            data = fetch_fet_data(spec["endpoint"], params, refresh)
            data = data if isinstance(data, list) else []
            rows.extend(
                rows_from_response(
                    data,
                    params["anno"],
                    params["comparto"],
                    spec["measure"],
                    spec.get("extra"),
                )
            )
            datasets.append(
                {
                    "dataset": spec.get("dataset", spec["endpoint"]),
                    "label": spec.get("label", spec["measure"]),
                    "status": "loaded",
                    "endpoint": spec["endpoint"],
                    "params": params,
                    "rows": len(data),
                }
            )
        except Exception as exc:
            meta = {
                "dataset": spec.get("dataset", spec["endpoint"]),
                "label": spec.get("label", spec["measure"]),
                "status": "error",
                "endpoint": spec["endpoint"],
                "params": params,
                "message": str(exc),
            }
            datasets.append(meta)
            errors.append(meta)
    return pd.DataFrame(rows), datasets, errors


def balance_frame(spending, revenue):
    if spending.empty or revenue.empty:
        return pd.DataFrame(columns=["regione", "anno", "mld", "misura", "comparto", "comparto_label"])

    spend = spending.rename(columns={"mld": "spese_mld"})
    rev = revenue.rename(columns={"mld": "entrate_mld"})
    merged = pd.merge(
        rev[["regione", "anno", "comparto", "comparto_label", "entrate_mld"]],
        spend[["regione", "anno", "comparto", "spese_mld"]],
        on=["regione", "anno", "comparto"],
        how="inner",
    )
    merged["mld"] = merged["entrate_mld"] - merged["spese_mld"]
    merged["misura"] = "saldo entrate-spese"
    return merged[["regione", "anno", "mld", "misura", "comparto", "comparto_label", "entrate_mld", "spese_mld"]]


def coverage(frame):
    coverage = []
    if frame is None or frame.empty:
        return coverage
    for (year, compartment), group in frame.groupby(["anno", "comparto"]):
        present = sorted(set(group["regione"]))
        missing = [region for region in EXPECTED_REGIONS if region not in present]
        coverage.append(
            {
                "anno": int(year),
                "comparto": compartment,
                "comparto_label": COMPARTMENTS.get(compartment, compartment),
                "regioni_presenti": len(present),
                "regioni_attese": len(EXPECTED_REGIONS),
                "regioni_mancanti": missing,
            }
        )
    return sorted(coverage, key=lambda row: (row["anno"], row["comparto"]))


def records(frame):
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


def year_frame(frame, year=OPENBDAP_DETAIL_YEAR):
    if frame is None or frame.empty or "anno" not in frame:
        return pd.DataFrame()
    return frame[frame["anno"] == int(year)].copy()


def top_frame(frame, limit=80):
    if frame is None or frame.empty or "mld" not in frame:
        return pd.DataFrame()
    return frame.sort_values("mld", ascending=False).head(limit).reset_index(drop=True)


def spending_2024_detail(regional_budgets):
    by_region = year_frame(regional_budgets.get("spending_by_region"))
    by_mission = year_frame(regional_budgets.get("spending_by_mission"))
    by_mission_title = year_frame(regional_budgets.get("spending_by_mission_title"))
    by_title = year_frame(regional_budgets.get("spending_by_title"))
    return {
        "year": OPENBDAP_DETAIL_YEAR,
        "source": regional_budgets.get("source", SOURCE_OPENBDAP_REGIONI),
        "unit": "mld",
        "perimeter": COMPARTMENTS.get(DEFAULT_COMPARTMENT, DEFAULT_COMPARTMENT),
        "by_region": records(by_region.sort_values("mld", ascending=False) if not by_region.empty else by_region),
        "by_mission": records(by_mission.sort_values(["regione", "missione_code"]) if not by_mission.empty else by_mission),
        "by_mission_title": records(by_mission_title.sort_values(["regione", "missione_code", "titolo_code"]) if not by_mission_title.empty else by_mission_title),
        "by_title": records(by_title.sort_values(["regione", "titolo_code"]) if not by_title.empty else by_title),
        "top_region_mission": records(top_frame(by_mission, limit=80)),
        "top_region_mission_title": records(top_frame(by_mission_title, limit=120)),
        "top_region_title": records(top_frame(by_title, limit=80)),
        "note": (
            "Dettaglio OpenBDAP FET 2024 per Regioni e province autonome. "
            "Le missioni e i titoli sono letti dagli endpoint della pagina Finanza degli Enti Territoriali."
        ),
    }


def load_regional_budgets(refresh=False):
    """Carica e normalizza la sezione sui bilanci regionali."""
    specs = []
    for year in FET_TOTAL_YEARS:
        specs.append({**region_spec(year, DEFAULT_COMPARTMENT, "1", measure="spesa"), "dataset": "spending_by_region", "label": "Spese per regione"})
        specs.append({**region_spec(year, DEFAULT_COMPARTMENT, "2", measure="entrate"), "dataset": "revenue_by_region", "label": "Entrate per regione"})

    for year in FET_DETAIL_YEARS:
        for code, label in MISSION_LABELS.items():
            specs.append(
                {
                    **region_spec(year, DEFAULT_COMPARTMENT, "1", mission=code, measure="spesa"),
                    "dataset": "spending_by_mission",
                    "label": "Spesa per missione",
                    "extra": {"missione_code": code, "missione": label},
                }
            )

        for code, label in SPENDING_TITLE_LABELS.items():
            specs.append(
                {
                    **region_spec(year, DEFAULT_COMPARTMENT, "1", title=code, measure="spesa"),
                    "dataset": "spending_by_title",
                    "label": "Spesa per titolo",
                    "extra": {"titolo_code": code, "titolo": label},
                }
            )

        for mission_code, mission_label in MISSION_LABELS.items():
            for title_code, title_label in SPENDING_TITLE_LABELS.items():
                specs.append(
                    {
                        **region_spec(year, DEFAULT_COMPARTMENT, "1", mission=mission_code, title=title_code, measure="spesa"),
                        "dataset": "spending_by_mission_title",
                        "label": "Spesa per missione e titolo",
                        "extra": {
                            "missione_code": mission_code,
                            "missione": mission_label,
                            "titolo_code": title_code,
                            "titolo": title_label,
                        },
                    }
                )

        for code, label in REVENUE_TITLE_LABELS.items():
            specs.append(
                {
                    **region_spec(year, DEFAULT_COMPARTMENT, "2", title=code, measure="entrate"),
                    "dataset": "revenue_by_title",
                    "label": "Entrate per titolo",
                    "extra": {"titolo_code": code, "titolo": label},
                }
            )

        for code, label in REVENUE_TIPOLOGY_LABELS.items():
            title_code = code[:2]
            specs.append(
                {
                    **region_spec(year, DEFAULT_COMPARTMENT, "2", title=title_code, tipologia=code, measure="entrate"),
                    "dataset": "revenue_by_tipology",
                    "label": "Entrate per tipologia",
                    "extra": {
                        "titolo_code": title_code,
                        "titolo": REVENUE_TITLE_LABELS.get(title_code, title_code),
                        "tipologia_code": code,
                        "tipologia": label,
                    },
                }
            )

    frame, datasets, errors = load_region_endpoint_rows(refresh, specs)
    if frame.empty:
        empty_region = pd.DataFrame(columns=["regione", "anno", "mld", "misura", "comparto", "comparto_label"])
        empty_category = pd.DataFrame(columns=["regione", "anno", "mld", "misura", "comparto", "comparto_label"])
        return {
            "source": SOURCE_OPENBDAP_REGIONI,
            "updated": None,
            "datasets": datasets,
            "errors": errors,
            "coverage": [],
            "spending_by_region": empty_region,
            "spending_by_mission": empty_category,
            "spending_by_mission_title": empty_category,
            "spending_by_title": empty_category,
            "revenue_by_region": empty_region,
            "revenue_by_title": empty_category,
            "revenue_by_tipology": empty_category,
            "balances_by_region": empty_region,
            "balances_detail": empty_category,
        }

    spending_by_region = frame[(frame["misura"] == "spesa") & frame["missione"].isna() & frame["titolo"].isna()].copy()
    revenue_by_region = frame[(frame["misura"] == "entrate") & frame["missione"].isna() & frame["titolo"].isna()].copy()
    spending_by_mission = frame[(frame["misura"] == "spesa") & frame["missione"].notna() & frame["titolo"].isna()].copy()
    spending_by_mission_title = frame[(frame["misura"] == "spesa") & frame["missione"].notna() & frame["titolo"].notna()].copy()
    spending_by_title = frame[(frame["misura"] == "spesa") & frame["missione"].isna() & frame["titolo"].notna()].copy()
    revenue_by_title = frame[(frame["misura"] == "entrate") & frame["titolo"].notna() & frame["tipologia"].isna()].copy()
    revenue_by_tipology = frame[(frame["misura"] == "entrate") & frame["tipologia"].notna()].copy()
    balances_by_region = balance_frame(spending_by_region, revenue_by_region)

    return {
        "source": SOURCE_OPENBDAP_REGIONI,
        "updated": "OpenBDAP/RGS FET, consultato " + datetime.now(timezone.utc).date().isoformat(),
        "datasets": datasets,
        "errors": errors,
        "coverage": coverage(spending_by_region),
        "perimeters": [{"code": code, "label": label} for code, label in COMPARTMENTS.items()],
        "spending_by_region": spending_by_region.sort_values(["anno", "regione"]).reset_index(drop=True),
        "spending_by_mission": spending_by_mission.sort_values(["anno", "regione", "missione_code"]).reset_index(drop=True),
        "spending_by_mission_title": spending_by_mission_title.sort_values(["anno", "regione", "missione_code", "titolo_code"]).reset_index(drop=True),
        "spending_by_title": spending_by_title.sort_values(["anno", "regione", "titolo_code"]).reset_index(drop=True),
        "revenue_by_region": revenue_by_region.sort_values(["anno", "regione"]).reset_index(drop=True),
        "revenue_by_title": revenue_by_title.sort_values(["anno", "regione", "titolo_code"]).reset_index(drop=True),
        "revenue_by_tipology": revenue_by_tipology.sort_values(["anno", "regione", "titolo_code", "tipologia_code"]).reset_index(drop=True),
        "balances_by_region": balances_by_region.sort_values(["anno", "regione"]).reset_index(drop=True),
        "balances_detail": pd.DataFrame(),
    }


def append_regional_budgets_to_source_json(regional_budgets, manifest_rows=None):
    """Aggiunge al JSON dashboard la sezione `regional_budgets`."""
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
        "coverage": regional_budgets.get("coverage", []),
        "perimeters": regional_budgets.get("perimeters", []),
        "spending_by_region": records(regional_budgets.get("spending_by_region")),
        "spending_by_mission": records(regional_budgets.get("spending_by_mission")),
        "spending_by_mission_title": records(regional_budgets.get("spending_by_mission_title")),
        "spending_by_title": records(regional_budgets.get("spending_by_title")),
        "spending_2024_detail": spending_2024_detail(regional_budgets),
        "revenue_by_region": records(regional_budgets.get("revenue_by_region")),
        "revenue_by_title": records(regional_budgets.get("revenue_by_title")),
        "revenue_by_tipology": records(regional_budgets.get("revenue_by_tipology")),
        "balances_by_region": records(regional_budgets.get("balances_by_region")),
        "balances_detail": records(regional_budgets.get("balances_detail")),
    }

    if manifest_rows is not None:
        payload["manifest"] = manifest_rows

    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
