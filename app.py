import streamlit as st
import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import numpy as np
import warnings
import time

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Huzur Portföyü V12.0 Quant-Prime", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("V12.0: Çift-Oracle (Yahoo+Stooq) ve Z-Skor Motoru")

# 1. STRATEJİK HEDEFLER
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

# 2. KONTROL PANELİ
with st.sidebar:
    st.header("1️⃣ Sermaye ve Operasyon")
    monthly_cash = st.number_input(
        "Elimdeki Net Nakit ($):", 
        min_value=1.0, 
        value=500.0, 
        step=50.0, 
        format="%.2f"
    )
    
    st.header("2️⃣ Makroekonomik Rejim")
    rejim = st.selectbox(
        "Piyasa Modu:",
        ["Normal / Denge", "Değer ve Temettüye Kaçış", "Agresif Büyüme", "Küresel Korku (Kriz)"]
    )
    
    # Rejim Çarpanları
    macro_sentiment = {"SPYM": 0.0, "SCHD": 0.0, "VEA": 0.0}
    if rejim == "Değer ve Temettüye Kaçış": macro_sentiment = {"SPYM": -0.05, "SCHD": +0.10, "VEA": +0.05}
    elif rejim == "Agresif Büyüme": macro_sentiment = {"SPYM": +0.10, "SCHD": -0.05, "VEA": +0.05}
    elif rejim == "Küresel Korku (Kriz)": macro_sentiment = {"SPYM": -0.10, "SCHD": +0.15, "VEA": -0.10}

# 3. ÇİFT MOTORLU VERİ ÇEKİMİ (DUAL-ORACLE)
def veri_cek(ticker):
    # MOTOR 1: Yahoo Finance (Ana Motor)
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if not df.empty and len(df) >= 200:
            return df['Close'], "Yahoo Finance"
    except: pass
    
    # MOTOR 2: Stooq (Açık Kaynak Yedek Motor)
    try:
        st_ticker = f"{ticker}.US" # Stooq Amerikan hisseleri için .US uzantısı ister
        df_stooq = web.DataReader(st_ticker, 'stooq')
        df_stooq = df_stooq.sort_index(ascending=True) # Stooq ters tarihli verir, düzelt
        if not df_stooq.empty and len(df_stooq) >= 200:
            return df_stooq['Close'], "Stooq (Yedek)"
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
            
            # 1. Z-Skoru (Kurumsal Şişkinlik Ölçer)
            z_score = (price - sma200) / std200 if std200 > 0 else 0
            
            # 2. Yıllıklandırılmış Volatilite (Risk Ölçer)
            gunluk_getiri = close_series.pct_change().dropna()
            volatility = float(gunluk_getiri.std() * np.sqrt(252))
            
            # 3. Zirveden Düşüş (İskonto)
            drawdown = (price - high_52w) / high_52w
            
            data_list.append({
                "Ticker": t, "Price": price, "Z_Score": z_score, 
                "Volatility": volatility, "Drawdown": drawdown, "Kaynak": kaynak
            })
        else:
            st.error(f"🔴 KRİTİK HATA: {t} için ne Yahoo ne de Stooq veri sağlayamadı.")
            
    return pd.DataFrame(data_list)

# 4. İLERİ DÜZEY KURUMSAL DAĞILIM (QUANT TILT)
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
        
        # A) Z-Skor Müdahalesi (İstatiksel Çekim Kuvveti)
        if z > 1.5: tilt -= 0.15      # Aşırı şişkin (2 Standart sapmaya yakın)
        elif z < -1.0: tilt += 0.15   # Aşırı satış yemiş (Ucuz)
        
        # B) Zirveden Düşüş Müdahalesi
        if dd < -0.10: tilt += 0.15      
        
        # C) Volatilite (Risk Paritesi) Müdahalesi
        if vol > 0.20: tilt -= 0.10   # Fon çok oynaksa (%20 üstü), güvenliğe kaç ve ağırlığı kıs
        
        # D) Makro Rejim Müdahalesi
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
        z_skor_gorsel = round(row_data['Z_Score'], 2)
        
        durum = "✅ DENGELİ"
        if final_weights[t] > targets[t] * 1.15: durum = "🔥 MATEMATİKSEL FIRSAT"
        elif final_weights[t] < targets[t] * 0.85: durum = "🛡️ İSTATİSTİKSEL ŞİŞKİNLİK"

        results.append({
            "ETF": t,
            "Fiyat": f"{round(price, 2)} $",
            "Z-Skoru": f"{z_skor_gorsel}σ",
            "Risk (Volatilite)": f"%{round(row_data['Volatility']*100, 1)}",
            "Bu Ayki Pay": f"%{round(final_weights[t]*100, 1)}",
            "Yatırılacak ($)": round(allocation, 2),
            "Alınacak Lot": round(lots, 3), 
            "Durum Analizi": durum,
            "Veri Kaynağı": row_data['Kaynak']
        })
    return pd.DataFrame(results)

# 5. EKRAN ÇIKTILARI
st.markdown(f"### 🎯 Quant-Prime Bütçe Dağılımı: **{monthly_cash} $**")

if st.button("⚖️ KURUMSAL DAĞILIMI HESAPLA (Dual-Oracle)"):
    with st.spinner("Çift Motor aktif. Yahoo/Stooq taranıyor. Z-Skorları ve Risk Paritesi hesaplanıyor..."):
        raw_data = kurumsal_analiz(tickers)
        
        if not raw_data.empty and len(raw_data) == len(tickers):
            plan = taktiksel_dagilim(raw_data, monthly_cash)
            if not plan.empty:
                st.dataframe(plan, use_container_width=True)
                
                csv = plan.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Quant-Prime Tablosunu İndir", data=csv, file_name='v12_quant_prime.csv', mime='text/csv')
                
                st.info("💡 **Denetçi Raporu:** Sistem; basit yüzdelikler yerine Z-Skorlarını (Standart Sapma) ve fonların kendi içindeki Volatilite (Risk) oranlarını hesaplayarak, trilyonluk fonların kullandığı 'Risk Paritesi' mantığıyla paranızı böldü.")
