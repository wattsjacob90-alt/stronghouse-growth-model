
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable
import math
import pandas as pd
import numpy as np


MONTHS = pd.date_range("2026-09-01", "2027-09-01", freq="MS")

DEFAULT_COMPANY_PATH = {
    "Sep-26": 4_000_000,
    "Oct-26": 4_100_000,
    "Nov-26": 4_200_000,
    "Dec-26": 4_000_000,
    "Jan-27": 3_800_000,
    "Feb-27": 3_900_000,
    "Mar-27": 4_200_000,
    "Apr-27": 5_000_000,
    "May-27": 6_100_000,
    "Jun-27": 7_400_000,
    "Jul-27": 8_900_000,
    "Aug-27": 125_000_000 / 12,
    "Sep-27": 125_000_000 / 12,
}

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
        ["Clubs", 0.50, 0.40, 0.25],
        ["PC, Referral, WOM", 0.70, 0.45, 0.15],
        ["Paid Search", 0.30, 0.35, 0.20],
        ["Paid Social", 0.20, 0.25, 0.10],
        ["Traditional", 0.50, 0.35, 0.10],
        ["Events", 0.30, 0.30, 0.10],
        ["JF / Exact / Porch", 0.25, 0.30, 0.10],
    ],
    columns=["Lead Channel", "Lead → Appt %", "Appt → Sale %", "Lead Mix"],
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
    labels = [d.strftime("%b-%y") for d in MONTHS]

    if shape == "Linear":
        vals = np.linspace(start_monthly, target_monthly, 12).tolist() + [target_monthly]
    elif shape == "Conservative":
        progress = [0, .01, .02, 0, -.03, -.02, .01, .08, .22, .40, .66, 1.0, 1.0]
        delta = target_monthly - start_monthly
        vals = [start_monthly + p * delta for p in progress]
    else:
        # Matches the agreed operating plan: flat 2026 / winter softness / Q2 acceleration.
        base_target = 125_000_000 / 12
        agreed = np.array([
            4_000_000, 4_100_000, 4_200_000, 4_000_000, 3_800_000, 3_900_000,
            4_200_000, 5_000_000, 6_100_000, 7_400_000, 8_900_000, base_target, base_target
        ], dtype=float)
        # Scale the agreed profile around the selected starting and ending values.
        denom = base_target - 4_000_000
        progress = (agreed - 4_000_000) / denom
        vals = [start_monthly + p * (target_monthly - start_monthly) for p in progress]

    return pd.DataFrame({"Month": MONTHS, "Revenue Target": vals})


def validate_inputs(markets: pd.DataFrame, channels: pd.DataFrame) -> list[str]:
    errors = []
    if markets["Exit Annual Revenue"].sum() <= 0:
        errors.append("Market exit revenue must be greater than zero.")
    if (markets["Average Ticket"] <= 0).any():
        errors.append("Average ticket must be greater than zero.")
    if (markets["Annual Revenue / Rep"] <= 0).any():
        errors.append("Revenue per rep must be greater than zero.")
    if channels["Lead Mix"].sum() <= 0:
        errors.append("Lead mix must sum to a positive number.")
    if (channels["Lead → Appt %"] <= 0).any() or (channels["Appt → Sale %"] <= 0).any():
        errors.append("Channel conversion rates must be greater than zero.")
    return errors


def allocate_market_revenue(
    path_df: pd.DataFrame,
    markets: pd.DataFrame,
    seasonality: pd.DataFrame,
) -> pd.DataFrame:
    """Allocate the company monthly plan to markets while respecting exit targets and seasonality."""
    markets = markets.copy()
    exit_monthly = markets.set_index("Market")["Exit Annual Revenue"] / 12
    start_monthly = markets.set_index("Market")["Starting Monthly Revenue"]

    # Use company-plan progress as the main growth driver.
    company_start = float(path_df.iloc[0]["Revenue Target"])
    company_exit = float(path_df.iloc[-2]["Revenue Target"])  # Aug-27
    denom = company_exit - company_start if abs(company_exit - company_start) > 1 else 1

    seas = seasonality.set_index("Month")
    rows = []
    for i, prow in path_df.iterrows():
        dt = pd.Timestamp(prow["Month"])
        target = float(prow["Revenue Target"])
        progress = max(-0.25, min(1.25, (target - company_start) / denom))
        month_key = dt.strftime("%b")

        raw = {}
        for _, m in markets.iterrows():
            market = m["Market"]
            region = m["Region"]
            base = float(start_monthly[market])
            exitv = float(exit_monthly[market])
            trend = base + progress * (exitv - base)

            if month_key in seas.index:
                factor = float(seas.loc[month_key, region])
                if market == "Florida":
                    factor *= float(seas.loc[month_key, "Florida Overlay"])
            else:
                factor = 1.0

            # Exit month is a hard target; other months use the seasonal trend.
            if dt.strftime("%b-%y") in ("Aug-27", "Sep-27"):
                raw[market] = exitv
            else:
                raw[market] = max(0, trend * factor)

        # Scale to the company monthly target so the plan reconciles exactly.
        raw_total = sum(raw.values()) or 1
        scale = target / raw_total
        for market, value in raw.items():
            rows.append({
                "Month": dt,
                "Market": market,
                "Revenue": value * scale,
            })

    return pd.DataFrame(rows)


def market_operating_plan(market_revenue: pd.DataFrame, markets: pd.DataFrame) -> pd.DataFrame:
    m = markets.set_index("Market")
    df = market_revenue.copy()
    df["Average Ticket"] = df["Market"].map(m["Average Ticket"])
    df["Annual Revenue / Rep"] = df["Market"].map(m["Annual Revenue / Rep"])
    df["Existing HC"] = df["Market"].map(m["Existing HC"])
    df["Sales"] = df["Revenue"] / df["Average Ticket"]
    df["Required HC"] = np.ceil(df["Revenue"] / (df["Annual Revenue / Rep"] / 12)).astype(int)

    planned = []
    additions = []
    for market, g in df.groupby("Market", sort=False):
        current = int(m.loc[market, "Existing HC"])
        prev = current
        for _, row in g.sort_values("Month").iterrows():
            req = int(row["Required HC"])
            new = max(prev, req)
            planned.append((row.name, new))
            additions.append((row.name, max(new - prev, 0)))
            prev = new
    planned_map = dict(planned)
    adds_map = dict(additions)
    df["Planned HC"] = [planned_map[i] for i in df.index]
    df["Monthly Adds"] = [adds_map[i] for i in df.index]
    return df


def lead_plan(monthly_market: pd.DataFrame, channels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly_sales = monthly_market.groupby("Month", as_index=False)["Sales"].sum()

    ch = channels.copy()
    mix_total = ch["Lead Mix"].sum()
    ch["Lead Mix"] = ch["Lead Mix"] / mix_total
    weighted_yield = (ch["Lead Mix"] * ch["Lead → Appt %"] * ch["Appt → Sale %"]).sum()

    rows = []
    summaries = []
    for _, mr in monthly_sales.iterrows():
        total_sales = float(mr["Sales"])
        total_leads = total_sales / weighted_yield
        total_appts = 0
        check_sales = 0
        for _, cr in ch.iterrows():
            leads = total_leads * cr["Lead Mix"]
            appts = leads * cr["Lead → Appt %"]
            sales = appts * cr["Appt → Sale %"]
            total_appts += appts
            check_sales += sales
            rows.append({
                "Month": mr["Month"],
                "Lead Channel": cr["Lead Channel"],
                "Leads": leads,
                "Appointments": appts,
                "Sales": sales,
                "Lead → Appt %": cr["Lead → Appt %"],
                "Appt → Sale %": cr["Appt → Sale %"],
                "Lead Mix": cr["Lead Mix"],
            })
        summaries.append({
            "Month": mr["Month"],
            "Sales": check_sales,
            "Appointments": total_appts,
            "Leads": total_leads,
        })
    return pd.DataFrame(rows), pd.DataFrame(summaries)


def build_model(
    target_annual: float,
    start_monthly: float,
    growth_shape: str,
    markets: pd.DataFrame,
    channels: pd.DataFrame,
    seasonality: pd.DataFrame,
    custom_path: pd.DataFrame | None = None,
) -> dict:
    path = custom_path.copy() if custom_path is not None else company_path(target_annual, start_monthly, growth_shape)
    market_rev = allocate_market_revenue(path, markets, seasonality)
    market_plan = market_operating_plan(market_rev, markets)
    channel_detail, funnel = lead_plan(market_plan, channels)

    monthly = (
        market_plan.groupby("Month", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Sales=("Sales", "sum"),
            Required_HC=("Required HC", "sum"),
            Planned_HC=("Planned HC", "sum"),
            Monthly_Adds=("Monthly Adds", "sum"),
        )
        .merge(funnel[["Month", "Appointments", "Leads"]], on="Month", how="left")
    )
    monthly["Annualized Run Rate"] = monthly["Revenue"] * 12
    monthly["Revenue / Planned Rep"] = monthly["Revenue"] * 12 / monthly["Planned_HC"].replace(0, np.nan)

    return {
        "company_path": path,
        "market_plan": market_plan,
        "channel_plan": channel_detail,
        "monthly": monthly,
    }
