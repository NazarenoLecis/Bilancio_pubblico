"""Funzioni di estrazione per fonti e serie nazionali italiane."""

from utils_bilancio.generali.data_extraction import (
    add_income_bands,
    aggregate_columns_by_band,
    collect_mef_items,
    find_mef_item,
    income_band,
    income_lower_bound,
    load_cofog_spending,
    load_cofog_spending_detail,
    load_cofog_spending_trend,
    load_declaration_data,
    load_mef_entrate,
    load_mef_territoriali,
    load_tax_pressure,
    load_total_spending_italy,
    mef_annual_series,
    mef_monthly_series,
    numeric_column,
    parse_mef_start,
)

