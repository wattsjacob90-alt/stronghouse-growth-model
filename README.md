
# Stronghouse Growth Model

A lightweight Streamlit app for experimenting with the operating plan to reach a Q3 2027 annual revenue run rate.

## What the app models

- Company monthly revenue ramp
- Market-level annualized revenue targets
- Seasonality by region
- Average ticket by market
- Existing sales headcount
- Revenue productivity per rep
- Lead mix by channel
- Lead-to-appointment conversion by channel
- Appointment-to-sale conversion by channel
- Required leads, appointments, sales, and sales headcount
- Monthly hiring additions
- Side-by-side saved scenario comparison

The default model reflects the latest planning assumptions:

- Q3 2027 target: **$125M annualized**
- September 2026 revenue: **$4.0M**
- Q2 2027 growth acceleration
- Rhode Island HC: **11**
- Massachusetts HC: **3**
- Michigan HC: **5**
- Indiana HC: **4**
- Florida HC: **4**
- South Carolina HC: **2**
- Florida target: **$36M annualized**
- Florida productivity: **$4M revenue / rep / year**
- Indiana target: **$25M annualized**
- Michigan target: **$20M annualized**
- South Carolina target: **$5M annualized**

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the app in your browser, normally at `http://localhost:8501`.

## Deploy quickly

### Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py`, `model.py`, and `requirements.txt`.
3. In Streamlit Community Cloud, create a new app from the repository.
4. Set the app entrypoint to `app.py`.
5. Deploy.

### Internal deployment

The app has no external service dependencies and can also be hosted in Docker, Azure, AWS, GCP, Render, Railway, or an internal VM.

## Recommended next additions

- Password / SSO authentication
- Persisted scenarios in a database
- CRM actual-vs-plan imports
- Club-count modeling by market
- Marketing spend / CPL by lead channel
- Gross margin and EBITDA layer
- Export scenarios back to Excel
