import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta, timezone
import calendar
import requests
from streamlit_option_menu import option_menu

# --- CLOUD DATABASE SETUP ---
try:
    base_url = st.secrets["DB_URL"] 
except Exception:
    base_url = "https://path-tracker-82d1a-default-rtdb.asia-southeast1.firebasedatabase.app/"

if base_url.endswith("/"):
    DB_URL = base_url + "path_data.json"
elif not base_url.endswith(".json"):
    DB_URL = base_url + "/path_data.json"
else:
    DB_URL = base_url

def sanitize_key(key_str):
    for char in ['.', '$', '#', '[', ']', '/']:
        key_str = key_str.replace(char, '')
    return key_str.strip()

def load_data():
    try:
        response = requests.get(DB_URL)
        data = response.json()
    except Exception:
        data = None

    if not data:
        default_data = {
            "daily_task_names": ["Control Systems Study", "Daily Routine"],
            "daily_tasks": {
                "Control Systems Study": ["Review LQR code", "Simulate inverted pendulum"],
                "Daily Routine": ["Morning walk", "Read 10 pages"]
            },
            "weekly_task_names": ["MTech Thesis", "Project Work"],
            "weekly_tasks": {
                "MTech Thesis": ["Draft literature review", "Run aerodynamics simulation"],
                "Project Work": ["GNSS signal testing", "Update Kalman filter"]
            },
            "daily_logs": {},
            "weekly_logs": {}
        }
        requests.put(DB_URL, json=default_data)
        return default_data
    return data

def save_data(data):
    response = requests.put(DB_URL, json=data)
    if response.status_code != 200:
        st.error(f"Database Error: {response.text}")

# --- THE ENGINE ---
data = load_data()

if "daily_task_names" not in data:
    data["daily_task_names"] = list(data.get("daily_tasks", {}).keys())
if "weekly_task_names" not in data:
    data["weekly_task_names"] = list(data.get("weekly_tasks", {}).keys())

IST = timezone(timedelta(hours=5, minutes=30))
ist_now = datetime.datetime.now(IST)
today = str(ist_now.date())
current_week = f"{ist_now.year}-W{ist_now.isocalendar()[1]}"

if "inspect_date" not in st.session_state:
    st.session_state.inspect_date = ist_now.date()

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

# --- APP LAYOUT ---
st.set_page_config(page_title="My Path Tracker", layout="centered")

# CSS Hack to push the menu to the absolute bottom and force it ON TOP of everything
st.markdown("""
    <style>
        .block-container {
            padding-bottom: 150px; 
        }
        iframe[title="streamlit_option_menu.option_menu"] {
            position: fixed;
            bottom: auto;
            left: 0;
            width: 60%;
            z-index: 9999999 !important; /* Cranked up to bury the Manage App button */
            background-color: #0d1b2a;
            /* Deep black background */ 
            border: 2px solid #0077b6; 
            /* "Radium" Neon Green */ 
            border-radius: 20px; 
            /* Rounded corners for a modern feel */ /* The "Radium" Glow Effect */ 
            box-shadow: 0px 4px 15px rgba(0, 119, 182, 0.4); 
            padding: 5px;
            bottom-padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("My Path Tracker")

# --- BOTTOM NAVIGATION BAR ---
selected = option_menu(
    menu_title=None,
    options=["Daily", "Weekly", "History", "Settings"],
    icons=["check2-square", "calendar-week", "clock-history", "gear"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "margin": "0!important", "background-color": "transparent"},
        "icon": {"font-size": "10px"},
        "nav-link": {"font-size": "5px", "text-align": "center", "margin":"0px", "--hover-color": "#f0f2f6"},
        "nav-link-selected": {"background-color": "#1a73e8"},
    }
)

# --- PAGE ROUTING ---
if selected == "Daily":
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

        for task in data["daily_task_names"]:
            if task in data["daily_tasks"]:
                subs = data["daily_tasks"][task]
                st.subheader(task)
                for sub in subs:
                    current_val = data["daily_logs"][today][task].get(sub, False)
                    new_val = st.checkbox(sub, value=current_val, key=f"d_{task}_{sub}")
                    
                    if new_val != current_val:
                        data["daily_logs"][today][task][sub] = new_val
                        save_data(data)
                        st.rerun()
    else:
        st.info("No daily tasks set up yet. Go to Settings!")

elif selected == "Weekly":
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

        for task in data["weekly_task_names"]:
            if task in data["weekly_tasks"]:
                subs = data["weekly_tasks"][task]
                st.subheader(task)
                for sub in subs:
                    current_val = data["weekly_logs"][current_week][task].get(sub, False)
                    new_val = st.checkbox(sub, value=current_val, key=f"w_{task}_{sub}")
                    
                    if new_val != current_val:
                        data["weekly_logs"][current_week][task][sub] = new_val
                        save_data(data)
                        st.rerun()
    else:
        st.info("No weekly tasks set up yet. Go to Settings!")

elif selected == "History":
    st.header("📈 Tracking History")
    
    st.subheader("Last 30 Days Trend")
    last_30_days = [str(ist_now.date() - timedelta(days=i)) for i in range(29, -1, -1)]
    trend_data = {"Date": [], "Progress (%)": []}
    
    for d in last_30_days:
        if d in data["daily_logs"]:
            day_log = data["daily_logs"][d]
            total = sum(len(subs) for subs in day_log.values())
            completed = sum(sum(1 for v in subs.values() if v) for subs in day_log.values())
            pct = (completed / total * 100) if total > 0 else 0
        else:
            pct = 0
            
        trend_data["Date"].append(d)
        trend_data["Progress (%)"].append(pct)
        
    df_trend = pd.DataFrame(trend_data)
    st.bar_chart(df_trend.set_index("Date"))
    
    st.divider()

    st.subheader("📅 Daily Snapshot & Calendar")
    st.write("Use the box below to select a day. The visual calendar will highlight it for you!")
    
    selected_date = st.date_input("🗓️ Select Date", st.session_state.inspect_date)
    if selected_date != st.session_state.inspect_date:
        st.session_state.inspect_date = selected_date
        st.rerun()
        
    selected_date_str = str(st.session_state.inspect_date)
    
    if selected_date_str in data["daily_logs"]:
        day_log = data["daily_logs"][selected_date_str]
        
        hist_total = sum(len(subs) for subs in day_log.values())
        hist_completed = sum(sum(1 for v in subs.values() if v) for subs in day_log.values())
        
        if hist_total > 0:
            hist_pct = hist_completed / hist_total
            st.metric(label=f"Total Progress on {selected_date_str}", value=f"{int(hist_pct*100)}%", delta=f"{hist_completed}/{hist_total} subtasks completed")
            st.progress(hist_pct)
            
            st.write("**Task Breakdown:**")
            for task, subs in day_log.items():
                if subs: 
                    with st.expander(task):
                        for sub, is_done in subs.items():
                            status = "✅" if is_done else "❌"
                            st.write(f"{status} {sub}")
        else:
             st.info(f"No tasks were logged on {selected_date_str}.")
    else:
        st.warning(f"No activity recorded for {selected_date_str}.")

    st.divider()

    calendar.setfirstweekday(calendar.SUNDAY)
    sel_year = st.session_state.inspect_date.year
    sel_month = st.session_state.inspect_date.month
    
    cal = calendar.monthcalendar(sel_year, sel_month)
    month_name = calendar.month_name[sel_month]
    
    html_cal = f"""
    <div style="padding: 10px; border: 1px solid rgba(128,128,128,0.2); border-radius: 10px;">
        <h3 style="text-align: center; margin-top: 0; font-family: sans-serif;">{month_name} {sel_year}</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: center; font-family: sans-serif; font-size: 16px;">
            <tr style="font-size: 14px; opacity: 0.7;">
                <th style="padding-bottom: 15px; font-weight: normal;">S</th>
                <th style="padding-bottom: 15px; font-weight: normal;">M</th>
                <th style="padding-bottom: 15px; font-weight: normal;">T</th>
                <th style="padding-bottom: 15px; font-weight: normal;">W</th>
                <th style="padding-bottom: 15px; font-weight: normal;">T</th>
                <th style="padding-bottom: 15px; font-weight: normal;">F</th>
                <th style="padding-bottom: 15px; font-weight: normal;">S</th>
            </tr>
    """
    
    for week in cal:
        html_cal += "<tr>"
        for day in week:
            if day == 0:
                html_cal += "<td></td>"
            else:
                is_selected = (day == st.session_state.inspect_date.day and 
                               sel_month == st.session_state.inspect_date.month and 
                               sel_year == st.session_state.inspect_date.year)
                
                date_str = f"{sel_year}-{sel_month:02d}-{day:02d}"
                has_progress = False
                if date_str in data["daily_logs"]:
                    day_log = data["daily_logs"][date_str]
                    completed = sum(sum(1 for v in subs.values() if v) for subs in day_log.values())
                    if completed > 0:
                        has_progress = True

                if is_selected:
                    cell_html = f"<div style='background-color: #1a73e8; color: white; border-radius: 50%; width: 34px; height: 34px; line-height: 34px; margin: auto; font-weight: bold;'>{day}</div>"
                elif has_progress:
                    cell_html = f"<div style='width: 34px; height: 34px; line-height: 34px; margin: auto; position: relative;'>{day}<span style='position:absolute; bottom:0px; left:15px; width:4px; height:4px; background-color:#1a73e8; border-radius:50%;'></span></div>"
                else:
                    cell_html = f"<div style='width: 34px; height: 34px; line-height: 34px; margin: auto;'>{day}</div>"

                html_cal += f"<td style='padding: 8px 0;'>{cell_html}</td>"
        html_cal += "</tr>"
    html_cal += "</table></div>"
    
    st.markdown(html_cal, unsafe_allow_html=True)

elif selected == "Settings":
    st.header("Configure Your Path")
    st.write("Separate your subtasks with commas. **Click the '+' icon to add new tasks.**")
    
    def dict_to_df(task_dict, order_list):
        rows = []
        for k in order_list:
            if k in task_dict:
                rows.append({"Task Name": k, "Subtasks (comma separated)": ", ".join(task_dict[k])})
        for k, v in task_dict.items():
            if k not in order_list:
                rows.append({"Task Name": k, "Subtasks (comma separated)": ", ".join(v)})
        return pd.DataFrame(rows)

    st.subheader("Daily Configuration")
    df_daily = dict_to_df(data["daily_tasks"], data["daily_task_names"])
    edited_daily = st.data_editor(df_daily, num_rows="dynamic", use_container_width=True, key="edit_daily")
    
    st.subheader("Weekly Configuration")
    df_weekly = dict_to_df(data["weekly_tasks"], data["weekly_task_names"])
    edited_weekly = st.data_editor(df_weekly, num_rows="dynamic", use_container_width=True, key="edit_weekly")
    
    if st.button("Save All Settings", type="primary"):
        new_daily, new_weekly = {}, {}
        daily_order, weekly_order = [], []
        
        for _, row in edited_daily.iterrows():
            raw_name = str(row["Task Name"]).strip()
            name = sanitize_key(raw_name) 
            subs = [s.strip() for s in str(row["Subtasks (comma separated)"]).split(",") if s.strip()]
            if name and subs and name != "nan":
                new_daily[name] = subs
                if name not in daily_order:
                    daily_order.append(name)
                
        for _, row in edited_weekly.iterrows():
            raw_name = str(row["Task Name"]).strip()
            name = sanitize_key(raw_name) 
            subs = [s.strip() for s in str(row["Subtasks (comma separated)"]).split(",") if s.strip()]
            if name and subs and name != "nan":
                new_weekly[name] = subs
                if name not in weekly_order:
                    weekly_order.append(name)
                
        data["daily_tasks"] = new_daily
        data["daily_task_names"] = daily_order
        data["weekly_tasks"] = new_weekly
        data["weekly_task_names"] = weekly_order
        save_data(data)
        st.success("Settings saved! Your paths have been updated.")
        st.rerun()
