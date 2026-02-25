import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="Huzur Portföyü V9.0", layout="centered")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("Huzur Portföyü: Akıllı Dağılım Modülü (V9.0)")

# HEDEFLER: SPYM (%60), SCHD (%25), VEA (%15)
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

with st.sidebar:
    st.header("💰 Bu Ayki Bütçe")
    monthly_cash = st.number_input("Yatırılacak Tutar ($)", min_value=10, value=500, step=10)
    st.info("İdeal dağılım RSI (Ucuzluk) değerine göre hesaplanır.")

def analiz_et(ticker_list):
    data_list = []
    for t in ticker_list:
        h = yf.Ticker(t)
        hist = h.history(period="1y")
        rsi = ta.momentum.RSIIndicator(hist['Close']).rsi().iloc[-1]
        price = hist['Close'].iloc[-1]
        data_list.append({"Ticker": t, "Price": price, "RSI": rsi})
    return pd.DataFrame(data_list)

def dagilim_hesapla(df, cash):
    weights = targets.copy()
    for index, row in df.iterrows():
        t, rsi = row['Ticker'], row['RSI']
        if rsi > 65: weights[t] = 0 # Şişmişse alma
        elif rsi < 40: weights[t] += 0.1 # Ucuzsa ağırlığı artır
    
    total_w = sum(weights.values())
    final_weights = {k: v / total_w for k, v in weights.items()} if total_w > 0 else targets

    results = []
    for t in tickers:
        allocation = cash * final_weights.get(t, 0)
        price = df[df['Ticker'] == t]['Price'].values[0]
        results.append({
            "Enstrüman": t,
            "RSI (Ucuzluk)": round(df[df['Ticker'] == t]['RSI'].values[0], 1),
            "Yatırılacak ($)": round(allocation, 2),
            "Tahmini Lot": round(allocation / price, 2),
            "Durum": "🔥 FIRSAT" if df[df['Ticker'] == t]['RSI'].values[0] < 40 else ("🛡️ BEKLET" if df[df['Ticker'] == t]['RSI'].values[0] > 65 else "✅ NORMAL")
        })
    return pd.DataFrame(results)

if st.button("⚖️ BU AYIN PLANINI ÇIKAR"):
    raw_data = analiz_et(tickers)
    plan = dagilim_hesapla(raw_data, monthly_cash)
    st.table(plan)
    st.success("Plan hazır. IBKR üzerinden alımları bu miktarlara göre yapabilirsiniz.")
