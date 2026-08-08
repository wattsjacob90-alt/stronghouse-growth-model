
# Stronghouse Growth Model — Web App

This Streamlit app is the simplified operating model for experimenting with the path to a **$125M annual revenue run rate by Q3 2027**.

## Current default planning assumptions

- September 2026 revenue: **$4.0M**
- Majority of growth begins in **Q2 2027**
- August 2027 monthly run rate: **$10.42M**
- Rhode Island HC: **11**
- Massachusetts HC: **3**
- Michigan HC: **5**
- Indiana HC: **4**
- Florida HC: **4**
- South Carolina HC: **2**
- Indiana exit target: **$25M annualized**
- Michigan exit target: **$20M annualized**
- Florida exit target: **$36M annualized**
- South Carolina exit target: **$5M annualized**
- Florida productivity: **$4M revenue / rep / year**
- Other markets: **$1.25M revenue / rep / year**

## What changed in this version

### Clubs are capacity-driven
Club leads are now calculated from:

`Planned Clubs × Leads per Club per Week × 52 / 12`

Each market has editable:
- Current club count
- Exit club count
- Leads per club per week

Club leads are calculated first. The model then solves for the non-club leads needed to close the remaining sales gap.

### Hiring is calendar-based
The app distinguishes:
- Revenue-productivity headcount
- Appointment-capacity headcount
- Required headcount
- Planned headcount
- Productive additions
- Recruit-by month

The recruit-by month is shifted earlier using the editable hiring lead-time assumption.

### Capacity warnings
The app flags markets where:
- Appointment demand requires more reps than the revenue-productivity model, or
- Revenue-productivity staffing is materially higher than appointment demand.

### Scenario comparison
The app automatically compares:
- Conservative: 10% lower conversions and rep productivity
- Base
- Upside: 10% higher conversions and rep productivity

The revenue target stays constant so the comparison shows the operational impact on leads, appointments, and headcount.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown by Streamlit, normally `http://localhost:8501`.

## Update the deployed Streamlit app

If your app is connected to GitHub:

1. Replace `app.py`, `model.py`, `README.md`, and `requirements.txt` in the GitHub repository with the files from this package.
2. Commit the changes.
3. Streamlit Community Cloud should redeploy automatically.
4. If it does not, open the app settings and choose **Reboot app**.

The Main file path should remain:

`app.py`

## Files

- `app.py` — user interface
- `model.py` — calculation engine and default assumptions
- `requirements.txt` — Python dependencies
- `Dockerfile` — optional container deployment
- `.streamlit/config.toml` — Streamlit configuration

## Important planning note

The club-count defaults are planning assumptions. Replace them with actual active partner locations when available. The app is designed so those inputs can be updated without changing code.
