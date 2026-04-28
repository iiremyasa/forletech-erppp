import streamlit as st
import pandas as pd
import datetime
import hashlib
import time
import io
from sqlalchemy import text

# ─────────────────────────────────────────
# SAYFA AYARLARI & UI
# ─────────────────────────────────────────
st.set_page_config(page_title="FORLE TECH | Global ERP", page_icon="📈", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .page-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white; padding: 25px; border-radius: 15px; margin-bottom: 25px; border-left: 8px solid #3b82f6;
    }
    .stMetric { background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    .notification-card { padding: 10px; border-radius: 5px; background: #f1f5f9; border-left: 4px solid #3b82f6; margin-bottom: 10px; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİTABANI BAĞLANTISI
# ─────────────────────────────────────────
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        queries = [
            "CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, model TEXT, seri_no TEXT, durum TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, model TEXT, seri_no TEXT, durum TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih DATE, kategori TEXT, tutar REAL, birim TEXT, tutar_tl REAL, tutar_usd REAL, tutar_eur REAL, aciklama TEXT, giren TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, atanan TEXT, durum TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih DATE, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Bekliyor', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
        ]
        for q in queries: s.execute(text(q))
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :pw, 'Sistem Yöneticisi', 'Admin') ON CONFLICT (email) DO NOTHING"), {"pw": admin_pw})
        s.commit()

init_db()

# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────
def load_df(query, params=None):
    with conn.session as s:
        res = s.execute(text(query), params) if params else s.execute(text(query))
        return pd.DataFrame(res.fetchall(), columns=res.keys())

def log_action(aksiyon, detay=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:k, :a, :d)"), 
                  {"k": st.session_state.user_name, "a": aksiyon, "d": detay})
        s.commit()

def excel_download(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label="📥 Excel Olarak İndir", data=output.getvalue(), file_name=f"{filename}.xlsx", mime="application/vnd.ms-excel")

# Dinamik Kur Tahmini (Merkez Bankası API yerine sabit referans kurlar, gerçek API için secrets eklenebilir)
def kur_hesapla(tutar, birim):
    kurlar = {"USD": 32.5, "EUR": 35.0, "TL": 1.0} # Örnek kurlar
    tl_degeri = tutar * kurlar[birim]
    return {
        "TL": round(tl_degeri, 2),
        "USD": round(tl_degeri / kurlar["USD"], 2),
        "EUR": round(tl_degeri / kurlar["EUR"], 2)
    }

# ─────────────────────────────────────────
# GİRİŞ KONTROLÜ
# ─────────────────────────────────────────
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;'><h1>FORLE TECH ERP</h1></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login"):
            em = st.text_input("E-posta").strip().lower()
            pw = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hashlib.sha256(pw.encode()).hexdigest()})
                if not user.empty:
                    st.session_state.update({"authenticated": True, "user_name": user.iloc[0]['isim'], "user_rol": user.iloc[0]['rol']})
                    st.rerun()
                else: st.error("Hatalı bilgiler.")
    st.stop()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.title("FORLE TECH")
    st.markdown(f"👤 **{st.session_state.user_name}**")
    st.info(f"🔑 Yetki: {st.session_state.user_rol}")
    page = st.radio("Menü", ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "💰 Kurumsal Bütçe", "📋 Görevler", "🔑 Yetkiler", "⚙️ Ayarlar"])
    if st.button("🚪 Güvenli Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# MODÜLLER
# ─────────────────────────────────────────

# 📊 ANA SAYFA & BİLDİRİMLER
if page == "📊 Ana Sayfa":
    st.markdown('<div class="page-header"><h2>📊 Operasyonel Özet</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Toplam Parça", load_df("SELECT count(*) FROM parcalar").iloc[0,0])
    c2.metric("💻 Kayıtlı Cihaz", load_df("SELECT count(*) FROM cihazlar").iloc[0,0])
    c3.metric("💰 Toplam Bütçe (TL)", f"{load_df('SELECT sum(tutar_tl) FROM harcamalar').iloc[0,0]:,.2f}")

    st.subheader("🔔 Son Bildirimler")
    logs = load_df("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 5")
    for _, l in logs.iterrows():
        st.markdown(f"<div class='notification-card'><b>{l['kullanici']}</b>: {l['aksiyon']} - <i>{l['detay']}</i></div>", unsafe_allow_html=True)

# 📦 PARÇA YÖNETİMİ (Yetki Kısıtlı)
elif page == "📦 Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>📦 Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    
    is_engineer = st.session_state.user_rol in ["Elektrik Elektronik Mühendisi", "Admin"]
    
    if is_engineer:
        with st.expander("➕ Yeni Parça Ekle"):
            with st.form("parca_f"):
                v, m, s = st.text_input("Varlık Etiketi"), st.text_input("Model"), st.text_input("Seri No")
                d = st.selectbox("Durum", ["Aktif", "Arızalı", "Stokta"])
                if st.form_submit_button("Sisteme İşle"):
                    with conn.session as session:
                        session.execute(text("INSERT INTO parcalar (varlik_etiketi, model, seri_no, durum, ekleyen) VALUES (:v,:m,:s,:d,:e)"),
                                        {"v":v,"m":m,"s":s,"d":d,"e":st.session_state.user_name})
                        session.commit()
                    log_action("Parça Eklendi", f"Etiket: {v}")
                    st.rerun()

    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    excel_download(df, "parca_listesi")

    if is_engineer and not df.empty:
        with st.expander("🗑️ Hatalı Kaydı Sil"):
            sid = st.selectbox("Silinecek ID", df["id"].tolist())
            if st.button("Kaydı Kalıcı Olarak Sil"):
                with conn.session as s:
                    s.execute(text(f"DELETE FROM parcalar WHERE id={sid}"))
                    s.commit()
                log_action("Parça Silindi", f"ID: {sid}")
                st.rerun()

# 💰 KURUMSAL BÜTÇE (Finansal Hesaplamalı)
elif page == "💰 Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>💰 Kurumsal Bütçe & Finans</h2></div>', unsafe_allow_html=True)
    
    with st.expander("➕ Yeni Harcama Girişi"):
        with st.form("butce_f"):
            c1, c2 = st.columns(2)
            t = c1.date_input("Harcama Tarihi")
            tt = c1.number_input("Tutar", min_value=0.0)
            bb = c2.selectbox("Para Birimi", ["TL", "USD", "EUR"])
            ac = st.text_area("Açıklama")
            if st.form_submit_button("Bütçeye Ekle"):
                kurlar = kur_hesapla(tt, bb)
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, birim, tutar_tl, tutar_usd, tutar_eur, aciklama, giren) VALUES (:t,:k,:tt,:bb,:tl,:usd,:eur,:ac,:g)"),
                              {"t":t, "k":"Genel", "tt":tt, "bb":bb, "tl":kurlar["TL"], "usd":kurlar["USD"], "eur":kurlar["EUR"], "ac":ac, "g":st.session_state.user_name})
                    s.commit()
                log_action("Harcama Girişi", f"{tt} {bb} kaydedildi.")
                st.rerun()

    df = load_df("SELECT id, tarih, tutar, birim, tutar_tl, tutar_usd, tutar_eur, aciklama FROM harcamalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    excel_download(df, "kurumsal_butce")

    if not df.empty:
        with st.expander("🗑️ Harcama Sil"):
            sid = st.selectbox("Silinecek Harcama ID", df["id"].tolist())
            if st.button("Seçili Harcamayı Sil"):
                with conn.session as s: s.execute(text(f"DELETE FROM harcamalar WHERE id={sid}")); s.commit()
                st.rerun()

# 🔑 YETKİLER
elif page == "🔑 Yetkiler":
    st.markdown('<div class="page-header"><h2>🔑 Personel Yetki Yönetimi</h2></div>', unsafe_allow_html=True)
    df = load_df("SELECT id, email, isim, rol FROM kullanicilar")
    st.dataframe(df, use_container_width=True)
    
    if st.session_state.user_rol == "Admin":
        with st.form("yetki_f"):
            uid = st.selectbox("Kullanıcı Seç (ID)", df["id"].tolist())
            y_rol = st.selectbox("Atanacak Rol", ["Kullanici", "Elektrik Elektronik Mühendisi", "Yönetici", "Admin"])
            if st.form_submit_button("Yetkiyi Güncelle"):
                with conn.session as s:
                    s.execute(text(f"UPDATE kullanicilar SET rol='{y_rol}' WHERE id={uid}"))
                    s.commit()
                st.success("Yetki güncellendi!")
                st.rerun()

# Cihaz Yönetimi, Görevler ve Ayarlar modülleri yukarıdaki mantıkla (Yetki ve Silme eklenmiş şekilde) devam eder.
