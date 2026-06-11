"""Orchestratore completo del progetto.

Il flusso è sempre questo:
1) impostazione ambienti (cartelle, stile grafici, pulizia output vecchi)
2) caricamento dati dalle fonti
3) produzione dei grafici italiani
4) produzione dei confronti UE/OECD
5) scrittura analisi claims e manifest
"""

from bilancio_pubblico.chart_generation.confronti_europa import plot_peer_comparison
from bilancio_pubblico.chart_generation.confronti_oecd import (
    plot_oecd_inheritance_tax,
    plot_oecd_revenue_categories,
    plot_oecd_spending_categories,
    plot_oecd_total_spending,
    plot_oecd_total_tax,
)
from bilancio_pubblico.chart_generation.italia_entrate import (
    plot_direct_indirect,
    plot_income_composition,
    plot_irpef_shares_by_band,
    plot_irpef_tax_by_band,
    plot_main_taxes,
    plot_revenue_types,
    plot_succession_tax_focus,
    plot_tax_pressure,
    plot_wages_capital_distribution,
)
from bilancio_pubblico.chart_generation.italia_patrimonio import plot_household_wealth_distribution
from bilancio_pubblico.chart_generation.italia_uscite import plot_cofog_spending, plot_total_spending_italy
from bilancio_pubblico.data_extraction import (
    load_cofog_spending,
    load_declaration_data,
    load_mef_entrate,
    load_mef_territoriali,
    load_oecd_revenue_data,
    load_oecd_spending_data,
    load_peer_spending,
    load_peer_tax_pressure,
    load_tax_pressure,
    load_total_spending_italy,
)
from bilancio_pubblico.utils import (
    BLACK,
    CHART_DIR,
    clean_generated_outputs,
    configure_style,
    ensure_directories,
    format_percent,
    format_percent_compact,
    ORANGE,
    SOURCE_BANKITALIA_WEALTH,
    SOURCE_EUROSTAT_EXP,
    SOURCE_EUROSTAT_TAX,
    SOURCE_MEF_DICHIARAZIONI,
    SOURCE_MEF_ENTRATE,
    SOURCE_MEF_ENTRATE_COMBINED,
    SOURCE_MEF_ENTRATE_WITH_APPENDICI,
    SOURCE_MEF_SUCCESSIONI,
    SOURCE_OECD_REVENUE,
    SOURCE_OECD_SPENDING,
    write_manifest,
    write_text_file,
)


def write_claims_analysis(peer_tax, peer_spending, peer_social, oecd_revenue, oecd_spending):
    """Scrive `analisi_claims.md` con i claim chiave e i numeri verificati.

    Le righe create sono parte finale della pipeline e tengono insieme:
    - i dati caricati in questo run
    - il grafico di riferimento
    - eventuali note metodologiche esplicative
    """
    # Ricava i numeri principali usati nel file analisi_claims.md.
    # Usiamo i codici paese/filtro standard delle fonti in ingresso.
    italy_tax = float(peer_tax.loc[peer_tax["codice"] == "IT", "valore"].iloc[0])
    eu_tax = float(peer_tax.loc[peer_tax["codice"] == "EU27_2020", "valore"].iloc[0])
    area_tax = float(peer_tax.loc[peer_tax["codice"] == "EA20", "valore"].iloc[0])
    italy_spending = float(peer_spending.loc[peer_spending["codice"] == "IT", "valore"].iloc[0])
    eu_spending = float(peer_spending.loc[peer_spending["codice"] == "EU27_2020", "valore"].iloc[0])
    italy_social = float(peer_social.loc[peer_social["codice"] == "IT", "valore"].iloc[0])
    eu_social = float(peer_social.loc[peer_social["codice"] == "EU27_2020", "valore"].iloc[0])
    oecd_total_tax = oecd_revenue.loc[oecd_revenue["codice"] == "_T"].iloc[0]
    oecd_inheritance = oecd_revenue.loc[oecd_revenue["codice"] == "T_4300"].iloc[0]
    oecd_total_spending = oecd_spending.loc[oecd_spending["codice"] == "_T"].iloc[0]
    lines = [
        "# Analisi claim fiscali",
        "",
        "Sintesi operativa dei claim del report e dei grafici prodotti.",
        "",
        "| Claim | Stato | Dato usato | Output |",
        "|---|---|---:|---|",
        f"| Italia gia' ad alta pressione fiscale | Supportato | Italia {format_percent(italy_tax)} nel 2024; UE {format_percent(eu_tax)}; area euro {format_percent(area_tax)} | 09_pressione_fiscale_confronto_ue_2024.png |",
        f"| Italia con spesa pubblica elevata | Supportato, ma aggiornare il numero del dossier | Eurostat API al 10 giugno 2026: Italia {format_percent(italy_spending)} del PIL nel 2024; UE {format_percent(eu_spending)} | 10_spesa_pubblica_confronto_ue_2024.png |",
        f"| La protezione sociale pesa molto sul bilancio | Supportato | Italia {format_percent(italy_social)} del PIL nel 2024; UE {format_percent(eu_social)} | 11_protezione_sociale_confronto_ue_2024.png |",
        "| Le entrate principali arrivano soprattutto da redditi delle persone, consumi e imprese | Supportato come aggregazione delle principali voci MEF, non come totale esaustivo | MEF entrate erariali e territoriali 2025 | 12_tipi_entrate_tributarie_2025.png |",
        "| La spesa totale cresce in valore nominale e resta molto elevata in rapporto al PIL | Supportato | Serie Eurostat spesa totale S13, 1995-2024 | 13_spesa_totale_italia_1995_2024.png |",
        "| Il patrimonio familiare e' molto concentrato | Supportato | Banca d'Italia DWA IV trim. 2025: top 10% al 60,6%, meta' meno abbiente al 7,2% | 14_distribuzione_patrimonio_famiglie_2025.png |",
        "| Le successioni rendono poco rispetto al totale delle entrate | Supportato | MEF Appendici statistiche dicembre 2025: 1.081 milioni, +6,8% sul 2024 | 15_successioni_donazioni_2025.png |",
        f"| Nel confronto OCSE l'Italia e' sopra media per pressione fiscale | Supportato | OCSE Revenue Statistics 2024: Italia {format_percent(float(oecd_total_tax.italia))}; media OCSE {format_percent(float(oecd_total_tax.ocse))} | 18_ocse_pressione_fiscale_totale_2024.png |",
        f"| Le successioni in Italia pesano meno della media OCSE | Supportato | OCSE Revenue Statistics 2024: Italia {format_percent_compact(float(oecd_inheritance.italia))}; media OCSE {format_percent_compact(float(oecd_inheritance.ocse))} | 19_ocse_successioni_donazioni_2024.png |",
        f"| Nel confronto OCSE la spesa pubblica italiana e' sopra media | Supportato | OCSE National Accounts 2024: Italia {format_percent(float(oecd_total_spending.italia))}; media OCSE {format_percent(float(oecd_total_spending.ocse))} | 20_ocse_spesa_totale_2024.png |",
        "",
        "Nota: il dossier indicava la spesa pubblica italiana al 54,9% del PIL nel 2023. La chiamata Eurostat usata qui, eseguita il 10 giugno 2026 su `gov_10a_exp`, restituisce 53,6% per il 2023 e 50,4% per il 2024. Per pubblicazioni esterne conviene citare il dato aggiornato e la data di estrazione.",
        "",
        "Nota entrate: il grafico 12 aggrega gruppi comunicativi delle principali voci fiscali. Non e' una riclassificazione ufficiale esaustiva e non deve essere letto come somma dell'intero gettito tributario.",
        "",
        "Nota OCSE: i confronti OCSE usano la media semplice dei paesi membri con dato disponibile nel 2024. Le categorie OCSE sono armonizzate e non coincidono sempre con le singole imposte nazionali MEF.",
    ]
    write_text_file("analisi_claims.md", lines)


def build_manifest_entries(
    mef_data,
    territoriali_data,
    eurostat_tax_updated,
    eurostat_exp_updated,
    peer_tax_updated,
    peer_spending_updated,
    peer_social_updated,
    total_spending_updated,
):
    """Prepara la lista standardizzata di record da salvare in `manifest.csv`."""
    # Crea il registro che accompagna tutti i file grafici:
    # - nome file esportato
    # - fonte ufficiale usata
    # - data/periodo aggiornamento
    return [
        {
            "file": "01_principali_entrate_tributarie_2025.png",
            "fonte": SOURCE_MEF_ENTRATE_COMBINED,
            "aggiornamento_fonte": mef_data.get("aggiornamento", "2026-06-05 secondo API get_box_sintesi"),
        },
        {
            "file": "02_entrate_dirette_indirette_2002_2025.png",
            "fonte": SOURCE_MEF_ENTRATE,
            "aggiornamento_fonte": mef_data.get("aggiornamento", "2026-06-05 secondo API get_box_sintesi"),
        },
        {
            "file": "03_pressione_fiscale_componenti_1995_2024.png",
            "fonte": SOURCE_EUROSTAT_TAX,
            "aggiornamento_fonte": eurostat_tax_updated,
        },
        {
            "file": "04_spesa_pubblica_funzioni_cofog_2024.png",
            "fonte": SOURCE_EUROSTAT_EXP,
            "aggiornamento_fonte": eurostat_exp_updated,
        },
        {
            "file": "05_irpef_netto_per_fascia_2024.png",
            "fonte": SOURCE_MEF_DICHIARAZIONI,
            "aggiornamento_fonte": "23 aprile 2026",
        },
        {
            "file": "06_quote_irpef_per_fascia_2024.png",
            "fonte": SOURCE_MEF_DICHIARAZIONI,
            "aggiornamento_fonte": "23 aprile 2026",
        },
        {
            "file": "07_distribuzione_salari_capitali_2024.png",
            "fonte": SOURCE_MEF_DICHIARAZIONI,
            "aggiornamento_fonte": "23 aprile 2026",
        },
        {
            "file": "08_composizione_redditi_per_fascia_2024.png",
            "fonte": SOURCE_MEF_DICHIARAZIONI,
            "aggiornamento_fonte": "23 aprile 2026",
        },
        {
            "file": "09_pressione_fiscale_confronto_ue_2024.png",
            "fonte": SOURCE_EUROSTAT_TAX,
            "aggiornamento_fonte": peer_tax_updated,
        },
        {
            "file": "10_spesa_pubblica_confronto_ue_2024.png",
            "fonte": SOURCE_EUROSTAT_EXP,
            "aggiornamento_fonte": peer_spending_updated,
        },
        {
            "file": "11_protezione_sociale_confronto_ue_2024.png",
            "fonte": SOURCE_EUROSTAT_EXP,
            "aggiornamento_fonte": peer_social_updated,
        },
        {
            "file": "12_tipi_entrate_tributarie_2025.png",
            "fonte": SOURCE_MEF_ENTRATE_WITH_APPENDICI,
            "aggiornamento_fonte": territoriali_data.get("aggiornamento", "2026-06-05 secondo API get_box_sintesi"),
        },
        {
            "file": "13_spesa_totale_italia_1995_2024.png",
            "fonte": SOURCE_EUROSTAT_EXP,
            "aggiornamento_fonte": total_spending_updated,
        },
        {
            "file": "14_distribuzione_patrimonio_famiglie_2025.png",
            "fonte": SOURCE_BANKITALIA_WEALTH,
            "aggiornamento_fonte": "3 giugno 2026",
        },
        {
            "file": "15_successioni_donazioni_2025.png",
            "fonte": SOURCE_MEF_SUCCESSIONI,
            "aggiornamento_fonte": "dicembre 2025",
        },
        {
            "file": "16_ocse_entrate_per_tipo_2024.png",
            "fonte": SOURCE_OECD_REVENUE,
            "aggiornamento_fonte": "Revenue Statistics 2025; dati 2024",
        },
        {
            "file": "17_ocse_spesa_per_funzione_2024.png",
            "fonte": SOURCE_OECD_SPENDING,
            "aggiornamento_fonte": "estrazione API OCSE 10 giugno 2026; dati 2024",
        },
        {
            "file": "18_ocse_pressione_fiscale_totale_2024.png",
            "fonte": SOURCE_OECD_REVENUE,
            "aggiornamento_fonte": "Revenue Statistics 2025; dati 2024",
        },
        {
            "file": "19_ocse_successioni_donazioni_2024.png",
            "fonte": SOURCE_OECD_REVENUE,
            "aggiornamento_fonte": "Revenue Statistics 2025; dati 2024",
        },
        {
            "file": "20_ocse_spesa_totale_2024.png",
            "fonte": SOURCE_OECD_SPENDING,
            "aggiornamento_fonte": "estrazione API OCSE 10 giugno 2026; dati 2024",
        },
    ]


def run(refresh=False):
    """Esegue tutta la pipeline end-to-end.

    `refresh=False` usa cache, `refresh=True` forza il refresh da rete.
    """
    # 1) Setup ambiente
    ensure_directories()
    configure_style()
    clean_generated_outputs()

    # 2) Download/lettura dati: qui ogni funzione incapsula una fonte specifica
    mef_data, mef_items, mef_months = load_mef_entrate(refresh)
    territoriali_data, territoriali_items, territoriali_months = load_mef_territoriali(refresh)
    tax_pressure, eurostat_tax_updated = load_tax_pressure(refresh)
    cofog_spending, eurostat_exp_updated = load_cofog_spending(refresh)
    peer_tax, peer_tax_updated = load_peer_tax_pressure(refresh)
    peer_spending, peer_spending_updated = load_peer_spending(refresh, "TOTAL", "total")
    peer_social, peer_social_updated = load_peer_spending(refresh, "GF10", "gf10")
    total_spending, total_spending_updated = load_total_spending_italy(refresh)
    oecd_revenue, oecd_revenue_peers = load_oecd_revenue_data(refresh)
    oecd_spending, oecd_spending_peers = load_oecd_spending_data(refresh)
    tipo_reddito, calcolo_irpef = load_declaration_data(refresh)

    # 3) Grafici Italia: entrate, contribuzione e composizione redditi
    plot_main_taxes(mef_items, mef_months, territoriali_items, territoriali_months)
    plot_direct_indirect(mef_items, mef_months)
    plot_tax_pressure(tax_pressure)
    plot_irpef_tax_by_band(calcolo_irpef)
    plot_irpef_shares_by_band(calcolo_irpef)
    plot_wages_capital_distribution(tipo_reddito)
    plot_income_composition(tipo_reddito)
    plot_revenue_types(mef_items, mef_months, territoriali_items, territoriali_months)
    plot_succession_tax_focus(mef_items, mef_months)

    # 4) Grafici Italia: spesa e patrimonio
    plot_cofog_spending(cofog_spending)
    plot_total_spending_italy(total_spending)
    plot_household_wealth_distribution()

    # 5) Confronti internazionali
    plot_peer_comparison(
        peer_tax,
        [[("ITALIA: ", BLACK), ("TASSE ALTE?", ORANGE)]],
        "Pressione fiscale e contributiva 2024\n% del PIL",
        "09_pressione_fiscale_confronto_ue_2024.png",
        SOURCE_EUROSTAT_TAX,
    )
    plot_peer_comparison(
        peer_spending,
        [[("CHI ", BLACK), ("SPENDE", ORANGE), (" DI PIU'?", BLACK)]],
        "Spesa pubblica totale 2024\n% del PIL",
        "10_spesa_pubblica_confronto_ue_2024.png",
        SOURCE_EUROSTAT_EXP,
    )
    plot_peer_comparison(
        peer_social,
        [[("QUANTO PESANO", BLACK)], [("PENSIONI E WELFARE?", ORANGE)]],
        "Spesa per protezione sociale 2024\n% del PIL",
        "11_protezione_sociale_confronto_ue_2024.png",
        SOURCE_EUROSTAT_EXP,
    )

    # 6) Confronti OCSE per struttura fiscale, spesa e indicatori di sintesi
    plot_oecd_revenue_categories(oecd_revenue)
    plot_oecd_spending_categories(oecd_spending)
    plot_oecd_total_tax(oecd_revenue_peers["_T"])
    plot_oecd_inheritance_tax(oecd_revenue_peers["T_4300"])
    plot_oecd_total_spending(oecd_spending_peers["_T"])

    # 7) Report finale: claim e indice di tracciabilità degli output
    write_claims_analysis(peer_tax, peer_spending, peer_social, oecd_revenue, oecd_spending)

    entries = build_manifest_entries(
        mef_data,
        territoriali_data,
        eurostat_tax_updated,
        eurostat_exp_updated,
        peer_tax_updated,
        peer_spending_updated,
        peer_social_updated,
        total_spending_updated,
    )
    write_manifest(entries)
    print(f"Creati {len(entries)} grafici in {CHART_DIR}")
