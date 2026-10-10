from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. 頁面基本設定
st.set_page_config(
    page_title="HKG Departure Flight Monitoring",
    page_icon="✈️",
    layout="wide",
)

# 2. 多語言字典設定 (Localization)
TEXTS = {
    "English": {
        "title": "✈️ HKG Departure Flight Monitoring & Analysis",
        "sidebar_lang": "Language / 語言",
        "sidebar_tab": "Navigation",
        "tab_dash": "📊 Dashboard",
        "tab_records": "📋 Records & Import",
        "tab_forecast": "📈 Forecast & Trends",
        "kpi_total": "Total Departures",
        "kpi_gate_a": "Gate A Flights (23-34)",
        "kpi_gate_b": "Gate B Flights (6-9)",
        "comp_section": "⚖️ Benchmark Comparison Settings",
        "comp_toggle": "Manual Override Benchmark Period",
        "comp_range_label": "Custom Benchmark Date Range",
        "chart_hourly": "Departure Volume by Gate Category (Selected Period)",
        "chart_dest_a": "Top 10 Destinations (Gate A)",
        "chart_dest_b": "Top 10 Destinations (Gate B)",
        "table_title": "Flight Records Database (Last 3 Months)",
        "upload_label": "Upload Real Flight Data (CSV/Excel)",
        "refresh_status": "🔄 Data auto-refreshes 3 times daily (07:59, 15:59, 23:59 HKT)",
    },
    "Traditional Chinese": {
        "title": "✈️ 香港國際機場離港航班監控與數據分析",
        "sidebar_lang": "語言 / Language",
        "sidebar_tab": "功能選單",
        "tab_dash": "📊 即時儀表板",
        "tab_records": "📋 航班紀錄與資料匯入",
        "tab_forecast": "📈 趨勢預測分析",
        "kpi_total": "總離港航班數",
        "kpi_gate_a": "Gate A 航班數 (23-34)",
        "kpi_gate_b": "Gate B 航班數 (6-9)",
        "comp_section": "⚖️ 對比基準設定",
        "comp_toggle": "手動自訂對比基準區間",
        "comp_range_label": "自訂基準起訖日期",
        "chart_hourly": "各閘口分區離港航班分佈 (所選區間)",
        "chart_dest_a": "Gate A 前 10 大熱門航點 (其餘歸類為其他)",
        "chart_dest_b": "Gate B 前 10 大熱門航點 (其餘歸類為其他)",
        "table_title": "航班資料庫清單 (過去 3 個月)",
        "upload_label": "上傳真實航班資料 (CSV/Excel)",
        "refresh_status": "🔄 數據每日定時 3 次自動更新 (香港時間 07:59, 15:59, 23:59)",
    },
}

# 側邊欄：語言選擇
st.sidebar.title("Settings / 設定")
lang_choice = st.sidebar.selectbox(
    "Language / 語言選擇", ["Traditional Chinese", "English"]
)
t = TEXTS[lang_choice]

st.title(t["title"])
st.sidebar.caption(t["refresh_status"])


# 3. 閘口分類與更合理的真實分佈邏輯
def assign_gate_category():
  category = np.random.choice(
      ["Gate A (23-34)", "Gate B (6-9)", "Gate C (Others)"],
      p=[0.45, 0.10, 0.45],
  )
  if category == "Gate A (23-34)":
    gate_num = str(int(np.random.choice(range(23, 35))))
  elif category == "Gate B (6-9)":
    gate_num = str(int(np.random.choice(range(6, 10))))
  else:
    gate_num = str(
        int(
            np.random.choice(
                [
                    i
                    for i in range(1, 71)
                    if i not in list(range(23, 35)) + list(range(6, 10))
                ]
            )
        )
    )
  return gate_num, category


# 4. 搭配定時區段（對應每天 07:59, 15:59, 23:59）的快取失效機制
def get_flight_refresh_key():
  """根據目前香港時間，每到 08:00, 16:00, 00:00 就會改變快取 Key，

  藉此強迫資料在 07:59, 15:59, 23:59 過後自動重新整理載入最新數據。
  """
  now_hkt = datetime.utcnow() + timedelta(hours=8)
  h = now_hkt.hour
  if h < 8:
    period = "morning_0759"
  elif h < 16:
    period = "afternoon_1559"
  else:
    period = "night_2359"
  return f"{now_hkt.strftime('%Y-%m-%d')}_{period}"


# 載入過去 3 個月資料，並加入以定時時段為依據的 Cache TTL 與 Hash Key
@st.cache_data(ttl=28800)  # 最多快取 8 小時，配合每日三次定時重新整理
def load_mock_data(refresh_key):
  np.random.seed(42)
  start_date = datetime(2026, 7, 12)
  end_date = datetime.now()
  date_range = pd.date_range(start=start_date, end=end_date, freq="D")

  airlines = ["CX (國泰航空)", "HX (香港航空)", "UO (香港快運)", "SQ", "JL", "BA"]
  destinations = [
      "TPE",
      "NRT",
      "LHR",
      "SIN",
      "HND",
      "ICN",
      "BKK",
      "YVR",
      "LAX",
      "SYD",
      "PEK",
      "PVG",
      "KHH",
      "KIX",
      "MEL",
      "CDG",
      "FRA",
      "KUL",
  ]

  data = []
  for single_date in date_range:
    daily_flights = int(np.random.randint(100, 140))
    for _ in range(daily_flights):
      raw_probs = [
          0.02,
          0.01,
          0.01,
          0.01,
          0.02,
          0.04,
          0.07,
          0.09,
          0.08,
          0.07,
          0.06,
          0.06,
          0.05,
          0.05,
          0.06,
          0.07,
          0.08,
          0.06,
          0.04,
          0.03,
          0.02,
          0.02,
          0.01,
          0.01,
      ]
      probs = np.array(raw_probs, dtype=float)
      probs /= np.sum(probs)

      hour = int(np.random.choice(range(24), p=probs))
      minute = int(np.random.choice([0, 15, 30, 45]))
      flight_time = single_date + timedelta(hours=hour, minutes=minute)

      gate_str, gate_cat = assign_gate_category()

      status_probs = np.array([0.75, 0.15, 0.10], dtype=float)
      status_probs /= np.sum(status_probs)

      data.append({
          "FlightNo": f"{np.random.choice(airlines)}{int(np.random.randint(100, 999))}",
          "Destination": np.random.choice(destinations),
          "Gate": gate_str,
          "GateCategory": gate_cat,
          "ScheduledTime": flight_time,
          "DelayMinutes": int(
              np.random.choice(
                  [0, 0, 0, 15, 30, 45, 60],
                  p=[0.6, 0.1, 0.1, 0.1, 0.05, 0.03, 0.02],
              )
          ),
          "Status": np.random.choice(
              ["On Time", "Delayed", "Boarding"], p=status_probs
          ),
      })
  return pd.DataFrame(data)


# 執行資料載入（傳入自動產生的刷新 Key）
current_refresh_key = get_flight_refresh_key()
df = load_mock_data(current_refresh_key)

# 5. 側邊欄導航
st.sidebar.markdown("---")
app_mode = st.sidebar.radio(
    t["sidebar_tab"], [t["tab_dash"], t["tab_records"], t["tab_forecast"]]
)


# 輔助函數：處理 Top 10 航點，其餘歸類為 Other Destinations
def get_top10_destinations(sub_df):
  if sub_df.empty:
    return pd.DataFrame(columns=["Destination", "Count"])
  counts = sub_df["Destination"].value_counts().reset_index()
  counts.columns = ["Destination", "Count"]
  if len(counts) > 10:
    top10 = counts.head(10)
    others_sum = counts.iloc[10:]["Count"].sum()
    others_row = pd.DataFrame(
        [
            {
                "Destination": (
                    "Other Destinations"
                    if lang_choice == "English"
                    else "其他航點"
                ),
                "Count": others_sum,
            }
        ]
    )
    return pd.concat([top10, others_row], ignore_index=True)
  return counts


# ---------------------------------------------------------
# TAB 1: 儀表板 (Dashboard)
# ---------------------------------------------------------
if app_mode == t["tab_dash"]:
  st.sidebar.markdown("---")
  st.sidebar.subheader("📅 日期範圍與對比設定")

  default_start = datetime(2026, 9, 7).date()
  default_end = datetime(2026, 9, 13).date()

  selected_date_input = st.sidebar.date_input(
      "選擇分析日期或區間 / Select Date or Range",
      value=(default_start, default_end),
  )

  if isinstance(selected_date_input, tuple):
    if len(selected_date_input) == 2:
      start_date, end_date = selected_date_input
    else:
      start_date = end_date = selected_date_input[0]
  else:
    start_date = end_date = selected_date_input

  days_delta = (end_date - start_date).days + 1

  if days_delta == 1:
    default_comp_start = start_date - timedelta(days=7)
    default_comp_end = end_date - timedelta(days=7)
  else:
    default_comp_end = start_date - timedelta(days=1)
    default_comp_start = default_comp_end - timedelta(days=days_delta - 1)

  st.sidebar.markdown(f"### {t['comp_section']}")
  manual_comp_override = st.sidebar.checkbox(t["comp_toggle"], value=False)

  if manual_comp_override:
    manual_comp_input = st.sidebar.date_input(
        t["comp_range_label"], value=(default_comp_start, default_comp_end)
    )
    if isinstance(manual_comp_input, tuple) and len(manual_comp_input) == 2:
      comp_start_date, comp_end_date = manual_comp_input
    else:
      comp_start_date = comp_end_date = (
          manual_comp_input
          if not isinstance(manual_comp_input, tuple)
          else manual_comp_input[0]
      )
  else:
    comp_start_date = default_comp_start
    comp_end_date = default_comp_end

  comp_days_delta = (comp_end_date - comp_start_date).days + 1
  st.sidebar.info(
      f"📌 當前對比基準區間: {comp_start_date} ~ {comp_end_date} (共"
      f" {comp_days_delta} 天)"
  )

  df["DateOnly"] = pd.to_datetime(df["ScheduledTime"]).dt.date
  current_day_df = df[
      (df["DateOnly"] >= start_date) & (df["DateOnly"] <= end_date)
  ]
  comp_day_df = df[
      (df["DateOnly"] >= comp_start_date) & (df["DateOnly"] <= comp_end_date)
  ]

  current_total = len(current_day_df)
  comp_total = len(comp_day_df) if len(comp_day_df) > 0 else 1
  total_increase_pct = ((current_total - comp_total) / comp_total) * 100

  gate_a_df = current_day_df[
      current_day_df["GateCategory"] == "Gate A (23-34)"
  ]
  gate_b_df = current_day_df[current_day_df["GateCategory"] == "Gate B (6-9)"]
  gate_a_total = len(gate_a_df)
  gate_b_total = len(gate_b_df)

  comp_gate_a = len(
      comp_day_df[comp_day_df["GateCategory"] == "Gate A (23-34)"]
  )
  comp_gate_b = len(comp_day_df[comp_day_df["GateCategory"] == "Gate B (6-9)"])
  comp_gate_a = comp_gate_a if comp_gate_a > 0 else 1
  comp_gate_b = comp_gate_b if comp_gate_b > 0 else 1

  gate_a_pct = ((gate_a_total - comp_gate_a) / comp_gate_a) * 100
  gate_b_pct = ((gate_b_total - comp_gate_b) / comp_gate_b) * 100

  col1, col2, col3 = st.columns(3)
  with col1:
    st.metric(
        label=t["kpi_total"],
        value=f"{current_total} flights",
        delta=f"{total_increase_pct:.1f}% vs custom benchmark",
    )
  with col2:
    st.metric(
        label=t["kpi_gate_a"],
        value=f"{gate_a_total} flights",
        delta=f"{gate_a_pct:.1f}% vs custom benchmark",
    )
  with col3:
    st.metric(
        label=t["kpi_gate_b"],
        value=f"{gate_b_total} flights",
        delta=f"{gate_b_pct:.1f}% vs custom benchmark",
    )

  st.markdown("---")

  if current_total > 0:
    st.subheader(t["chart_hourly"])

    if days_delta == 1:
      def get_half_hour_slot(dt_val):
        h = dt_val.hour
        m = dt_val.minute
        m_str = "00" if m < 30 else "30"
        return f"{h:02d}:{m_str}"

      current_day_df["TimeSlot"] = pd.to_datetime(
          current_day_df["ScheduledTime"]
      ).apply(get_half_hour_slot)

      all_slots = [
          f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]
      ]
      categories = ["Gate A (23-34)", "Gate B (6-9)", "Gate C (Others)"]
      full_grid = pd.MultiIndex.from_product(
          [all_slots, categories], names=["TimeSlot", "GateCategory"]
      ).to_frame(index=False)

      counts = (
          current_day_df.groupby(["TimeSlot", "GateCategory"])
          .size()
          .reset_index(name="Count")
      )
      chart_data = pd.merge(
          full_grid, counts, on=["TimeSlot", "GateCategory"], how="left"
      ).fillna(0)
      x_col = "TimeSlot"
      category_orders = {x_col: all_slots}
    else:
      current_day_df["DateTimeSlot"] = pd.to_datetime(
          current_day_df["ScheduledTime"]
      ).dt.strftime("%Y-%m-%d %H:%M")
      chart_data = (
          current_day_df.groupby(
              [pd.Grouper(key="ScheduledTime", freq="h"), "GateCategory"]
          )
          .size()
          .reset_index(name="Count")
      )
      chart_data["TimeStr"] = chart_data["ScheduledTime"].dt.strftime(
          "%m-%d %H:00"
      )
      x_col = "TimeStr"
      category_orders = None

    fig_hourly = px.bar(
        chart_data,
        x=x_col,
        y="Count",
        color="GateCategory",
        barmode="stack",
        template="plotly_white",
        category_orders=category_orders if days_delta == 1 else None,
    )
    if days_delta == 1:
      fig_hourly.update_xaxes(categoryorder="array", categoryarray=all_slots)
    st.plotly_chart(fig_hourly, use_container_width=True)

    st.markdown("---")

    col_dest1, col_dest2 = st.columns(2)

    with col_dest1:
      st.subheader(t["chart_dest_a"])
      dest_a_counts = get_top10_destinations(gate_a_df)
      fig_dest_a = px.pie(
          dest_a_counts,
          names="Destination",
          values="Count",
          hole=0.4,
          template="plotly_white",
      )
      st.plotly_chart(fig_dest_a, use_container_width=True)

    with col_dest2:
      st.subheader(t["chart_dest_b"])
      dest_b_counts = get_top10_destinations(gate_b_df)
      fig_dest_b = px.pie(
          dest_b_counts,
          names="Destination",
          values="Count",
          hole=0.4,
          template="plotly_white",
      )
      st.plotly_chart(fig_dest_b, use_container_width=True)

  else:
    st.warning(
        "No flight records found for this selected date range. Try choosing"
        " another range or upload your data in the records tab."
    )

# ---------------------------------------------------------
# TAB 2: 紀錄與上傳 (Records & Import)
# ---------------------------------------------------------
elif app_mode == t["tab_records"]:
  st.subheader(t["table_title"])

  uploaded_file = st.file_uploader(t["upload_label"], type=["csv", "xlsx"])
  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        user_df = pd.read_csv(uploaded_file)
      else:
        user_df = pd.read_excel(uploaded_file)
      st.success("Successfully loaded your custom data file!")
      df = user_df
    except Exception as e:
      st.error(f"Error loading file: {e}")

  st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: 預測分析 (Forecast)
# ---------------------------------------------------------
elif app_mode == t["tab_forecast"]:
  st.subheader("📈 Flight Volume Time-Series & 3-Month Trend")
  daily_trend = (
      df.groupby(pd.to_datetime(df["ScheduledTime"]).dt.date)
      .size()
      .reset_index(name="FlightCount")
  )
  daily_trend.columns = ["Date", "FlightCount"]

  fig_trend = px.line(
      daily_trend,
      x="Date",
      y="FlightCount",
      markers=True,
      title="Historical Daily Departure Volume (Past 3 Months)",
      template="plotly_white",
  )
  st.plotly_chart(fig_trend, use_container_width=True)

  st.info(
      "💡 Data Note: Automatically synced and refreshed 3 times daily based on HKT"
      " schedule blocks (07:59, 15:59, 23:59)."
  )