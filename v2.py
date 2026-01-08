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
    /* 1. GLOBAL DARK BACKGROUND */
    .stApp {
        background-color: #131722 !important;
        color: #E0E0E0 !important;
        font-family: 'Inter', sans-serif;
    }

    /* 2. PRO SIDEBAR DESIGN */
    [data-testid="stSidebar"] {
        background-color: #0b0e11 !important;
        border-right: 1px solid #2A2E39;
    }
    [data-testid="stSidebar"] h1 {
        background: linear-gradient(to right, #00ADB5, #00F5FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900 !important;
        font-size: 28px !important;
        margin-bottom: 20px !important;
    }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label p, [data-testid="stSidebar"] .stRadio label p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: linear-gradient(90deg, #00ADB5 0%, #007E85 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(0, 173, 181, 0.4);
        transition: all 0.3s ease;
        margin-top: 15px;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 173, 181, 0.6);
    }

    /* 3. INPUT FIELDS STYLING */
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #1E222D !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #00ADB5 !important;
    }
    div[data-baseweb="input"] {
        background-color: #1E222D !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    /* Bright Labels for Inputs */
    .stNumberInput label p, .stTextInput label p, .stSelectbox label p {
        color: #FFFFFF !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    /* 4. METRIC CARDS */
    [data-testid="stMetricLabel"] {
        color: #b0b3b8 !important; 
        font-size: 15px !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00ADB5 !important;
        font-weight: 700 !important;
        font-size: 28px !important;
    }
    [data-testid="stMetricDelta"] svg { fill: #00ADB5 !important; }
    [data-testid="stMetricDelta"] > div { color: #00ADB5 !important; font-weight: 600 !important; }

    /* 5. TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: #1E222D;
        border-radius: 6px;
        color: #B2B5BE;
        border: 1px solid #2A2E39;
        font-weight: 600;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00ADB5 !important;
        color: #FFFFFF !important;
        border: 1px solid #00ADB5 !important;
        box-shadow: 0 0 10px rgba(0, 173, 181, 0.3);
    }
    
    /* 6. DROPDOWNS & TABLE */
    div[data-baseweb="select"] > div { background-color: #1E222D !important; color: #FFFFFF !important; border: 1px solid #374151 !important; }
    li[data-baseweb="option"] { color: white !important; }
    div[data-baseweb="select"] span { color: #FFFFFF !important; }
    th { color: #00ADB5 !important; font-size: 16px !important;}

</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FIREANT API BACKEND
# ==============================================================================

@st.cache_data(ttl=3000)
def get_fireant_token():
    url = "https://api.fireant.vn/authentication/login"
    headers = {"Content-Type": "application/json"}
    payload = {
        "email": "rdteam.beqholdings@gmail.com",
        "password": "BqHgSK@2023"
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("accessToken")
    except Exception:
        return None

def get_fireant_history(symbol, start_date, end_date):
    token = get_fireant_token()
    if not token: return pd.DataFrame()

    url = f"https://api.fireant.vn/symbols/{symbol}/historical-quotes"
    s_date = start_date.strftime("%Y-%m-%dT00:00:00")
    e_date = end_date.strftime("%Y-%m-%dT23:59:59")
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {"startDate": s_date, "endDate": e_date, "offset": 0, "limit": 5000}

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        raw = res.json()
        if not raw: return pd.DataFrame()

        df = pd.DataFrame(raw)
        map_cols = {
            'date': 'date', 'priceHigh': 'high', 'priceLow': 'low', 
            'priceOpen': 'open', 'priceClose': 'close', 'dealVolume': 'volume'
        }
        df = df.rename(columns={k: v for k, v in map_cols.items() if k in df.columns})
        df = df[['date', 'high', 'low', 'open', 'close', 'volume']]
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"FireAnt API Error: {e}")
        return pd.DataFrame()

def get_financial_report_raw(symbol, report_type, year, quarter, limit=5):
    token = get_fireant_token()
    if not token: return []

    url = f"https://api.fireant.vn/symbols/{symbol}/full-financial-reports"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"type": report_type, "year": year, "quarter": quarter, "limit": limit}

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Financial API Error: {e}")
        return []

def process_financial_report(data_json):
    if not data_json: return pd.DataFrame()
    processed_rows = []
    all_periods = set()
    
    for item in data_json:
        row = {'name': item.get('name')}
        values_list = item.get('values', [])
        if values_list:
            for v in values_list:
                col_name = f"Q{v.get('quarter')}/{v.get('year')}" if v.get('quarter') else f"{v.get('year')}"
                row[col_name] = v.get('value')
                all_periods.add(col_name)
        processed_rows.append(row)
    
    df = pd.DataFrame(processed_rows)
    if df.empty: return df
    
    period_cols = sorted(list(all_periods), reverse=True)
    df = df.rename(columns={'name': 'Item'}) 
    return df[['Item'] + [c for c in period_cols if c in df.columns]]

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

def calculate_rsi(data, window=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_technical_score(df):
    score = 0
    drivers = []
    if len(df) < 20: return 0, ["Insufficient Data"]
    latest = df.iloc[0]
    
    if latest['close'] > latest['ma20']:
        score += 2; drivers.append("✅ Price > MA20 (Short-term Bullish)")
    else: drivers.append("⚠️ Price < MA20 (Short-term Bearish)")
        
    if latest['ma20'] > latest['ma50']:
        score += 2; drivers.append("✅ MA20 > MA50 (Mid-term Bullish)")
    else: drivers.append("⚠️ MA20 < MA50 (Mid-term Bearish)")
        
    rsi = latest['rsi']
    if rsi < 30: score += 3; drivers.append("🟢 RSI Oversold (<30) - Buy")
    elif 30 <= rsi <= 70: score += 1; drivers.append("⚪ RSI Neutral")
    else: score -= 2; drivers.append("🔴 RSI Overbought (>70) - Risk")
        
    vol_avg_20 = df['volume'].iloc[0:20].mean()
    if latest['volume'] > vol_avg_20:
        score += 1; drivers.append("✅ Volume Spike (>20MA)")
    else: drivers.append("⚪ Low Volume")
        
    return max(0, score), drivers

def process_dataframe(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if isinstance(df.index, pd.DatetimeIndex): df = df.reset_index()
    
    df.columns = df.columns.str.strip().str.lower()
    if 'date' not in df.columns and 'index' in df.columns: df = df.rename(columns={'index': 'date'})
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=True)
    
    if 'close' in df.columns:
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['rsi'] = calculate_rsi(df)
        
        std_dev = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['ma20'] + (std_dev * 2)
        df['bb_lower'] = df['ma20'] - (std_dev * 2)
        
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

    return df.sort_values('date', ascending=False).reset_index(drop=True)

def backtest_strategy(df, initial_capital):
    df = df.copy().sort_values('date', ascending=True).reset_index(drop=True)
    cash = initial_capital
    shares = 0
    equity_curve = []
    buy_signals = [] 
    sell_signals = [] 
    start_idx = 50 
    
    for i in range(len(df)):
        price = df.loc[i, 'close']
        current_equity = cash + (shares * price)
        equity_curve.append(current_equity)
        if i < start_idx: continue
            
        ma20_curr = df.loc[i, 'ma20']
        ma50_curr = df.loc[i, 'ma50']
        ma20_prev = df.loc[i-1, 'ma20']
        ma50_prev = df.loc[i-1, 'ma50']
        date = df.loc[i, 'date']
        
        if (ma20_prev <= ma50_prev) and (ma20_curr > ma50_curr):
            if shares == 0:
                shares = cash / price
                cash = 0
                buy_signals.append({'date': date, 'price': price})
        elif (ma20_prev >= ma50_prev) and (ma20_curr < ma50_curr):
            if shares > 0:
                cash = shares * price
                shares = 0
                sell_signals.append({'date': date, 'price': price})
                
    final_equity = equity_curve[-1]
    df['equity'] = equity_curve
    return {
        'df_result': df, 'final_equity': final_equity,
        'pct_return': ((final_equity - initial_capital) / initial_capital) * 100,
        'total_trades': len(sell_signals)
    }

# ==============================================================================
# 4. MAIN APP LOGIC
# ==============================================================================

if 'data' not in st.session_state: st.session_state['data'] = None
if 'ticker' not in st.session_state: st.session_state['ticker'] = None

# --- SIDEBAR ---
st.sidebar.title("🔥 PRO ANALYST")
st.sidebar.markdown("---")
data_source = st.sidebar.radio(
    "Data Source:",
    ('FireAnt API (Vietnam)', 'Yahoo Finance (Global)')
)

st.sidebar.subheader("Time Period")
today = datetime.date.today()
last_year = today - datetime.timedelta(days=365)
start_date = st.sidebar.date_input("Start Date", last_year)
end_date = st.sidebar.date_input("End Date", today)

# --- LOAD DATA HANDLER ---
if data_source == 'FireAnt API (Vietnam)':
    raw_ticker = st.sidebar.text_input("Ticker (e.g., SSI, FPT):", value="SSI").upper().strip()
    vnstock_ticker = raw_ticker.replace('.VN', '')
    
    if st.sidebar.button("🚀 Load Data", type="primary"):
        with st.spinner(f"Connecting to FireAnt Server..."):
            df_fireant = get_fireant_history(vnstock_ticker, start_date, end_date)
            if not df_fireant.empty:
                st.success("Data Loaded Successfully!")
                st.session_state['data'] = process_dataframe(df_fireant)
                st.session_state['ticker'] = vnstock_ticker
            else:
                st.error("Error loading data. Please check ticker.")

elif data_source == 'Yahoo Finance (Global)':
    raw_ticker = st.sidebar.text_input("Symbol (e.g., AAPL, BTC-USD):", value="AAPL").upper().strip()
    if st.sidebar.button("🚀 Load Data"):
        yahoo_ticker = raw_ticker if not raw_ticker.isalpha() or len(raw_ticker) > 3 else f"{raw_ticker}.VN"
        with st.spinner(f'Downloading {yahoo_ticker}...'):
            df_yahoo = yf.download(yahoo_ticker, start=start_date, end=end_date + datetime.timedelta(days=1), progress=False)
            if not df_yahoo.empty:
                st.session_state['data'] = process_dataframe(df_yahoo)
                st.session_state['ticker'] = raw_ticker
            else:
                st.error("Symbol not found!")

# --- MAIN DASHBOARD ---
if st.session_state['data'] is not None:
    df = st.session_state['data']
    symbol = st.session_state.get('ticker', 'Unknown')
    st.title(f"{symbol} - ANALYTICS DASHBOARD")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Overview", "🕯️ Technical Chart", "📋 Raw Data", "⚙️ Backtest",
        "⚖️ Compare", "🔍 Watchlist", "📅 Seasonality", "💰 Financials"
    ])
    
    # --- TAB 1: OVERVIEW (ALL WHITE TEXT) ---
    with tab1:
        st.subheader("Market Overview")
        if len(df) > 0:
            latest = df.iloc[0]
            close = latest['close']
            prev = df.iloc[1]['close'] if len(df) > 1 else close
            change = close - prev
            pct = (change / prev) * 100
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Price", f"{close:,.2f}", f"{change:,.2f} ({pct:.2f}%)")
            c2.metric("Change", f"{change:,.2f}", f"{pct:.2f}%")
            c3.metric("52W High", f"{df['high'].max():,.2f}")
            c4.metric("Volume", f"{latest.get('volume', 0):,.0f}")
        st.markdown("---")
        
        df_chart = df.sort_values('date', ascending=True)
        fig_area = go.Figure(go.Scatter(
            x=df_chart['date'], y=df_chart['close'], 
            fill='tozeroy', mode='lines',
            line=dict(color='#00ADB5', width=2), 
            fillcolor='rgba(0, 173, 181, 0.2)', name='Close'
        ))
        fig_area.update_layout(
            title=dict(text=f"{symbol} - Price History", font=dict(color='white')), # Title White
            height=400, 
            template="plotly_dark", 
            plot_bgcolor='#131722', paper_bgcolor='#131722',
            margin=dict(t=40, l=0, r=0),
            font=dict(color="white"), # ALL CHART TEXT WHITE
            xaxis=dict(showgrid=False, tickmode='auto', nticks=10), 
            yaxis=dict(gridcolor='#2A2E39'),
            hovermode="x unified"
        )
        st.plotly_chart(fig_area, use_container_width=True)

        st.subheader("🤖 AI Technical Score")
        tech_score, tech_drivers = calculate_technical_score(df)
        col_score, col_drivers = st.columns([1, 2])
        with col_score:
            st.metric("Technical Score", f"{tech_score}/10")
            if tech_score >= 6: st.success("SIGNAL: STRONG BUY")
            elif tech_score >= 3: st.warning("SIGNAL: NEUTRAL")
            else: st.error("SIGNAL: SELL")
        with col_drivers:
            for driver in tech_drivers: st.markdown(f"- {driver}")

    # --- TAB 2: TECHNICAL (ALL WHITE TEXT) ---
    with tab2:
        st.subheader("Advanced Technical Chart")
        with st.form(key='tech_chart_form'):
            c1, c2, c3 = st.columns(3)
            show_ma20 = c1.checkbox("Show MA20", True)
            show_ma50 = c2.checkbox("Show MA50", True)
            show_bb = c3.checkbox("Bollinger Bands", False)
            st.form_submit_button("Update Chart")
        
        df_chart = df.sort_values('date', ascending=True)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df_chart['date'], open=df_chart['open'], high=df_chart['high'], 
            low=df_chart['low'], close=df_chart['close'], name='OHLC'), row=1, col=1)
        if show_ma20 and 'ma20' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['ma20'], line=dict(color='#F6A623', width=1), name='MA20'), row=1, col=1)
        if show_ma50 and 'ma50' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['ma50'], line=dict(color='#E91E63', width=1), name='MA50'), row=1, col=1)
        if 'rsi' in df_chart.columns:
            fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['rsi'], line=dict(color='#00ADB5'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        if 'macd' in df_chart.columns:
            fig.add_trace(go.Bar(x=df_chart['date'], y=df_chart['macd_hist'], marker_color='#555', name='MACD Hist'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['macd'], line=dict(color='orange'), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['macd_signal'], line=dict(color='blue'), name='Signal'), row=3, col=1)
        
        # APPLY WHITE FONT
        fig.update_layout(
            height=800, xaxis_rangeslider_visible=False, 
            template="plotly_dark", plot_bgcolor='#131722', paper_bgcolor='#131722', 
            font=dict(color="white"), # ALL WHITE
            yaxis=dict(gridcolor='#2A2E39'), yaxis2=dict(gridcolor='#2A2E39'), yaxis3=dict(gridcolor='#2A2E39')
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: RAW DATA ---
    with tab3:
        st.dataframe(df, use_container_width=True)

    # --- TAB 4: BACKTEST (ALL WHITE TEXT) ---
    with tab4:
        st.subheader("🛠️ Strategy Backtest (MA Golden Cross)")
        st.markdown("""
        <div style='background-color: #1E222D; padding: 15px; border-radius: 8px; border: 1px solid #2A2E39; margin-bottom: 20px;'>
            <h4 style='color: #00ADB5; margin: 0;'>📝 Strategy Logic:</h4>
            <ul style='color: #E0E0E0; margin-top: 10px;'>
                <li><b>BUY SIGNAL:</b> When <b>MA20</b> crosses ABOVE <b>MA50</b> (Uptrend Confirmation).</li>
                <li><b>SELL SIGNAL:</b> When <b>MA20</b> crosses BELOW <b>MA50</b> (Downtrend Warning).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        initial_cap = st.number_input("Initial Capital (VND)", value=100_000_000, step=10_000_000)
        if st.button("▶️ Run Backtest"):
            res = backtest_strategy(df, initial_cap)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Return", f"{res['pct_return']:.2f}%")
            m2.metric("Final Equity", f"{res['final_equity']:,.0f}")
            m3.metric("Total Trades", res['total_trades'])
            fig_eq = go.Figure(go.Scatter(x=res['df_result']['date'], y=res['df_result']['equity'], fill='tozeroy', line=dict(color='#00ADB5')))
            fig_eq.update_layout(
                title=dict(text="Equity Curve", font=dict(color='white')), 
                font=dict(color="white"), # ALL WHITE
                template="plotly_dark", height=400, plot_bgcolor='#131722', paper_bgcolor='#131722'
            )
            st.plotly_chart(fig_eq, use_container_width=True)

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