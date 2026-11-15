import datetime
import sqlite3
import pandas as pd
import requests
import streamlit as st

# --- 1. 資料庫設定 ---
DB_NAME = "hk_flights.db"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  c = conn.cursor()
  c.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_type TEXT, -- 'DEP' (離港) 或 'ARR' (抵港)
            date TEXT,
            flight_no TEXT,
            destination_or_origin TEXT, -- 離港為目的地，抵港為出發地
            std_time TEXT,
            gate TEXT,
            category TEXT,
            UNIQUE(flight_type, date, flight_no, std_time)
        )
    ''')
  conn.commit()
  conn.close()


init_db()

# --- 2. 閘口分類邏輯 ---


def classify_gate(gate_str):
  if not gate_str:
    return "C) 其他 Gate"
  gate_str = str(gate_str).strip().upper()
  import re

  numbers = re.findall(r"\d+", gate_str)
  if numbers:
    gate_num = int(numbers[0])
    if 23 <= gate_num <= 34:
      return "A) Gate 23-34"
    elif 6 <= gate_num <= 9:
      return "B) Gate 6-9"
  return "C) 其他 Gate"


# --- 3. 獲取機場數據 (離港 & 抵港) ---


def fetch_flight_data(flight_type="DEP"):
  if flight_type == "DEP":
    url = "https://www.hongkongairport.com/flightinfo/chinese/outgoing.json"
    dest_key = "destination"
    time_key = "time"
  else:
    url = "https://www.hongkongairport.com/flightinfo/chinese/incoming.json"
    dest_key = "origin"  # 抵港航班使用 origin (出發地)
    time_key = "time"

  try:
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
      data = response.json()
      flights = []
      today_str = datetime.date.today().isoformat()
      for flight in data:
        flight_no = flight.get("flight", [{}])[0].get("no", "Unknown")
        loc_info = flight.get(dest_key, [{}])
        location = loc_info[0].get("name", "Unknown") if loc_info else "Unknown"
        std_time = flight.get(time_key, "")
        gate = flight.get("gate", "")
        category = classify_gate(gate)

        flights.append({
            "flight_type": flight_type,
            "date": today_str,
            "flight_no": flight_no,
            "destination_or_origin": location,
            "std_time": std_time,
            "gate": gate,
            "category": category,
        })
      return pd.DataFrame(flights)
  except Exception as e:
    st.error(f"獲取 {flight_type} 數據失敗: {e}")
  return pd.DataFrame()


# 自動更新今日數據
def auto_update_today():
  # 更新離港
  df_dep = fetch_flight_data("DEP")
  # 更新抵港
  df_arr = fetch_flight_data("ARR")
  df_combined = pd.concat([df_dep, df_arr], ignore_index=True)

  if not df_combined.empty:
    conn = sqlite3.connect(DB_NAME)
    df_combined.to_sql("flights", conn, if_exists="append", index=False)
    conn.close()


try:
  auto_update_today()
except:
  pass

# --- 4. Streamlit 介面設計 ---
st.set_page_config(
    page_title="香港機場航班監控 Dashboard", page_icon="✈️", layout="wide"
)

st.title("✈️ 香港機場航班監控與預測 Dashboard")
st.markdown("同步追蹤**離港 (Departures)** 與 **抵港 (Arrivals)** 航班數據。")

# 讀取資料庫
conn = sqlite3.connect(DB_NAME)
df_all = pd.read_sql("SELECT * FROM flights", conn)
conn.close()

if not df_all.empty:
  st.sidebar.header("🔍 篩選面板")

  # 選擇航班類型 (離港 vs 抵港)
  tab_choice = st.sidebar.radio("選擇航班類別", ["🛫 離港航班 (Departures)", "🛬 抵港航班 (Arrivals)"])
  f_type = "DEP" if "離港" in tab_choice else "ARR"

  # 日期選擇
  available_dates = sorted(df_all["date"].unique(), reverse=True)
  selected_date = st.sidebar.selectbox("選擇查看日期", available_dates, index=0)

  # 過濾數據
  df_filtered = df_all[
      (df_all["date"] == selected_date) & (df_all["flight_type"] == f_type)
  ]

  st.subheader(
      f"📊 {selected_date} {'離港' if f_type == 'DEP' else '抵港'} 航班統計概覽"
  )

  # KPI 指標卡片
  col1, col2, col3, col4 = st.columns(4)
  total_flights = len(df_filtered)
  cat_counts = df_filtered["category"].value_counts()

  with col1:
    st.metric("總航班數", total_flights)
  with col2:
    st.metric("A) Gate 23-34", cat_counts.get("A) Gate 23-34", 0))
  with col3:
    st.metric("B) Gate 6-9", cat_counts.get("B) Gate 6-9", 0))
  with col4:
    st.metric("C) 其他 Gate", cat_counts.get("C) 其他 Gate", 0))

  st.markdown("---")

  # 詳細數據表格
  st.markdown(
      f"### 📋 {'離港' if f_type == 'DEP' else '抵港'} 航班詳細清單"
  )
  display_df = df_filtered[
      ["flight_no", "std_time", "destination_or_origin", "gate", "category"]
  ].copy()
  display_df.columns = [
      "航班編號",
      "時間",
      "目的地" if f_type == "DEP" else "出發地",
      "閘口",
      "分類",
  ]
  st.dataframe(display_df, use_container_width=True)

  # 每週趨勢
  st.markdown("---")
  st.subheader("📈 每週航班數目趨勢")
  df_all["datetime"] = pd.to_datetime(df_all["date"])
  df_all["week"] = df_all["datetime"].dt.isocalendar().week

  df_type_all = df_all[df_all["flight_type"] == f_type]
  weekly_summary = (
      df_type_all.groupby(["week", "category"]).size().unstack(fill_value=0)
  )
  st.bar_chart(weekly_summary)

else:
  st.warning("資料庫尚無數據。")
  if st.button("🚀 立即手動抓取今日航班"):
    auto_update_today()
    st.success("抓取完成！請重新整理頁面。")
    st.rerun()
