import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Meta Ads Intelligence", layout="wide")

st.title("Meta Ads Intelligence")
st.write("Upload campaign, ad set, and ad level CSV files for deeper analysis.")


campaign_file = st.file_uploader("Upload Campaign Level CSV", type=["csv"], key="campaign")
adset_file = st.file_uploader("Upload Ad Set Level CSV", type=["csv"], key="adset")
ad_file = st.file_uploader("Upload Ad Level CSV", type=["csv"], key="ad")


def normalize_columns(df):
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def find_col(df, keywords):
    for col in df.columns:
        for keyword in keywords:
            if keyword in col:
                return col
    return None


def to_numeric_safe(df, cols):
    for col in cols:
        if col and col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace("%", "", regex=False)
                .replace("nan", np.nan)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def classify_result_type(indicator):
    if pd.isna(indicator):
        return "No result type"
    indicator = str(indicator).lower()

    if "invitee_meeting_scheduled" in indicator:
        return "Demo booked"
    elif "complete_registration" in indicator:
        return "Registration"
    elif "landing_page_view" in indicator:
        return "Landing page view"
    else:
        return "Other result"


def prepare_df(df, level_name):
    df = normalize_columns(df)

    name_col = find_col(df, [f"{level_name} name", "campaign name", "ad set name", "ad name"])
    spend_col = find_col(df, ["amount spent", "spend"])
    impressions_col = find_col(df, ["impressions"])
    reach_col = find_col(df, ["reach"])
    frequency_col = find_col(df, ["frequency"])
    cpm_col = find_col(df, ["cpm"])
    clicks_col = find_col(df, ["link clicks"])
    ctr_col = find_col(df, ["ctr (link click-through rate)", "ctr"])
    cpc_col = find_col(df, ["cpc (cost per link click)", "cpc"])
    lpv_col = find_col(df, ["landing page views"])
    cplpv_col = find_col(df, ["cost per landing page view"])
    results_col = find_col(df, ["results"])
    result_indicator_col = find_col(df, ["result indicator"])
    cost_per_results_col = find_col(df, ["cost per results"])

    numeric_cols = [
        spend_col, impressions_col, reach_col, frequency_col, cpm_col,
        clicks_col, ctr_col, cpc_col, lpv_col, cplpv_col,
        results_col, cost_per_results_col
    ]
    df = to_numeric_safe(df, numeric_cols)

    if ctr_col is None and clicks_col and impressions_col:
        df["calculated_ctr"] = (df[clicks_col] / df[impressions_col].replace(0, np.nan) * 100).fillna(0)
        ctr_col = "calculated_ctr"

    if cpc_col is None and clicks_col and spend_col:
        df["calculated_cpc"] = (df[spend_col] / df[clicks_col].replace(0, np.nan)).fillna(0)
        cpc_col = "calculated_cpc"

    if cplpv_col is None and lpv_col and spend_col:
        df["calculated_cost_per_lpv"] = (df[spend_col] / df[lpv_col].replace(0, np.nan)).fillna(0)
        cplpv_col = "calculated_cost_per_lpv"

    if result_indicator_col:
        df["result_type"] = df[result_indicator_col].apply(classify_result_type)
    else:
        df["result_type"] = "No result type"

    if results_col:
        df["result_count"] = df[results_col].fillna(0)
    else:
        df["result_count"] = 0

    df["demos_booked"] = np.where(df["result_type"] == "Demo booked", df["result_count"], 0)
    df["registrations"] = np.where(df["result_type"] == "Registration", df["result_count"], 0)
    df["landing_page_view_results"] = np.where(df["result_type"] == "Landing page view", df["result_count"], 0)

    return {
        "df": df,
        "name_col": name_col,
        "spend_col": spend_col,
        "impressions_col": impressions_col,
        "reach_col": reach_col,
        "frequency_col": frequency_col,
        "cpm_col": cpm_col,
        "clicks_col": clicks_col,
        "ctr_col": ctr_col,
        "cpc_col": cpc_col,
        "lpv_col": lpv_col,
        "cplpv_col": cplpv_col,
        "results_col": results_col,
        "result_indicator_col": result_indicator_col,
        "cost_per_results_col": cost_per_results_col,
    }


def add_funnel_diagnosis(df, ctr_col, cpc_col, cpm_col, lpv_col, cplpv_col, clicks_col):
    avg_ctr = df[ctr_col].mean() if ctr_col and ctr_col in df.columns else 0
    avg_cpc = df[cpc_col].mean() if cpc_col and cpc_col in df.columns else 0
    avg_cpm = df[cpm_col].mean() if cpm_col and cpm_col in df.columns else 0
    avg_cplpv = df[cplpv_col].mean() if cplpv_col and cplpv_col in df.columns else 0
    avg_clicks = df[clicks_col].mean() if clicks_col and clicks_col in df.columns else 0
    avg_lpv = df[lpv_col].mean() if lpv_col and lpv_col in df.columns else 0

    diagnoses = []

    for _, row in df.iterrows():
        diagnosis = []

        row_ctr = row[ctr_col] if ctr_col and ctr_col in df.columns else 0
        row_cpc = row[cpc_col] if cpc_col and cpc_col in df.columns else 0
        row_cpm = row[cpm_col] if cpm_col and cpm_col in df.columns else 0
        row_lpv = row[lpv_col] if lpv_col and lpv_col in df.columns else 0
        row_cplpv = row[cplpv_col] if cplpv_col and cplpv_col in df.columns else 0
        row_clicks = row[clicks_col] if clicks_col and clicks_col in df.columns else 0

        if ctr_col and row_ctr < avg_ctr:
            diagnosis.append("Weak attention")

        if cpm_col and row_cpm > avg_cpm:
            diagnosis.append("Costly reach")

        if cpc_col and row_cpc > avg_cpc:
            diagnosis.append("Expensive traffic")

        if clicks_col and lpv_col and row_clicks > avg_clicks and row_lpv < avg_lpv:
            diagnosis.append("Weak click quality")

        if cplpv_col and row_cplpv > avg_cplpv:
            diagnosis.append("Post click inefficiency")

        if not diagnosis:
            diagnosis.append("Healthy funnel")

        diagnoses.append(", ".join(diagnosis))

    df["funnel_diagnosis"] = diagnoses
    return df


def add_health_labels(df, spend_col, ctr_col, cpc_col, cplpv_col, demos_col, regs_col):
    avg_ctr = df[ctr_col].mean() if ctr_col and ctr_col in df.columns else 0
    avg_cpc = df[cpc_col].mean() if cpc_col and cpc_col in df.columns else 0
    avg_cplpv = df[cplpv_col].mean() if cplpv_col and cplpv_col in df.columns else 0
    avg_spend = df[spend_col].mean() if spend_col and spend_col in df.columns else 0

    labels = []
    insights = []

    for _, row in df.iterrows():
        score = 0
        notes = []

        if ctr_col and row[ctr_col] > avg_ctr:
            score += 1
            notes.append("strong CTR")
        elif ctr_col:
            notes.append("weak CTR")

        if cpc_col and row[cpc_col] < avg_cpc:
            score += 1
            notes.append("efficient CPC")
        elif cpc_col:
            notes.append("expensive CPC")

        if cplpv_col and row[cplpv_col] < avg_cplpv:
            score += 1
            notes.append("efficient landing page cost")
        elif cplpv_col:
            notes.append("expensive landing page cost")

        total_primary_results = 0
        if demos_col and demos_col in df.columns:
            total_primary_results += row[demos_col]
        if regs_col and regs_col in df.columns:
            total_primary_results += row[regs_col]

        if total_primary_results > 0:
            score += 1
            notes.append("driving primary results")

        if spend_col and row[spend_col] > avg_spend and total_primary_results == 0:
            notes.append("spending without primary results")

        if score >= 4:
            labels.append("Scale")
        elif score == 3:
            labels.append("Healthy")
        elif score == 2:
            labels.append("Monitor")
        else:
            labels.append("Underperforming")

        insights.append(", ".join(notes))

    df["health_status"] = labels
    df["diagnosis"] = insights
    return df


def build_executive_report(df, name_col, spend_col, ctr_col, cpc_col, cplpv_col):
    lines = []

    if df.empty:
        return ["No data available for this section."]

    if "health_status" in df.columns:
        scale_count = int((df["health_status"] == "Scale").sum())
        under_count = int((df["health_status"] == "Underperforming").sum())
        lines.append(f"{scale_count} units look scalable and {under_count} units need closer review.")

    if "demos_booked" in df.columns and df["demos_booked"].sum() > 0:
        top_demo = df.sort_values("demos_booked", ascending=False).iloc[0]
        if top_demo["demos_booked"] > 0:
            lines.append(
                f'"{top_demo[name_col]}" is the strongest demo driver with {int(top_demo["demos_booked"])} demos booked.'
            )

    if "registrations" in df.columns and df["registrations"].sum() > 0:
        top_reg = df.sort_values("registrations", ascending=False).iloc[0]
        if top_reg["registrations"] > 0:
            lines.append(
                f'"{top_reg[name_col]}" is the strongest registration driver with {int(top_reg["registrations"])} registrations.'
            )

    if cplpv_col and cplpv_col in df.columns:
        best_eff = df.sort_values(cplpv_col, ascending=True).iloc[0]
        lines.append(
            f'"{best_eff[name_col]}" has the strongest landing page efficiency at ${best_eff[cplpv_col]:.2f} per landing page view.'
        )

    if spend_col and cplpv_col and spend_col in df.columns and cplpv_col in df.columns:
        weak_df = df.sort_values([spend_col, cplpv_col], ascending=[False, False])
        weak = weak_df.iloc[0]
        lines.append(
            f'"{weak[name_col]}" needs attention because it combines meaningful spend with weaker efficiency.'
        )

    if "funnel_diagnosis" in df.columns:
        healthy = int(df["funnel_diagnosis"].str.contains("Healthy funnel", na=False).sum())
        weak_attention = int(df["funnel_diagnosis"].str.contains("Weak attention", na=False).sum())
        post_click = int(df["funnel_diagnosis"].str.contains("Post click inefficiency", na=False).sum())

        lines.append(
            f"Funnel read: {healthy} units look healthy, {weak_attention} show attention issues, and {post_click} show post click inefficiency."
        )

    return lines


def generate_recommendations(df, name_col, spend_col, ctr_col, cpc_col, cplpv_col):
    recommendations = []

    if df.empty:
        return ["No recommendations available because the data is empty."]

    avg_ctr = df[ctr_col].mean() if ctr_col and ctr_col in df.columns else 0
    avg_cpc = df[cpc_col].mean() if cpc_col and cpc_col in df.columns else 0
    avg_cplpv = df[cplpv_col].mean() if cplpv_col and cplpv_col in df.columns else 0
    avg_spend = df[spend_col].mean() if spend_col and spend_col in df.columns else 0

    if all(col and col in df.columns for col in [ctr_col, cpc_col, cplpv_col]):
        scale_candidates = df[
            (df[ctr_col] > avg_ctr) &
            (df[cpc_col] < avg_cpc) &
            (df[cplpv_col] < avg_cplpv)
        ]
        if not scale_candidates.empty:
            best = scale_candidates.sort_values(by=cplpv_col, ascending=True).iloc[0]
            recommendations.append(
                f'Scale "{best[name_col]}". It is outperforming the average on CTR, CPC, and cost per landing page view.'
            )

    if all(col and col in df.columns for col in [spend_col, cplpv_col]):
        wasted = df[
            (df[spend_col] > avg_spend) &
            (df[cplpv_col] > avg_cplpv)
        ]
        if not wasted.empty:
            worst = wasted.sort_values(by=spend_col, ascending=False).iloc[0]
            recommendations.append(
                f'Review or reduce spend on "{worst[name_col]}". It is taking above average spend with weaker landing page efficiency.'
            )

    if "funnel_diagnosis" in df.columns:
        weak_attention = df[df["funnel_diagnosis"].str.contains("Weak attention", na=False)]
        if not weak_attention.empty:
            row = weak_attention.iloc[0]
            recommendations.append(
                f'Test stronger first frame hooks and messaging for "{row[name_col]}". It is showing an attention problem.'
            )

        post_click = df[df["funnel_diagnosis"].str.contains("Post click inefficiency", na=False)]
        if not post_click.empty:
            row = post_click.iloc[0]
            recommendations.append(
                f'Check landing page alignment for "{row[name_col]}". The traffic is arriving but downstream efficiency is weak.'
            )

        expensive_traffic = df[df["funnel_diagnosis"].str.contains("Expensive traffic", na=False)]
        if not expensive_traffic.empty:
            row = expensive_traffic.iloc[0]
            recommendations.append(
                f'Review targeting for "{row[name_col]}". Traffic cost is above average.'
            )

    if "demos_booked" in df.columns and df["demos_booked"].sum() > 0:
        best_demo = df.sort_values("demos_booked", ascending=False).iloc[0]
        if best_demo["demos_booked"] > 0:
            recommendations.append(
                f'Protect and learn from "{best_demo[name_col]}". It is currently the strongest demo booking driver.'
            )

    if "registrations" in df.columns and df["registrations"].sum() > 0:
        best_reg = df.sort_values("registrations", ascending=False).iloc[0]
        if best_reg["registrations"] > 0:
            recommendations.append(
                f'Extract messaging lessons from "{best_reg[name_col]}". It is leading on registrations.'
            )

    if not recommendations:
        recommendations.append("No major issues stand out right now. Focus on controlled scaling and fresh creative testing.")

    return recommendations[:6]


def show_results_breakdown(df, name_col):
    total_results = int(df["result_count"].sum()) if "result_count" in df.columns else 0
    total_demos = int(df["demos_booked"].sum()) if "demos_booked" in df.columns else 0
    total_regs = int(df["registrations"].sum()) if "registrations" in df.columns else 0

    r1, r2, r3 = st.columns(3)
    r1.metric("Total Results", f"{total_results:,}")
    r2.metric("Demos Booked", f"{total_demos:,}")
    r3.metric("Registrations", f"{total_regs:,}")

    if total_demos > 0:
        st.subheader("Top Demo Drivers")
        demo_df = (
            df[df["demos_booked"] > 0]
            [[name_col, "demos_booked", "result_count", "result_type", "diagnosis", "funnel_diagnosis"]]
            .sort_values("demos_booked", ascending=False)
        )
        st.dataframe(demo_df, use_container_width=True)

    if total_regs > 0:
        st.subheader("Top Registration Drivers")
        reg_df = (
            df[df["registrations"] > 0]
            [[name_col, "registrations", "result_count", "result_type", "diagnosis", "funnel_diagnosis"]]
            .sort_values("registrations", ascending=False)
        )
        st.dataframe(reg_df, use_container_width=True)


def show_overview(title, prepared, level_label):
    df = prepared["df"].copy()

    name_col = prepared["name_col"]
    spend_col = prepared["spend_col"]
    impressions_col = prepared["impressions_col"]
    reach_col = prepared["reach_col"]
    frequency_col = prepared["frequency_col"]
    cpm_col = prepared["cpm_col"]
    clicks_col = prepared["clicks_col"]
    ctr_col = prepared["ctr_col"]
    cpc_col = prepared["cpc_col"]
    lpv_col = prepared["lpv_col"]
    cplpv_col = prepared["cplpv_col"]

    st.header(title)

    df = add_funnel_diagnosis(df, ctr_col, cpc_col, cpm_col, lpv_col, cplpv_col, clicks_col)
    df = add_health_labels(df, spend_col, ctr_col, cpc_col, cplpv_col, "demos_booked", "registrations")

    total_spend = df[spend_col].sum() if spend_col else 0
    total_impressions = df[impressions_col].sum() if impressions_col else 0
    total_clicks = df[clicks_col].sum() if clicks_col else 0
    total_lpv = df[lpv_col].sum() if lpv_col else 0
    avg_ctr = df[ctr_col].mean() if ctr_col else 0
    avg_cpc = df[cpc_col].mean() if cpc_col else 0
    avg_cplpv = df[cplpv_col].mean() if cplpv_col else 0
    total_results = int(df["result_count"].sum())
    total_demos = int(df["demos_booked"].sum())
    total_regs = int(df["registrations"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spend", f"${total_spend:,.2f}")
    c2.metric("Impressions", f"{int(total_impressions):,}")
    c3.metric("Clicks", f"{int(total_clicks):,}")
    c4.metric("Landing Page Views", f"{int(total_lpv):,}")

    c5, c6, c7, c8, c9 = st.columns(5)
    c5.metric("Avg CTR", f"{avg_ctr:.2f}%")
    c6.metric("Avg CPC", f"${avg_cpc:.2f}" if avg_cpc else "$0.00")
    c7.metric("Avg Cost per LPV", f"${avg_cplpv:.2f}" if avg_cplpv else "$0.00")
    c8.metric("Total Results", f"{total_results:,}")
    c9.metric("Demos / Registrations", f"{total_demos:,} / {total_regs:,}")

    st.subheader(f"{level_label} Executive Report")
    report_lines = build_executive_report(df, name_col, spend_col, ctr_col, cpc_col, cplpv_col)
    for line in report_lines:
        st.write(f"• {line}")

    st.subheader(f"{level_label} Funnel Diagnosis Summary")
    funnel_summary = (
        df["funnel_diagnosis"]
        .value_counts()
        .reset_index()
    )
    funnel_summary.columns = ["Funnel diagnosis", "Count"]
    st.dataframe(funnel_summary, use_container_width=True)

    keep_cols = [
        col for col in [
            name_col, spend_col, impressions_col, reach_col, frequency_col,
            clicks_col, ctr_col, cpc_col, lpv_col, cplpv_col
        ] if col
    ]
    keep_cols += [
        "result_type", "result_count", "demos_booked", "registrations",
        "health_status", "diagnosis", "funnel_diagnosis"
    ]

    st.subheader(f"{level_label} Health Table")
    st.dataframe(
        df[keep_cols].sort_values(by=spend_col, ascending=False),
        use_container_width=True
    )

    if name_col and spend_col:
        chart_df = df[[name_col, spend_col]].sort_values(by=spend_col, ascending=False).head(10)
        fig = px.bar(chart_df, x=name_col, y=spend_col, title=f"Top 10 {level_label}s by Spend")
        st.plotly_chart(fig, use_container_width=True)

    if name_col and "result_count" in df.columns and df["result_count"].sum() > 0:
        result_chart_df = (
            df[[name_col, "result_count"]]
            .sort_values(by="result_count", ascending=False)
            .head(10)
        )
        fig_results = px.bar(
            result_chart_df,
            x=name_col,
            y="result_count",
            title=f"Top 10 {level_label}s by Results"
        )
        st.plotly_chart(fig_results, use_container_width=True)

    st.subheader(f"{level_label} Scale Candidates")
    scale_df = df[df["health_status"] == "Scale"]
    if not scale_df.empty:
        st.dataframe(
            scale_df[keep_cols].sort_values(by=cplpv_col, ascending=True),
            use_container_width=True
        )
    else:
        st.info("No clear scale candidates found yet.")

    st.subheader(f"{level_label} Underperformers")
    under_df = df[df["health_status"] == "Underperforming"]
    if not under_df.empty:
        st.dataframe(
            under_df[keep_cols].sort_values(by=spend_col, ascending=False),
            use_container_width=True
        )
    else:
        st.info("No major underperformers found.")

    st.subheader(f"{level_label} Results Breakdown")
    show_results_breakdown(df, name_col)

    st.subheader(f"{level_label} Weekly Recommendations")
    recommendations = generate_recommendations(df, name_col, spend_col, ctr_col, cpc_col, cplpv_col)
    for rec in recommendations:
        st.write(f"• {rec}")


if campaign_file and adset_file and ad_file:
    campaign_df = pd.read_csv(campaign_file)
    adset_df = pd.read_csv(adset_file)
    ad_df = pd.read_csv(ad_file)

    campaign_prepared = prepare_df(campaign_df, "campaign")
    adset_prepared = prepare_df(adset_df, "ad set")
    ad_prepared = prepare_df(ad_df, "ad")

    tabs = st.tabs(["Campaign Analysis", "Ad Set Analysis", "Ad Analysis"])

    with tabs[0]:
        show_overview("Campaign Level Intelligence", campaign_prepared, "Campaign")

    with tabs[1]:
        show_overview("Ad Set Level Intelligence", adset_prepared, "Ad Set")

    with tabs[2]:
        show_overview("Ad Level Intelligence", ad_prepared, "Ad")

st.info("Upload all three CSV files to begin full funnel analysis.")
    