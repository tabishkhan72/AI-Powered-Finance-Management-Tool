# AI Powered Finance Manager

A simple personal finance app built with Streamlit. Upload a CSV of transactions and get automatic categorization, budgets, charts, and smart insights. Ask questions in natural language and export a cleaned CSV.

## Features

1. Upload a CSV with Date Description Amount
2. Auto categorize spending and income using editable keyword rules
3. Dashboard cards for inflow outflow monthly spend and unique merchants
4. Charts for spend by category and a monthly trend
5. Budgets per category with status for the current month
6. Insights such as recurring subscriptions budget alerts and unusual spend
7. Ask free form questions such as How much did I spend on groceries last month
8. Fix categories in a table and download a cleaned CSV

## Quick start

1. Ensure Python 3 dot 10 or newer is installed
2. Create and activate a virtual environment if you wish
3. Install the libraries listed in requirements txt using your preferred package manager
4. Run the app

```bash
streamlit run app.py
```

5. Open the local URL that Streamlit prints
6. Use the sample CSV in the repo to try it out

## CSV format

Required columns

1. Date
2. Description
3. Amount  negative for spend positive for income

The app detects month from the Date column and normalizes Description text for matching.

## Categorization rules

Rules map categories to keyword lists. You can add rules in the sidebar. The default set includes examples for Groceries Dining Transport Utilities Shopping Entertainment Health Housing Income and Other.

Matching is case insensitive and uses simple substring checks.

## Budgets

Set a monthly budget per category in the sidebar. The app compares current month spend with your budgets and calls out any overage.

## Insights

The app computes

1. Top spend categories
2. Possible recurring subscriptions from repeated merchants at similar amounts
3. Unusual spend inside a category using a simple Z score
4. Budget alerts for the current month

## Ask a question

Type a plain English question such as

```text
How much did I spend on groceries in July
What is my income last month
Net total for July
```

The app parses category and time range and then returns a concise answer.

## Edit and export

Use the data editor to correct categories. When ready use the download button to save a cleaned CSV.

## Project layout

1. app.py  Streamlit UI and charts
2. finance_ai.py  rules categorization insights and Q and A logic
3. requirements.txt  Python libraries
4. sample_transactions.csv  sample data for a quick demo

## Development notes

1. The app uses pandas numpy altair and python dateutil
2. All charts are built with Altair
3. The insights module flags recurring charges and outliers with simple heuristics

## Privacy and security

All data stays on your machine during local use. Do not upload private data to shared servers unless you have reviewed the setup and risks.
