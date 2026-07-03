"""Orchestratore completo del progetto.

Il flusso è sempre questo:
1) impostazione ambienti (cartelle, stile grafici, pulizia output vecchi)
2) caricamento dati dalle fonti
3) produzione dei grafici italiani
4) produzione dei confronti UE/OECD
5) scrittura manifest e JSON dashboard
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
from bilancio_pubblico.chart_generation.regioni import (
    clean_regional_outputs,
    plot_regional_balances_by_region,
    plot_regional_revenue_by_region,
    plot_regional_spending_by_mission,
    plot_regional_spending_by_region,
)
from bilancio_pubblico.data_extraction import (
    load_cofog_spending,
    load_cofog_spending_trend,
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
from bilancio_pubblico.exporter import export_bilancio_source_json
from bilancio_pubblico.regional_budgets import (
    SOURCE_OPENBDAP_REGIONI,
    append_regional_budgets_to_source_json,
    load_regional_budgets,
)
from bilancio_pubblico.utils import (
    BLACK,
    CHART_DIR,
    clean_generated_outputs,
    configure_style,
    ensure_directories,
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
)


def build_manifest_entries(
    mef_data,
    territoriali_data,
    eurostat_tax_updated,
    eurostat_exp_updated,
    peer_tax_updated,
    peer_spending_updated,
    peer_social_updated,
    total_spending_updated,
    regional_outputs=None,
    regional_updated=None,
):
    """Prepara la lista standardizzata di record da salvare in `manifest.csv`."""
    # Crea il registro che accompagna tutti i file grafici:
    # - nome file esportato
    # - fonte ufficiale usata
    # - data/periodo aggiornamento
    entries = [
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

    for filename in regional_outputs or []:
        entries.append(
            {
                "file": filename,
                "fonte": SOURCE_OPENBDAP_REGIONI,
                "aggiornamento_fonte": regional_updated or "OpenBDAP/RGS",
            }
        )

    return entries


def run(refresh=False):
    """Esegue tutta la pipeline end-to-end.

    `refresh=False` usa cache, `refresh=True` forza il refresh da rete.
    """
    # 1) Setup ambiente
    ensure_directories()
    configure_style()
    clean_generated_outputs()
    clean_regional_outputs()

    # 2) Download/lettura dati: qui ogni funzione incapsula una fonte specifica
    mef_data, mef_items, mef_months = load_mef_entrate(refresh)
    territoriali_data, territoriali_items, territoriali_months = load_mef_territoriali(refresh)
    tax_pressure, eurostat_tax_updated = load_tax_pressure(refresh)
    cofog_spending, eurostat_exp_updated = load_cofog_spending(refresh)
    cofog_spending_trend, _cofog_spending_trend_updated = load_cofog_spending_trend(refresh)
    peer_tax, peer_tax_updated = load_peer_tax_pressure(refresh)
    peer_spending, peer_spending_updated = load_peer_spending(refresh, "TOTAL", "total")
    peer_social, peer_social_updated = load_peer_spending(refresh, "GF10", "gf10")
    total_spending, total_spending_updated = load_total_spending_italy(refresh)
    oecd_revenue, oecd_revenue_peers = load_oecd_revenue_data(refresh)
    oecd_spending, oecd_spending_peers = load_oecd_spending_data(refresh)
    tipo_reddito, calcolo_irpef = load_declaration_data(refresh)
    regional_budgets = load_regional_budgets(refresh)

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

    # 4) Grafici Italia: spesa, patrimonio e bilanci regionali
    plot_cofog_spending(cofog_spending)
    plot_total_spending_italy(total_spending)
    plot_household_wealth_distribution()

    regional_outputs = [
        filename
        for filename in (
            plot_regional_spending_by_region(regional_budgets["spending_by_region"]),
            plot_regional_revenue_by_region(regional_budgets["revenue_by_region"]),
            plot_regional_spending_by_mission(regional_budgets["spending_by_mission"]),
            plot_regional_balances_by_region(regional_budgets["balances_by_region"]),
        )
        if filename
    ]

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

    # 7) Report finale: manifest grafici e dati normalizzati
    entries = build_manifest_entries(
        mef_data,
        territoriali_data,
        eurostat_tax_updated,
        eurostat_exp_updated,
        peer_tax_updated,
        peer_spending_updated,
        peer_social_updated,
        total_spending_updated,
        regional_outputs=regional_outputs,
        regional_updated=regional_budgets.get("updated"),
    )
    export_bilancio_source_json(
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
        source_updates={
            "eurostat_tax": eurostat_tax_updated,
            "eurostat_exp": eurostat_exp_updated,
            "peer_tax": peer_tax_updated,
            "peer_spending": peer_spending_updated,
            "peer_social": peer_social_updated,
            "total_spending": total_spending_updated,
            "regional_budgets": regional_budgets.get("updated"),
        },
        manifest_rows=entries,
    )
    append_regional_budgets_to_source_json(regional_budgets, manifest_rows=entries)
    write_manifest(entries)
    print(f"Creati {len(entries)} grafici in {CHART_DIR}")
