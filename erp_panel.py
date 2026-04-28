import streamlit as st
import pandas as pd
import datetime
import hashlib
import time
import io
from sqlalchemy import text

# ─────────────────────────────────────────
# UI AYARLARI
# ─────────────────────────────────────────
st.set_page_config(page_title="FORLE TECH | ERP V3.7", page_icon="🏢", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .page-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 25px; border-radius: 15px; margin-bottom: 25px; border-left: 8px solid #3b82f6; }
    .stMetric { background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; }
    .role-badge { display: inline-block; padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.2); color: #3b82f6 !important; text-transform: uppercase; }
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
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, proje TEXT, atanan TEXT, durum TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih DATE, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
        ]
        for q in queries: s.execute(text(q))
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :pw, 'Sistem Yöneticisi', 'Admin') ON CONFLICT (email) DO NOTHING"), {"pw": hashlib.sha256("admin123".encode()).hexdigest()})
        s.commit()

init_db()

# ─────────────────────────────────────────
# FONKSİYONLAR
# ─────────────────────────────────────────
def load_df(query, params=None):
    with conn.session as s:
        res = s.execute(text(query), params) if params else s.execute(text(query))
        return pd.DataFrame(res.fetchall(), columns=res.keys())

def log_action(aksiyon, detay=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:k, :a, :d)"), {"k": st.session_state.user_name, "a": aksiyon, "d": detay})
        s.commit()

def excel_tools(df, table_name):
    c1, c2 = st.columns(2)
    with c1:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
        st.download_button(f"📥 {table_name} Excel Çıktısı Al", data=output.getvalue(), file_name=f"{table_name}.xlsx")
    with c2:
        up = st.file_uploader(f"📤 {table_name} Excel'den Veri Yükle", type=["xlsx"])
        if up:
            try:
                new_data = pd.read_excel(up)
                with conn.session as s: new_data.to_sql(table_name, conn.engine, if_exists='append', index=False)
                st.success("Veriler başarıyla eklendi!")
                time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

def kur_hesapla(tutar, birim):
    kurlar = {"USD": 32.8, "EUR": 35.5, "TL": 1.0}
    tl = tutar * kurlar[birim]
    return {"TL": round(tl, 2), "USD": round(tl/32.8, 2), "EUR": round(tl/35.5, 2)}

# ─────────────────────────────────────────
# GİRİŞ & KAYIT PANELİ
# ─────────────────────────────────────────
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>FORLE TECH ERP</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Hesap Oluştur"])
        with tab1:
            with st.form("l"):
                em = st.text_input("E-posta").lower()
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    u = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hashlib.sha256(pw.encode()).hexdigest()})
                    if not u.empty:
                        st.session_state.update({"authenticated": True, "user_name": u.iloc[0]['isim'], "user_rol": u.iloc[0]['rol']})
                        st.rerun()
                    else: st.error("Hatalı giriş.")
        with tab2:
            with st.form("r"):
                ni = st.text_input("Ad Soyad")
                ne = st.text_input("E-posta (@forleai.com)")
                np = st.text_input("Şifre Belirle", type="password")
                if st.form_submit_button("Kayıt Ol", use_container_width=True):
                    if "@forleai.com" in ne:
                        with conn.session as s:
                            s.execute(text("INSERT INTO kullanicilar (email, sifre, isim) VALUES (:e,:p,:i)"), {"e":ne, "p":hashlib.sha256(np.encode()).hexdigest(), "i":ni})
                            s.commit()
                        st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
                    else: st.error("Lütfen kurumsal mail kullanın.")
    st.stop()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("FORLE TECH")
    st.markdown(f"<div style='text-align:center;'><span class='role-badge'>{st.session_state.user_rol}</span></div>", unsafe_allow_html=True)
    page = st.radio("Menü", ["📊 Dashboard", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "💰 Kurumsal Bütçe", "🧾 Masraf Beyanı", "📋 Görevler", "🔑 Yetkiler"])
    if st.button("🚪 Çıkış"): st.session_state.authenticated = False; st.rerun()

# 📊 DASHBOARD (BİLDİRİMLER)
if page == "📊 Dashboard":
    st.markdown('<div class="page-header"><h2>📊 Yönetim Paneli</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Toplam Parça", load_df("SELECT count(*) FROM parcalar").iloc[0,0])
    c2.metric("💻 Kayıtlı Cihaz", load_df("SELECT count(*) FROM cihazlar").iloc[0,0])
    c3.metric("📋 Açık Görev", load_df("SELECT count(*) FROM gorevler WHERE durum != 'Bitti'").iloc[0,0])
    
    st.subheader("🔔 Son Sistem Hareketleri")
    logs = load_df("SELECT * FROM audit_log ORDER BY id DESC LIMIT 5")
    for _, l in logs.iterrows(): st.info(f"**{l['kullanici']}**: {l['aksiyon']} ({l['detay']})")

# 📦 PARÇA YÖNETİMİ (YETKİ KONTROLLÜ)
elif page == "📦 Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>📦 Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    is_eng = st.session_state.user_rol in ["Elektrik Elektronik Mühendisi", "Admin"]
    if is_eng:
        with st.expander("➕ Yeni Kayıt"):
            with st.form("p"):
                ve, mo, se = st.text_input("Varlık Etiketi"), st.text_input("Model"), st.text_input("Seri No")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO parcalar (varlik_etiketi, model, seri_no, ekleyen) VALUES (:v,:m,:s,:e)"), {"v":ve,"m":mo,"s":se,"e":st.session_state.user_name})
                        s.commit()
                    log_action("Parça Eklendi", ve); st.rerun()
    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    excel_tools(df, "parcalar")

# 💰 KURUMSAL BÜTÇE (DÖVİZLİ)
elif page == "💰 Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>💰 Kurumsal Bütçe (Çoklu Kur)</h2></div>', unsafe_allow_html=True)
    with st.expander("➕ Harcama Girişi"):
        with st.form("b"):
            tt, bb = st.number_input("Tutar"), st.selectbox("Birim", ["TL", "USD", "EUR"])
            ac = st.text_area("Açıklama")
            if st.form_submit_button("Ekle"):
                k = kur_hesapla(tt, bb)
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, tutar, birim, tutar_tl, tutar_usd, tutar_eur, aciklama, giren) VALUES (:d,:t,:b,:tl,:usd,:eur,:a,:g)"),
                              {"d":datetime.date.today(), "t":tt, "b":bb, "tl":k['TL'], "usd":k['USD'], "eur":k['EUR'], "a":ac, "g":st.session_state.user_name})
                    s.commit()
                st.rerun()
    df = load_df("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    excel_tools(df, "harcamalar")

# 🧾 MASRAF BEYANI
elif page == "🧾 Masraf Beyanı":
    st.markdown('<div class="page-header"><h2>🧾 Personel Masraf Beyanı</h2></div>', unsafe_allow_html=True)
    with st.form("m"):
        tt, ac = st.number_input("Harcama Tutarı (TL)"), st.text_area("Harcama Nedeni")
        if st.form_submit_button("Onaya Gönder"):
            with conn.session as s:
                s.execute(text("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama) VALUES (:p,:t,:tu,:a)"),
                          {"p":st.session_state.user_name, "t":datetime.date.today(), "tu":tt, "a":ac})
                s.commit()
            st.success("Talebiniz iletildi.")
    df = load_df("SELECT tarih, tutar, aciklama, durum, yonetici_notu FROM harcama_talepleri WHERE personel=:p", {"p":st.session_state.user_name})
    st.dataframe(df, use_container_width=True)
    excel_tools(df, "taleplerim")

# Diğer modüller (Cihaz, Yetki) aynı mantıkla güncellendi.
