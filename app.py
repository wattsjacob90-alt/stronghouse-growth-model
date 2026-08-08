
import pandas as pd
import streamlit as st

from model import (
    DEFAULT_MARKETS,
    DEFAULT_CHANNELS,
    DEFAULT_CLUBS,
    DEFAULT_SEASONALITY,
    company_path,
    build_model,
    scenario_comparison,
    validate_inputs,
)

st.set_page_config(page_title="Stronghouse Growth Model", page_icon="📈", layout="wide")
st.title("Stronghouse Revenue Growth Model")
st.caption("Experiment with the path to a Q3 2027 annual revenue run rate using market targets, leads by channel, club growth, and sales headcount.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Company scenario")
    target_annual = st.number_input(
        "Q3 2027 annual run rate target",
        min_value=50_000_000, max_value=250_000_000,
        value=125_000_000, step=5_000_000, format="%d",
    )
    start_monthly = st.number_input(
        "September 2026 revenue",
        min_value=1_000_000, max_value=20_000_000,
        value=4_000_000, step=100_000, format="%d",
    )
    growth_shape = st.selectbox("Revenue pacing", ["Q2 acceleration", "Linear", "Conservative"])

    st.header("Sales capacity")
    hiring_lead_time = st.slider("Hiring lead time (months)", 0, 4, 2)
    appts_per_rep_day = st.number_input("Appointments / rep / day", 0.5, 5.0, 2.0, 0.25)
    selling_days_week = st.number_input("Selling days / week", 3.0, 7.0, 5.0, 0.5)
    utilization = st.slider("Rep utilization", 0.50, 1.00, 0.85, 0.05)

    st.divider()
    st.metric("Target monthly run rate", f"${target_annual/12/1e6:,.2f}M")

# ---------------- Assumptions ----------------
st.subheader("Operating assumptions")
tabs = st.tabs(["Markets", "Lead channels", "Clubs", "Seasonality", "Revenue path"])

with tabs[0]:
    markets = st.data_editor(
        DEFAULT_MARKETS,
        use_container_width=True,
        num_rows="dynamic",
        key="markets_v2",
        column_config={
            "Average Ticket": st.column_config.NumberColumn(format="$%d"),
            "Existing HC": st.column_config.NumberColumn(format="%d"),
            "Annual Revenue / Rep": st.column_config.NumberColumn(format="$%d"),
            "Exit Annual Revenue": st.column_config.NumberColumn(format="$%d"),
            "Starting Monthly Revenue": st.column_config.NumberColumn(format="$%d"),
        },
    )
    total_market_target = float(markets["Exit Annual Revenue"].sum())
    st.caption(f"Market exit targets currently total ${total_market_target/1e6:,.1f}M annualized.")

with tabs[1]:
    channels = st.data_editor(
        DEFAULT_CHANNELS,
        use_container_width=True,
        num_rows="dynamic",
        key="channels_v2",
        column_config={
            "Lead → Appt %": st.column_config.NumberColumn(format="%.0f%%", min_value=0.01, max_value=1.0),
            "Appt → Sale %": st.column_config.NumberColumn(format="%.0f%%", min_value=0.01, max_value=1.0),
            "Non-Club Lead Mix": st.column_config.NumberColumn(format="%.0f%%", min_value=0.0, max_value=1.0),
        },
    )
    st.caption("Clubs are no longer modeled as a percentage of lead mix. Club leads are driven from club count × leads per club per week.")

with tabs[2]:
    clubs = st.data_editor(
        DEFAULT_CLUBS,
        use_container_width=True,
        num_rows="dynamic",
        key="clubs_v2",
        column_config={
            "Current Clubs": st.column_config.NumberColumn(format="%.0f"),
            "Exit Clubs": st.column_config.NumberColumn(format="%.0f"),
            "Leads / Club / Week": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.info("Club count ramps with the company growth curve. Change Exit Clubs to test B2B partnership expansion by market.")

with tabs[3]:
    seasonality = st.data_editor(
        DEFAULT_SEASONALITY,
        use_container_width=True,
        key="seasonality_v2",
        column_config={
            "Northeast": st.column_config.NumberColumn(format="%.2fx"),
            "Midwest": st.column_config.NumberColumn(format="%.2fx"),
            "Southeast": st.column_config.NumberColumn(format="%.2fx"),
            "Florida Overlay": st.column_config.NumberColumn(format="%.2fx"),
        },
    )

with tabs[4]:
    generated_path = company_path(target_annual, start_monthly, growth_shape)
    editable_path = generated_path.copy()
    editable_path["Month"] = editable_path["Month"].dt.strftime("%b-%y")
    edited_path = st.data_editor(
        editable_path,
        use_container_width=True,
        key=f"path_v2_{growth_shape}_{target_annual}_{start_monthly}",
        column_config={"Revenue Target": st.column_config.NumberColumn(format="$%d")},
    )
    custom_path = edited_path.copy()
    custom_path["Month"] = pd.to_datetime(custom_path["Month"], format="%b-%y")

errors = validate_inputs(markets, channels, clubs)
if abs(float(markets["Exit Annual Revenue"].sum()) - target_annual) > 100_000:
    st.warning(
        f"Market exit targets total ${markets['Exit Annual Revenue'].sum()/1e6:,.1f}M versus "
        f"the ${target_annual/1e6:,.1f}M company target. The monthly plan reconciles to the company target, "
        "but review the exit market mix."
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
    clubs=clubs,
    seasonality=seasonality,
    hiring_lead_time=hiring_lead_time,
    appts_per_rep_day=appts_per_rep_day,
    selling_days_week=selling_days_week,
    utilization=utilization,
    custom_path=custom_path,
)

monthly = results["monthly"]
market_funnel = results["market_funnel"]
channel_plan = results["channel_plan"]
headcount = results["headcount_plan"]
recruiting = results["recruiting_plan"]
club_schedule = results["club_schedule"]

# ---------------- Executive Dashboard ----------------
st.divider()
st.subheader("Executive dashboard")

aug = monthly[monthly["Month"] == pd.Timestamp("2027-08-01")].iloc[0]
current_hc = int(markets["Existing HC"].sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Aug-27 monthly revenue", f"${aug['Revenue']/1e6:,.2f}M")
c2.metric("Annualized run rate", f"${aug['Annualized Run Rate']/1e6:,.0f}M")
c3.metric("Monthly leads", f"{aug['Leads']:,.0f}")
c4.metric("Monthly appointments", f"{aug['Appointments']:,.0f}")
c5.metric("Planned sales HC", f"{int(aug['Planned_HC'])}", delta=f"+{int(aug['Planned_HC'])-current_hc} vs. today")

chart = monthly.set_index("Month")[["Revenue"]] / 1e6
st.line_chart(chart, y_label="Monthly revenue ($M)", x_label="Month", height=330)

# Capacity warning
aug_hc = headcount[headcount["Month"] == pd.Timestamp("2027-08-01")]
warnings = aug_hc[aug_hc["Capacity Status"] != "Aligned"]
if not warnings.empty:
    with st.expander("Capacity checks requiring review", expanded=True):
        st.dataframe(
            warnings[["Market","Revenue HC","Appointment HC","Required HC","Capacity Status"]],
            use_container_width=True, hide_index=True,
        )

dash_tabs = st.tabs(["Monthly plan", "Market funnel", "Lead engine", "Headcount & hiring", "Club growth", "Scenario comparison"])

with dash_tabs[0]:
    d = monthly.copy()
    d["Month"] = d["Month"].dt.strftime("%b-%y")
    st.dataframe(
        d,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="$%d"),
            "Annualized Run Rate": st.column_config.NumberColumn(format="$%d"),
            "Revenue / Planned Rep": st.column_config.NumberColumn(format="$%d"),
            "Sales": st.column_config.NumberColumn(format="%.0f"),
            "Appointments": st.column_config.NumberColumn(format="%.0f"),
            "Leads": st.column_config.NumberColumn(format="%.0f"),
        },
    )

with dash_tabs[1]:
    aug_market = headcount[headcount["Month"] == pd.Timestamp("2027-08-01")].copy()
    aug_market["Annualized Revenue"] = aug_market["Revenue"] * 12
    aug_market["HC Gap vs Today"] = (aug_market["Planned HC"] - aug_market["Existing HC"]).clip(lower=0)
    st.dataframe(
        aug_market[[
            "Market","Revenue","Annualized Revenue","Sales Required","Leads","Appointments",
            "Existing HC","Revenue HC","Appointment HC","Required HC","Planned HC","HC Gap vs Today"
        ]],
        use_container_width=True, hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="$%d"),
            "Annualized Revenue": st.column_config.NumberColumn(format="$%d"),
            "Sales Required": st.column_config.NumberColumn(format="%.0f"),
            "Leads": st.column_config.NumberColumn(format="%.0f"),
            "Appointments": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.bar_chart(
        aug_market.set_index("Market")[["Annualized Revenue"]] / 1e6,
        y_label="Annualized revenue ($M)", height=300,
    )

with dash_tabs[2]:
    month_choice = st.selectbox(
        "Lead plan month",
        options=list(monthly["Month"]),
        index=11,
        format_func=lambda x: pd.Timestamp(x).strftime("%b-%y"),
    )
    month_channels = (
        channel_plan[channel_plan["Month"] == month_choice]
        .groupby("Lead Channel", as_index=False)
        .agg(Leads=("Leads","sum"), Appointments=("Appointments","sum"), Sales=("Sales","sum"))
    )
    st.dataframe(
        month_channels,
        use_container_width=True, hide_index=True,
        column_config={
            "Leads": st.column_config.NumberColumn(format="%.0f"),
            "Appointments": st.column_config.NumberColumn(format="%.0f"),
            "Sales": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.bar_chart(month_channels.set_index("Lead Channel")[["Leads"]], y_label="Required leads", height=300)

    st.caption("Detailed market-by-channel requirement")
    detail = channel_plan[channel_plan["Month"] == month_choice].copy()
    st.dataframe(
        detail[["Market","Lead Channel","Leads","Appointments","Sales","Planned Clubs"]],
        use_container_width=True, hide_index=True,
        column_config={
            "Leads": st.column_config.NumberColumn(format="%.0f"),
            "Appointments": st.column_config.NumberColumn(format="%.0f"),
            "Sales": st.column_config.NumberColumn(format="%.0f"),
            "Planned Clubs": st.column_config.NumberColumn(format="%.1f"),
        },
    )

with dash_tabs[3]:
    hc_chart = monthly.set_index("Month")[["Required_HC","Planned_HC"]]
    st.line_chart(hc_chart, y_label="Sales headcount", height=300)

    st.markdown("**Productive headcount by market**")
    hc_view = headcount[[
        "Month","Market","Existing HC","Revenue HC","Appointment HC","Required HC",
        "Planned HC","Productive Adds","Recruit By","Capacity Status"
    ]].copy()
    hc_view["Month"] = hc_view["Month"].dt.strftime("%b-%y")
    hc_view["Recruit By"] = hc_view["Recruit By"].dt.strftime("%b-%y")
    st.dataframe(hc_view, use_container_width=True, hide_index=True)

    st.markdown("**Recruiting / onboarding calendar**")
    if recruiting.empty:
        st.success("No incremental recruiting required under this scenario.")
    else:
        rec = recruiting.copy()
        rec["Recruit By"] = rec["Recruit By"].dt.strftime("%b-%y")
        st.dataframe(rec, use_container_width=True, hide_index=True)

with dash_tabs[4]:
    club_month = st.selectbox(
        "Club plan month",
        options=list(monthly["Month"]),
        index=11,
        format_func=lambda x: pd.Timestamp(x).strftime("%b-%y"),
        key="club_month",
    )
    club_view = club_schedule[club_schedule["Month"] == club_month].copy()
    st.dataframe(
        club_view,
        use_container_width=True, hide_index=True,
        column_config={
            "Planned Clubs": st.column_config.NumberColumn(format="%.1f"),
            "Leads / Club / Week": st.column_config.NumberColumn(format="%.1f"),
            "Club Leads": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.bar_chart(club_view.set_index("Market")[["Club Leads"]], y_label="Monthly club leads", height=300)

with dash_tabs[5]:
    comparison = scenario_comparison(
        target_annual, start_monthly, growth_shape,
        markets, channels, clubs, seasonality,
        hiring_lead_time, appts_per_rep_day, selling_days_week, utilization,
    )
    st.dataframe(
        comparison,
        use_container_width=True, hide_index=True,
        column_config={
            "Annualized Run Rate": st.column_config.NumberColumn(format="$%d"),
            "Monthly Leads": st.column_config.NumberColumn(format="%.0f"),
            "Monthly Appointments": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.caption("Conservative = 10% lower conversions/productivity. Upside = 10% higher conversions/productivity. Revenue target is held constant.")

# ---------------- Exports ----------------
st.divider()
st.subheader("Export current scenario")
a,b,c,d = st.columns(4)
with a:
    st.download_button("Monthly plan CSV", monthly.to_csv(index=False).encode(), "monthly_plan.csv", "text/csv")
with b:
    st.download_button("Market headcount CSV", headcount.to_csv(index=False).encode(), "market_headcount.csv", "text/csv")
with c:
    st.download_button("Lead plan CSV", channel_plan.to_csv(index=False).encode(), "lead_plan.csv", "text/csv")
with d:
    st.download_button("Recruiting plan CSV", recruiting.to_csv(index=False).encode(), "recruiting_plan.csv", "text/csv")
