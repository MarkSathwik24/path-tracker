import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import calendar
import requests

# --- CLOUD DATABASE SETUP ---
try:
    DB_URL = st.secrets["DB_URL"] 
except Exception:
    # FIX 1: Added .json to the end of the URL so Firebase accepts the data
    DB_URL = "https://path-tracker-82d1a-default-rtdb.asia-southeast1.firebasedatabase.app/.json"

def load_data():
    try:
        response = requests.get(DB_URL)
        data = response.json()
    except Exception:
        data = None

    if not data:
        default_data = {
            "daily_tasks": {
                "Control Systems Study": ["Review LQR code", "Simulate inverted pendulum"],
                "Daily Routine": ["Morning walk", "Read 10 pages"]
            },
            "weekly_tasks": {
                "M.Tech Thesis": ["Draft literature review", "Run aerodynamics simulation"],
                "Project Work": ["GNSS signal testing", "Update Kalman filter"]
            },
            "daily_logs": {},
            "weekly_logs": {}
        }
        requests.put(DB_URL, json=default_data)
        return default_data
    return data

def save_data(data):
    requests.put(DB_URL, json=data)

# --- FIX 2: Use Indian Standard Time (IST) ---
# This ensures that at 12:30 AM in Kharagpur, the app knows it is a new day.
IST = timezone(timedelta(hours=5, minutes=30))
ist_now = datetime.now(IST)
today = str(ist_now.date())
current_week = f"{ist_now.year}-W{ist_now.isocalendar()[1]}"

data = load_data()

# --- Your Original Strict Sync and Purge Logic ---
current_daily_log = data["daily_logs"].get(today, {})
data["daily_logs"][today] = {
    task: {sub: current_daily_log.get(task, {}).get(sub, False) for sub in subs}
    for task, subs in data["daily_tasks"].items()
}

current_weekly_log = data["weekly_logs"].get(current_week, {})
data["weekly_logs"][current_week] = {
    task: {sub: current_weekly_log.get(task, {}).get(sub, False) for sub in subs}
    for task, subs in data["weekly_tasks"].items()
}
save_data(data)

# --- APP LAYOUT (Your Original Framework) ---
st.set_page_config(page_title="My Path Tracker", layout="centered")
st.title("My Path Tracker")

tab_daily, tab_weekly, tab_history, tab_settings = st.tabs(["Daily Path", "Weekly Path", "Calendar & History", "Settings"])

with tab_daily:
    st.header(f"Daily Log: {today}")
    total_daily_subs = sum(len(subs) for subs in data["daily_tasks"].values())
    completed_daily = sum(
        sum(1 for sub in subs if data["daily_logs"][today].get(task, {}).get(sub, False))
        for task, subs in data["daily_tasks"].items()
    )
    
    if total_daily_subs > 0:
        progress_pct = completed_daily / total_daily_subs
        st.progress(progress_pct)
        st.write(f"**Today's Progress:** {int(progress_pct * 100)}% ({completed_daily}/{total_daily_subs} subtasks)")
        st.divider()

        for task, subs in data["daily_tasks"].items():
            st.subheader(task)
            for sub in subs:
                current_val = data["daily_logs"][today][task].get(sub, False)
                if st.checkbox(sub, value=current_val, key=f"d_{task}_{sub}"):
                    if not current_val:
                        data["daily_logs"][today][task][sub] = True
                        save_data(data)
                        st.rerun()
                else:
                    if current_val:
                        data["daily_logs"][today][task][sub] = False
                        save_data(data)
                        st.rerun()
    else:
        st.info("No daily tasks set up yet. Go to Settings!")

with tab_weekly:
    st.header(f"Weekly Log: {current_week}")
    total_weekly_subs = sum(len(subs) for subs in data["weekly_tasks"].values())
    completed_weekly = sum(
        sum(1 for sub in subs if data["weekly_logs"][current_week].get(task, {}).get(sub, False))
        for task, subs in data["weekly_tasks"].items()
    )
    
    if total_weekly_subs > 0:
        progress_pct_w = completed_weekly / total_weekly_subs
        st.progress(progress_pct_w)
        st.write(f"**This Week's Progress:** {int(progress_pct_w * 100)}% ({completed_weekly}/{total_weekly_subs} subtasks)")
        st.divider()

        for task, subs in data["weekly_tasks"].items():
            st.subheader(task)
            for sub in subs:
                current_val = data["weekly_logs"][current_week][task].get(sub, False)
                if st.checkbox(sub, value=current_val, key=f"w_{task}_{sub}"):
                    if not current_val:
                        data["weekly_logs"][current_week][task][sub] = True
                        save_data(data)
                        st.rerun()
                else:
                    if current_val:
                        data["weekly_logs"][current_week][task][sub] = False
                        save_data(data)
                        st.rerun()
    else:
        st.info("No weekly tasks set up yet. Go to Settings!")

with tab_history:
    st.header("📈 Tracking History")
    # Using IST for history calculation
    last_30_days = [str(ist_now.date() - timedelta(days=i)) for i in range(29, -1, -1)]
    trend_data = {"Date": [], "Progress (%)": []}
    
    for d in last_30_days:
        if d in data["daily_logs"]:
            day_log = data["daily_logs"][d]
            total = sum(len(subs) for subs in day_log.values())
            completed = sum(sum(1 for v in subs.values() if v) for subs in day_log.values())
            pct = (completed / total * 100) if total > 0 else 0
            trend_data["Date"].append(d)
            trend_data["Progress (%)"].append(pct)
        
    if trend_data["Date"]:
        st.bar_chart(pd.DataFrame(trend_data).set_index("Date"))

with tab_settings:
    st.header("Configure Your Path")
    
    def dict_to_df(task_dict):
        return pd.DataFrame([
            {"Task Name": k, "Subtasks (comma separated)": ", ".join(v)} 
            for k, v in task_dict.items()
        ])

    st.subheader("Daily Configuration")
    df_daily = dict_to_df(data["daily_tasks"])
    edited_daily = st.data_editor(df_daily, num_rows="dynamic", use_container_width=True, key="edit_daily")
    
    st.subheader("Weekly Configuration")
    df_weekly = dict_to_df(data["weekly_tasks"])
    edited_weekly = st.data_editor(df_weekly, num_rows="dynamic", use_container_width=True, key="edit_weekly")
    
    if st.button("Save All Settings", type="primary"):
        new_daily, new_weekly = {}, {}
        
        for _, row in edited_daily.iterrows():
            name = str(row["Task Name"]).strip()
            subs = [s.strip() for s in str(row["Subtasks (comma separated)"]).split(",") if s.strip()]
            if name and subs and name != "nan":
                new_daily[name] = subs
                
        for _, row in edited_weekly.iterrows():
            name = str(row["Task Name"]).strip()
            subs = [s.strip() for s in str(row["Subtasks (comma separated)"]).split(",") if s.strip()]
            if name and subs and name != "nan":
                new_weekly[name] = subs
                
        data["daily_tasks"] = new_daily
        data["weekly_tasks"] = new_weekly
        save_data(data)
        st.success("Settings saved! Your paths have been updated.")
        st.rerun()
