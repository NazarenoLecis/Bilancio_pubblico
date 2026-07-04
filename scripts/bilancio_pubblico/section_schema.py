"""Schema operativo delle sezioni del progetto Bilancio pubblico.

Il modulo centralizza gli identificativi delle quattro sezioni, i metadati usati
negli export e gli aggregati contabili regionali. Ogni nuova analisi deve essere
ricondotta a una di queste sezioni quando possibile.
"""

SECTION_IDS = ("italia", "confronto_europeo", "confronto_ocse", "regioni")

SECTION_SCHEMA = [
    {
        "id": "italia",
        "label": "Italia",
        "order": 1,
        "scope": "Quadro nazionale",
        "description": "Entrate, spese, pressione fiscale, distribuzione IRPEF, patrimonio e serie storiche italiane.",
        "primary_sources": ["MEF", "Eurostat", "Banca d'Italia", "UPB"],
        "legacy_keys": [
            "kpis",
            "top_taxes",
            "tax_pressure_trend",
            "pressure_components",
            "revenue_items",
            "all_revenue_lines",
            "revenue_category_series",
            "spending_focus",
            "spending_by_function",
            "spending_category_series",
            "spending_function_detail_series",
            "total_spending_trend",
            "declaration_summary",
            "household_wealth_distribution",
            "succession_gift_tax",
        ],
        "output_file": "sections/italia.json",
        "notebook": "notebooks/01_italia.ipynb",
    },
    {
        "id": "confronto_europeo",
        "label": "Confronto europeo",
        "order": 2,
        "scope": "Paesi europei, UE e area euro quando disponibili",
        "description": "Confronti armonizzati Eurostat su pressione fiscale, spesa pubblica e funzioni COFOG.",
        "primary_sources": ["Eurostat gov_10a_taxag", "Eurostat gov_10a_exp"],
        "legacy_keys": [
            "peer",
            "peer_spending_function_options",
            "peer_spending_functions",
        ],
        "output_file": "sections/confronto_europeo.json",
        "notebook": "notebooks/02_confronto_europeo.ipynb",
    },
    {
        "id": "confronto_ocse",
        "label": "Confronto OCSE",
        "order": 3,
        "scope": "Paesi OCSE e media OCSE quando disponibile",
        "description": "Confronti OCSE su gettito, struttura delle entrate, spesa e imposte su successioni e donazioni.",
        "primary_sources": ["OECD Revenue Statistics", "OECD National Accounts"],
        "legacy_keys": ["oecd"],
        "output_file": "sections/confronto_ocse.json",
        "notebook": "notebooks/03_confronto_ocse.ipynb",
    },
    {
        "id": "regioni",
        "label": "Regioni",
        "order": 4,
        "scope": "Regioni e province autonome",
        "description": "Rendiconti OpenBDAP/FET con entrate, spese, saldi, titoli, missioni e normalizzazioni territoriali.",
        "primary_sources": ["RGS OpenBDAP/FET", "Eurostat popolazione regionale", "ISTAT/SISTAN superfici"],
        "legacy_keys": ["regional_budgets"],
        "output_file": "sections/regioni.json",
        "notebook": "notebooks/04_regioni.ipynb",
    },
]

SECTION_BY_ID = {section["id"]: section for section in SECTION_SCHEMA}

SECTION_ALIASES = {
    "all": list(SECTION_IDS),
    "tutte": list(SECTION_IDS),
    "tutto": list(SECTION_IDS),
    "italia": ["italia"],
    "italy": ["italia"],
    "europa": ["confronto_europeo"],
    "europe": ["confronto_europeo"],
    "ue": ["confronto_europeo"],
    "eu": ["confronto_europeo"],
    "confronto_europeo": ["confronto_europeo"],
    "ocse": ["confronto_ocse"],
    "oecd": ["confronto_ocse"],
    "confronto_ocse": ["confronto_ocse"],
    "regioni": ["regioni"],
    "regions": ["regioni"],
}

REGIONAL_REVENUE_AGGREGATES = [
    {
        "id": "entrate_finali",
        "label": "Entrate finali",
        "title_codes": ["01", "02", "03", "04", "05"],
        "note": "Titoli 1-5. Esclude accensione prestiti, anticipazioni e partite di giro.",
    },
    {
        "id": "entrate_correnti",
        "label": "Entrate correnti",
        "title_codes": ["01", "02", "03"],
        "note": "Titoli 1-3.",
    },
    {
        "id": "entrate_tributarie_perequative",
        "label": "Entrate tributarie, contributive e perequative",
        "title_codes": ["01"],
    },
    {"id": "trasferimenti_correnti", "label": "Trasferimenti correnti", "title_codes": ["02"]},
    {"id": "entrate_extratributarie", "label": "Entrate extratributarie", "title_codes": ["03"]},
    {"id": "entrate_conto_capitale", "label": "Entrate in conto capitale", "title_codes": ["04"]},
    {
        "id": "riduzione_attivita_finanziarie",
        "label": "Riduzione di attivita finanziarie",
        "title_codes": ["05"],
    },
    {"id": "accensione_prestiti", "label": "Accensione prestiti", "title_codes": ["06"]},
    {
        "id": "anticipazioni_tesoreria",
        "label": "Anticipazioni da tesoriere/cassiere",
        "title_codes": ["07"],
    },
    {"id": "partite_giro", "label": "Entrate per conto terzi e partite di giro", "title_codes": ["09"]},
]

REGIONAL_SPENDING_AGGREGATES = [
    {
        "id": "spese_finali",
        "label": "Spese finali",
        "title_codes": ["01", "02", "03"],
        "note": "Titoli 1-3. Esclude rimborso prestiti e chiusura anticipazioni.",
    },
    {"id": "spese_correnti", "label": "Spese correnti", "title_codes": ["01"]},
    {"id": "spese_conto_capitale", "label": "Spese in conto capitale", "title_codes": ["02"]},
    {
        "id": "incremento_attivita_finanziarie",
        "label": "Incremento attivita finanziarie",
        "title_codes": ["03"],
    },
    {"id": "rimborso_prestiti", "label": "Rimborso prestiti", "title_codes": ["04"]},
    {
        "id": "chiusura_anticipazioni",
        "label": "Chiusura anticipazioni ricevute",
        "title_codes": ["05"],
    },
]


def list_section_ids():
    """Restituisce la lista ordinata degli identificativi di sezione.

    Output:
        list[str]: identificativi stabili usati da pipeline, notebook ed export.
    """
    return list(SECTION_IDS)


def section_index():
    """Restituisce i metadati delle sezioni come lista di dizionari copiati.

    Output:
        list[dict]: schema serializzabile da inserire in `source-data.json`.
    """
    return [dict(section) for section in SECTION_SCHEMA]


def normalize_section_ids(selection=None):
    """Normalizza input CLI o liste in identificativi di sezione validi.

    Input:
        selection (str | list | tuple | None): alias, lista di alias o stringa separata da virgole.

    Output:
        list[str]: sezioni valide, ordinate secondo `SECTION_IDS` e senza duplicati.

    Criterio:
        gli alias vengono risolti tramite `SECTION_ALIASES`; l'ordine finale resta quello
        dello schema per mantenere export e notebook coerenti.
    """
    if selection is None:
        return list(SECTION_IDS)
    if isinstance(selection, str):
        raw_items = [item.strip() for item in selection.split(",") if item.strip()]
    else:
        raw_items = []
        for item in selection:
            raw_items.extend(str(item).split(","))
        raw_items = [item.strip() for item in raw_items if item.strip()]
    if not raw_items:
        return list(SECTION_IDS)

    selected = []
    for item in raw_items:
        key = item.lower().replace("-", "_")
        if key not in SECTION_ALIASES:
            allowed = ", ".join([*SECTION_ALIASES.keys()])
            raise ValueError(f"Sezione non riconosciuta: {item}. Valori ammessi: {allowed}")
        selected.extend(SECTION_ALIASES[key])

    deduped = []
    for section_id in SECTION_IDS:
        if section_id in selected and section_id not in deduped:
            deduped.append(section_id)
    return deduped
