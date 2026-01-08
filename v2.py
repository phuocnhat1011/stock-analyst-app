import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests

# ==============================================================================
# 1. PAGE CONFIG & PRO UI CSS (GIỮ NGUYÊN GIAO DIỆN ĐẸP)
# ==============================================================================
st.set_page_config(page_title="Pro Stock Analyst", layout="wide", page_icon="🔥")

st.markdown("""
<style>
    .stApp { background-color: #131722 !important; color: #E0E0E0 !important; }
    [data-testid="stSidebar"] { background-color: #0b0e11 !important; border-right: 1px solid #2A2E39; }
    [data-testid="stSidebar"] h1 { background: linear-gradient(to right, #00ADB5, #00F5FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900 !important; font-size: 28px !important; }
    [data-testid="stSidebar"] h3, label p { color: #FFFFFF !important; font-weight: 600 !important; }
    .stTextInput input, .stNumberInput input, .stDateInput input { background-color: #1E222D !important; color: #FFFFFF !important; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #1E222D; border-radius: 6px; color: #B2B5BE; font-weight: 600; margin-right: 5px; }
    .stTabs [aria-selected="true"] { background-color: #00ADB5 !important; color: #FFFFFF !important; }
    [data-testid="stMetricValue"] { color: #00ADB5 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. API & LOGIC FUNCTIONS (KHÔI PHỤC TOÀN BỘ)
# ==============================================================================

@st.cache_data(ttl=3000)
def get_fireant_token():
    try:
        url = "https://api.fireant.vn/authentication/login"
        payload = {"email": "rdteam.beqholdings@gmail.com", "password": "BqHgSK@2023"}
        return requests.post(url, json=payload).json().get("accessToken")
    except: return None

def get_fireant_history(symbol, start_date, end_date):
    token = get_fireant_token()
    if not token: return pd.DataFrame()
    url = f"https://api.fireant.vn/symbols/{symbol}/historical-quotes"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"startDate": start_date.strftime("%Y-%m-%d"), "endDate": end_date.strftime("%Y-%m-%d"), "limit": 5000}
    try:
        res = requests.get(url, headers=headers, params=params).json()
        df = pd.DataFrame(res).rename(columns={'date': 'date', 'priceHigh': 'high', 'priceLow': 'low', 'priceOpen': 'open', 'priceClose': 'close', 'dealVolume': 'volume'})
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'high', 'low', 'open', 'close', 'volume']]
    except: return pd.DataFrame()

def calculate_technical_score(df):
    if len(df) < 20: return 0, ["Insufficient Data"]
    score, drivers = 0, []
    latest = df.iloc[0]
    if latest['close'] > latest['ma20']: score += 2; drivers.append("✅ Price > MA20")
    if latest['ma20'] > latest['ma50']: score += 2; drivers.append("✅ MA20 > MA50")
    if latest['rsi'] < 30: score += 3; drivers.append("🟢 RSI Oversold")
    elif latest['rsi'] > 70: score -= 2; drivers.append("🔴 RSI Overbought")
    return max(0, score), drivers

def process_data(df):
    df = df.sort_values('date')
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain/loss))
    return df.sort_values('date', ascending=False)

def backtest_strategy(df, initial_capital):
    df_bt = df.copy().sort_values('date').reset_index(drop=True)
    cash, shares = initial_capital, 0
    equity_curve = []
    for i in range(len(df_bt)):
        price = df_bt.loc[i, 'close']
        if i > 0:
            if df_bt.loc[i-1, 'ma20'] <= df_bt.loc[i-1, 'ma50'] and df_bt.loc[i, 'ma20'] > df_bt.loc[i, 'ma50']:
                if cash > 0: shares, cash = cash / price, 0
            elif df_bt.loc[i-1, 'ma20'] >= df_bt.loc[i-1, 'ma50'] and df_bt.loc[i, 'ma20'] < df_bt.loc[i, 'ma50']:
                if shares > 0: cash, shares = shares * price, 0
        equity_curve.append(cash + (shares * price))
    df_bt['equity'] = equity_curve
    return df_bt, equity_curve[-1]

# ==============================================================================
# 3. MAIN APP (FIXED TAB BUG & FULL FEATURES)
# ==============================================================================

if 'main_df' not in st.session_state: st.session_state.main_df = None

with st.sidebar:
    st.title("🔥 PRO ANALYST")
    source = st.radio("Source:", ('FireAnt (VN)', 'Yahoo (Global)'))
    start = st.date_input("Start", datetime.date.today() - datetime.timedelta(days=365))
    end = st.date_input("End", datetime.date.today())
    ticker = st.text_input("Ticker:", value="SSI").upper()
    if st.button("🚀 LOAD DATA", type="primary"):
        with st.spinner("Fetching..."):
            raw = get_fireant_history(ticker, start, end) if source == 'FireAnt (VN)' else yf.download(ticker, start=start, end=end).reset_index().rename(columns=str.lower)
            if not raw.empty:
                st.session_state.main_df = process_data(raw)
                st.session_state.ticker = ticker

if st.session_state.main_df is not None:
    df, tk = st.session_state.main_df, st.session_state.ticker
    st.title(f"{tk} - DASHBOARD")

    # KHỞI TẠO ĐỦ 8 TABS (SỬ DỤNG INDEX ĐỂ KHÔNG BỊ NAME ERROR)
    tabs = st.tabs(["📊 Overview", "🕯️ Tech Chart", "📋 Raw Data", "⚙️ Backtest", "⚖️ Compare", "🔍 Watchlist", "📅 Seasonality", "💰 Financials"])

    with tabs[0]: # Overview
        latest = df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"{latest['close']:,.2f}")
        c2.metric("Change %", f"{((latest['close']-df.iloc[1]['close'])/df.iloc[1]['close']*100):.2f}%")
        c3.metric("RSI", f"{latest['rsi']:.2f}")
        c4.metric("Volume", f"{latest['volume']:,.0f}")
        
        score, drivers = calculate_technical_score(df)
        st.subheader(f"🤖 AI Score: {score}/10")
        for d in drivers: st.write(d)
        
        fig = go.Figure(go.Scatter(x=df['date'], y=df['close'], fill='tozeroy', line=dict(color='#00ADB5')))
        fig.update_layout(template="plotly_dark", font=dict(color="white"), paper_bgcolor='#131722', plot_bgcolor='#131722')
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]: # Technical
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close']), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['ma20'], name="MA20", line=dict(color="orange")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['ma50'], name="MA50", line=dict(color="red")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name="RSI", line=dict(color="#00ADB5")), row=2, col=1)
        fig.update_layout(template="plotly_dark", font=dict(color="white"), height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]: # Raw
        st.dataframe(df, use_container_width=True)

    with tabs[3]: # Backtest
        st.subheader("Strategy: MA20/50 Golden Cross")
        cap = st.number_input("Initial Capital (VND)", value=100_000_000)
        if st.button("▶️ Run Backtest"):
            res_df, final = backtest_strategy(df, cap)
            st.metric("Final Equity", f"{final:,.0f}", f"{((final-cap)/cap*100):.2f}%")
            fig = go.Figure(go.Scatter(x=res_df['date'], y=res_df['equity'], fill='tozeroy', line=dict(color='#00ADB5')))
            fig.update_layout(template="plotly_dark", font=dict(color="white"), title="Backtest Equity Curve")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[4]: # Compare
        bench = st.text_input("Benchmark Symbol:", value="VNINDEX").upper()
        if st.button("⚖️ Compare Now"):
            b_df = get_fireant_history(bench, start, end)
            if not b_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['date'], y=(df['close']/df['close'].iloc[-1]*100), name=tk))
                fig.add_trace(go.Scatter(x=b_df['date'], y=(b_df['close']/b_df['close'].iloc[-1]*100), name=bench))
                fig.update_layout(template="plotly_dark", font=dict(color="white"), title="Relative Return Comparison (%)")
                st.plotly_chart(fig, use_container_width=True)

    with tabs[6]: # Seasonality
        df_s = df.copy().set_index('date')
        m_ret = df_s['close'].resample('M').last().pct_change() * 100
        season = m_ret.groupby(m_ret.index.month).mean()
        fig = go.Figure(go.Bar(x=season.index, y=season.values, marker_color=['#00ADB5' if x > 0 else '#FF5252' for x in season.values]))
        fig.update_layout(template="plotly_dark", font=dict(color="white"), title="Avg Monthly Return (%)", xaxis=dict(tickvals=list(range(1,13))))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[7]: # Financials
        st.subheader("Financial Reports")
        r_type = st.selectbox("Report Type", [1, 2, 3, 4], format_func=lambda x: {1:"Balance Sheet", 2:"Income Statement", 3:"Cash Flow (D)", 4:"Cash Flow (I)"}[x])
        if st.button("📥 Load Financials"):
            token = get_fireant_token()
            url = f"https://api.fireant.vn/symbols/{tk}/full-financial-reports"
            data = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"type": r_type, "year": 2024, "quarter": 4, "limit": 5}).json()
            # Logic xử lý DataFrame đơn giản cho Financials
            st.write(data) 

else:
    st.info("👈 Please load data from the sidebar.")
