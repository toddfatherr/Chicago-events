import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("events.csv")
    return df

df = load_data()

st.set_page_config(page_title="Chicago Events Analyzer", layout="wide")
st.title("Chicago Events Analyzer for Local Style Potato Chips")
st.markdown(
    "This app evaluates Chicago events for Local Style Potato Chips marketing opportunities. "
    "Filter events, adjust weights and budget, and explore ROI & FitScores."
)

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")

# Default: all unique values in dataset
month_filter = st.sidebar.multiselect(
    "Select Month(s):",
    options=df["Month"].sort_values().unique(),
    default=df["Month"].sort_values().unique()
)

season_filter = st.sidebar.multiselect(
    "Select Season(s):",
    options=df["Season"].sort_values().unique(),
    default=df["Season"].sort_values().unique()
)

category_filter = st.sidebar.multiselect(
    "Select Category(ies):",
    options=sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique())
)

ticket_filter = st.sidebar.multiselect(
    "Free or Ticketed:",
    options=sorted(df["Free_or_Ticketed"].unique()),
    default=sorted(df["Free_or_Ticketed"].unique())
)

# Apply filters only if selections are not empty
filtered_df = df[
    (df["Season"].isin(season_filter)) &
    (df["Month"].isin(month_filter)) &
    (df["Category"].isin(category_filter)) &
    (df["Free_or_Ticketed"].isin(ticket_filter))
]

# -----------------------------
# Cost Adjustments & Budget
# -----------------------------
st.sidebar.header("Budget & Cost Adjustment")
cost_adjustment = st.sidebar.number_input("Cost Adjustment Multiplier", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
filtered_df["AdjustedCost"] = filtered_df["Estimated_Sponsorship_Cost"] * cost_adjustment
budget = st.sidebar.number_input("Total Marketing Budget ($)", min_value=0, value=50000, step=1000)

# -----------------------------
# Scoring Weights
# -----------------------------
st.sidebar.header("Scoring Weights")
attendance_w = st.sidebar.slider("Weight: Attendance", 0.0, 1.0, 0.3)
publicity_w = st.sidebar.slider("Weight: Publicity Score", 0.0, 1.0, 0.2)
pride_w = st.sidebar.slider("Weight: Pride Factor", 0.0, 1.0, 0.2)
media_w = st.sidebar.slider("Weight: Media Coverage", 0.0, 1.0, 0.2)
cost_w = st.sidebar.slider("Weight: Sponsorship Cost (penalty)", 0.0, 1.0, 0.1)
demo_w = st.sidebar.slider("Weight: Demographics Alignment", 0.0, 1.0, 0.1)

# -----------------------------
# FitScore & ROI Calculations
# -----------------------------
filtered_df["NormAttendance"] = filtered_df["Attendance"] / filtered_df["Attendance"].max()
filtered_df["NormCost"] = filtered_df["AdjustedCost"] / filtered_df["AdjustedCost"].max()
demo_scores = {"Families": 1.0, "Young Adults": 0.9, "Sports Fans": 0.8, "Cultural Communities": 0.7, "General Public": 0.8}
filtered_df["DemoScore"] = filtered_df["Demographic"].map(demo_scores).fillna(0.6)
filtered_df["DynamicFitScore"] = (
    attendance_w * filtered_df["NormAttendance"] +
    publicity_w * (filtered_df["Publicity_Score"] / 10) +
    pride_w * (filtered_df["PrideFactor"] / 10) +
    media_w * (filtered_df["Media_Coverage_Score"] / 10) +
    demo_w * filtered_df["DemoScore"] -
    cost_w * filtered_df["NormCost"]
)
filtered_df["ROI"] = ((filtered_df["Attendance"] * filtered_df["Publicity_Score"] * filtered_df["Media_Coverage_Score"]) / filtered_df["AdjustedCost"]).round(2)

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard","Visualizations","Map","Info","Recommended Events"])

# -----------------------------
# Tab 1: Dashboard
# -----------------------------
with tab1:
    st.subheader("Filtered Events")
    st.dataframe(
        filtered_df[["Event","Month","Season","Category","Demographic","Attendance","AdjustedCost","Free_or_Ticketed","Location","DynamicFitScore","ROI"]]
        .sort_values(by="DynamicFitScore", ascending=False)
    )
    csv_export = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(label="Download Filtered Data as CSV", data=csv_export, file_name="filtered_events.csv", mime="text/csv")

# -----------------------------
# Tab 2: Visualizations
# -----------------------------
with tab2:
    st.subheader("Event Category Breakdown")
    fig_pie = px.pie(filtered_df, names="Category")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Seasonal Event Counts")
    season_counts = filtered_df["Season"].value_counts().reset_index()
    season_counts.columns = ["Season","Count"]
    fig_season = px.bar(season_counts, x="Season", y="Count", color="Season")
    st.plotly_chart(fig_season, use_container_width=True)

    st.subheader("Demographic Breakdown")
    demo_counts = filtered_df["Demographic"].value_counts().reset_index()
    demo_counts.columns = ["Demographic","Count"]
    fig_demo = px.bar(demo_counts, x="Demographic", y="Count", color="Demographic")
    st.plotly_chart(fig_demo, use_container_width=True)

# -----------------------------
# Tab 3: Map
# -----------------------------
with tab3:
    st.subheader("Map of Events")
    map_df = filtered_df.dropna(subset=["Latitude", "Longitude"])
    if len(map_df) < len(filtered_df):
        st.warning(f"{len(filtered_df) - len(map_df)} events have missing coordinates and will not appear on the map.")
    m = folium.Map(location=[41.8781, -87.6298], zoom_start=11)
    for _, row in map_df.iterrows():
        popup_text = (
            f"<b>{row['Event']}</b><br>"
            f"Category: {row['Category']}<br>"
            f"Demographic: {row['Demographic']}<br>"
            f"Attendance: {row['Attendance']:,}<br>"
            f"Sponsorship Cost: ${row['AdjustedCost']:,}<br>"
            f"FitScore: {row['DynamicFitScore']:.2f}<br>"
            f"ROI: {row['ROI']}"
        )
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=popup_text,
            tooltip=row["Event"]
        ).add_to(m)
    st_map = st_folium(m, width=900, height=600)

# -----------------------------
# Tab 4: Info
# -----------------------------
with tab4:
    st.subheader("How Scoring and ROI Are Calculated")
    st.markdown(
        "**Dynamic FitScore** combines normalized attendance, publicity, pride, media, demographics, and cost penalty.  "
        "**ROI** estimates marketing return per dollar spent.\n\n"
        "Formulas:\n"
        "```\n"
        "FitScore = (Attendance_w * NormAttendance) + (Publicity_w * Publicity/10) + "
        "(Pride_w * PrideFactor/10) + (Media_w * MediaCoverage/10) + (Demo_w * DemoScore) - (Cost_w * NormCost)\n"
        "ROI = (Attendance * Publicity Score * Media Coverage Score) / AdjustedCost\n"
        "```\n"
        "Adjust all weights and budget using the sidebar sliders."
    )

# -----------------------------
# Tab 5: Recommended Events
# -----------------------------
with tab5:
    st.subheader("Recommended Events Within Total Budget")
    if filtered_df.empty:
        st.warning("No events available with current filters.")
    else:
        budget_df = filtered_df[filtered_df["AdjustedCost"] <= budget].copy()
        if budget_df.empty:
            st.warning("No events fit within the total budget.")
        else:
            budget_df["NormFitScore"] = budget_df["DynamicFitScore"] / budget_df["DynamicFitScore"].max()
            budget_df["NormROI"] = budget_df["ROI"] / budget_df["ROI"].max()
            budget_df["CombinedScore"] = (budget_df["NormFitScore"] + budget_df["NormROI"]) / 2

            events = budget_df.to_dict('records')
            n = len(events)
            W = int(budget)
            costs = [int(e["AdjustedCost"]) for e in events]
            values = [e["CombinedScore"] for e in events]

            # Knapsack DP
            dp = [[0]*(W+1) for _ in range(n+1)]
            for i in range(1,n+1):
                for w in range(W+1):
                    if costs[i-1] <= w:
                        dp[i][w] = max(dp[i-1][w], dp[i-1][w-costs[i-1]] + values[i-1])
                    else:
                        dp[i][w] = dp[i-1][w]

            # Backtrack
            w = W
            selected_indices = []
            for i in range(n,0,-1):
                if dp[i][w] != dp[i-1][w]:
                    selected_indices.append(i-1)
                    w -= costs[i-1]

            recommended_events = [events[i] for i in selected_indices]
            recommended_df = pd.DataFrame(recommended_events).sort_values(by="CombinedScore", ascending=False)
            st.dataframe(recommended_df[["Event","Month","Season","Category","Demographic","Attendance","AdjustedCost","DynamicFitScore","ROI","CombinedScore"]])

            csv_export = recommended_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Optimized Events CSV",
                data=csv_export,
                file_name="optimized_events.csv",
                mime="text/csv"
            )
