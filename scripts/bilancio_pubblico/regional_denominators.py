"""Denominatori regionali per normalizzare i bilanci OpenBDAP."""

import pandas as pd

from bilancio_pubblico.data_extraction import eurostat_series


SOURCE_EUROSTAT_REGIONAL_POPULATION = (
    "Fonte: Eurostat demo_r_pjanaggr3, popolazione al 1 gennaio per regione NUTS"
)
SOURCE_REGIONAL_AREA = (
    "Fonte: superfici territoriali regionali ISTAT/SISTAN; valori kmq stabili nel tempo, usati solo come denominatore derivato"
)

REGION_NUTS2_GEOS = {
    "Piemonte": ["ITC1"],
    "Valle d'Aosta": ["ITC2"],
    "Liguria": ["ITC3"],
    "Lombardia": ["ITC4"],
    "Trentino-Alto Adige": ["ITH1", "ITH2"],
    "Veneto": ["ITH3"],
    "Friuli-Venezia Giulia": ["ITH4"],
    "Emilia-Romagna": ["ITH5"],
    "Toscana": ["ITI1"],
    "Umbria": ["ITI2"],
    "Marche": ["ITI3"],
    "Lazio": ["ITI4"],
    "Abruzzo": ["ITF1"],
    "Molise": ["ITF2"],
    "Campania": ["ITF3"],
    "Puglia": ["ITF4"],
    "Basilicata": ["ITF5"],
    "Calabria": ["ITF6"],
    "Sicilia": ["ITG1"],
    "Sardegna": ["ITG2"],
}

REGION_AREA_KM2 = {
    "Piemonte": 25386.70,
    "Valle d'Aosta": 3260.90,
    "Liguria": 5416.21,
    "Lombardia": 23863.65,
    "Trentino-Alto Adige": 13605.50,
    "Veneto": 18399.00,
    "Friuli-Venezia Giulia": 7935.22,
    "Emilia-Romagna": 22452.78,
    "Toscana": 22987.04,
    "Umbria": 8464.33,
    "Marche": 9401.38,
    "Lazio": 17232.29,
    "Abruzzo": 10831.84,
    "Molise": 4460.65,
    "Campania": 13670.95,
    "Puglia": 19540.90,
    "Basilicata": 10073.32,
    "Calabria": 15221.90,
    "Sicilia": 25832.39,
    "Sardegna": 24100.02,
}


def _population_series_for_geo(geo, refresh):
    params = {
        "format": "JSON",
        "lang": "en",
        "freq": "A",
        "unit": "NR",
        "sex": "T",
        "age": "TOTAL",
        "geo": geo,
    }
    series, updated = eurostat_series(
        "demo_r_pjanaggr3",
        params,
        f"eurostat_demo_r_pjanaggr3_{geo}_population.json",
        refresh,
    )
    series = series.dropna().sort_index()
    return series, updated


def _population_for_geo(geo, refresh):
    series, updated = _population_series_for_geo(geo, refresh)
    if series.empty:
        return None, None, updated
    year = int(series.index.max())
    return year, float(series.loc[year]), updated


def load_regional_denominators(refresh=False):
    rows = []
    errors = []
    updated = None
    for region, geos in REGION_NUTS2_GEOS.items():
        series_by_geo = []
        for geo in geos:
            try:
                series, item_updated = _population_series_for_geo(geo, refresh)
                updated = item_updated or updated
            except Exception as exc:
                errors.append({"regione": region, "geo": geo, "message": str(exc)})
                continue
            if not series.empty:
                series_by_geo.append(series)

        if series_by_geo:
            population_by_year = pd.concat(series_by_geo, axis=1).sum(axis=1, min_count=1).dropna()
        else:
            population_by_year = pd.Series(dtype="float64")

        if population_by_year.empty:
            rows.append(
                {
                    "regione": region,
                    "anno": None,
                    "area_km2": REGION_AREA_KM2.get(region),
                    "area_source": SOURCE_REGIONAL_AREA,
                    "population": None,
                    "population_year": None,
                    "population_source": SOURCE_EUROSTAT_REGIONAL_POPULATION,
                }
            )
            continue

        for year, population in population_by_year.items():
            rows.append(
                {
                    "regione": region,
                    "anno": int(year),
                    "area_km2": REGION_AREA_KM2.get(region),
                    "area_source": SOURCE_REGIONAL_AREA,
                    "population": float(population),
                    "population_year": int(year),
                    "population_source": SOURCE_EUROSTAT_REGIONAL_POPULATION,
                }
            )
    return {
        "frame": pd.DataFrame(rows),
        "updated": updated,
        "errors": errors,
        "sources": [SOURCE_EUROSTAT_REGIONAL_POPULATION, SOURCE_REGIONAL_AREA],
    }


def add_regional_denominators(frame, denominators):
    if frame is None or frame.empty:
        return frame
    denom = denominators.get("frame") if isinstance(denominators, dict) else None
    if denom is None or denom.empty:
        return frame
    if "anno" in frame.columns and "anno" in denom.columns:
        result = frame.merge(denom, on=["regione", "anno"], how="left")
    else:
        latest = denom.sort_values("anno").drop_duplicates("regione", keep="last")
        result = frame.merge(latest.drop(columns=["anno"], errors="ignore"), on="regione", how="left")
    if "mld" in result.columns:
        result["euro_per_capita"] = result.apply(
            lambda row: row["mld"] * 1_000_000_000.0 / row["population"]
            if pd.notna(row.get("mld")) and pd.notna(row.get("population")) and row.get("population")
            else None,
            axis=1,
        )
        result["euro_per_km2"] = result.apply(
            lambda row: row["mld"] * 1_000_000_000.0 / row["area_km2"]
            if pd.notna(row.get("mld")) and pd.notna(row.get("area_km2")) and row.get("area_km2")
            else None,
            axis=1,
        )
    return result


def denominator_records(denominators):
    frame = denominators.get("frame") if isinstance(denominators, dict) else None
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
            else:
                clean[key] = value
        rows.append(clean)
    return rows
