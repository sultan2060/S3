import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Page configuration for mobile optimization
st.set_page_config(
    page_title="S2 Pro: Ultimate Quant Matrix",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom styling for a clean, professional LTR layout
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        background-color: #0e1117;
    }
    .disclaimer-box {
        background-color: #1a1d24;
        border: 1px solid #2f3542;
        color: #f0b90b;
        text-align: center;
        padding: 8px;
        border-radius: 6px;
        font-size: 0.85rem;
        margin-bottom: 15px;
    }
    .metric-card {
        background-color: #161a25;
        border: 1px solid #2a2e39;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
    }
    .signal-bar {
        background-color: #161a25;
        border: 1px solid #2a2e39;
        padding: 14px;
        border-radius: 8px;
        text-align: center;
        font-family: monospace;
        font-size: 0.95rem;
        direction: ltr;
        unicode-bidi: embed;
        margin-bottom: 15px;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# Experimental warning disclaimer
st.markdown("<div class='disclaimer-box'>Experimental paper-trading analysis for educational purposes — not financial advice</div>", unsafe_allow_html=True)

# Comprehensive Assets Dictionary
stocks_dict = {
    "NDX (Nasdaq)": "^IXIC",
    "SPX (S&P 500)": "^GSPC",
    "QQQ (Nasdaq 100 ETF)": "QQQ",
    "SPY (S&P 500 ETF)": "SPY",
    "MU (Micron Technology)": "MU",
    "VIX (Volatility Index)": "^VIX",
    "TSLA (Tesla)": "TSLA",
    "NVDA (NVIDIA)": "NVDA",
    "AAPL (Apple)": "AAPL",
    "MSFT (Microsoft)": "MSFT",
    "AMZN (Amazon)": "AMZN",
    "AMD (AMD)": "AMD"
}

# UI Selection Controls
st.markdown("<p style='color: #848e9c; margin-bottom: 5px; font-size: 0.9rem;'>Select Asset</p>", unsafe_allow_html=True)
selected_stock_name = st.selectbox("", list(stocks_dict.keys()), label_visibility="collapsed")
ticker = stocks_dict[selected_stock_name]

st.markdown("<p style='color: #848e9c; margin-bottom: 5px; font-size: 0.9rem;'>Timeframe</p>", unsafe_allow_html=True)
timeframe_dict = {
    "5 Minutes": "5m",
    "15 Minutes": "15m",
    "30 Minutes": "30m",
    "1 Hour": "1h",
    "4 Hours": "4h",
    "Daily": "1d"
}
selected_tf_name = st.selectbox("", list(timeframe_dict.keys()), label_visibility="collapsed")
timeframe = timeframe_dict[selected_tf_name]

period_map = {"5m": "5d", "15m": "10d", "30m": "20d", "1h": "1mo", "4h": "3mo", "1d": "6mo"}
data_period = period_map.get(timeframe, "1mo")

@st.cache_data(ttl=15)
def load_data(symbol, tf, period):
    try:
        df = yf.download(symbol, period=period, interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return None

df = load_data(ticker, timeframe, data_period)

if df is None or df.empty:
    st.error(f"Sorry, unable to fetch data for {selected_stock_name}.")
else:
    # Indicators & Filters (EMA 50 + ATR)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()

    # Swing Pattern Engine
    lookback = 15
    df['Swing_High'] = df['High'].rolling(window=lookback).max()
    df['Swing_Low'] = df['Low'].rolling(window=lookback).min()

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    current_price = c1['Close']
    atr_val = c1['ATR']
    ema50 = c1['EMA_50']
    
    # Strategy Logic
    is_bullish = (c2['Low'] <= df['Swing_Low'].iloc[-2]) and (c2['Close'] > c2['Open']) and (current_price > ema50)
    is_bearish = (c2['High'] >= df['Swing_High'].iloc[-2]) and (c2['Close'] < c2['Open']) and (current_price < ema50)

    if is_bullish:
        signal = "CALL"
        signal_display = "CALL 🟢"
        sl = c2['Low'] - (0.5 * atr_val)
    elif is_bearish:
        signal = "PUT"
        signal_display = "PUT 🔴"
        sl = c2['High'] + (0.5 * atr_val)
    else:
        if current_price > ema50:
            signal = "WATCH (Bullish)"
            signal_display = "WATCH 🟢"
            sl = current_price - (1.5 * atr_val)
        else:
            signal = "WATCH (Bearish)"
            signal_display = "WATCH 🔴"
            sl = current_price + (1.5 * atr_val)

    risk = abs(current_price - sl)
    if "CALL" in signal or "Bullish" in signal:
        t1, t2, t3, t4 = current_price + (1*risk), current_price + (2*risk), current_price + (3*risk), current_price + (4*risk)
    else:
        t1, t2, t3, t4 = current_price - (1*risk), current_price - (2*risk), current_price - (3*risk), current_price - (4*risk)

    # Main Signal Bar
    signal_color = '#0ecb81' if 'CALL' in signal or 'Bullish' in signal else '#f6465d'
    st.markdown(f"""
        <div class='signal-bar'>
            <b>{selected_stock_name}</b> [{selected_tf_name}] &nbsp;|&nbsp; 
            <span style='color: {signal_color};'>{signal_display}</span><br>
            EP: <b>${current_price:.2f}</b> &nbsp;|&nbsp; SL: <b>${sl:.2f}</b>
        </div>
    """, unsafe_allow_html=True)

    # Target Matrix (Properly ordered row-by-row: T1 & T2, then T3 & T4)
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        st.markdown(f"<div class='metric-card'><b>Target 1</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t1:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~10m</span></div>", unsafe_allow_html=True)
    with r1_c2:
        st.markdown(f"<div class='metric-card'><b>Target 2</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t2:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~20m</span></div>", unsafe_allow_html=True)

    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        st.markdown(f"<div class='metric-card'><b>Target 3</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t3:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~30m</span></div>", unsafe_allow_html=True)
    with r2_c2:
        st.markdown(f"<div class='metric-card'><b>Target 4</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t4:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~40m</span></div>", unsafe_allow_html=True)

    # Plotly Chart with SL and Key Levels
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price'
    ))
    
    fig.add_hline(y=sl, line_dash="dash", line_color="#f6465d", annotation_text="SL", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis_rangeslider_visible=False,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117'
    )

    st.plotly_chart(fig, use_container_width=True)
