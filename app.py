import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# Gereksiz uyarıları gizle
warnings.filterwarnings('ignore')

# 1. SAYFA VE ARAYÜZ AYARLARI
st.set_page_config(page_title="Huzur Portföyü V10.1", layout="wide")
st.title("🏛️ AKADEMİK FİNANS KONSEYİ")
st.subheader("Hibrit DCA Motoru: Matematik + Makro Haber Entegrasyonu (V10.1)")

# 2. STRATEJİK HEDEFLER (Kişisel Genetiğiniz)
targets = {"SPYM": 0.60, "SCHD": 0.25, "VEA": 0.15}
tickers = list(targets.keys())

# 3. MAKROEKONOMİK DUYARLILIK (SENTIMENT) SKORLARI - GÜNCEL
# (Piyasadaki haber akışına göre algoritmaya manuel "Katalizör" müdahalesi)
macro_sentiment = {
    "SPYM": -0.05,  # Gümrük tarifesi gerilimi ve mega-cap stresleri (Negatif baskı)
    "SCHD": +0.10,  # 'Değer' hisselerine ve temettüye kaçış rotasyonu (Pozitif rüzgar)
    "VEA":  +0.10   # ABD dışı piyasaların güçlü para girişi (Pozitif rüzgar)
}

# 4. YAN PANEL (KULLANICI GİRİŞİ)
with st.sidebar:
    st.header("💰 Sermaye Girişi")
    
    # İstenilen küsuratlı ve manuel giriş alanı
    monthly_cash = st.number_input(
        "Bu Ayki Yatırım Bütçenizi Giriniz ($):", 
        min_value=1.0, 
        value=500.0, 
        step=10.0, 
        format="%.2f"
    )
    
    st.markdown("---")
    st.info("💡 **Hibrit Çekirdek:** Bu versiyon; 200 günlük hareketli ortalamayı, zirveden düşüş iskontosunu ve **Güncel Küresel Haber Akışını (Sektörel Rotasyon, Tarife Riskleri)** aynı anda hesaplayarak portföyü optimize eder.")

# 5. KURUMSAL VERİ ÇEKİM VE ANALİZ MOTORU
@st.cache_data(ttl=3600)
def kurumsal_analiz(ticker_list):
    data_list = []
    for t in ticker_list:
        try:
            h = yf.Ticker(t)
            # 200 SMA için en az 1 yıllık veri şarttır
            hist = h.history(period="1y") 
            if len(hist) < 200: continue
            
            price = hist['Close'].iloc[-1]
            sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            high_52w = hist['High'].max()
            
            # Formüller
            drawdown = (price - high_52w) / high_52w  # Negatif değer
            sma_dist = (price - sma200) / sma200      # 200 günlüğe uzaklık
            
            data_list.append({
                "Ticker": t, 
                "Price": price, 
                "Drawdown": drawdown, 
                "SMA200_Dist": sma_dist
            })
        except Exception as e:
            pass
    return pd.DataFrame(data_list)

# 6. TAKTİKSEL DAĞILIM (MATEMATİK VE HABERLERİN BİRLEŞİMİ)
def taktiksel_dagilim(df, cash):
    raw_weights = {}
    
    for index, row in df.iterrows():
        t = row['Ticker']
        dd = row['Drawdown']      
        sma_d = row['SMA200_Dist'] 
        base_w = targets[t]
        
        # TEKNİK ÇARPAN (Matematiksel İskonto)
        tilt = 1.0
        if sma_d < 0: 
            tilt += 0.15      # 200 SMA altındaysa ucuzdur
        elif sma_d > 0.10: 
            tilt -= 0.15      # 200 SMA'dan %10 uzaklaştıysa şişmiştir
        
        if dd < -0.10: 
            tilt += 0.20      # %10'dan fazla düştüyse fırsattır
        elif dd < -0.05: 
            tilt += 0.10      # %5-%10 arası düşüş
            
        # MAKRO ÇARPAN (Haber Akışı Etkisi)
        tilt += macro_sentiment.get(t, 0)

        # Güvenlik Kilidi: Ne olursa olsun temel birikim durmaz, en azından %20'si korunur
        if tilt < 0.2: 
            tilt = 0.2
        
        raw_weights[t] = base_w * tilt

    # Ağırlıkları Toplam %100 (1.0) Olacak Şekilde Normalize Et
    total_w = sum(raw_weights.values())
    final_weights = {k: v / total_w for k, v in raw_weights.items()}

    results = []
    for t in tickers:
        allocation = cash * final_weights.get(t, 0)
        row_data = df[df['Ticker'] == t].iloc[0]
        price = row_data['Price']
        
        # Durum Belirleyici
        durum = "✅ DENGELİ"
        if final_weights[t] > targets[t] * 1.15: durum = "🔥 MAKRO & TEKNİK FIRSAT (Artırıldı)"
        elif final_weights[t] < targets[t] * 0.85: durum = "🛡️ RİSK KORUMASI (Azaltıldı)"

        results.append({
            "ETF": t,
            "Fiyat ($)": round(price, 2),
            "Zirveden Düşüş": f"{round(row_data['Drawdown']*100, 1)}%",
            "200G Ort. Mesafe": f"{round(row_data['SMA200_Dist']*100, 1)}%",
            "Makro Rüzgar": "Pozitif 🟢" if macro_sentiment.get(t,0) > 0 else ("Negatif 🔴" if macro_sentiment.get(t,0) < 0 else "Nötr ⚪"),
            "Stratejik Hedef": f"%{int(targets[t]*100)}",
            "Bu Ayki Ağırlık": f"%{round(final_weights[t]*100, 1)}",
            "Yatırılacak Tutar ($)": round(allocation, 2),
            "Durum Analizi": durum
        })
    return pd.DataFrame(results)

# 7. ÇALIŞTIRMA VE GÖRSELLEŞTİRME
if st.button("⚖️ HİBRİT DAĞILIMI HESAPLA"):
    with st.spinner("Piyasa verileri çekiliyor, 200 SMA hesaplanıyor ve makro haberler entegre ediliyor..."):
        raw_data = kurumsal_analiz(tickers)
        if not raw_data.empty:
            plan = taktiksel_dagilim(raw_data, monthly_cash)
            
            st.markdown("### 📊 V10.1 Makro-Optimize Satın Alma Planınız")
            st.dataframe(plan, use_container_width=True)
            
            # İndirme Butonu
            csv = plan.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Tabloyu İndir (CSV)",
                data=csv,
                file_name='v10_1_huzur_portfoyu_dagilim.csv',
                mime='text/csv',
            )
            
            st.success("Sistem Çalıştı: Paranızı uzun vadeli ortalamalara (200-SMA), gerçek iskontolara (Drawdown) ve Küresel Makro Haberlere göre en verimli şekilde böldü.")
        else:
            st.error("Veri bağlantı hatası. Lütfen Yahoo Finance bağlantısını kontrol edin.")
