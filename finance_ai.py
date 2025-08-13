import os
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def default_category_rules():
    return {
        "Groceries": ["walmart", "aldi", "kroger", "whole foods", "safeway", "instacart"],
        "Dining": ["mcdonald", "burger king", "kfc", "chipotle", "starbucks", "ubereats", "doordash"],
        "Transport": ["uber", "lyft", "shell", "chevron", "exxon", "bp", "metro"],
        "Utilities": ["comcast", "xfinity", "verizon", "atandt", "electric", "water", "gas bill"],
        "Shopping": ["amazon", "target", "best buy", "walmart.com", "costco"],
        "Entertainment": ["netflix", "spotify", "hulu", "steam", "playstation"],
        "Health": ["cvs", "walgreens", "rite aid", "pharmacy", "dental", "clinic"],
        "Housing": ["rent", "mortgage", "landlord"],
        "Income": ["payroll", "salary", "direct deposit", "stripe", "paypal"],
        "Other": []
    }

def normalize_text(s):
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def categorize_row(desc, amount, rules):
    text = normalize_text(desc)
    # Income classification
    if amount > 0:
        for kw in rules.get("Income", []):
            if kw in text:
                return "Income", text
        return "Income", text
    # Expense
    for cat, kws in rules.items():
        if cat == "Income":
            continue
        for kw in kws:
            if kw in text:
                return cat, text
    return "Other", text

def categorize_transactions(df, rules):
    cats = []
    norms = []
    for d, a in zip(df["Description"], df["Amount"]):
        cat, norm = categorize_row(d, a, rules)
        cats.append(cat)
        norms.append(norm)
    out = df.copy()
    out["Category"] = cats
    out["Normalized"] = norms
    return out

def detect_recurring(df, min_months=3):
    exp = df[df["Amount"] < 0].copy()
    exp["Abs"] = exp["Amount"].abs()
    # group by normalized merchant and round amount to nearest dollar
    exp["Rounded"] = exp["Abs"].round(0)
    key = exp.groupby(["Normalized", "Rounded"])["Month"].nunique()
    rec = key[key >= min_months].reset_index().sort_values("Normalized")
    return rec

def detect_anomalies(df):
    exp = df[df["Amount"] < 0].copy()
    if exp.empty:
        return pd.DataFrame(columns=df.columns.tolist() + ["Z"])
    exp["Abs"] = exp["Amount"].abs()
    res = []
    for cat, grp in exp.groupby("Category"):
        if len(grp) < 5:
            continue
        mean = grp["Abs"].mean()
        std = grp["Abs"].std(ddof=0) or 1.0
        z = (grp["Abs"] - mean) / std
        flagged = grp[z > 2.5].copy()
        flagged["Z"] = z[z > 2.5]
        res.append(flagged)
    if res:
        return pd.concat(res).sort_values("Z", ascending=False)
    return pd.DataFrame(columns=df.columns.tolist() + ["Z"])

def month_range(label, today=None):
    today = today or datetime.today().date()
    label = label.lower()
    if label == "last month":
        first = datetime(today.year, today.month, 1).date()
        last_month_last_day = first - timedelta(days=1)
        first_last = datetime(last_month_last_day.year, last_month_last_day.month, 1).date()
        return first_last, last_month_last_day
    # Named month like July or Jul
    months = ["january","february","march","april","may","june","july","august","september","october","november","december"]
    short = [m[:3] for m in months]
    if label in months or label in short:
        idx = months.index(label) if label in months else short.index(label)
        year = today.year
        first = datetime(year, idx+1, 1).date()
        if idx+1 == 12:
            end = datetime(year+1, 1, 1).date() - timedelta(days=1)
        else:
            end = datetime(year, idx+2, 1).date() - timedelta(days=1)
        return first, end
    return None, None

def generate_insights(df, budgets):
    insights = []

    spend = df[df["Amount"] < 0].copy()
    spend["Abs"] = spend["Amount"].abs()
    if not spend.empty:
        top = spend.groupby("Category")["Abs"].sum().sort_values(ascending=False).head(3)
        items = [f"{c} ${v:,.0f}" for c, v in top.items()]
        insights.append("Top spending categories  " + ", ".join(items))

        # Budget overages for current month
        cur_month = pd.Timestamp(datetime.today().strftime("%Y-%m-01"))
        cur = spend[spend["Month"] == cur_month]
        if not cur.empty:
            agg = cur.groupby("Category")["Abs"].sum()
            over = []
            for c, val in agg.items():
                b = budgets.get(c, 0.0) or 0.0
                if b > 0 and val > b:
                    over.append(f"{c} over by ${val-b:,.0f}")
            if over:
                insights.append("Budget alerts  " + ", ".join(over))

        # Recurring
        rec = detect_recurring(df)
        if not rec.empty:
            names = rec["Normalized"].head(5).tolist()
            insights.append("Possible recurring subscriptions  " + ", ".join(names))

        # Anomalies
        an = detect_anomalies(df)
        if not an.empty:
            row = an.iloc[0]
            insights.append(f"Unusual spend  {row['Description']} for ${abs(row['Amount']):,.0f} in {row['Category']}")
    else:
        insights.append("No spending rows found")

    return insights

def answer_question(df, question, budgets=None):
    # Simple parser for questions like
    # How much did I spend on groceries in July
    q = question.lower()
    # category
    cats = df["Category"].unique().tolist()
    cats_lower = {c.lower(): c for c in cats}
    cat_hit = None
    for c in cats_lower:
        if c in q:
            cat_hit = cats_lower[c]
            break
    # time
    when = None
    if "last month" in q:
        when = "last month"
    else:
        for m in ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",
                  "january","february","march","april","may","june","july","august","september","october","november","december"]:
            if m in q:
                when = m
                break

    subset = df.copy()
    if cat_hit:
        subset = subset[subset["Category"].str.lower() == cat_hit.lower()]
    if when:
        start, end = month_range(when)
        if start and end:
            subset = subset[(subset["Date"] >= start) & (subset["Date"] <= end)]
    # compute answer
    spend = subset[subset["Amount"] < 0]["Amount"].sum()
    income = subset[subset["Amount"] > 0]["Amount"].sum()
    if "spend" in q or "spent" in q or "cost" in q:
        return f"You spent ${-spend:,.2f}"
    if "income" in q or "earn" in q or "made" in q:
        return f"Income ${income:,.2f}"
    total = income + spend
    return f"Net total ${total:,.2f}"