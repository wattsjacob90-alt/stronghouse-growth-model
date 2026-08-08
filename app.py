
import json
import pandas as pd
import streamlit as st
from model import (
    DEFAULT_MARKETS,
    DEFAULT_CHANNELS,
    DEFAULT_SEASONALITY,
    company_path,
    build_model,
    validate_inputs,
)

st.set_page_config(page_title="Stronghouse Growth Model", page_icon="📈", layout="wide")

st.title("Stronghouse Revenue Growth Model")
st.caption("Experiment with the path to a Q3 2027 annual run rate target using market revenue, lead-channel conversion, and sales headcount.")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Scenario")
    scenario_name = st.text_input("Scenario name", "Base Plan")
    target_annual = st.number_input(
        "Q3 2027 annual run rate target",
        min_value=50_000_000,
        max_value=250_000_000,
        value=125_000_000,
        step=5_000_000,
        format="%d",
    )
    start_monthly = st.number_input(
        "September 2026 monthly revenue",
        min_value=1_000_000,
        max_value=20_000_000,
        value=4_000_000,
        step=100_000,
        format="%d",
    )
    growth_shape = st.selectbox("Growth shape", ["Q2 acceleration", "Linear", "Conservative"])
    hiring_lead_time = st.slider("Hiring lead time (months)", 0, 4, 2)

    st.divider()
    st.metric("Target monthly run rate", f"${target_annual/12/1e6:,.2f}M")
    st.metric("Starting monthly revenue", f"${start_monthly/1e6:,.2f}M")

# ---------- Editable assumptions ----------
st.subheader("Assumptions")
assump_tabs = st.tabs(["Markets", "Lead channels", "Seasonality", "Revenue path"])

with assump_tabs[0]:
    markets = st.data_editor(
        DEFAULT_MARKETS,
        use_container_width=True,
        num_rows="dynamic",
        key="markets",
        column_config={
            "Average Ticket": st.column_config.NumberColumn(format="$%d"),
            "Existing HC": st.column_config.NumberColumn(format="%d"),
            "Annual Revenue / Rep": st.column_config.NumberColumn(format="$%d"),
            "Exit Annual Revenue": st.column_config.NumberColumn(format="$%d"),
            "Starting Monthly Revenue": st.column_config.NumberColumn(format="$%d"),
        },
    )
    st.caption("Exit annual revenue should sum to the company annual run-rate target. Florida is intentionally modeled at $4M annual revenue per rep.")

with assump_tabs[1]:
    channels = st.data_editor(
        DEFAULT_CHANNELS,
        use_container_width=True,
        num_rows="dynamic",
        key="channels",
        column_config={
            "Lead → Appt %": st.column_config.NumberColumn(format="%.0f%%", min_value=0.01, max_value=1.0),
            "Appt → Sale %": st.column_config.NumberColumn(format="%.0f%%", min_value=0.01, max_value=1.0),
            "Lead Mix": st.column_config.NumberColumn(format="%.0f%%", min_value=0.0, max_value=1.0),
        },
    )
    st.caption("Lead mix is automatically normalized to 100% in the calculation engine.")

with assump_tabs[2]:
    seasonality = st.data_editor(
        DEFAULT_SEASONALITY,
        use_container_width=True,
        key="seasonality",
        column_config={
            "Northeast": st.column_config.NumberColumn(format="%.2fx"),
            "Midwest": st.column_config.NumberColumn(format="%.2fx"),
            "Southeast": st.column_config.NumberColumn(format="%.2fx"),
            "Florida Overlay": st.column_config.NumberColumn(format="%.2fx"),
        },
    )
    st.caption("Northeast carries the deepest Dec–Feb trough, Midwest a moderate trough, and the Southeast is more stable.")

with assump_tabs[3]:
    generated_path = company_path(target_annual, start_monthly, growth_shape)
    editable_path = generated_path.copy()
    editable_path["Month"] = editable_path["Month"].dt.strftime("%b-%y")
    edited_path = st.data_editor(
        editable_path,
        use_container_width=True,
        key=f"path_{growth_shape}_{target_annual}_{start_monthly}",
        column_config={"Revenue Target": st.column_config.NumberColumn(format="$%d")},
    )
    custom_path = edited_path.copy()
    custom_path["Month"] = pd.to_datetime(custom_path["Month"], format="%b-%y")

errors = validate_inputs(markets, channels)
market_target_total = float(markets["Exit Annual Revenue"].sum())

if abs(market_target_total - target_annual) > 100_000:
    st.warning(
        f"Market exit targets sum to ${market_target_total/1e6:,.1f}M, "
        f"while the company target is ${target_annual/1e6:,.1f}M. "
        "The monthly model will still reconcile to the company target, but the exit market mix should be reviewed."
    )
if errors:
    for e in errors:
        st.error(e)
    st.stop()

results = build_model(
    target_annual=target_annual,
    start_monthly=start_monthly,
    growth_shape=growth_shape,
    markets=markets,
    channels=channels,
    seasonality=seasonality,
    custom_path=custom_path,
)

monthly = results["monthly"].copy()
market_plan = results["market_plan"].copy()
channel_plan = results["channel_plan"].copy()

# ---------- Dashboard ----------
st.divider()
st.subheader("Executive dashboard")

aug = monthly[monthly["Month"] == pd.Timestamp("2027-08-01")].iloc[0]
current_hc = int(markets["Existing HC"].sum())
target_hc = int(aug["Planned_HC"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Aug-27 monthly revenue", f"${aug['Revenue']/1e6:,.2f}M")
c2.metric("Annualized run rate", f"${aug['Annualized Run Rate']/1e6:,.0f}M")
c3.metric("Monthly leads", f"{aug['Leads']:,.0f}")
c4.metric("Monthly appointments", f"{aug['Appointments']:,.0f}")
c5.metric("Planned sales HC", f"{target_hc}", delta=f"+{target_hc-current_hc} vs. today")

chart_df = monthly.set_index("Month")[["Revenue"]].copy()
chart_df["Revenue"] = chart_df["Revenue"] / 1e6
st.line_chart(chart_df, y_label="Monthly revenue ($M)", x_label="Month", height=350)

dashboard_tabs = st.tabs(["Monthly operating plan", "Market plan", "Lead engine", "Headcount"])

with dashboard_tabs[0]:
    display = monthly.copy()
    display["Month"] = display["Month"].dt.strftime("%b-%y")
    display["Revenue"] = display["Revenue"].map(lambda x: f"${x/1e6:,.2f}M")
    display["Annualized Run Rate"] = display["Annualized Run Rate"].map(lambda x: f"${x/1e6:,.1f}M")
    display["Revenue / Planned Rep"] = display["Revenue / Planned Rep"].map(lambda x: f"${x/1e6:,.2f}M")
    for c in ["Sales","Appointments","Leads"]:
        display[c] = display[c].round(0).astype(int)
    st.dataframe(
        display[[
            "Month","Revenue","Annualized Run Rate","Sales","Appointments","Leads",
            "Required_HC","Planned_HC","Monthly_Adds","Revenue / Planned Rep"
        ]],
        use_container_width=True,
        hide_index=True,
    )

with dashboard_tabs[1]:
    aug_market = market_plan[market_plan["Month"] == pd.Timestamp("2027-08-01")].copy()
    aug_market["Annualized Revenue"] = aug_market["Revenue"] * 12
    aug_market["HC Gap vs Today"] = (aug_market["Planned HC"] - aug_market["Existing HC"]).clip(lower=0)
    show = aug_market[[
        "Market","Revenue","Annualized Revenue","Average Ticket","Existing HC","Required HC","Planned HC","HC Gap vs Today"
    ]].copy()
    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="$%d"),
            "Annualized Revenue": st.column_config.NumberColumn(format="$%d"),
            "Average Ticket": st.column_config.NumberColumn(format="$%d"),
        },
    )
    bar = show.set_index("Market")[["Annualized Revenue"]] / 1e6
    st.bar_chart(bar, y_label="Annualized revenue ($M)", height=320)

with dashboard_tabs[2]:
    aug_channels = channel_plan[channel_plan["Month"] == pd.Timestamp("2027-08-01")].copy()
    for c in ["Leads","Appointments","Sales"]:
        aug_channels[c] = aug_channels[c].round(0).astype(int)
    st.dataframe(
        aug_channels[[
            "Lead Channel","Leads","Appointments","Sales","Lead → Appt %","Appt → Sale %","Lead Mix"
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Lead → Appt %": st.column_config.NumberColumn(format="%.0f%%"),
            "Appt → Sale %": st.column_config.NumberColumn(format="%.0f%%"),
            "Lead Mix": st.column_config.NumberColumn(format="%.0f%%"),
        },
    )
    st.bar_chart(
        aug_channels.set_index("Lead Channel")[["Leads"]],
        y_label="Required monthly leads",
        height=320,
    )

with dashboard_tabs[3]:
    hc_month = monthly[["Month","Required_HC","Planned_HC","Monthly_Adds"]].copy()
    hc_month = hc_month.set_index("Month")
    st.line_chart(hc_month[["Required_HC","Planned_HC"]], y_label="Sales headcount", height=320)

    adds = market_plan.pivot_table(
        index="Month", columns="Market", values="Monthly Adds", aggfunc="sum", fill_value=0
    )
    st.caption(f"Hiring lead-time assumption: {hiring_lead_time} months. Use this table to pull recruiting activity forward.")
    st.dataframe(adds.astype(int), use_container_width=True)

# ---------- Scenario comparison ----------
st.divider()
st.subheader("Scenario comparison")

if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []

if st.button("Save current scenario"):
    st.session_state.saved_scenarios.append({
        "Scenario": scenario_name,
        "Aug-27 Annual Run Rate": float(aug["Annualized Run Rate"]),
        "Aug-27 Leads": float(aug["Leads"]),
        "Aug-27 Appointments": float(aug["Appointments"]),
        "Aug-27 Planned HC": int(aug["Planned_HC"]),
        "Incremental HC": int(aug["Planned_HC"] - current_hc),
    })

if st.session_state.saved_scenarios:
    comp = pd.DataFrame(st.session_state.saved_scenarios)
    st.dataframe(
        comp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Aug-27 Annual Run Rate": st.column_config.NumberColumn(format="$%d"),
            "Aug-27 Leads": st.column_config.NumberColumn(format="%.0f"),
            "Aug-27 Appointments": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    if st.button("Clear saved scenarios"):
        st.session_state.saved_scenarios = []
        st.rerun()

# ---------- Downloads ----------
st.divider()
st.subheader("Export")
col1, col2, col3 = st.columns(3)
with col1:
    st.download_button(
        "Download monthly plan CSV",
        monthly.to_csv(index=False).encode("utf-8"),
        file_name="monthly_operating_plan.csv",
        mime="text/csv",
    )
with col2:
    st.download_button(
        "Download market plan CSV",
        market_plan.to_csv(index=False).encode("utf-8"),
        file_name="market_plan.csv",
        mime="text/csv",
    )
with col3:
    st.download_button(
        "Download lead plan CSV",
        channel_plan.to_csv(index=False).encode("utf-8"),
        file_name="lead_channel_plan.csv",
        mime="text/csv",
    )
