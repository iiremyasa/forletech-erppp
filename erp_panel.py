import streamlit as st
import pandas as pd
import datetime
from sqlalchemy import text
import hashlib
import io

st.set_page_config(page_title="FORLE TECH | ERP Portal", page_icon=":material/business:", layout="wide")

# --- 0. VERİTABANI BAĞLANTISI (POSTGRESQL) ---
try:
    conn = st.connection("postgresql", type="sql")
    with conn.session as s:
        # Tüm tabloları PostgreSQL formatında oluşturuyoruz
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici'
            );
            CREATE TABLE IF NOT EXISTS parcalar (
                id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT,
                durum TEXT, seri_no TEXT, durum_notu TEXT, ekleyen TEXT
            );
            CREATE TABLE IF NOT EXISTS harcamalar (
                id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar FLOAT,
                fatura_no TEXT, aciklama TEXT, giren TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        # İlk admini oluştur
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :pw, 'Yönetici', 'Admin') ON CONFLICT DO NOTHING"), {"pw": admin_pw})
        s.commit()
    db_status = True
except Exception as e:
    st.error(f"Veritabanı Hatası: {e}")
    db_status = False

# --- 1. FONKSİYONLAR ---
def log_action(user, action, detail=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:u, :a, :d)"), {"u": user, "a": action, "d": detail})
        s.commit()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# --- 2. GİRİŞ EKRANI ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>FORLE TECH ERP</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs([":material/login: Giriş", ":material/person_add: Kayıt"])
    with tab1:
        with st.form("l"):
            e = st.text_input("E-posta").strip().lower()
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş"):
                res = conn.query("SELECT * FROM kullanicilar WHERE email = :e AND sifre = :p", params={"e":e, "p":hash_pw(p)})
                if not res.empty:
                    st.session_state.authenticated, st.session_state.user_name, st.session_state.user_rol = True, res.iloc[0]['isim'], res.iloc[0]['rol']
                    log_action(st.session_state.user_name, "Giriş Yapıldı")
                    st.rerun()
                else: st.error("Hatalı bilgiler.")
    st.stop()

# --- 3. ANA PANEL ---
st.sidebar.title("FORLE TECH")
st.sidebar.write(f"👤 {st.session_state.user_name} ({st.session_state.user_rol})")
page = st.sidebar.radio("Menü", [":material/dashboard: Panel", ":material/payments: Harcamalar", ":material/inventory: Envanter"])

if page == ":material/dashboard: Panel":
    st.title("Yönetim Paneli")
    h_data = conn.query("SELECT SUM(tutar) as t FROM harcamalar")
    st.metric("Toplam Harcama", f"{h_data.iloc[0]['t'] or 0:,.2f} TL")

elif page == ":material/payments: Harcamalar":
    st.subheader("Harcama Kaydı")
    with st.form("h"):
        t, k, tu = st.date_input("Tarih"), st.selectbox("Tür", ["Ar-Ge", "Ofis", "Seyahat"]), st.number_input("Tutar")
        if st.form_submit_button("Kaydet"):
            with conn.session as s:
                s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, giren) VALUES (:t,:k,:tu,:g)"),
                          {"t":t.strftime("%Y-%m-%d"), "k":k, "tu":tu, "g":st.session_state.user_name})
                s.commit()
            st.success("Veritabanına işlendi!")
    st.dataframe(conn.query("SELECT * FROM harcamalar"), use_container_width=True)

if st.sidebar.button("Çıkış"):
    st.session_state.authenticated = False
    st.rerun()
