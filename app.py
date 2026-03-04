import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests

# --- 1. CLOUD DATABASE SETUP ---
# IMPORTANT: The URL must end in .json for Firebase to work!
try:
    DB_URL = st.secrets["DB_URL"] 
except Exception:
    # Adding .json to the end of your Firebase link
    DB_URL = "https://path-tracker-82d1a-default-rtdb.asia-southeast1.firebasedatabase.app/path_data.json"

def load_data():
    try:
        response = requests.get(DB_URL)
        data = response.json()
    except Exception:
        data = None

    if not data:
        # Default template
        default_data = {
            "daily_tasks": {"Morning Routine": ["Wake up 6am", "Exercise"]},
            "weekly_tasks": {"M.Tech": ["Thesis Progress"]},
            "daily_logs": {},
            "weekly_logs": {}
        }
        requests.put(DB_URL, json=default_data)
        return default_data
    return data

def save_data(data):
    requests.put(DB_URL, json=data)

# --- 2. TIMEZONE & SYNC LOGIC ---
IST = timezone(timedelta(hours=5, minutes=30))
ist_now = datetime.now(IST)
today = str(ist_now.date())
current_week = f"{ist_now.year}-W{ist_now.isocalendar()[1]}"

data = load_data()

# This function ensures that any task in 'settings' exists in the 'daily log'
def sync_logs(data, date_str, week_str):
    # Sync Daily
    current_daily = data["daily_logs"].get(date_str, {})
    data["daily_logs"][date_str] = {
        task: {sub: current_daily.get(task, {}).get(sub, False) for sub in subs}
        for task, subs in data["daily_tasks"].items()
    }
    # Sync Weekly
    current_weekly = data["weekly_logs"].get(week_str, {})
    data["weekly_logs"][week_str] = {
        task: {sub: current_weekly.get(task, {}).get(sub, False) for sub in subs}
        for task, subs in data["weekly_tasks"].items()
    }
    return data

# Run sync on load
data = sync_logs(data, today, current_week)
save_data(data)

# --- 3. APP LAYOUT ---
st.set_page_config(page_title="My Path Tracker", layout="centered")
st.title("My Path Tracker 🚀")

tab_daily, tab_weekly, tab_history, tab_settings = st.tabs(["Daily Path", "Weekly Path", "History", "Settings"])

with tab_daily:
    st.header(f"Daily: {today}")
    daily_tasks = data["daily_tasks"]
    if daily_tasks:
        for task, subs in daily_tasks.items():
            st.subheader(task)
            for sub in subs:
                # Get the current status from the log
                status = data["daily_logs"][today][task].get(sub, False)
                if st.checkbox(sub, value=status, key=f"d_{task}_{sub}"):
                    if not status:
                        data["daily_logs"][today][task][sub] = True
                        save_data(data)
                        st.rerun()
                else:
                    if status:
                        data["daily_logs"][today][task][sub] = False
                        save_data(data)
                        st.rerun()
    else:
        st.info("Setup tasks in Settings!")

with tab_weekly:
    st.header(f"Weekly: {current_week}")
    for task, subs in data["weekly_tasks"].items():
        st.subheader(task)
        for sub in subs:
            status = data["weekly_logs"][current_week][task].get(sub, False)
            if st.checkbox(sub, value=status, key=f"w_{task}_{sub}"):
                if not status:
                    data["weekly_logs"][current_week][task][sub] = True
                    save_data(data)
                    st.rerun()
            else:
                if status:
                    data["weekly_logs"][current_week][task][sub] = False
                    save_data(data)
                    st.rerun()

with tab_history:
    st.header("Progress History")
    st.write("Your history is being recorded in the database.")
    # (Simplified history for now to ensure settings work first)

with tab_settings:
    st.header("Settings")
    
    def dict_to_df(d):
        return pd.DataFrame([{"Task": k, "Subtasks": ", ".join(v)} for k, v in d.items()])

    st.subheader("Edit Daily Tasks")
    edit_d = st.data_editor(dict_to_df(data["daily_tasks"]), num_rows="dynamic", use_container_width=True)
    
    st.subheader("Edit Weekly Tasks")
    edit_w = st.data_editor(dict_to_df(data["weekly_tasks"]), num_rows="dynamic", use_container_width=True)

    if st.button("Save All Settings", type="primary"):
        new_daily = {}
        for _, row in edit_d.iterrows():
            t, s = str(row["Task"]), str(row["Subtasks"])
            if t and s and t != "nan":
                new_daily[t] = [i.strip() for i in s.split(",") if i.strip()]
        
        new_weekly = {}
        for _, row in edit_w.iterrows():
            t, s = str(row["Task"]), str(row["Subtasks"])
            if t and s and t != "nan":
                new_weekly[t] = [i.strip() for i in s.split(",") if i.strip()]

        data["daily_tasks"] = new_daily
        data["weekly_tasks"] = new_weekly
        
        # Sync immediately so the logs match the new settings
        data = sync_logs(data, today, current_week)
        save_data(data)
        st.success("Changes Saved! Go to Daily Path to see them.")
        st.rerun()
