import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# إعدادات الصفحة للتجربة المثالية على الجوال
st.set_page_config(
    page_title="S2 Pro: Ultimate Quant Matrix",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تخصيص التصميم ليكون مطابقاً للواجهة الاحترافية (خلفية داكنة وتنسيق أنيق)
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
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# تنبيه التحليل التجريبي
st.markdown("<div class='disclaimer-box'>تحليل تجريبي للمحفظة التجريبية لغرض التعلم وليست توصية استثمارية او مالية</div>", unsafe_allow_html=True)

# قائمة الأسهم والمؤشرات الشاملة
stocks_dict = {
    "NDX (Nasdaq)": "^IXIC",
    "SPX (S&P 500)": "^GSPC",
    "QQQ (Nasdaq 100 ETF)": "QQQ",
    "SPY (S&P 500 ETF)": "SPY",
    "MU (Micron Technology)": "MU",
    "VIX (Volatility Index)": "^VIX",
    "TSLA (تسلا)": "TSLA",
    "NVDA (إنفيديا)": "NVDA",
    "AAPL (أبل)": "AAPL",
    "MSFT (مايكروسوفت)": "MSFT",
    "AMZN (أمازون)": "AMZN",
    "AMD (أيه إم دي)": "AMD"
}

# قوائم الاختيار في الواجهة
st.markdown("<p style='color: #848e9c; margin-bottom: 5px; font-size: 0.9rem;'>اختر السهم</p>", unsafe_allow_html=True)
selected_stock_name = st.selectbox("", list(stocks_dict.keys()), label_visibility="collapsed")
ticker = stocks_dict[selected_stock_name]

st.markdown("<p style='color: #848e9c; margin-bottom: 5px; font-size: 0.9rem;'>الفريم الزمني</p>", unsafe_allow_html=True)
timeframe_dict = {
    "دقائق 5": "5m",
    "دقائق 15": "15m",
    "دقائق 30": "30m",
    "ساعة 1": "1h",
    "ساعات 4": "4h",
    "يومي": "1d"
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
    st.error(f"عذراً يا أبو سعيد، لم نتمكن من جلب البيانات للرمز {selected_stock_name}.")
else:
    # حساب المؤشرات والفلاتر (EMA 50 + ATR)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()

    # محرك الأنماط والشموع
    lookback = 15
    df['Swing_High'] = df['High'].rolling(window=lookback).max()
    df['Swing_Low'] = df['Low'].rolling(window=lookback).min()

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    current_price = c1['Close']
    atr_val = c1['ATR']
    ema50 = c1['EMA_50']
    
    # فحص شروط الدخول والاتجاه
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
            signal = "WATCH (صاعد)"
            signal_display = "WATCH 🟢"
            sl = current_price - (1.5 * atr_val)
        else:
            signal = "WATCH (هابط)"
            signal_display = "WATCH 🔴"
            sl = current_price + (1.5 * atr_val)

    risk = abs(current_price - sl)
    if "CALL" in signal or "صاعد" in signal:
        t1, t2, t3, t4 = current_price + (1*risk), current_price + (2*risk), current_price + (3*risk), current_price + (4*risk)
    else:
        t1, t2, t3, t4 = current_price - (1*risk), current_price - (2*risk), current_price - (3*risk), current_price - (4*risk)

    # شريط الإشارة الرئيسي
    st.markdown(f"""
        <div class='signal-bar'>
            {selected_stock_name} [{selected_tf_name}] &nbsp;|&nbsp; 
            <span style='color: {'#0ecb81' if 'CALL' in signal or 'صاعد' in signal else '#f6465d'};'>{signal_display}</span> 
            &nbsp;|&nbsp; EP: ${current_price:.2f} &nbsp;|&nbsp; SL: ${sl:.2f}
        </div>
    """, unsafe_allow_html=True)

    # مصفوفة الأهداف مع حساب الوقت التقديري
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown(f"<div class='metric-card'><b>Target 1</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t1:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~10m</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><b>Target 3</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t3:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~30m</span></div>", unsafe_allow_html=True)
    with t_col2:
        st.markdown(f"<div class='metric-card'><b>Target 2</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t2:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~20m</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><b>Target 4</b><br><span style='color: #0ecb81; font-size: 1.1rem;'>${t4:.2f}</span><br><span style='color: #848e9c; font-size: 0.75rem;'>⏱️ ~40m</span></div>", unsafe_allow_html=True)

    # رسم الشارت بأسلوب احترافي داكن
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='السعر'
    ))
    
    # خط وقف الخسارة على الشارت
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
