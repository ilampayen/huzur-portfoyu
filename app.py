import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import time

warnings.filterwarnings('ignore')

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Huzur Portföyü V12.3", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("V12.3: Ana Ekran Kontrollü Quant-Prime Motoru")

# 2. STRATEJİK HEDEFLER
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

# =================================================================
# 3. ANA EKRAN KONTROL PANELİ (GİZLİ SİDEBAR İPTAL EDİLDİ)
# =================================================================
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    kasa_girdisi = st.text_input(
        "💰 Yatırılacak Net Nakit ($):", 
        value="500.00",
        help="Nokta veya virgül kullanabilirsiniz (Örn: 532,45)"
    )
    # Virgülü noktaya çevirip matematiksel rakama dönüştür
    try:
        monthly_cash = float(kasa_girdisi.replace(',', '.'))
    except ValueError:
        st.error("⚠️ Lütfen sadece rakam giriniz (Örn: 1250.45)")
        monthly_cash = 0.0

with col2:
    rejim = st.selectbox(
        "🌍 Piyasa Modu (Makro Rüzgar):",
        ["Normal / Denge", "Değer ve Temettüye Kaçış", "Agresif Büyüme", "Küresel Korku (Kriz)"]
    )
    
    macro_sentiment = {"SPYM": 0.0, "SCHD": 0.0, "VEA": 0.0}
    if rejim == "Değer ve Temettüye Kaçış": macro_sentiment = {"SPYM": -0.05, "SCHD": +0.10, "VEA": +0.05}
    elif rejim == "Agresif Büyüme": macro_sentiment = {"SPYM": +0.10, "SCHD": -0.05, "VEA": +0.05}
    elif rejim == "Küresel Korku (Kriz)": macro_sentiment = {"SPYM": -0.10, "SCHD": +0.15, "VEA": -0.10}

st.markdown("---")
# =================================================================

# 4. KÜTÜPHANESİZ ÇİFT MOTOR (PURE DUAL-ORACLE)
def veri_cek(ticker):
    # Motor 1: Yahoo Finance
    for _ in range(2):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if not df.empty and len(df) >= 200:
                return df['Close'], "Yahoo Finance"
        except: time.sleep(1)
    
    # Motor 2: Stooq
    try:
        url = f"https://stooq.com/q/d/l/?s={ticker}.US&i=d"
        df_stooq = pd.read_csv(url, index_col='Date', parse_dates=True)
        df_stooq = df_stooq.sort_index(ascending=True)
        if not df_stooq.empty and len(df_stooq) >= 200:
            return df_stooq['Close'], "Stooq (Doğrudan)"
    except: pass
        
    return pd.Series(), "Veri Yok"

@st.cache_data(ttl=3600)
def kurumsal_analiz(ticker_list):
    data_list = []
    for t in ticker_list:
        close_series, kaynak = veri_cek(t)
        if not close_series.empty:
            price = float(close_series.iloc[-1])
            sma200 = float(close_series.rolling(window=200).mean().iloc[-1])
            std200 = float(close_series.rolling(window=200).std().iloc[-1])
            high_52w = float(close_series.max())
            
            z_score = (price - sma200) / std200 if std200 > 0 else 0
            gunluk_getiri = close_series.pct_change().dropna()
            volatility = float(gunluk_getiri.std() * np.sqrt(252))
            drawdown = (price - high_52w) / high_52w
            
            data_list.append({
                "Ticker": t, "Price": price, "Z_Score": z_score, 
                "Volatility": volatility, "Drawdown": drawdown, "Kaynak": kaynak
            })
        else:
            st.error(f"🔴 KRİTİK HATA: {t} için veri çekilemedi.")
    return pd.DataFrame(data_list)

def taktiksel_dagilim(df, cash):
    if len(df) < len(tickers): return pd.DataFrame()
    raw_weights = {}
    
    for index, row in df.iterrows():
        t = row['Ticker']
        z = row['Z_Score']
        vol = row['Volatility']
        dd = row['Drawdown']
        base_w = targets[t]
        tilt = 1.0
        
        # Matematiksel Çarpanlar
        if z > 1.5: tilt -= 0.15      
        elif z < -1.0: tilt += 0.15   
        if dd < -0.10: tilt += 0.15      
        if vol > 0.20: tilt -= 0.10   
        
        tilt += macro_sentiment.get(t, 0)
        if tilt < 0.2: tilt = 0.2
        raw_weights[t] = base_w * tilt

    total_w = sum(raw_weights.values())
    final_weights = {k: v / total_w for k, v in raw_weights.items()}

    results = []
    for t in tickers:
        allocation = cash * final_weights.get(t, 0)
        row_data = df[df['Ticker'] == t].iloc[0]
        price = row_data['Price']
        lots = allocation / price
        
        durum = "✅ DENGELİ"
        if final_weights[t] > targets[t] * 1.15: durum = "🔥 MATEMATİKSEL FIRSAT"
        elif final_weights[t] < targets[t] * 0.85: durum = "🛡️ İSTATİSTİKSEL ŞİŞKİNLİK"

        results.append({
            "ETF": t,
            "Fiyat": f"{round(price, 2)} $",
            "Z-Skoru": f"{round(row_data['Z_Score'], 2)}σ",
            "Risk (Vol)": f"%{round(row_data['Volatility']*100, 1)}",
            "Ağırlık": f"%{round(final_weights[t]*100, 1)}",
            "Tutar ($)": round(allocation, 2),
            "Lot (IBKR)": round(lots, 3), 
            "Durum": durum,
            "Kaynak": row_data['Kaynak']
        })
    return pd.DataFrame(results)

# 5. MOTORU ÇALIŞTIRMA VE ÇIKTI
if monthly_cash > 0:
    if st.button(f"⚖️ {monthly_cash} $ İÇİN KURUMSAL DAĞILIMI HESAPLA"):
        with st.spinner("Motorlar çalışıyor. Z-Skorları ve Makro Rüzgarlar analiz ediliyor..."):
            raw_data = kurumsal_analiz(tickers)
            if not raw_data.empty and len(raw_data) == len(tickers):
                plan = taktiksel_dagilim(raw_data, monthly_cash)
                if not plan.empty:
                    st.dataframe(plan, use_container_width=True)
                    csv = plan.to_csv(index=False).encode('utf-8')
                    st.download_button(label="📥 Quant-Prime Tablosunu İndir", data=csv, file_name='v12_ana_ekran_dagilim.csv', mime='text/csv')
else:
    st.info("👆 Lütfen işleme başlamak için yukarıdaki kutuya elinizdeki net nakdi giriniz.")
