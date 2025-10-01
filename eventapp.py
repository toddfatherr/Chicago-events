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
    # Clean numeric columns
    df["Attendance"] = pd.to_numeric(df["Attendance"].astype(str).str.replace(",",""), errors="coerce")
    df["Estimated_Sponsorship_Cost"] = pd.to_numeric(df["Estimated_Sponsorship_Cost"].astype(str).str.replace(",",""), errors="coerce")
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
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

month_filter = st.sidebar.multiselect("Select Month(s):", options=df["Month"].unique(), default=df["Month"].unique())
season_filter = st.sidebar.multiselect("Select Season(s):", options=df["Season"].unique(), default=df["Season"].unique())
category_filter = st.sidebar.multiselect("Select Category(ies):", options=df["Category"].unique(), default=df["Category"].unique())
ticket_filter = st.sidebar.multiselect("Free or Ticketed:", options=df["Free_or_Ticketed"].unique(), default=df["Free_or_Ticketed"].unique())

filtered_df = df[
    df["Month"].isin(month_filter) &
    df["Season"].isin(season_filter) &
    df["Category"].isin(category_filter) &
    df["Free_or_Ticketed"].isin(ticket_filter)
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
    publicity_w * (pd.to_numeric(filtered_df["Publicity_Score"], errors='coerce') / 10) +
    pride_w * (pd.to_numeric(filtered_df["PrideFactor"], errors='coerce') / 10) +
    media_w * (pd.to_numeric(filtered_df["Media_Coverage_Score"], errors='coerce') / 10) +
    demo_w * filtered_df["DemoScore"] -
    cost_w * filtered_df["NormCost"]
)
filtered_df["ROI"] = ((filtered_df["Attendance"] * pd.to_numeric(filtered_df["Publicity_Score"], errors='coerce') * pd.to_numeric(filtered_df["Media_Coverage_Score"], errors='coerce')) / filtered_df["AdjustedCost"]).round(2)

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
    st.download_button("Download Filtered Data as CSV", data=csv_export, file_name="filtered_events.csv", mime="text/csv")

# -----------------------------
# Tab 3: Map
# -----------------------------
with tab3:
    st.subheader("Map of Events")
    # Remove rows with missing lat/lon
    map_df = filtered_df.dropna(subset=["Latitude","Longitude"]).copy()
    m = folium.Map(location=[41.8781, -87.6298], zoom_start=11)
    for _, row in map_df.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=(
                f"<b>{row['Event']}</b><br>"
                f"Category: {row['Category']}<br>"
                f"Demographic: {row['Demographic']}<br>"
                f"Attendance: {row['Attendance']:,}<br>"
                f"Sponsorship Cost: ${row['AdjustedCost']:,}<br>"
                f"FitScore: {row['DynamicFitScore']:.2f}<br>"
                f"ROI: {row['ROI']}"
            ),
            tooltip=row["Event"]
        ).add_to(m)
    st_map = st_folium(m, width=900, height=600)
    if len(map_df) < len(filtered_df):
        st.warning(f"{len(filtered_df)-len(map_df)} events have missing coordinates and will not appear on the map.")
