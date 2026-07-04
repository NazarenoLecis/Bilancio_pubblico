"""Costanti condivise per fonti, path, codici e stile grafico."""

from pathlib import Path
import sys

from utils_bilancio.europa.geografie import EUROPEAN_GEOS


BASE_DIR = None
BASE_CANDIDATES = [Path.cwd().resolve(), *Path.cwd().resolve().parents]
for path_text in sys.path:
    if not path_text:
        continue
    path_value = Path(path_text).resolve()
    BASE_CANDIDATES.extend([path_value, *path_value.parents])
for candidate in BASE_CANDIDATES:
    if (candidate / "scripts" / "utils_bilancio").is_dir():
        BASE_DIR = candidate
        break
if BASE_DIR is None:
    BASE_DIR = Path.cwd().resolve()
DATA_DIR = BASE_DIR / "data" / "raw"
CHART_DIR = BASE_DIR / "grafici"
ASSET_DIR = BASE_DIR / "assets"
EXPORT_ROOT_DIR = BASE_DIR / "data" / "export"
SOURCE_DATA_JSON_PATH = EXPORT_ROOT_DIR / "bilancio-pubblico" / "source-data.json"
LOGO_PATH = ASSET_DIR / "gufo_logo.png"

USER_AGENT = "Fisco grafici - Elaborazione Nazareno Lecis"
AUTHOR_LINE = "Elaborazione di Nazareno Lecis"

MEF_ENTRATE_URL = "https://www1.finanze.gov.it/finanze/entrate_tributarie/public/api/api.php?action=get_entrate_erariali"
MEF_TERRITORIALI_URL = "https://www1.finanze.gov.it/finanze/entrate_tributarie/public/api/api.php?action=get_entrate_tributarie"
MEF_DICHIARAZIONI_BASE = "https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
OECD_REVENUE_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD"
OECD_COFOG_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11"
OECD_GDP_BASE_URL = "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE1"

ORANGE = "#f05a1a"
BLACK = "#090909"
NAVY = "#0d1b2a"
PAPER = "#f6f3ed"
GRID = "#d8d4ca"

BAND_ORDER = [
    "0 - 15.000",
    "15.001 - 29.000",
    "29.001 - 55.000",
    "55.001 - 75.000",
    "oltre 75.000",
]

COFOG_LABELS = {
    "GF01": "Servizi generali",
    "GF02": "Difesa",
    "GF03": "Ordine pubblico",
    "GF04": "Affari economici",
    "GF05": "Ambiente",
    "GF06": "Casa e territorio",
    "GF07": "Sanita",
    "GF08": "Cultura e religione",
    "GF09": "Istruzione",
    "GF10": "Protezione sociale",
}

COFOG_DETAIL_LABELS = {
    "GF0101": "Organi esecutivi e legislativi, affari finanziari e fiscali, affari esteri",
    "GF0102": "Aiuti economici esteri",
    "GF0103": "Servizi generali",
    "GF0104": "Ricerca di base",
    "GF0105": "Ricerca e sviluppo per servizi generali",
    "GF0106": "Servizi generali n.c.a.",
    "GF0107": "Operazioni sul debito pubblico",
    "GF0108": "Trasferimenti generali tra livelli di governo",
    "GF0201": "Difesa militare",
    "GF0202": "Difesa civile",
    "GF0203": "Aiuti militari esteri",
    "GF0204": "Ricerca e sviluppo per la difesa",
    "GF0205": "Difesa n.c.a.",
    "GF0301": "Servizi di polizia",
    "GF0302": "Servizi antincendio",
    "GF0303": "Tribunali",
    "GF0304": "Istituti penitenziari",
    "GF0305": "Ricerca e sviluppo per ordine pubblico e sicurezza",
    "GF0306": "Ordine pubblico e sicurezza n.c.a.",
    "GF0401": "Affari economici, commerciali e del lavoro",
    "GF0402": "Agricoltura, silvicoltura, pesca e caccia",
    "GF0403": "Combustibili ed energia",
    "GF0404": "Attivita' estrattive, manifatturiere e costruzioni",
    "GF0405": "Trasporti",
    "GF0406": "Comunicazioni",
    "GF0407": "Altre industrie",
    "GF0408": "Ricerca e sviluppo per affari economici",
    "GF0409": "Affari economici n.c.a.",
    "GF0501": "Gestione dei rifiuti",
    "GF0502": "Gestione delle acque reflue",
    "GF0503": "Riduzione dell'inquinamento",
    "GF0504": "Protezione biodiversita' e paesaggio",
    "GF0505": "Ricerca e sviluppo per protezione ambientale",
    "GF0506": "Protezione ambientale n.c.a.",
    "GF0601": "Sviluppo abitativo",
    "GF0602": "Sviluppo del territorio",
    "GF0603": "Approvvigionamento idrico",
    "GF0604": "Illuminazione stradale",
    "GF0605": "Ricerca e sviluppo per abitazioni e assetto territoriale",
    "GF0606": "Abitazioni e assetto territoriale n.c.a.",
    "GF0701": "Prodotti, apparecchi e attrezzature mediche",
    "GF0702": "Servizi ambulatoriali",
    "GF0703": "Servizi ospedalieri",
    "GF0704": "Servizi di sanita' pubblica",
    "GF0705": "Ricerca e sviluppo per sanita'",
    "GF0706": "Sanita' n.c.a.",
    "GF0801": "Servizi ricreativi e sportivi",
    "GF0802": "Servizi culturali",
    "GF0803": "Servizi radiotelevisivi ed editoriali",
    "GF0804": "Servizi religiosi e altre comunita'",
    "GF0805": "Ricerca e sviluppo per cultura, religione e ricreazione",
    "GF0806": "Cultura, religione e ricreazione n.c.a.",
    "GF0901": "Istruzione prescolastica e primaria",
    "GF0902": "Istruzione secondaria",
    "GF0903": "Istruzione post-secondaria non terziaria",
    "GF0904": "Istruzione terziaria",
    "GF0905": "Istruzione non definibile per livello",
    "GF0906": "Servizi ausiliari dell'istruzione",
    "GF0907": "Ricerca e sviluppo per istruzione",
    "GF0908": "Istruzione n.c.a.",
    "GF1001": "Malattia e disabilita'",
    "GF1002": "Vecchiaia",
    "GF1003": "Superstiti",
    "GF1004": "Famiglia e figli",
    "GF1005": "Disoccupazione",
    "GF1006": "Abitazione",
    "GF1007": "Esclusione sociale n.c.a.",
    "GF1008": "Ricerca e sviluppo per protezione sociale",
    "GF1009": "Protezione sociale n.c.a.",
}

TAXAG_LABELS = {
    "D2": "Imposte su produzione e importazioni",
    "D51": "Imposte su reddito",
    "D59": "Imposte su patrimonio",
    "D61": "Contributi sociali netti",
    "D91": "Imposte in conto capitale",
}

SOURCE_MEF_ENTRATE = (
    "Fonte: MEF - Dipartimento delle Finanze, Entrate tributarie erariali, "
    "competenza giuridica"
)
SOURCE_MEF_ENTRATE_COMBINED = (
    "Fonte: MEF - Dipartimento delle Finanze, Entrate tributarie erariali e territoriali, "
    "competenza giuridica"
)
SOURCE_MEF_ENTRATE_WITH_APPENDICI = (
    "Fonte: MEF - Dipartimento delle Finanze, API entrate erariali e territoriali; "
    "Appendici statistiche dicembre 2025"
)
SOURCE_MEF_DICHIARAZIONI = (
    "Fonte: MEF - Dipartimento delle Finanze, Statistiche dichiarazioni 2025, "
    "anno d'imposta 2024"
)
SOURCE_MEF_SUCCESSIONI = (
    "Fonte: MEF - Dipartimento delle Finanze, Appendici statistiche al bollettino entrate tributarie, "
    "dicembre 2025"
)
SOURCE_UPB_TARI = (
    "Fonte: Ufficio parlamentare di bilancio, Focus n. 5/2024 sulla TARI, dati 2023"
)
SOURCE_EUROSTAT_TAX = (
    "Fonte: Eurostat gov_10a_taxag, amministrazioni pubbliche S13"
)
SOURCE_EUROSTAT_EXP = (
    "Fonte: Eurostat gov_10a_exp, spesa totale S13 per funzione COFOG"
)
SOURCE_BANKITALIA_WEALTH = (
    "Fonte: Banca d'Italia, Conti distributivi sulla ricchezza delle famiglie, IV trimestre 2025"
)
SOURCE_OECD_REVENUE = (
    "Fonte: OCSE, Revenue Statistics 2025, Comparative tax revenues, dati 2024"
)
SOURCE_OECD_SPENDING = (
    "Fonte: OCSE, National Accounts Statistics, Table 1100 COFOG e Table 0101 PIL corrente, dati 2024"
)

SUCCESSIONI_DONAZIONI_2025 = 1.081
SUCCESSIONI_DONAZIONI_SERIE = [
    {"anno": 2023, "milioni": 998},
    {"anno": 2024, "milioni": 1012},
    {"anno": 2025, "milioni": 1081},
]

PEER_GEOS = EUROPEAN_GEOS

OECD_MEMBER_AREAS = [
    "AUS",
    "AUT",
    "BEL",
    "CAN",
    "CHL",
    "COL",
    "CRI",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "ISL",
    "IRL",
    "ISR",
    "ITA",
    "JPN",
    "KOR",
    "LVA",
    "LTU",
    "LUX",
    "MEX",
    "NLD",
    "NZL",
    "NOR",
    "POL",
    "PRT",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
    "CHE",
    "TUR",
    "GBR",
    "USA",
]

OECD_AREA_LABELS = {
    "OECD_AVG": "Media OCSE",
    "ITA": "Italia",
    "FRA": "Francia",
    "DEU": "Germania",
    "ESP": "Spagna",
    "GBR": "Regno Unito",
    "USA": "Stati Uniti",
    "SWE": "Svezia",
    "DNK": "Danimarca",
    "NLD": "Paesi Bassi",
    "BEL": "Belgio",
    "AUT": "Austria",
}
OECD_PEER_ORDER = ["USA", "GBR", "ESP", "DEU", "OECD_AVG", "ITA", "FRA", "SWE", "DNK"]

OECD_REVENUE_CATEGORIES = [
    {"codice": "_T", "categoria": "Totale\nfisco"},
    {"codice": "T_1100", "categoria": "Redditi\npersone"},
    {"codice": "T_1200", "categoria": "Imprese"},
    {"codice": "T_2000", "categoria": "Contributi\nsociali"},
    {"codice": "T_5000", "categoria": "Beni e\nservizi"},
    {"codice": "T_5111", "categoria": "IVA"},
    {"codice": "T_5120", "categoria": "Accise e\nspecifiche"},
    {"codice": "T_4000", "categoria": "Patrimonio"},
    {"codice": "T_4300", "categoria": "Successioni\ne donazioni"},
]

OECD_SPENDING_CATEGORIES = [{"codice": "_T", "categoria": "Totale"}] + [
    {"codice": code, "categoria": label}
    for code, label in COFOG_LABELS.items()
]

GENERATED_FILES = [
    "01_principali_entrate_tributarie_2025.png",
    "01_principali_entrate_tributarie_erariali_2025.png",
    "02_entrate_dirette_indirette_2002_2025.png",
    "03_pressione_fiscale_componenti_1995_2024.png",
    "04_spesa_pubblica_funzioni_cofog_2024.png",
    "05_irpef_netto_per_fascia_2024.png",
    "06_quote_irpef_per_fascia_2024.png",
    "07_distribuzione_salari_capitali_2024.png",
    "08_composizione_redditi_per_fascia_2024.png",
    "09_pressione_fiscale_confronto_ue_2024.png",
    "10_spesa_pubblica_confronto_ue_2024.png",
    "11_protezione_sociale_confronto_ue_2024.png",
    "12_tipi_entrate_tributarie_2025.png",
    "13_spesa_totale_italia_1995_2024.png",
    "14_distribuzione_patrimonio_famiglie_2025.png",
    "15_successioni_donazioni_2025.png",
    "16_ocse_entrate_per_tipo_2024.png",
    "17_ocse_spesa_per_funzione_2024.png",
    "18_ocse_pressione_fiscale_totale_2024.png",
    "19_ocse_successioni_donazioni_2024.png",
    "20_ocse_spesa_totale_2024.png",
    "12_gettito_1_percento_vs_superbonus.png",
    "13_aliquote_patrimoniale_1_percento.png",
    "14_successioni_gettito_riforma.png",
    "15_imu_prima_seconda_casa.png",
]
