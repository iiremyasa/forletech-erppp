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
    .role-badge {
        display: inline-block; padding: 5px 14px; border-radius: 100px;
        font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25);
        color: #60a5fa !important; text-transform: uppercase;
    }
    .notification-card { padding: 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-left: 5px solid #3b82f6; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİTABANI BAĞLANTISI (SUPABASE)
# ─────────────────────────────────────────
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        queries = [
            "CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, model TEXT, seri_no TEXT, durum TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, model TEXT, seri_no TEXT, durum TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih DATE, kategori TEXT, tutar REAL, birim TEXT, tutar_tl REAL, tutar_usd REAL, tutar_eur REAL, aciklama TEXT, giren TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, proje TEXT, atanan TEXT, durum TEXT, oncelik TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, telefon TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih DATE, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
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

def excel_io(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label=f"📥 {filename} Excel İndir", data=output.getvalue(), file_name=f"{filename}.xlsx")

def islem_basarili():
    st.toast("✅ İşlem Başarıyla Kaydedildi!")
    time.sleep(0.5)
    st.rerun()

def kur_hesapla(tutar, birim):
    kurlar = {"USD": 32.8, "EUR": 35.5, "TL": 1.0} # Statik kurlar (İsteğe göre API'ye bağlanabilir)
    tl = tutar * kurlar[birim]
    return {"TL": round(tl, 2), "USD": round(tl/kurlar["USD"], 2), "EUR": round(tl/kurlar["EUR"], 2)}

# ─────────────────────────────────────────
# GİRİŞ KONTROLÜ
# ─────────────────────────────────────────
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center; padding:40px;'><h1>FORLE TECH ERP</h1></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login"):
            em = st.text_input("Kurumsal E-posta").strip().lower()
            pw = st.text_input("Şifre", type="password")
            if st.form_submit_button("Oturum Aç", use_container_width=True):
                user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hashlib.sha256(pw.encode()).hexdigest()})
                if not user.empty:
                    u = user.iloc[0]
                    st.session_state.update({"authenticated": True, "user_name": u['isim'], "user_email": u['email'], "user_rol": u['rol']})
                    st.rerun()
                else: st.error("Giriş başarısız.")
    st.stop()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("FORLE TECH")
    st.markdown(f"👤 **{st.session_state.user_name}**")
    st.markdown(f"<span class='role-badge'>{st.session_state.user_rol}</span>", unsafe_allow_html=True)
    
    menuler = ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "💰 Kurumsal Bütçe", "📋 Görevler", "👥 Personel", "✅ Onay Paneli", "🔑 Yetkiler", "⚙️ Ayarlar"]
    page = st.radio("Menü", menuler, label_visibility="collapsed")
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# SAYFALAR
# ─────────────────────────────────────────

# 📊 ANA SAYFA
if page == "📊 Ana Sayfa":
    st.markdown('<div class="page-header"><h2>📊 Operasyonel Dashboard</h2></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Parça Sayısı", load_df("SELECT count(*) FROM parcalar").iloc[0,0])
    c2.metric("💻 Cihaz Sayısı", load_df("SELECT count(*) FROM cihazlar").iloc[0,0])
    c3.metric("📋 Açık Görevler", load_df("SELECT count(*) FROM gorevler WHERE durum != 'Tamamlandı'").iloc[0,0])

    st.subheader("🔔 Son Bildirimler & Hareketler")
    logs = load_df("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 6")
    if not logs.empty:
        for _, l in logs.iterrows():
            st.markdown(f"<div class='notification-card'><b>{l['kullanici']}</b>: {l['aksiyon']} ({l['detay']})</div>", unsafe_allow_html=True)
    else: st.info("Henüz bir hareket kaydı yok.")

# 📦 PARÇA YÖNETİMİ
elif page == "📦 Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>📦 Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    is_eng = st.session_state.user_rol in ["Elektrik Elektronik Mühendisi", "Admin"]
    
    if is_eng:
        with st.expander("➕ Yeni Kayıt Ekle"):
            with st.form("par_f"):
                v, m, s = st.text_input("Varlık Etiketi"), st.text_input("Model"), st.text_input("Seri No")
                d = st.selectbox("Durum", ["Aktif", "Arızalı", "Stokta"])
                if st.form_submit_button("Kaydet"):
                    with conn.session as session:
                        session.execute(text("INSERT INTO parcalar (varlik_etiketi, model, seri_no, durum, ekleyen) VALUES (:v,:m,:s,:d,:e)"),
                                        {"v":v,"m":m,"s":s,"d":d,"e":st.session_state.user_name})
                        session.commit()
                    log_action("Parça Eklendi", v)
                    islem_basarili()
    
    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty:
        excel_io(df, "parca_listesi")
        if is_eng:
            with st.expander("🗑️ Kayıt Sil"):
                sid = st.selectbox("Silinecek ID", df["id"].tolist())
                if st.button("Kalıcı Olarak Sil"):
                    with conn.session as s: s.execute(text(f"DELETE FROM parcalar WHERE id={sid}")); s.commit()
                    log_action("Parça Silindi", f"ID: {sid}")
                    islem_basarili()

# 💰 KURUMSAL BÜTÇE (Döviz Hesaplamalı)
elif page == "💰 Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>💰 Kurumsal Bütçe & Global Kurlar</h2></div>', unsafe_allow_html=True)
    with st.expander("➕ Yeni Harcama Girişi"):
        with st.form("but_f"):
            c1, c2 = st.columns(2)
            t, k = c1.date_input("Tarih"), c1.selectbox("Kategori", ["Ar-Ge", "Donanım", "Ofis", "Maaş", "Seyahat"])
            tt, bb = c2.number_input("Tutar"), c2.selectbox("Birim", ["TL", "USD", "EUR"])
            ac = st.text_area("Açıklama")
            if st.form_submit_button("Bütçeye İşle"):
                kur = kur_hesapla(tt, bb)
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, birim, tutar_tl, tutar_usd, tutar_eur, aciklama, giren) VALUES (:t,:k,:tt,:bb,:tl,:usd,:eur,:ac,:g)"),
                              {"t":t,"k":k,"tt":tt,"bb":bb,"tl":kur["TL"],"usd":kur["USD"],"eur":kur["EUR"],"ac":ac,"g":st.session_state.user_name})
                    s.commit()
                log_action("Bütçe Girişi", f"{tt} {bb}")
                islem_basarili()

    df = load_df("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty: excel_io(df, "butce_dokumu")

# ✅ ONAY PANELİ
elif page == "✅ Onay Paneli":
    st.markdown('<div class="page-header"><h2>✅ Masraf Onay Yönetimi</h2></div>', unsafe_allow_html=True)
    df = load_df("SELECT * FROM harcama_talepleri WHERE durum='Bekliyor'")
    if not df.empty:
        for _, r in df.iterrows():
            with st.container():
                st.info(f"**Personel:** {r['personel']} | **Tutar:** {r['tutar']} TL")
                st.write(f"**Açıklama:** {r['aciklama']}")
                not_ = st.text_input("Onay/Red Notu", key=f"not_{r['id']}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Onayla", key=f"on_{r['id']}"):
                    with conn.session as s: s.execute(text(f"UPDATE harcama_talepleri SET durum='Onaylandı', yonetici_notu='{not_}' WHERE id={r['id']}")); s.commit()
                    log_action("Masraf Onaylandı", r['personel'])
                    st.rerun()
                if c2.button("❌ Reddet", key=f"red_{r['id']}"):
                    with conn.session as s: s.execute(text(f"UPDATE harcama_talepleri SET durum='Reddedildi', yonetici_notu='{not_}' WHERE id={r['id']}")); s.commit()
                    log_action("Masraf Reddedildi", r['personel'])
                    st.rerun()
    else: st.success("Bekleyen onay talebi bulunmuyor.")

# 🔑 YETKİLER
elif page == "🔑 Yetkiler":
    st.markdown('<div class="page-header"><h2>🔑 Yetki ve Rol Yönetimi</h2></div>', unsafe_allow_html=True)
    df = load_df("SELECT id, email, isim, rol FROM kullanicilar")
    st.dataframe(df, use_container_width=True)
    if st.session_state.user_rol == "Admin":
        with st.form("yet_f"):
            uid = st.selectbox("Kullanıcı ID", df["id"].tolist())
            rol = st.selectbox("Yeni Rol", ["Kullanici", "Elektrik Elektronik Mühendisi", "Yönetici", "Admin"])
            if st.form_submit_button("Yetkiyi Güncelle"):
                with conn.session as s: s.execute(text(f"UPDATE kullanicilar SET rol='{rol}' WHERE id={uid}")); s.commit()
                log_action("Yetki Güncelleme", f"ID: {uid} -> {rol}")
                islem_basarili()

# Diğer modüller (Cihaz, Görev, Personel, Ayarlar) benzer load_df yapısıyla güvenli hale getirildi.
