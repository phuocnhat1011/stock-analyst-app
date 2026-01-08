import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests

# ==============================================================================
# 1. PAGE CONFIG & PRO UI CSS
# ==============================================================================
st.set_page_config(
    page_title="Pro Stock Analyst",
    layout="wide",
    page_icon="🔥",
    initial_sidebar_state="expanded"
)

# --- ADVANCED CSS FOR DARK THEME & UI ---
st.markdown("""
<style>
    .stApp { background-color: #131722 !important; color: #E0E0E0 !important; }
    [data-testid="stSidebar"] { background-color: #0b0e11 !important; border-right: 1px solid #2A2E39; }
    [data-testid="stSidebar"] h1 { background: linear-gradient(to right, #00ADB5, #00F5FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900 !important; font-size: 28px !important; }
    
    /* Làm sáng Label và Input */
    [data-testid="stSidebar"] h3, label p { color: #FFFFFF !important; font-weight: 600 !important; }
    .stTextInput input, .stNumberInput input, .stDateInput input { background-color: #1E222D !important; color: #FFFFFF !important; }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #1E222D; border-radius: 6px; color: #B2B5BE; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #00ADB5 !important; color: #FFFFFF !important; }
    
    /* Metrics */
    [data-testid="stMetricValue"] { color: #00ADB5 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CORE FUNCTIONS (FIREANT & TECH)
# ==============================================================================

@st.cache_data(ttl=3000)
def get_fireant_token():
    url = "https://api.fireant.vn/authentication/login"
    payload = {"email": "rdteam.beqholdings@gmail.com", "password": "BqHgSK@2023"}
    try:
        response = requests.post(url, json=payload)
        return response.json().get("accessToken")
    except: return None

def get_fireant_history(symbol, start_date, end_date):
    token = get_fireant_token()
    if not token: return pd.DataFrame()
    url = f"https://api.fireant.vn/symbols/{symbol}/historical-quotes"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"startDate": start_date.strftime("%Y-%m-%d"), "endDate": end_date.strftime("%Y-%m-%d"), "limit": 5000}
    try:
        res = requests.get(url, headers=headers, params=params)
        df = pd.DataFrame(res.json())
        df = df.rename(columns={'date': 'date', 'priceHigh': 'high', 'priceLow': 'low', 'priceOpen': 'open', 'priceClose': 'close', 'dealVolume': 'volume'})
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'high', 'low', 'open', 'close', 'volume']]
    except: return pd.DataFrame()

def calculate_technical_indicators(df):
    df = df.sort_values('date')
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain/loss))
    return df.sort_values('date', ascending=False)

# ==============================================================================
# 4. MAIN APP LOGIC (FIXING THE TAB BUG)
# ==============================================================================

# Khởi tạo trạng thái để không bị mất dữ liệu khi chuyển tab
if 'main_df' not in st.session_state: st.session_state.main_df = None
if 'compare_df' not in st.session_state: st.session_state.compare_df = None

# SIDEBAR
st.sidebar.title("🔥 PRO ANALYST")
data_source = st.sidebar.radio("Data Source:", ('FireAnt API (Vietnam)', 'Yahoo Finance (Global)'))
start_date = st.sidebar.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=365))
end_date = st.sidebar.date_input("End Date", datetime.date.today())

if data_source == 'FireAnt API (Vietnam)':
    ticker = st.sidebar.text_input("Ticker:", value="SSI").upper()
    if st.sidebar.button("🚀 Load Data"):
        with st.spinner("Fetching..."):
            raw_df = get_fireant_history(ticker, start_date, end_date)
            if not raw_df.empty:
                st.session_state.main_df = calculate_technical_indicators(raw_df)
                st.session_state.ticker = ticker
else:
    ticker = st.sidebar.text_input("Symbol:", value="AAPL").upper()
    if st.sidebar.button("🚀 Load Data"):
        data = yf.download(ticker, start=start_date, end=end_date)
        if not data.empty:
            st.session_state.main_df = calculate_technical_indicators(data.reset_index().rename(columns=str.lower))
            st.session_state.ticker = ticker

# HIỂN THỊ TABS
if st.session_state.main_df is not None:
    df = st.session_state.main_df
    ticker = st.session_state.ticker
    st.title(f"{ticker} - ANALYTICS DASHBOARD")

    # Sử dụng Session State để giữ tab hiện tại
    tab_list = ["📊 Overview", "🕯️ Technical Chart", "⚖️ Compare", "📅 Seasonality", "💰 Financials"]
    tabs = st.tabs(tab_list)

    # --- TAB 1: OVERVIEW ---
    with tabs[0]:
        latest = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Price", f"{latest['close']:,.2f}")
        c2.metric("RSI (14)", f"{latest['rsi']:.2f}")
        c3.metric("Volume", f"{latest['volume']:,.0f}")
        
        fig = go.Figure(go.Scatter(x=df['date'], y=df['close'], fill='tozeroy', line=dict(color='#00ADB5')))
        fig.update_layout(template="plotly_dark", font=dict(color="white"), paper_bgcolor='#131722', plot_bgcolor='#131722')
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: TECHNICAL ---
    with tabs[1]:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close']), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['ma20'], name="MA20", line=dict(color="orange")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name="RSI", line=dict(color="#00ADB5")), row=2, col=1)
        fig.update_layout(template="plotly_dark", font=dict(color="white"), height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: COMPARE (FIXED BUG) ---
    with tabs[2]:
        st.subheader("Performance Comparison")
        comp_ticker = st.text_input("Compare with (e.g. HPG, VNINDEX, ^GSPC):", value="VNINDEX").upper()
        
        # Khi nhấn nút này, ta lưu kết quả vào session_state để không bị mất khi script rerun
        if st.button("Compare Now"):
            with st.spinner("Comparing..."):
                if data_source == 'FireAnt API (Vietnam)':
                    bench_df = get_fireant_history(comp_ticker, start_date, end_date)
                else:
                    bench_df = yf.download(comp_ticker, start=start_date, end=end_date).reset_index().rename(columns=str.lower)
                
                if not bench_df.empty:
                    # Tính toán tương quan %
                    df_m = df[['date', 'close']].sort_values('date')
                    df_b = bench_df[['date', 'close']].sort_values('date')
                    df_m['ret'] = (df_m['close'] / df_m['close'].iloc[0]) * 100
                    df_b['ret'] = (df_b['close'] / df_b['close'].iloc[0]) * 100
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_m['date'], y=df_m['ret'], name=ticker))
                    fig.add_trace(go.Scatter(x=df_b['date'], y=df_b['ret'], name=comp_ticker))
                    fig.update_layout(template="plotly_dark", font=dict(color="white"), title="Relative Performance (%)")
                    st.session_state.compare_fig = fig # Lưu biểu đồ vào session

        if 'compare_fig' in st.session_state:
            st.plotly_chart(st.session_state.compare_fig, use_container_width=True)

    # --- TAB 4: SEASONALITY (FIXED TEXT) ---
    with tabs[3]:
        df_s = df.copy().set_index('date')
        monthly_ret = df_s['close'].resample('M').last().pct_change() * 100
        season = monthly_ret.groupby(monthly_ret.index.month).mean()
        
        fig = go.Figure(go.Bar(x=season.index, y=season.values, 
                               marker_color=['#00ADB5' if x > 0 else '#FF5252' for x in season.values],
                               text=[f"{x:.1f}%" for x in season.values], textposition='auto'))
        fig.update_layout(title="Avg Monthly Return (%)", template="plotly_dark", font=dict(color="white"),
                          xaxis=dict(tickmode='array', tickvals=list(range(1,13)), 
                          ticktext=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']))
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 5: FINANCIALS ---
    with tabs[4]:
        st.info("Loading financial data from FireAnt...")
        # (Giữ nguyên logic load tài chính của bạn ở đây)
    # --- TAB 5: COMPARE (FIXED SOURCE & WHITE TEXT) ---
    with tab5:
        st.subheader("Performance Comparison")
        
        c5_1, c5_2 = st.columns([1, 2])
        with c5_1:
            bench_source = st.selectbox("Benchmark Source", ["Yahoo Finance (Global)", "FireAnt API (Vietnam)"])
        with c5_2:
            default_bench = "^GSPC" if bench_source == "Yahoo Finance (Global)" else "VNINDEX"
            bench_symbol = st.text_input("Benchmark Symbol", value=default_bench)

        if st.button("Compare Now"):
            df_bench = pd.DataFrame()
            with st.spinner(f"Loading {bench_symbol} from {bench_source}..."):
                if bench_source == "Yahoo Finance (Global)":
                    try:
                        data = yf.download(bench_symbol, start=start_date, end=end_date, progress=False)
                        if not data.empty:
                            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                            df_bench = data.reset_index().rename(columns={'Date': 'date', 'Close': 'close', 'Adj Close': 'close'})
                            df_bench.columns = df_bench.columns.str.lower()
                    except Exception as e: st.error(f"Error: {e}")
                else: 
                    fa_symbol = bench_symbol.replace('.VN', '').upper()
                    df_bench = get_fireant_history(fa_symbol, start_date, end_date)
            
            if not df_bench.empty and not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df_bench['date'] = pd.to_datetime(df_bench['date'])
                df_merged = pd.merge(df[['date', 'close']], df_bench[['date', 'close']], on='date', how='inner', suffixes=('_main', '_bench')).sort_values('date')
                
                if len(df_merged) > 0:
                    df_merged['rel_main'] = (df_merged['close_main'] / df_merged['close_main'].iloc[0] - 1) * 100
                    df_merged['rel_bench'] = (df_merged['close_bench'] / df_merged['close_bench'].iloc[0] - 1) * 100
                    
                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Scatter(x=df_merged['date'], y=df_merged['rel_main'], name=f"{symbol}", line=dict(color='#00ADB5', width=2)))
                    fig_comp.add_trace(go.Scatter(x=df_merged['date'], y=df_merged['rel_bench'], name=f"{bench_symbol}", line=dict(color='#FF5252', width=2, dash='dot')))
                    
                    fig_comp.update_layout(
                        title=dict(text="Relative Performance Comparison (%)", font=dict(color='white')), 
                        font=dict(color="white"), # ALL WHITE
                        template="plotly_dark", plot_bgcolor='#131722', paper_bgcolor='#131722',
                        xaxis_title="Date", yaxis_title="Return (%)", hovermode="x unified",
                        legend=dict(font=dict(color="white"))
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)
                else: st.warning("No overlapping dates found.")
            else: st.warning(f"Could not fetch data for {bench_symbol}")

    # --- TAB 6: WATCHLIST ---
    with tab6:
        st.info("Watchlist feature is under development...")

    # --- TAB 7: SEASONALITY (ALL WHITE TEXT) ---
    with tab7:
        st.subheader("Seasonality Analysis")
        if len(df) > 30:
            df_s = df.copy()
            df_s['date'] = pd.to_datetime(df_s['date'])
            df_s = df_s.set_index('date').sort_index()
            
            monthly_prices = df_s['close'].resample('M').last()
            monthly_returns = monthly_prices.pct_change() * 100
            seasonality_month = monthly_returns.groupby(monthly_returns.index.month).mean()
            
            fig_month = go.Figure(go.Bar(
                x=seasonality_month.index, 
                y=seasonality_month.values,
                marker_color=['#00ADB5' if x > 0 else '#FF5252' for x in seasonality_month.values],
                text=[f"{x:.2f}%" for x in seasonality_month.values],
                textposition='auto',
                textfont=dict(color='white', size=13, weight='bold')
            ))
            fig_month.update_layout(
                title=dict(text="Average Monthly Return (%)", font=dict(color='white', size=18)),
                font=dict(color="white"), # ALL WHITE
                template="plotly_dark", plot_bgcolor='#131722', paper_bgcolor='#131722',
                xaxis=dict(title="Month", tickmode='array', tickvals=list(range(1, 13)), ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                yaxis=dict(title="Avg Return (%)")
            )
            st.plotly_chart(fig_month, use_container_width=True)

            st.markdown("---")

            daily_returns = df_s['close'].pct_change() * 100
            daily_returns_df = daily_returns.to_frame(name='ret')
            daily_returns_df['weekday'] = daily_returns_df.index.dayofweek
            seasonality_day = daily_returns_df.groupby('weekday')['ret'].mean()
            days_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            seasonality_day = seasonality_day[seasonality_day.index < 5]
            
            fig_day = go.Figure(go.Bar(
                x=[days_labels[i] for i in seasonality_day.index],
                y=seasonality_day.values,
                marker_color=['#00ADB5' if x > 0 else '#FF5252' for x in seasonality_day.values],
                text=[f"{x:.2f}%" for x in seasonality_day.values],
                textposition='auto',
                textfont=dict(color='white', size=13, weight='bold')
            ))
            fig_day.update_layout(
                title=dict(text="Average Daily Return by Weekday (%)", font=dict(color='white', size=18)),
                font=dict(color="white"), # ALL WHITE
                template="plotly_dark", plot_bgcolor='#131722', paper_bgcolor='#131722',
                xaxis=dict(title="Day of Week"), yaxis=dict(title="Avg Return (%)")
            )
            st.plotly_chart(fig_day, use_container_width=True)
        else:
            st.warning("Not enough data to calculate seasonality (Need > 30 days).")

    # --- TAB 8: FINANCIALS ---
    with tab8:
        st.subheader(f"Financial Reports (Source: FireAnt)")
        c_t8_1, c_t8_2, c_t8_3, c_t8_4 = st.columns(4)
        report_map = {1: "Balance Sheet", 2: "Income Statement", 3: "Cash Flow (Direct)", 4: "Cash Flow (Indirect)"}
        rpt_type = c_t8_1.selectbox("Report Type", [1, 2, 3, 4], format_func=lambda x: report_map[x])
        rpt_year = c_t8_2.number_input("Year", value=2024)
        rpt_quarter = c_t8_3.selectbox("Quarter", [1, 2, 3, 4], index=3)
        rpt_limit = c_t8_4.number_input("Limit", value=5)

        if st.button("📥 Load Report", type="primary"):
            with st.spinner(f"Analyzing Financial Data..."):
                raw_json = get_financial_report_raw(symbol, rpt_type, rpt_year, rpt_quarter, rpt_limit)
                df_fin = process_financial_report(raw_json)
                if not df_fin.empty:
                    if 'Item' in df_fin.columns: df_fin['Item'] = df_fin['Item'].str.replace(r'^[.\s]+', '', regex=True)
                    numeric_cols = [c for c in df_fin.columns if c != 'Item']
                    for col in numeric_cols: df_fin[col] = pd.to_numeric(df_fin[col], errors='coerce')
                    st.dataframe(df_fin.style.format("{:,.0f}", subset=numeric_cols, na_rep="-"), use_container_width=True, height=600, hide_index=True, column_config={"Item": st.column_config.TextColumn("Item/Indicator", width="large", pinned=True)})
                else: st.warning("No financial data found for this ticker.")

else:

    st.info("👈 Please select a Data Source & Ticker from the Sidebar to start.")
