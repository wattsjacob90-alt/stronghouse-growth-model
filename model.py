
from __future__ import annotations

import math
import numpy as np
import pandas as pd


MONTHS = pd.date_range("2026-09-01", "2027-09-01", freq="MS")

DEFAULT_MARKETS = pd.DataFrame(
    [
        ["Rhode Island", "Northeast", 20_000, 11, 1_250_000, 11_466_666.67, 550_000],
        ["Massachusetts", "Northeast", 20_000, 3, 1_250_000, 27_533_333.33, 1_310_000],
        ["Michigan", "Midwest", 18_000, 5, 1_250_000, 20_000_000.00, 430_000],
        ["Indiana", "Midwest", 20_000, 4, 1_250_000, 25_000_000.00, 415_000],
        ["Florida", "Southeast", 30_000, 4, 4_000_000, 36_000_000.00, 1_750_000],
        ["South Carolina", "Southeast", 18_000, 2, 1_250_000, 5_000_000.00, 120_000],
    ],
    columns=[
        "Market",
        "Region",
        "Average Ticket",
        "Existing HC",
        "Annual Revenue / Rep",
        "Exit Annual Revenue",
        "Starting Monthly Revenue",
    ],
)

DEFAULT_CHANNELS = pd.DataFrame(
    [
        ["Clubs", 0.50, 0.40, 0.00],
        ["PC, Referral, WOM", 0.70, 0.45, 0.20],
        ["Paid Search", 0.30, 0.35, 0.27],
        ["Paid Social", 0.20, 0.25, 0.13],
        ["Traditional", 0.50, 0.35, 0.13],
        ["Events", 0.30, 0.30, 0.13],
        ["JF / Exact / Porch", 0.25, 0.30, 0.14],
    ],
    columns=["Lead Channel", "Lead → Appt %", "Appt → Sale %", "Non-Club Lead Mix"],
)

# Starting defaults are deliberately editable. They are planning assumptions, not CRM actuals.
DEFAULT_CLUBS = pd.DataFrame(
    [
        ["Rhode Island", 4, 6, 10.0],
        ["Massachusetts", 16, 20, 10.0],
        ["Michigan", 4, 8, 10.0],
        ["Indiana", 3, 8, 10.0],
        ["Florida", 0, 8, 10.0],
        ["South Carolina", 0, 3, 10.0],
    ],
    columns=["Market", "Current Clubs", "Exit Clubs", "Leads / Club / Week"],
)

DEFAULT_SEASONALITY = pd.DataFrame(
    {
        "Month": ["Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug"],
        "Northeast": [1.00,1.02,1.00,0.78,0.68,0.72,0.90,1.00,1.05,1.08,1.08,1.00],
        "Midwest":   [1.00,1.02,1.00,0.85,0.78,0.81,0.93,1.00,1.04,1.06,1.06,1.00],
        "Southeast": [1.00,1.01,1.01,1.00,1.00,1.00,1.01,1.01,1.02,1.02,1.01,1.00],
        "Florida Overlay": [1.00,1.02,1.04,1.05,1.06,1.06,1.04,1.02,1.01,1.00,1.00,1.00],
    }
)


def company_path(target_annual: float, start_monthly: float, shape: str = "Q2 acceleration") -> pd.DataFrame:
    target_monthly = target_annual / 12
    if shape == "Linear":
        vals = np.linspace(start_monthly, target_monthly, 12).tolist() + [target_monthly]
    elif shape == "Conservative":
        progress = np.array([0, .01, .02, 0, -.03, -.02, .01, .07, .18, .34, .58, 1.0, 1.0])
        vals = (start_monthly + progress * (target_monthly - start_monthly)).tolist()
    else:
        # Agreed pacing: restrained through 2026/Q1, majority of growth from Q2 2027.
        base_target = 125_000_000 / 12
        agreed = np.array([
            4_000_000, 4_100_000, 4_200_000, 4_000_000, 3_800_000, 3_900_000,
            4_200_000, 5_000_000, 6_100_000, 7_400_000, 8_900_000, base_target, base_target
        ], dtype=float)
        progress = (agreed - 4_000_000) / (base_target - 4_000_000)
        vals = (start_monthly + progress * (target_monthly - start_monthly)).tolist()

    return pd.DataFrame({"Month": MONTHS, "Revenue Target": vals})


def validate_inputs(markets: pd.DataFrame, channels: pd.DataFrame, clubs: pd.DataFrame) -> list[str]:
    errors = []
    required_market_cols = {
        "Market","Region","Average Ticket","Existing HC","Annual Revenue / Rep",
        "Exit Annual Revenue","Starting Monthly Revenue"
    }
    if not required_market_cols.issubset(markets.columns):
        errors.append("Market table is missing one or more required columns.")
        return errors

    if (markets["Average Ticket"] <= 0).any():
        errors.append("Average ticket must be greater than zero.")
    if (markets["Annual Revenue / Rep"] <= 0).any():
        errors.append("Revenue per rep must be greater than zero.")
    if (markets["Existing HC"] < 0).any():
        errors.append("Existing headcount cannot be negative.")
    if channels["Lead → Appt %"].le(0).any() or channels["Appt → Sale %"].le(0).any():
        errors.append("Channel conversion rates must be greater than zero.")
    nonclub = channels[channels["Lead Channel"] != "Clubs"]
    if nonclub["Non-Club Lead Mix"].sum() <= 0:
        errors.append("Non-club lead mix must sum to a positive number.")
    if (clubs[["Current Clubs","Exit Clubs","Leads / Club / Week"]] < 0).any().any():
        errors.append("Club assumptions cannot be negative.")
    missing = set(markets["Market"]) - set(clubs["Market"])
    if missing:
        errors.append("Club assumptions are missing for: " + ", ".join(sorted(missing)))
    return errors


def allocate_market_revenue(path_df: pd.DataFrame, markets: pd.DataFrame, seasonality: pd.DataFrame) -> pd.DataFrame:
    markets = markets.copy()
    exit_monthly = markets.set_index("Market")["Exit Annual Revenue"] / 12
    start_monthly = markets.set_index("Market")["Starting Monthly Revenue"]

    company_start = float(path_df.iloc[0]["Revenue Target"])
    company_exit = float(path_df[path_df["Month"] == pd.Timestamp("2027-08-01")].iloc[0]["Revenue Target"])
    denom = company_exit - company_start if abs(company_exit - company_start) > 1 else 1
    seas = seasonality.set_index("Month")

    rows = []
    for _, prow in path_df.iterrows():
        dt = pd.Timestamp(prow["Month"])
        target = float(prow["Revenue Target"])
        progress = max(-0.25, min(1.25, (target - company_start) / denom))
        month_key = dt.strftime("%b")
        raw = {}

        for _, m in markets.iterrows():
            market, region = m["Market"], m["Region"]
            base = float(start_monthly[market])
            exitv = float(exit_monthly[market])
            trend = base + progress * (exitv - base)

            factor = float(seas.loc[month_key, region]) if month_key in seas.index else 1.0
            if market == "Florida" and month_key in seas.index:
                factor *= float(seas.loc[month_key, "Florida Overlay"])

            if dt in (pd.Timestamp("2027-08-01"), pd.Timestamp("2027-09-01")):
                raw[market] = exitv
            else:
                raw[market] = max(0.0, trend * factor)

        raw_total = sum(raw.values()) or 1
        scale = target / raw_total
        for market, value in raw.items():
            rows.append({"Month": dt, "Market": market, "Revenue": value * scale})

    return pd.DataFrame(rows)


def _company_progress(path_df: pd.DataFrame) -> dict[pd.Timestamp, float]:
    start = float(path_df.iloc[0]["Revenue Target"])
    aug = float(path_df[path_df["Month"] == pd.Timestamp("2027-08-01")].iloc[0]["Revenue Target"])
    denom = aug - start if abs(aug - start) > 1 else 1
    return {
        pd.Timestamp(r["Month"]): max(0.0, min(1.0, (float(r["Revenue Target"]) - start) / denom))
        for _, r in path_df.iterrows()
    }


def club_schedule(
    path_df: pd.DataFrame,
    clubs: pd.DataFrame,
    club_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
    progress = _company_progress(path_df)
    override_map = {}
    if club_overrides is not None and not club_overrides.empty:
        tmp = club_overrides.copy()
        tmp["Month"] = pd.to_datetime(tmp["Month"])
        override_map = {
            (pd.Timestamp(r["Month"]), r["Market"]): float(r["Planned Clubs"])
            for _, r in tmp.iterrows()
            if pd.notna(r.get("Planned Clubs"))
        }

    rows = []
    for _, c in clubs.iterrows():
        for dt in path_df["Month"]:
            dt = pd.Timestamp(dt)
            p = 1.0 if dt >= pd.Timestamp("2027-08-01") else progress[dt]
            calculated = float(c["Current Clubs"]) + p * (float(c["Exit Clubs"]) - float(c["Current Clubs"]))
            active = override_map.get((dt, c["Market"]), calculated)
            rows.append({
                "Month": dt,
                "Market": c["Market"],
                "Planned Clubs": active,
                "Leads / Club / Week": float(c["Leads / Club / Week"]),
                "Club Leads": active * float(c["Leads / Club / Week"]) * 52 / 12,
            })
    return pd.DataFrame(rows)


def market_funnel_plan(
    market_revenue: pd.DataFrame,
    markets: pd.DataFrame,
    channels: pd.DataFrame,
    clubs: pd.DataFrame,
    path_df: pd.DataFrame,
    club_overrides: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build required funnel backwards from revenue, using clubs as a capacity-driven channel."""
    market_map = markets.set_index("Market")
    ch = channels.copy()
    club_row = ch[ch["Lead Channel"] == "Clubs"].iloc[0]
    nonclub = ch[ch["Lead Channel"] != "Clubs"].copy()
    nonclub["Norm Mix"] = nonclub["Non-Club Lead Mix"] / nonclub["Non-Club Lead Mix"].sum()
    nonclub_yield = (nonclub["Norm Mix"] * nonclub["Lead → Appt %"] * nonclub["Appt → Sale %"]).sum()

    club_df = club_schedule(path_df, clubs, club_overrides)
    rows, market_rows = [], []

    for _, mr in market_revenue.iterrows():
        dt, market, revenue = pd.Timestamp(mr["Month"]), mr["Market"], float(mr["Revenue"])
        ticket = float(market_map.loc[market, "Average Ticket"])
        sales_required = revenue / ticket

        cinfo = club_df[(club_df["Month"] == dt) & (club_df["Market"] == market)].iloc[0]
        club_leads = float(cinfo["Club Leads"])
        club_appts = club_leads * float(club_row["Lead → Appt %"])
        club_sales = club_appts * float(club_row["Appt → Sale %"])

        remaining_sales = max(sales_required - club_sales, 0.0)
        nonclub_leads_total = remaining_sales / nonclub_yield if nonclub_yield > 0 else 0.0

        rows.append({
            "Month": dt, "Market": market, "Lead Channel": "Clubs",
            "Leads": club_leads, "Appointments": club_appts, "Sales": club_sales,
            "Lead → Appt %": float(club_row["Lead → Appt %"]),
            "Appt → Sale %": float(club_row["Appt → Sale %"]),
            "Lead Mix": np.nan, "Planned Clubs": float(cinfo["Planned Clubs"]),
        })

        total_leads, total_appts, total_sales = club_leads, club_appts, club_sales
        for _, cr in nonclub.iterrows():
            leads = nonclub_leads_total * float(cr["Norm Mix"])
            appts = leads * float(cr["Lead → Appt %"])
            sales = appts * float(cr["Appt → Sale %"])
            total_leads += leads
            total_appts += appts
            total_sales += sales
            rows.append({
                "Month": dt, "Market": market, "Lead Channel": cr["Lead Channel"],
                "Leads": leads, "Appointments": appts, "Sales": sales,
                "Lead → Appt %": float(cr["Lead → Appt %"]),
                "Appt → Sale %": float(cr["Appt → Sale %"]),
                "Lead Mix": float(cr["Norm Mix"]), "Planned Clubs": np.nan,
            })

        market_rows.append({
            "Month": dt, "Market": market, "Revenue": revenue,
            "Sales Required": sales_required,
            "Leads": total_leads,
            "Appointments": total_appts,
            "Funnel Sales": total_sales,
            "Club Sales": club_sales,
            "Club Sales Surplus": max(club_sales - sales_required, 0.0),
        })

    return pd.DataFrame(rows), pd.DataFrame(market_rows)


def headcount_plan(
    market_funnel: pd.DataFrame,
    markets: pd.DataFrame,
    hiring_lead_time: int,
    appts_per_rep_day: float,
    selling_days_week: float,
    utilization: float,
) -> pd.DataFrame:
    market_map = markets.set_index("Market")
    df = market_funnel.copy()
    df["Existing HC"] = df["Market"].map(market_map["Existing HC"]).astype(int)
    df["Annual Revenue / Rep"] = df["Market"].map(market_map["Annual Revenue / Rep"])
    df["Revenue HC"] = np.ceil(df["Revenue"] / (df["Annual Revenue / Rep"] / 12)).astype(int)

    monthly_appt_capacity = appts_per_rep_day * selling_days_week * 52 / 12 * utilization
    df["Appointment Capacity / Rep"] = monthly_appt_capacity
    df["Appointment HC"] = np.ceil(df["Appointments"] / monthly_appt_capacity).astype(int)
    df["Required HC"] = df[["Revenue HC", "Appointment HC"]].max(axis=1)

    planned_map, adds_map = {}, {}
    for market, g in df.groupby("Market", sort=False):
        prev = int(market_map.loc[market, "Existing HC"])
        for idx, row in g.sort_values("Month").iterrows():
            req = int(row["Required HC"])
            planned = max(prev, req)
            planned_map[idx] = planned
            adds_map[idx] = max(planned - prev, 0)
            prev = planned

    df["Planned HC"] = [planned_map[i] for i in df.index]
    df["Productive Adds"] = [adds_map[i] for i in df.index]
    df["Recruit By"] = [
        (pd.Timestamp(m) - pd.DateOffset(months=hiring_lead_time)) if adds > 0 else pd.NaT
        for m, adds in zip(df["Month"], df["Productive Adds"])
    ]
    df["Capacity Status"] = np.where(
        df["Appointment HC"] > df["Revenue HC"],
        "Lead/appointment demand exceeds revenue-productivity HC",
        np.where(
            df["Revenue HC"] > df["Appointment HC"] + 2,
            "Revenue productivity requires more HC than appointment demand",
            "Aligned",
        ),
    )
    return df


def build_model(
    target_annual: float,
    start_monthly: float,
    growth_shape: str,
    markets: pd.DataFrame,
    channels: pd.DataFrame,
    clubs: pd.DataFrame,
    seasonality: pd.DataFrame,
    hiring_lead_time: int = 2,
    appts_per_rep_day: float = 2.0,
    selling_days_week: float = 5.0,
    utilization: float = 0.85,
    custom_path: pd.DataFrame | None = None,
    club_overrides: pd.DataFrame | None = None,
) -> dict:
    path = custom_path.copy() if custom_path is not None else company_path(target_annual, start_monthly, growth_shape)
    market_rev = allocate_market_revenue(path, markets, seasonality)
    channel_plan, market_funnel = market_funnel_plan(
        market_rev, markets, channels, clubs, path, club_overrides
    )
    hc = headcount_plan(
        market_funnel, markets, hiring_lead_time,
        appts_per_rep_day, selling_days_week, utilization,
    )

    monthly = (
        hc.groupby("Month", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Sales=("Sales Required", "sum"),
            Appointments=("Appointments", "sum"),
            Leads=("Leads", "sum"),
            Revenue_HC=("Revenue HC", "sum"),
            Appointment_HC=("Appointment HC", "sum"),
            Required_HC=("Required HC", "sum"),
            Planned_HC=("Planned HC", "sum"),
            Productive_Adds=("Productive Adds", "sum"),
        )
    )
    monthly["Annualized Run Rate"] = monthly["Revenue"] * 12
    monthly["Revenue / Planned Rep"] = monthly["Revenue"] * 12 / monthly["Planned_HC"].replace(0, np.nan)

    # Recruiting plan is grouped by the month recruiting/onboarding must begin.
    recruiting = (
        hc.dropna(subset=["Recruit By"])
        .groupby(["Recruit By", "Market"], as_index=False)["Productive Adds"].sum()
        .rename(columns={"Productive Adds": "Reps to Recruit"})
    )

    return {
        "company_path": path,
        "market_revenue": market_rev,
        "channel_plan": channel_plan,
        "market_funnel": market_funnel,
        "headcount_plan": hc,
        "monthly": monthly,
        "recruiting_plan": recruiting,
        "club_schedule": club_schedule(path, clubs, club_overrides),
    }


def scenario_comparison(
    target_annual: float,
    start_monthly: float,
    growth_shape: str,
    markets: pd.DataFrame,
    channels: pd.DataFrame,
    clubs: pd.DataFrame,
    seasonality: pd.DataFrame,
    hiring_lead_time: int,
    appts_per_rep_day: float,
    selling_days_week: float,
    utilization: float,
    club_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
    scenarios = [
        ("Conservative", 0.90, 0.90),
        ("Base", 1.00, 1.00),
        ("Upside", 1.10, 1.10),
    ]
    rows = []
    for name, conv_mult, productivity_mult in scenarios:
        c = channels.copy()
        c["Lead → Appt %"] = (c["Lead → Appt %"] * conv_mult).clip(upper=0.95)
        c["Appt → Sale %"] = (c["Appt → Sale %"] * conv_mult).clip(upper=0.80)
        m = markets.copy()
        m["Annual Revenue / Rep"] = m["Annual Revenue / Rep"] * productivity_mult
        res = build_model(
            target_annual, start_monthly, growth_shape, m, c, clubs, seasonality,
            hiring_lead_time, appts_per_rep_day, selling_days_week, utilization,
            club_overrides=club_overrides,
        )
        aug = res["monthly"][res["monthly"]["Month"] == pd.Timestamp("2027-08-01")].iloc[0]
        rows.append({
            "Scenario": name,
            "Annualized Run Rate": aug["Annualized Run Rate"],
            "Monthly Leads": aug["Leads"],
            "Monthly Appointments": aug["Appointments"],
            "Planned HC": aug["Planned_HC"],
            "Incremental HC": aug["Planned_HC"] - markets["Existing HC"].sum(),
        })
    return pd.DataFrame(rows)
