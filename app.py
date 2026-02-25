import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Huzur Portföyü V10.0", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("Kurumsal DCA & Akıllı Varlık Dağılım Motoru (V10.0)")

# 1. STRATEJİK HEDEFLER (Sizin Genetiğiniz)
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

with st.sidebar:
    st.header("💰 Sermaye Girişi")
    monthly_cash = st.number_input("Bu Ayki Yatırım Bütçesi ($)", min_value=50, value=500, step=50)
    st.markdown("---")
    st.info("💡 **Bilimsel Çekirdek:** Bu sistem RSI kullanmaz. Dağılımlar; 52 Haftalık Zirveden Düşüş (Drawdown) ve 200 Günlük Hareketli Ortalama (SMA) sapmalarına göre **Taktiksel Ağırlıklandırma (Tactical Tilt)** yöntemiyle hesaplanır.")

@st.cache_data(ttl=3600)
def kurumsal_analiz(ticker_list):
    data_list = []
    for t in ticker_list:
        try:
            h = yf.Ticker(t)
            # 200 SMA için 1 yıllık veri şarttır (Yaklaşık 252 işlem günü)
            hist = h.history(period="1y") 
            if len(hist) < 200: continue
            
            price = hist['Close'].iloc[-1]
            sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            high_52w = hist['High'].max()
            
            # Akademik Metrikler
            drawdown = (price - high_52w) / high_52w  # Negatif değer (Örn: -0.05 = %5 düşüş)
            sma_dist = (price - sma200) / sma200      # 200 günlüğe uzaklık
            
            data_list.append({
                "Ticker": t, 
                "Price": price, 
                "Drawdown": drawdown, 
                "SMA200_Dist": sma_dist
            })
        except: pass
    return pd.DataFrame(data_list)

def taktiksel_dagilim(df, cash):
    raw_weights = {}
    
    for index, row in df.iterrows():
        t = row['Ticker']
        dd = row['Drawdown']      # Örn: -0.08
        sma_d = row['SMA200_Dist'] # Örn: 0.05
        base_w = targets[t]
        
        # TILT (Sapma) ÇARPANLARI HESAPLAMASI
        tilt_multiplier = 1.0
        
        # 1. Kural: 200 SMA Altındaysa iskontoludur, ağırlığı artır.
        if sma_d < 0:
            tilt_multiplier += 0.15
        # 2. Kural: 200 SMA'nın %10'dan fazla üstündeyse aşırı şişmiştir, alımı hafiflet.
        elif sma_d > 0.10:
            tilt_multiplier -= 0.15
            
        # 3. Kural: Zirveden Düşüş (Drawdown) fırsatı. Düşüş derinleştikçe alımı agresifleştir.
        if dd < -0.10:
            tilt_multiplier += 0.20 # %10'dan fazla düşmüşse ciddi fırsat
        elif dd < -0.05:
            tilt_multiplier += 0.10 # %5-%10 arası düşüş
            
        # Yeni Taktiksel Ağırlık (Asla 0'a inmez, uzun vade felsefesi korunur)
        raw_weights[t] = base_w * tilt_multiplier

    # Ağırlıkları 1.0 (Yani %100) olacak şekilde normalize et
    total_w = sum(raw_weights.values())
    final_weights = {k: v / total_w for k, v in raw_weights.items()}

    results = []
    for t in tickers:
        allocation = cash * final_weights.get(t, 0)
        row_data = df[df['Ticker'] == t].iloc[0]
        price = row_data['Price']
        
        # Durum Belirleyici
        durum = "✅ NORMAL"
        if final_weights[t] > targets[t] * 1.15: durum = "🔥 İSKONTOLU (Ağırlık Artırıldı)"
        elif final_weights[t] < targets[t] * 0.85: durum = "🛡️ ŞİŞKİN (Ağırlık Azaltıldı)"

        results.append({
            "ETF": t,
            "Fiyat ($)": round(price, 2),
            "Zirveye Uzaklık": f"{round(row_data['Drawdown']*100, 1)}%",
            "200G Ort. Mesafe": f"{round(row_data['SMA200_Dist']*100, 1)}%",
            "Stratejik Hedef": f"%{int(targets[t]*100)}",
            "Bu Ayki Reel Ağırlık": f"%{round(final_weights[t]*100, 1)}",
            "Yatırılacak Tutar ($)": round(allocation, 2),
            "Durum Analizi": durum
        })
    return pd.DataFrame(results)

if st.button("⚖️ BİLİMSEL DAĞILIMI HESAPLA"):
    with st.spinner("Kurumsal metrikler ve iskonto oranları hesaplanıyor..."):
        raw_data = kurumsal_analiz(tickers)
        if not raw_data.empty:
            plan = taktiksel_dagilim(raw_data, monthly_cash)
            
            st.markdown("### 📊 V10.0 Akıllı Satın Alma Planınız")
            st.dataframe(plan, use_container_width=True)
            
            st.success("Analiz Tamamlandı: Sistem, paranızı uzun vadeli ortalamalara (200-SMA) ve gerçek iskontolara (Drawdown) göre matematiksel olarak en verimli limanlara kaydırdı.")
        else:
            st.error("Veri çekilirken bir hata oluştu. Lütfen tekrar deneyin.")
