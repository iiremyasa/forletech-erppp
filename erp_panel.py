import streamlit as st
import pandas as pd
import datetime
import hashlib
import random
import smtplib
import time
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import text

# ─────────────────────────────────────────
# SAYFA AYARLARI & MODERN UI
# ─────────────────────────────────────────
st.set_page_config(
    page_title="FORLE TECH | ERP Portal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .page-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white; padding: 30px; border-radius: 18px; margin-bottom: 30px;
        border-left: 8px solid #3b82f6;
    }
    .role-badge {
        display: inline-block; padding: 5px 14px; border-radius: 100px;
        font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25);
        color: #60a5fa !important; text-transform: uppercase;
    }
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
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, belge_adi TEXT, belge_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih TEXT, tutar REAL, aciklama TEXT, belge_adi TEXT, belge_data BYTEA, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, dekont_adi TEXT, dekont_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
        ]
        for q in queries:
            s.execute(text(q))
        
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :pw, 'Sistem Yöneticisi', 'Admin') ON CONFLICT (email) DO NOTHING"), {"pw": admin_pw})
        s.commit()

init_db()

# ─────────────────────────────────────────
# FONKSİYONLAR
# ─────────────────────────────────────────
def load_df(query, params=None):
    with conn.session as s:
        res = s.execute(text(query), params) if params else s.execute(text(query))
        return pd.DataFrame(res.fetchall(), columns=res.keys())

def islem_basarili():
    st.toast("✅ İşlem Kaydedildi!", icon="✅")
    time.sleep(0.5)
    st.rerun()

def excel_export(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ─────────────────────────────────────────
# GİRİŞ VE OTURUM
# ─────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>FORLE TECH ERP</h1>", unsafe_allow_html=True)
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
# SIDEBAR & MENU
# ─────────────────────────────────────────
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("FORLE TECH")
    st.markdown(f"<span class='role-badge'>{st.session_state.user_rol}</span>", unsafe_allow_html=True)
    
    pages = ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "🧾 Masraf Beyanı", "📋 Görevler"]
    if st.session_state.user_rol in ["Admin", "Yönetici"]:
        pages.extend(["💰 Kurumsal Bütçe", "👥 Personel", "✅ Onay Paneli"])
    
    page = st.radio("Menü", pages)
    if st.button("🚪 Çıkış"):
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# SAYFALAR
# ─────────────────────────────────────────

if page == "📊 Ana Sayfa":
    st.markdown('<div class="page-header"><h2>📊 Ana Sayfa</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Parça", load_df("SELECT count(*) FROM parcalar").iloc[0,0])
    c2.metric("💻 Cihaz", load_df("SELECT count(*) FROM cihazlar").iloc[0,0])
    c3.metric("📋 Görev", load_df("SELECT count(*) FROM gorevler WHERE durum != 'Tamamlandı'").iloc[0,0])

elif page == "📦 Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>📦 Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    with st.expander("➕ Yeni Ekle"):
        with st.form("p"):
            v, m, s = st.text_input("Etiket"), st.text_input("Model"), st.text_input("Seri No")
            d = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda"])
            if st.form_submit_button("Kaydet"):
                with conn.session as session:
                    session.execute(text("INSERT INTO parcalar (varlik_etiketi, model, seri_no, durum, ekleyen) VALUES (:v,:m,:s,:d,:e)"),
                                    {"v":v,"m":m,"s":s,"d":d,"e":st.session_state.user_name})
                    session.commit()
                islem_basarili()
    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty: st.download_button("📥 Excel", excel_export(df), "parcalar.xlsx")

elif page == "💰 Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>💰 Kurumsal Bütçe</h2></div>', unsafe_allow_html=True)
    with st.expander("➕ Harcama Girişi"):
        with st.form("h"):
            t, k, tt = st.date_input("Tarih"), st.selectbox("Kat", ["Ar-Ge", "Ofis", "Seyahat"]), st.number_input("Tutar")
            if st.form_submit_button("Kaydet"):
                with conn.session as session:
                    session.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, giren) VALUES (:t,:k,:tt,:g)"),
                                    {"t":str(t),"k":k,"tt":tt,"g":st.session_state.user_name})
                    session.commit()
                islem_basarili()
    df = load_df("SELECT id, tarih, kategori, tutar, giren FROM harcamalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty: st.download_button("📥 Excel", excel_export(df), "butce.xlsx")

elif page == "🧾 Masraf Beyanı":
    st.markdown('<div class="page-header"><h2>🧾 Masraf Beyanı</h2></div>', unsafe_allow_html=True)
    with st.form("m"):
        tt, ac = st.number_input("Tutar"), st.text_area("Açıklama")
        if st.form_submit_button("Gönder"):
            with conn.session as session:
                session.execute(text("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama) VALUES (:p,:t,:tu,:a)"),
                                {"p":st.session_state.user_name, "t":str(datetime.date.today()), "tu":tt, "a":ac})
                session.commit()
            islem_basarili()
    df = load_df("SELECT tarih, tutar, aciklama, durum FROM harcama_talepleri WHERE personel=:p", {"p":st.session_state.user_name})
    st.dataframe(df, use_container_width=True, hide_index=True)

# ... Diğer sayfalar (Cihaz, Görev, Personel, Onay) benzer load_df mantığıyla çalışır ...
