"""Flussi di cassa regionali da SIOPE.

SIOPE e' usato come livello granulare di cassa: incassi, pagamenti, codici
gestionali, mese, ente e territorio. Gli ZIP massivi restano in `data/raw`;
nel JSON pubblico esportiamo aggregati regionali adatti a notebook e dashboard.
"""

from datetime import datetime, timezone
import csv
import io
import json
import os
from pathlib import Path
import zipfile

import pandas as pd
import requests

from utils_bilancio.regioni.denominatori import (
    add_regional_denominators,
    denominator_records,
    load_regional_denominators,
)
from utils_bilancio.generali.costanti import DATA_DIR, SOURCE_DATA_JSON_PATH, USER_AGENT


SIOPE_BASE_URL = "https://www.siope.it/Siope/documenti/siope2/open/last"
SOURCE_SIOPE_FLUSSI = (
    "Fonte: SIOPE - Banca d'Italia/RGS, download massivo open data, "
    "incassi e pagamenti per codice gestionale"
)

SIOPE_AVAILABLE_YEARS = list(range(2010, 2027))
SIOPE_YEAR_ENV = "BILANCIO_PUBBLICO_SIOPE_YEARS"
SIOPE_CACHE_DIR = DATA_DIR / "siope"
SIOPE_CHUNK_SIZE = 500_000

SIOPE_FLOWS = {
    "entrate": {
        "filename": "SIOPE_ENTRATE.{year}.zip",
        "prefix": "ENTRATE",
        "codebook_prefix": "ANAG_CODGEST_ENTRATE",
        "label": "Incassi",
    },
    "uscite": {
        "filename": "SIOPE_USCITE.{year}.zip",
        "prefix": "USCITE",
        "codebook_prefix": "ANAG_CODGEST_USCITE",
        "label": "Pagamenti",
    },
}

SIOPE_PERIMETERS = [
    {
        "id": "regioni",
        "label": "Regioni",
        "description": "Solo enti SIOPE con sotto-comparto REGIONE.",
        "compartments": ["REGIONE"],
        "code_detail": True,
    },
    {
        "id": "regioni_sanita",
        "label": "Regioni + gestione sanitaria regionale",
        "description": "Enti REGIONE e REG_GEST_SAN: utile per avvicinare il perimetro regionale completo di cassa.",
        "compartments": ["REGIONE", "REG_GEST_SAN"],
        "code_detail": True,
    },
    {
        "id": "pa_localizzate",
        "label": "PA localizzate nella regione",
        "description": "Tutti gli enti SIOPE agganciabili a una provincia/regione. Il dettaglio codice non viene esportato per evitare JSON troppo pesanti.",
        "compartments": None,
        "code_detail": False,
    },
]

SIOPE_REGION_LABELS = {
    "01": "Piemonte",
    "02": "Valle d'Aosta",
    "03": "Lombardia",
    "04": "Trentino-Alto Adige",
    "05": "Veneto",
    "06": "Friuli-Venezia Giulia",
    "07": "Liguria",
    "08": "Emilia-Romagna",
    "09": "Toscana",
    "10": "Umbria",
    "11": "Marche",
    "12": "Lazio",
    "13": "Abruzzo",
    "14": "Molise",
    "15": "Campania",
    "16": "Puglia",
    "17": "Basilicata",
    "18": "Calabria",
    "19": "Sicilia",
    "20": "Sardegna",
}


def selected_siope_years(years=None):
    if years is not None:
        return sorted({int(year) for year in years})

    raw = os.getenv(SIOPE_YEAR_ENV, "").strip()
    if not raw:
        return list(SIOPE_AVAILABLE_YEARS)

    selected = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start, end = item.split("-", 1)
            selected.extend(range(int(start), int(end) + 1))
        else:
            selected.append(int(item))
    return sorted({year for year in selected if year in SIOPE_AVAILABLE_YEARS})


def siope_zip_url(flow, year=None):
    if flow == "anagrafiche":
        return f"{SIOPE_BASE_URL}/SIOPE_ANAGRAFICHE.zip"
    filename = SIOPE_FLOWS[flow]["filename"].format(year=int(year))
    return f"{SIOPE_BASE_URL}/{filename}"


def siope_zip_path(flow, year=None):
    SIOPE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if flow == "anagrafiche":
        return SIOPE_CACHE_DIR / "SIOPE_ANAGRAFICHE.zip"
    return SIOPE_CACHE_DIR / SIOPE_FLOWS[flow]["filename"].format(year=int(year))


def download_siope_zip(flow, year=None, refresh=False):
    path = siope_zip_path(flow, year)
    if path.exists() and not refresh:
        return {
            "flow": flow,
            "year": int(year) if year is not None else None,
            "path": str(path),
            "status": "cached",
            "bytes": path.stat().st_size,
            "updated": None,
        }

    url = siope_zip_url(flow, year)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=180, stream=True)
    response.raise_for_status()
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("wb") as output:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                output.write(chunk)
    temporary_path.replace(path)
    return {
        "flow": flow,
        "year": int(year) if year is not None else None,
        "path": str(path),
        "status": "downloaded",
        "url": url,
        "bytes": path.stat().st_size,
        "updated": response.headers.get("Last-Modified"),
    }


def zip_member(path, prefix):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if Path(name).name.startswith(prefix):
                return name
    return None


def read_zip_csv_rows(path, prefix):
    member = zip_member(path, prefix)
    if member is None:
        return []
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="latin1", newline="")
            return list(csv.reader(text))


def load_siope_anagraphics(refresh=False):
    meta = download_siope_zip("anagrafiche", refresh=refresh)
    path = Path(meta["path"])

    province_rows = read_zip_csv_rows(path, "ANAG_REG_PROV")
    province_map = {}
    for row in province_rows:
        if len(row) < 5:
            continue
        province_map[row[3]] = {
            "ripartizione": row[0],
            "codice_regione": row[1],
            "regione": SIOPE_REGION_LABELS.get(row[1], row[2].title()),
            "codice_provincia": row[3],
            "provincia": row[4],
        }

    entity_rows = read_zip_csv_rows(path, "ANAG_ENTI_SIOPE")
    entities = []
    for row in entity_rows:
        if len(row) < 9:
            continue
        province = province_map.get(row[6])
        if province is None:
            continue
        entities.append(
            {
                "codice_ente": row[0],
                "data_inizio": row[1],
                "data_fine": row[2],
                "codice_fiscale": row[3],
                "ente": row[4],
                "codice_comune": row[5],
                "codice_provincia": row[6],
                "popolazione_ente": None if row[7] == "N.A." else row[7],
                "comparto": row[8],
                **province,
            }
        )

    compartments = []
    for row in read_zip_csv_rows(path, "ANAG_SOTTOCOMPARTI"):
        if len(row) >= 3:
            compartments.append({"comparto": row[0], "comparto_label": row[1], "macro_comparto": row[2]})

    codebooks = {}
    for flow, spec in SIOPE_FLOWS.items():
        rows = []
        for row in read_zip_csv_rows(path, spec["codebook_prefix"]):
            if len(row) >= 5:
                rows.append(
                    {
                        "flusso": flow,
                        "codice_gestionale": row[0],
                        "comparto": row[1],
                        "descrizione": row[2],
                        "data_inizio": row[3],
                        "data_fine": row[4],
                    }
                )
        codebooks[flow] = pd.DataFrame(rows)

    return {
        "meta": meta,
        "entities": pd.DataFrame(entities),
        "compartments": pd.DataFrame(compartments),
        "codebooks": codebooks,
        "province": pd.DataFrame(province_map.values()),
    }


def empty_flow_frame():
    return pd.DataFrame(columns=["perimetro", "flusso", "regione", "codice_regione", "anno", "mld"])


def code_labels(codebook):
    if codebook is None or codebook.empty:
        return pd.DataFrame(columns=["flusso", "codice_gestionale", "descrizione_codice"])
    labels = codebook.sort_values(["codice_gestionale", "data_inizio"]).drop_duplicates(
        ["flusso", "codice_gestionale"],
        keep="last",
    )
    return labels[["flusso", "codice_gestionale", "descrizione"]].rename(
        columns={"descrizione": "descrizione_codice"}
    )


def aggregate_siope_file(flow, year, entities, refresh=False):
    meta = download_siope_zip(flow, year=year, refresh=refresh)
    path = Path(meta["path"])
    member = zip_member(path, SIOPE_FLOWS[flow]["prefix"])
    if member is None:
        meta["status"] = "missing_member"
        return {
            "meta": meta,
            "year": empty_flow_frame(),
            "month": empty_flow_frame(),
            "code_year": empty_flow_frame(),
            "compartment_year": pd.DataFrame(),
            "rows": 0,
        }

    entity_columns = ["codice_ente", "regione", "codice_regione", "comparto"]
    entity_frame = entities[entity_columns].copy()
    entity_frame["codice_ente"] = entity_frame["codice_ente"].astype("string")
    year_parts = []
    month_parts = []
    code_parts = []
    compartment_parts = []
    raw_rows = 0

    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as raw:
            chunks = pd.read_csv(
                raw,
                header=None,
                names=["codice_ente", "anno", "mese", "codice_gestionale", "importo_cent"],
                dtype={
                    "codice_ente": "string",
                    "anno": "int64",
                    "mese": "int64",
                    "codice_gestionale": "string",
                    "importo_cent": "int64",
                },
                chunksize=SIOPE_CHUNK_SIZE,
            )
            for chunk in chunks:
                raw_rows += len(chunk)
                merged = chunk.merge(entity_frame, on="codice_ente", how="inner")
                if merged.empty:
                    continue
                merged["mld"] = merged["importo_cent"] / 100.0 / 1_000_000_000.0
                merged["flusso"] = flow

                compartment_group = merged.groupby(
                    ["flusso", "regione", "codice_regione", "anno", "comparto"],
                    as_index=False,
                )["mld"].sum()
                compartment_parts.append(compartment_group)

                for perimeter in SIOPE_PERIMETERS:
                    compartments = perimeter["compartments"]
                    if compartments is None:
                        selected = merged
                    else:
                        selected = merged[merged["comparto"].isin(compartments)]
                    if selected.empty:
                        continue

                    selected = selected.assign(perimetro=perimeter["id"])
                    year_parts.append(
                        selected.groupby(
                            ["perimetro", "flusso", "regione", "codice_regione", "anno"],
                            as_index=False,
                        )["mld"].sum()
                    )
                    month_parts.append(
                        selected.groupby(
                            ["perimetro", "flusso", "regione", "codice_regione", "anno", "mese"],
                            as_index=False,
                        )["mld"].sum()
                    )
                    if perimeter["code_detail"]:
                        code_parts.append(
                            selected.groupby(
                                [
                                    "perimetro",
                                    "flusso",
                                    "regione",
                                    "codice_regione",
                                    "anno",
                                    "codice_gestionale",
                                ],
                                as_index=False,
                            )["mld"].sum()
                        )

    meta["rows"] = raw_rows
    return {
        "meta": meta,
        "year": combine_parts(year_parts, ["perimetro", "flusso", "regione", "codice_regione", "anno"]),
        "month": combine_parts(month_parts, ["perimetro", "flusso", "regione", "codice_regione", "anno", "mese"]),
        "code_year": combine_parts(
            code_parts,
            ["perimetro", "flusso", "regione", "codice_regione", "anno", "codice_gestionale"],
        ),
        "compartment_year": combine_parts(
            compartment_parts,
            ["flusso", "regione", "codice_regione", "anno", "comparto"],
        ),
        "rows": raw_rows,
    }


def combine_parts(parts, columns):
    if not parts:
        return pd.DataFrame(columns=[*columns, "mld"])
    frame = pd.concat(parts, ignore_index=True)
    return frame.groupby(columns, as_index=False)["mld"].sum()


def enrich_siope_frame(frame, denominators):
    if frame is None or frame.empty:
        return frame
    return add_regional_denominators(frame, denominators)


def build_siope_balances(year_frame, denominators):
    if year_frame is None or year_frame.empty:
        return pd.DataFrame()
    pivot = year_frame.pivot_table(
        index=["perimetro", "regione", "codice_regione", "anno"],
        columns="flusso",
        values="mld",
        aggfunc="sum",
    ).reset_index()
    pivot.columns.name = None
    pivot["entrate_mld"] = pivot.get("entrate")
    pivot["uscite_mld"] = pivot.get("uscite")
    pivot["mld"] = pivot["entrate_mld"].fillna(0) - pivot["uscite_mld"].fillna(0)
    pivot["flusso"] = "saldo_cassa"
    result = pivot[
        [
            "perimetro",
            "flusso",
            "regione",
            "codice_regione",
            "anno",
            "mld",
            "entrate_mld",
            "uscite_mld",
        ]
    ].copy()
    return enrich_siope_frame(result, denominators)


def records_from_frame(frame):
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


def load_siope_flows(refresh=False, years=None, adjustments=None):
    selected_years = selected_siope_years(years)
    current_year = datetime.now(timezone.utc).year
    anagraphics = load_siope_anagraphics(refresh=refresh)
    entities = anagraphics["entities"]
    codebook_frame = pd.concat(anagraphics["codebooks"].values(), ignore_index=True)
    labels = code_labels(codebook_frame)

    year_parts = []
    month_parts = []
    code_parts = []
    compartment_parts = []
    datasets = [anagraphics["meta"]]
    errors = []

    for year in selected_years:
        for flow in SIOPE_FLOWS:
            try:
                result = aggregate_siope_file(flow, year, entities, refresh=refresh)
                datasets.append(result["meta"])
                year_parts.append(result["year"])
                month_parts.append(result["month"])
                code_parts.append(result["code_year"])
                compartment_parts.append(result["compartment_year"])
            except Exception as exc:
                errors.append({"anno": year, "flusso": flow, "message": str(exc)})

    year_frame = combine_parts(
        year_parts,
        ["perimetro", "flusso", "regione", "codice_regione", "anno"],
    )
    month_frame = combine_parts(
        month_parts,
        ["perimetro", "flusso", "regione", "codice_regione", "anno", "mese"],
    )
    code_frame = combine_parts(
        code_parts,
        ["perimetro", "flusso", "regione", "codice_regione", "anno", "codice_gestionale"],
    )
    compartment_frame = combine_parts(
        compartment_parts,
        ["flusso", "regione", "codice_regione", "anno", "comparto"],
    )

    if not code_frame.empty:
        code_frame = code_frame.merge(labels, on=["flusso", "codice_gestionale"], how="left")

    compartments = anagraphics["compartments"]
    if not compartment_frame.empty and not compartments.empty:
        compartment_frame = compartment_frame.merge(compartments, on="comparto", how="left")

    denominators = load_regional_denominators(refresh=refresh)
    year_frame = enrich_siope_frame(year_frame, denominators)
    code_frame = enrich_siope_frame(code_frame, denominators)
    compartment_frame = enrich_siope_frame(compartment_frame, denominators)
    balances = build_siope_balances(year_frame, denominators)

    return {
        "source": SOURCE_SIOPE_FLUSSI,
        "updated": "SIOPE download massivo, consultato " + datetime.now(timezone.utc).date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "years": selected_years,
        "complete_years": [year for year in selected_years if year < current_year],
        "partial_years": [year for year in selected_years if year >= current_year],
        "perimeters": SIOPE_PERIMETERS,
        "normalization_options": [
            {"id": "mld", "label": "Miliardi correnti", "field": "mld", "unit": "mld"},
            {"id": "pil", "label": "% PIL regionale", "field": "pil", "unit": "% PIL"},
            {"id": "euro_per_capita", "label": "Euro pro capite", "field": "euro_per_capita", "unit": "euro"},
        ],
        "real_adjustment_sources": {},
        "denominators": {
            "rows": denominator_records(denominators),
            "sources": denominators.get("sources", []),
            "updated": denominators.get("updated"),
            "errors": denominators.get("errors", []),
        },
        "datasets": datasets,
        "errors": errors,
        "by_region_year": records_from_frame(year_frame.sort_values(["perimetro", "flusso", "anno", "regione"])),
        "by_region_month": records_from_frame(month_frame.sort_values(["perimetro", "flusso", "anno", "mese", "regione"])),
        "by_region_code_year": records_from_frame(
            code_frame.sort_values(["perimetro", "flusso", "anno", "regione", "codice_gestionale"])
        ),
        "balances_by_region_year": records_from_frame(balances.sort_values(["perimetro", "anno", "regione"])),
        "by_region_compartment_year": records_from_frame(
            compartment_frame.sort_values(["flusso", "anno", "regione", "comparto"])
        ),
        "entity_counts_by_region": records_from_frame(
            entities.groupby(["regione", "codice_regione", "comparto"], as_index=False)
            .size()
            .rename(columns={"size": "enti"})
            .sort_values(["regione", "comparto"])
        ),
        "note": (
            "SIOPE misura flussi di cassa, non rendiconti di competenza. "
            "Gli importi originali sono in centesimi; il JSON li espone in miliardi di euro."
        ),
    }


def append_siope_flows_to_source_json(siope_flows):
    if not SOURCE_DATA_JSON_PATH.exists():
        return

    payload = json.loads(SOURCE_DATA_JSON_PATH.read_text(encoding="utf-8"))
    payload["siope_flussi"] = siope_flows

    meta = payload.setdefault("meta", {})
    sources = meta.setdefault("sources", [])
    if SOURCE_SIOPE_FLUSSI not in sources:
        sources.append(SOURCE_SIOPE_FLUSSI)

    method_notes = meta.setdefault("method_notes", [])
    for note in (
        "SIOPE e OpenBDAP non hanno lo stesso perimetro: SIOPE misura incassi e pagamenti di cassa, OpenBDAP usa dati di rendiconto.",
        "Nei flussi SIOPE gli importi originali sono in centesimi; l'export li converte in miliardi di euro.",
        "Il dettaglio SIOPE per codice gestionale viene esportato per Regioni e gestione sanitaria regionale; il perimetro PA localizzate resta aggregato per comparto.",
    ):
        if note not in method_notes:
            method_notes.append(note)

    meta.setdefault("source_updates", {})["siope_flussi"] = {
        "updated": siope_flows.get("updated"),
        "generated_at": siope_flows.get("generated_at"),
        "years": siope_flows.get("years", []),
    }

    counts = payload.setdefault("counts", {})
    counts["siope_by_region_year"] = len(siope_flows.get("by_region_year", []))
    counts["siope_by_region_code_year"] = len(siope_flows.get("by_region_code_year", []))
    counts["siope_by_region_month"] = len(siope_flows.get("by_region_month", []))

    SOURCE_DATA_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
