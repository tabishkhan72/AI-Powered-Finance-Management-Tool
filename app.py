import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from dateutil import parser as dateparser
from finance_ai import default_category_rules, categorize_transactions, generate_insights, answer_question

# ---------------- CONFIG ----------------
CATEGORIES = ["Groceries", "Dining", "Transport", "Utilities", "Shopping", 
              "Entertainment", "Health", "Housing", "Income", "Other"]
REQUIRED_COLUMNS = {"Date", "Description", "Amount"}

st.set_page_config(page_title="AI Powered Finance Manager", page_icon="💰", layout="wide")
st.title("AI Powered Finance Manager")

# ---------------- HELPERS ----------------
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

def preprocess_data(df):
    def parse_date(x):
        try:
            return dateparser.parse(str(x)).date()
        except Exception:
            return pd.NaT

    df["Date"] = df["Date"].apply(parse_date)
    df = df.dropna(subset=["Date"]).copy()
    df["Description"] = df["Description"].astype(str)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    df["Month"] = pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    return df

def budget_status(df, budgets, this_month):
    spend = df[(df["Month"] == this_month) & (df["Amount"] < 0)].copy()
    spend["AbsAmount"] = spend["Amount"].abs()
    by_cat = spend.groupby("Category", as_index=False)["AbsAmount"].sum()
    by_cat["Budget"] = by_cat["Category"].map(budgets).fillna(0.0)
    by_cat["Over"] = by_cat["AbsAmount"] - by_cat["Budget"]
    return by_cat

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("Data Upload")
    uploaded = st.file_uploader("Upload a CSV of transactions", type=["csv"])
    st.caption("Required columns: Date, Description, Amount (negative for spend, positive for income)")

    st.header("Budgets")
    budgets = {cat: st.number_input(f"{cat} budget", min_value=0.0, value=0.0, step=10.0) for cat in CATEGORIES}

    st.header("Rules")
    if "rules" not in st.session_state:
        st.session_state.rules = default_category_rules()

    new_rule = st.text_input("Add rule (Category keywords...)")
    if st.button("Add rule") and new_rule.strip():
        parts = new_rule.strip().split()
        if len(parts) >= 2:
            cat, kws = parts[0], parts[1:]
            st.session_state.rules.setdefault(cat, [])
            for k in kws:
                if k.lower() not in st.session_state.rules[cat]:
                    st.session_state.rules[cat].append(k.lower())
            st.success(f"Added rule for {cat}")

# ---------------- MAIN APP ----------------
if uploaded:
    df = load_data(uploaded)
    if df is not None:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
            st.stop()

        df = preprocess_data(df)
        df = categorize_transactions(df, st.session_state.rules)

        # KPI Cards
        st.subheader("Overview")
        col1, col2, col3, col4 = st.columns(4)
        total_out = df.loc[df["Amount"] < 0, "Amount"].sum()
        total_in = df.loc[df["Amount"] > 0, "Amount"].sum()
        this_month = pd.Timestamp(datetime.today().strftime("%Y-%m-01"))
        m_out = df[(df["Month"] == this_month) & (df["Amount"] < 0)]["Amount"].sum()
        col1.metric("Total Outflow", f"${-total_out:,.2f}")
        col2.metric("Total Inflow", f"${total_in:,.2f}")
        col3.metric("This Month Spend", f"${-m_out:,.2f}")
        col4.metric("Unique Merchants", df["Normalized"].nunique())

        # Tabs for better navigation
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Charts", "💵 Budgets", "💡 Insights", "🤖 Q&A", "📤 Export"])

        with tab1:
            st.subheader("Spending by Category")
            spend = df[df["Amount"] < 0].copy()
            spend["AbsAmount"] = spend["Amount"].abs()
            by_cat = spend.groupby("Category", as_index=False)["AbsAmount"].sum().sort_values("AbsAmount", ascending=False)
            if not by_cat.empty:
                chart = alt.Chart(by_cat).mark_arc().encode(
                    theta="AbsAmount", color="Category", tooltip=["Category", "AbsAmount"]
                )
                st.altair_chart(chart, use_container_width=True)

            st.subheader("Trend by Month")
            by_month = spend.groupby("Month", as_index=False)["AbsAmount"].sum()
            line = alt.Chart(by_month).mark_line(point=True).encode(
                x="Month:T", y="AbsAmount:Q", tooltip=["Month", "AbsAmount"]
            )
            st.altair_chart(line, use_container_width=True)

        with tab2:
            st.subheader("Budget Status")
            cat_month = budget_status(df, budgets, this_month)
            st.dataframe(cat_month.rename(columns={"AbsAmount": "Spend"}))

        with tab3:
            st.subheader("AI Insights")
            for s in generate_insights(df, budgets):
                st.write("• " + s)

        with tab4:
            st.subheader("Ask a Question")
            q = st.text_input("Example: How much did I spend on groceries last month?")
            if st.button("Get Answer") and q.strip():
                st.success(answer_question(df, q.strip(), budgets=budgets))

        with tab5:
            st.subheader("Fix Categories & Export")
            edit_cols = ["Date", "Description", "Amount", "Category"]
            edited = st.data_editor(df[edit_cols], num_rows="dynamic", use_container_width=True)
            st.download_button("Download cleaned CSV", data=edited.to_csv(index=False).encode("utf-8"),
                               file_name="cleaned_transactions.csv")
else:
    st.info("⬆️ Upload a CSV to begin")
