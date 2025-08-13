import os
import io
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import datetime, timedelta
from dateutil import parser as dateparser

from finance_ai import (
    default_category_rules,
    categorize_transactions,
    generate_insights,
    answer_question,
)

st.set_page_config(page_title="AI Powered Finance Manager", page_icon="💰", layout="wide")

st.title("AI Powered Finance Manager")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload a CSV of transactions", type=["csv"])
    st.caption("Required columns  Date  Description  Amount. Amount negative for outflow and positive for inflow")

    st.header("Budgets per category")
    budgets = {}
    for cat in ["Groceries", "Dining", "Transport", "Utilities", "Shopping", "Entertainment", "Health", "Housing", "Income", "Other"]:
        budgets[cat] = st.number_input(f"{cat} monthly budget", min_value=0.0, value=0.0, step=10.0)

    st.header("Rules")
    st.caption("Add keyword rules. Example  Groceries  walmart kroger aldi")
    new_rule = st.text_input("Category and keywords separated by spaces")
    add_rule = st.button("Add rule")

if "rules" not in st.session_state:
    st.session_state.rules = default_category_rules()

if add_rule and new_rule.strip():
    parts = new_rule.strip().split()
    if len(parts) >= 2:
        cat = parts[0]
        kws = parts[1:]
        st.session_state.rules.setdefault(cat, [])
        for k in kws:
            if k.lower() not in st.session_state.rules[cat]:
                st.session_state.rules[cat].append(k.lower())
        st.success(f"Added rule for {cat}")

if uploaded is not None:
    df = pd.read_csv(uploaded)
    expected = {"Date", "Description", "Amount"}
    missing = expected - set(df.columns)
    if missing:
        st.error(f"Missing columns  {', '.join(missing)}")
        st.stop()

    # Clean and normalize
    def parse_date(x):
        try:
            return dateparser.parse(str(x)).date()
        except Exception:
            return pd.NaT

    df["Date"] = df["Date"].apply(parse_date)
    df = df.dropna(subset=["Date"]).copy()
    df["Description"] = df["Description"].astype(str)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    df["Month"] = df["Date"].apply(lambda d: pd.Timestamp(d).to_period("M").to_timestamp())

    # Categorize
    df = categorize_transactions(df, st.session_state.rules)

    # Summary top cards
    col1, col2, col3, col4 = st.columns(4)
    total_out = df.loc[df["Amount"] < 0, "Amount"].sum()
    total_in = df.loc[df["Amount"] > 0, "Amount"].sum()
    col1.metric("Total outflow", f"${-total_out:,.2f}")
    col2.metric("Total inflow", f"${total_in:,.2f}")
    this_month = pd.Timestamp(datetime.today().strftime("%Y-%m-01"))
    m_out = df[(df["Month"] == this_month) & (df["Amount"] < 0)]["Amount"].sum()
    col3.metric("This month spend", f"${-m_out:,.2f}")
    unique_merchants = df["Normalized"].nunique()
    col4.metric("Unique merchants", f"{unique_merchants}")

    # Charts
    st.subheader("Spending by category")
    spend = df[df["Amount"] < 0].copy()
    spend["AbsAmount"] = spend["Amount"].abs()
    by_cat = spend.groupby("Category", as_index=False)["AbsAmount"].sum().sort_values("AbsAmount", ascending=False)
    if not by_cat.empty:
        chart = alt.Chart(by_cat).mark_arc().encode(theta="AbsAmount", color="Category", tooltip=["Category", "AbsAmount"])
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No spending rows found")

    st.subheader("Trend by month")
    by_month = spend.groupby("Month", as_index=False)["AbsAmount"].sum()
    line = alt.Chart(by_month).mark_line(point=True).encode(x="Month:T", y="AbsAmount:Q", tooltip=["Month", "AbsAmount"])
    st.altair_chart(line, use_container_width=True)

    # Budget status
    st.subheader("Budget status for this month")
    cur = spend[spend["Month"] == this_month]
    cat_month = cur.groupby("Category", as_index=False)["AbsAmount"].sum()
    cat_month["Budget"] = cat_month["Category"].map(budgets).fillna(0.0)
    cat_month["Over"] = cat_month["AbsAmount"] - cat_month["Budget"]
    st.dataframe(cat_month.rename(columns={"AbsAmount": "Spend"}))

    # Insights
    st.subheader("Insights")
    insights = generate_insights(df, budgets)
    for s in insights:
        st.write("• " + s)

    # Natural language questions
    st.subheader("Ask a question")
    q = st.text_input("Example  How much did I spend on groceries last month")
    if st.button("Answer") and q.strip():
        ans = answer_question(df, q.strip(), budgets=budgets)
        st.success(ans)

    # Manual recategorization
    st.subheader("Fix categories and export")
    st.caption("Click a cell to edit the category then download the cleaned CSV")
    edit_cols = ["Date", "Description", "Amount", "Category"]
    edited = st.data_editor(df[edit_cols], num_rows="dynamic", use_container_width=True)
    if st.download_button("Download cleaned CSV", data=edited.to_csv(index=False).encode("utf-8"), file_name="cleaned_transactions.csv"):
        st.toast("Downloaded")
else:
    st.info("Upload a CSV to begin")