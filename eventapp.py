import streamlit as st
import pandas as pd

# --------------------------
# Simple password gate
# --------------------------
st.set_page_config(page_title="Local Style Chips: Chicago Event Fit Calculator", layout="wide")

# Set your password here
PASSWORD = "chips2025"

# Ask user to enter password
password = st.text_input("Enter access code:", type="password")

if password != PASSWORD:
    st.warning("Please enter the correct access code to continue.")
    st.stop()


# --------------------------
# Page setup
# --------------------------
st.set_page_config(
    page_title="Local Style Chips: Chicago Event Fit Calculator",
    layout="wide"
)

# --------------------------
# Load data
# --------------------------
@st.cache_data
def load_data():
    return pd.read_csv("events.csv")

df = load_data()

st.title("Local Style Potato Chips — Chicago Event Fit Calculator")

# --------------------------
# Sidebar filters
# --------------------------
st.sidebar.header("Filters")

season_filter = st.sidebar.multiselect("Season", sorted(df["Season"].dropna().unique()))
month_filter = st.sidebar.multiselect("Month", sorted(df["Month"].dropna().unique()))
category_filter = st.sidebar.multiselect("Category", sorted(df["Category"].dropna().unique()))
demo_filter = st.sidebar.multiselect("Demographic", sorted(df["Demographic"].dropna().unique()))
min_attendance = st.sidebar.number_input("Minimum Attendance", min_value=0, value=0, step=5000)

filtered = df.copy()
if season_filter:
    filtered = filtered[filtered["Season"].isin(season_filter)]
if month_filter:
    filtered = filtered[filtered["Month"].isin(month_filter)]
if category_filter:
    filtered = filtered[filtered["Category"].isin(category_filter)]
if demo_filter:
    filtered = filtered[filtered["Demographic"].isin(demo_filter)]
filtered = filtered[filtered["Attendance"] >= min_attendance]

# --------------------------
# Sidebar weights
# --------------------------
st.sidebar.header("Weights (adjust importance)")

w_attendance = st.sidebar.slider("Attendance", 0.0, 1.0, 0.20, 0.05)
w_demo = st.sidebar.slider("Demographic", 0.0, 1.0, 0.30, 0.05)
w_emotion = st.sidebar.slider("Emotional Connection", 0.0, 1.0, 0.25, 0.05)
w_publicity = st.sidebar.slider("Publicity", 0.0, 1.0, 0.15, 0.05)
w_pride = st.sidebar.slider("Pride", 0.0, 1.0, 0.10, 0.05)

# normalize so they sum to 1
weight_sum = w_attendance + w_demo + w_emotion + w_publicity + w_pride
if weight_sum == 0:
    weight_sum = 1
w_attendance /= weight_sum
w_demo /= weight_sum
w_emotion /= weight_sum
w_publicity /= weight_sum
w_pride /= weight_sum

# --------------------------
# Compute Dynamic Fit Score
# --------------------------
def calc_fit_score(row):
    # scale attendance 0–10
    att_scaled = 10 * (row["Attendance"] - df["Attendance"].min()) / (df["Attendance"].max() - df["Attendance"].min())
    return round(
        w_attendance * att_scaled +
        w_demo * 10 +   # demographic baseline weight (treat as categorical strength)
        w_emotion * row["Publicity_Score"] +
        w_publicity * row["PrideFactor"] +
        w_pride * row["FitScore"],
        2
    )

filtered = filtered.copy()
filtered["DynamicFitScore"] = filtered.apply(calc_fit_score, axis=1)

# --------------------------
# Display filtered events
# --------------------------
st.subheader("📋 Filtered Events")
st.dataframe(filtered[[
    "Event","Month","Season","Category","Attendance","Demographic",
    "Emotional_Connection","Publicity_Score","PrideFactor","DynamicFitScore",
    "Free_or_Ticketed","Location"
]])

# --------------------------
# Top events
# --------------------------
st.subheader("Top Recommended Events")
top_n = st.slider("How many top events?", 5, 25, 10)
top_events = filtered.sort_values("DynamicFitScore", ascending=False).head(top_n)
st.bar_chart(top_events.set_index("Event")["DynamicFitScore"])

# --------------------------
# Download buttons
# --------------------------
st.subheader("Download Results")

st.download_button(
    "Download Filtered Events as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_events.csv",
    mime="text/csv"
)

st.download_button(
    "Download Top Events as CSV",
    data=top_events.to_csv(index=False).encode("utf-8"),
    file_name="top_events.csv",
    mime="text/csv"
)

# --------------------------
# Quick insights
# --------------------------
st.subheader("Quick Insights")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("By Category")
    st.bar_chart(filtered["Category"].value_counts())

with col2:
    st.write("By Season")
    st.bar_chart(filtered["Season"].value_counts())

with col3:
    st.write("By Demographic")
    st.bar_chart(filtered["Demographic"].value_counts())
