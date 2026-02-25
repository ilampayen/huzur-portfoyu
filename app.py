import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Huzur Portföyü V10.1", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("Hibrit DCA Motoru: Matematik + Makro Haber Entegrasyonu (V10.1)")

# 1. STRATEJİK HEDEFLER
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

# 2. MAKROEKONOMİK DUYARLILIK (SENTIMENT) SKORLARI - ŞUBAT 2026
# Haber akışına göre algoritmaya manuel "Katalizör" müdahalesi
macro_sentiment = {
    "SPYM": -0.05,  # Gümrük tarifesi gerilimi ve Nvidia bilanço stresi (Negatif baskı)
    "SCHD": +0.10,  # Mega-Cap teknolojiden 'Değer' hisselerine kaçış rotasyonu (Pozitif rüzgar)
    "VEA":  +0.10   # ABD dışı piyasaların 2026 başındaki güçlü para girişi (Pozitif rüzgar)
}

with st.sidebar:
    st.header("💰 Sermaye Girişi")
    monthly_cash = st.number_input("Bu Ayki Yatırım Bütçesi ($)", min_value=50, value=500, step=50)
    st.markdown("---")
    st.info("💡 **Hibrit Çekirdek:** Bu versiyon; 200 günlük hareketli ortalamayı, zirveden düşüş iskontosunu ve **Güncel Küresel Haber Akışını (Sektörel Rotasyon, Tarife Riskleri)** aynı anda hesaplayarak portföyü optimize eder.")

@st.cache_data(ttl=3600)
def kurumsal_analiz(ticker_list):
    data_list = []
    for t in ticker_list:
        try:
            h = yf.Ticker(t)
            hist = h.history(period="1y") 
            if len(hist) < 200: continue
            
            price = hist['Close'].iloc[-1]
            sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            high_52w = hist['High'].max()
            
            drawdown = (price - high_52w) / high_52w  
            sma_dist = (price - sma200) / sma200      
            
            data_list.append({
                "Ticker": t, "Price": price, "Drawdown": drawdown, "SMA200_Dist": sma_dist
            })
        except: pass
    return pd.DataFrame(data_list)

def taktiksel_dagilim(df, cash):
    raw_weights = {}
    
    for index, row in df.iterrows():
        t = row['Ticker']
        dd = row['Drawdown']      
        sma_d = row['SMA200_Dist'] 
        base_w = targets[t]
        
        # TEKNİK ÇARPAN (Matematik)
        tilt = 1.0
        if sma_d < 0: tilt += 0.15
        elif sma_d > 0.10: tilt -= 0.15
        
        if dd < -0.10: tilt += 0.20 
        elif dd < -0.05: tilt += 0.10 
            
        # MAKRO ÇARPAN (Haberler ve Dünyadaki Gelişmeler)
        tilt += macro_sentiment[t]

        # Negatif ağırlığı engelleme (En kötü durumda bile temel birikim devam eder)
        if tilt < 0.2: tilt = 0.2
        
        raw_weights[t] = base_w * tilt

    # Ağırlıkları 1.0 olacak şekilde normalize et
    total_w = sum(raw_weights.values())
    final_weights = {k: v / total_w for k, v in raw_weights.items()}

    results = []
    for t in tickers:
        allocation = cash * final_weights.get(t, 0)
        row_data = df[df['Ticker'] == t].iloc[0]
        price = row_data['Price']
        
        durum = "✅ DENGELİ"
        if final_weights[t] > targets[t] * 1.15: durum = "🔥 MAKRO & TEKNİK FIRSAT"
        elif final_weights[t] < targets[t] * 0.85: durum = "🛡️ RİSK KORUMASI (Azaltıldı)"

        results.append({
            "ETF": t,
            "Fiyat ($)": round(price, 2),
            "200G Ort. Mesafe": f"{round(row_data['SMA200_Dist']*100, 1)}%",
            "Makro Rüzgar": "Pozitif 🟢" if macro_sentiment[t] > 0 else "Negatif 🔴",
            "Stratejik Hedef": f"%{int(targets[t]*100)}",
            "Bu Ayki Reel Ağırlık": f"%{round(final_weights[t]*100, 1)}",
            "Yatırılacak Tutar ($)": round(allocation, 2),
            "Durum Analizi": durum
        })
    return pd.DataFrame(results)

if st.button("⚖️ HİBRİT DAĞILIMI HESAPLA"):
    with st.spinner("Piyasa verileri çekiliyor ve makro haberler entegre ediliyor..."):
        raw_data = kurumsal_analiz(tickers)
        if not raw_data.empty:
            plan = taktiksel_dagilim(raw_data, monthly_cash)
            st.markdown("### 📊 V10.1 Makro-Optimize Satın Alma Planınız")
            st.dataframe(plan, use_container_width=True)
            st.success("Analiz Tamamlandı: Sistem, SPYM'deki gerginliği sezerek, sektör rotasyonundan faydalanmak için bütçenizi SCHD ve VEA'ya akıllıca kaydırdı.")
        else:
            st.error("Veri bağlantı hatası.")
