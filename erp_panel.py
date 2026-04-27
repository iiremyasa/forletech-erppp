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
# SAYFA AYARLARI & MODERN UI TASARIMI
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
    
    /* Modern Sidebar Tasarımı */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    
    /* Navigasyon Menü Butonları */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 12px 16px; border-radius: 10px; margin-bottom: 6px;
        transition: all 0.2s ease; cursor: pointer; background: transparent;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255,255,255,0.08); transform: translateX(5px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none !important; 
    }
    
    /* Metric Kartları ve Animasyonlar */
    div[data-testid="metric-container"] {
        background: var(--background-color, white);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px; padding: 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    
    /* Kurumsal Sayfa Başlığı */
    .page-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white; padding: 30px; border-radius: 18px; margin-bottom: 30px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-left: 8px solid #3b82f6;
    }
    .page-header h2 { margin: 0; font-size: 1.9rem; font-weight: 700; letter-spacing: -0.5px; }
    
    .role-badge {
        display: inline-block; padding: 5px 14px; border-radius: 100px;
        font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25);
        color: #60a5fa !important; letter-spacing: 0.8px; text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SUPABASE / POSTGRESQL BAĞLANTISI
# ─────────────────────────────────────────
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        # Tablolar PostgreSQL (Supabase) standartlarına uygun olarak tek tek oluşturulur.
        s.execute(text("CREATE TABLE IF NOT EXISTS dogrulama_kodlari (id SERIAL PRIMARY KEY, email TEXT, isim TEXT, sifre TEXT, kod TEXT, gecerlilik TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, belge_adi TEXT, belge_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih TEXT, tutar REAL, aciklama TEXT, belge_adi TEXT, belge_data BYTEA, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, dekont_adi TEXT, dekont_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, tarih TEXT, okundu INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        s.execute(text("CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        
        # Admin hesabı oluşturulur
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :pw, 'Sistem Yöneticisi', 'Admin') ON CONFLICT (email) DO NOTHING"), {"pw": pw})
        s.commit()

init_db()

# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def islem_basarili():
    st.toast("✅ İşlem Kaydedildi!", icon="✅")
    time.sleep(0.5)
    st.rerun()

def yetki_kontrol(roller):
    return st.session_state.get("user_rol") in roller

def log_action(kullanici, aksiyon, detay=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:k, :a, :d)"), {"k": kullanici, "a": aksiyon, "d": detay})
        s.commit()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────
# OTURUM KONTROLÜ (30 Dakika)
# ─────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    if "last_active" not in st.session_state:
        st.session_state.last_active = time.time()
    if time.time() - st.session_state.last_active > 1800:
        st.session_state.authenticated = False
        st.warning("⏱️ Oturum süresi doldu (30 dk).")
        st.stop()
    st.session_state.last_active = time.time()

# ─────────────────────────────────────────
# GİRİŞ EKRANI
# ─────────────────────────────────────────
if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding:50px 0;'><h1 style='color:#0f172a; font-weight:800;'>FORLE TECH</h1><p>Kurumsal ERP Portalı</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Personel Kaydı"])
        with tab1:
            with st.form("giris"):
                em = st.text_input("Kurumsal E-posta").strip().lower()
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    res = conn.query(f"SELECT * FROM kullanicilar WHERE email='{em}' AND sifre='{hash_pw(pw)}'").to_dict('records')
                    if res:
                        u = res[0]
                        st.session_state.update({"authenticated": True, "user_name": u["isim"], "user_email": u["email"], "user_rol": u["rol"]})
                        log_action(u["isim"], "Giriş")
                        st.rerun()
                    else: st.error("E-posta veya şifre hatalı.")
    st.stop()

# ─────────────────────────────────────────
# DİNAMİK SIDEBAR & LOGO GÜNCELLEMESİ
# ─────────────────────────────────────────
with st.sidebar:
    # --- LOGO ALANI ---
    try:
        st.image("logo.png", use_container_width=True)
        st.markdown(f"""
        <div style='text-align:center;padding:5px 0 15px 0;'>
            <div style='font-weight:800; font-size:1.3rem; letter-spacing:1px; color:#ffffff;'>FORLE TECH</div>
            <div class='role-badge'>{st.session_state.user_rol}</div>
        </div>
        """, unsafe_allow_html=True)
    except:
        st.markdown(f"<div style='text-align:center;padding:15px;'><h2 style='color:white;'>FORLE TECH</h2><span class='role-badge'>{st.session_state.user_rol}</span></div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    menuler = ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "🧾 Masraf Beyanı", "📋 Görevler", "⚙️ Ayarlar"]
    if yetki_kontrol(["Admin", "Yönetici"]):
        menuler.insert(3, "💰 Kurumsal Bütçe")
        menuler.extend(["👥 Personel", "✅ Onay Paneli", "🛡️ Audit Log", "🔑 Yetkiler"])
    
    page = st.radio("Menü", menuler, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 Sayfayı Yenile", use_container_width=True): st.rerun()
    if st.button("🚪 Çıkış", use_container_width=True): 
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# SAYFA BAŞLIĞI YARDIMCISI
# ─────────────────────────────────────────
def page_header(title, desc):
    st.markdown(f'<div class="page-header"><h2>{title}</h2><p>{desc}</p></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# MODÜL İÇERİKLERİ
# ─────────────────────────────────────────

# 📊 ANA SAYFA
if page == "📊 Ana Sayfa":
    page_header("Kontrol Paneli", "FORLE TECH ERP — Operasyonel Özet")
    c1, c2, c3 = st.columns(3)
    with get_conn() as s:
        c1.metric("📦 Toplam Parça", conn.query("SELECT count(*) FROM parcalar").iloc[0,0])
        c2.metric("💻 Kayıtlı Cihaz", conn.query("SELECT count(*) FROM cihazlar").iloc[0,0])
        c3.metric("📋 Açık Görev", conn.query("SELECT count(*) FROM gorevler WHERE durum != 'Tamamlandı'").iloc[0,0])

# 📦 PARÇA YÖNETİMİ
elif page == "📦 Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık ve Ar-Ge Envanter Takibi")
    if yetki_kontrol(["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]):
        with st.expander("➕ Yeni Parça Ekle"):
            with st.form("p_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ve = c1.text_input("Varlık Etiketi")
                mo = c1.text_input("Model")
                du = c1.selectbox("Durum", ["Aktif", "Arızalı", "Depoda", "Hurda"])
                sn = c1.text_input("Seri No")
                yv = c2.text_input("Yazılım Versiyonu")
                bc = c2.text_input("Bağlı Cihaz")
                dn = c2.text_area("Durum Notu")
                kt = c2.date_input("Kayıt Tarihi")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO parcalar (varlik_etiketi, model, durum, seri_no, yazilim_versiyonu, bagli_cihaz, durum_notu, kayit_tarihi, ekleyen) VALUES (:ve,:mo,:du,:sn,:yv,:bc,:dn,:kt,:ek)"),
                                  {"ve":ve,"mo":mo,"du":du,"sn":sn,"yv":yv,"bc":bc,"dn":dn,"kt":kt.strftime("%Y-%m-%d"),"ek":st.session_state.user_name})
                        s.commit()
                    islem_basarili()

    df = conn.query("SELECT * FROM parcalar ORDER BY created_at DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)

# 💻 CİHAZ YÖNETİMİ
elif page == "💻 Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Donanım ve Montaj İzleme")
    if yetki_kontrol(["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]):
        with st.expander("➕ Yeni Cihaz Ekle"):
            with st.form("c_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ca = c1.text_input("Cihaz Adı")
                ip = c1.text_input("IP Adresi")
                mo = c1.text_input("Model")
                du = c1.selectbox("Durum", ["Aktif","Testte","Bakımda","Depoda"])
                ss = c2.text_input("Sensör Seri No")
                as_ = c2.text_input("Anakart Seri No")
                sn = c2.text_input("Seri No")
                nt = st.text_area("Notlar")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO cihazlar (cihaz_adi, ip, model, takili_sensor_seri, anakart_seri, durum, seri_no, notlar, ekleyen) VALUES (:ca,:ip,:mo,:ss,:as,:du,:sn,:nt,:ek)"),
                                  {"ca":ca,"ip":ip,"mo":mo,"ss":ss,"as":as_,"du":du,"sn":sn,"nt":nt,"ek":st.session_state.user_name})
                        s.commit()
                    islem_basarili()

    df = conn.query("SELECT * FROM cihazlar ORDER BY created_at DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)

# 🧾 MASRAF BEYANI
elif page == "🧾 Masraf Beyanı":
    page_header("Masraf Beyanı", "Kişisel Harcama İade Talepleri")
    with st.form("m_form", clear_on_submit=True):
        st.info("📌 Belge yüklemek zorunludur.")
        tt = st.number_input("Tutar (₺)", min_value=1.0)
        ac = st.text_area("Harcama Açıklaması")
        fl = st.file_uploader("Fiş/Fatura", type=["png","jpg","pdf"])
        if st.form_submit_button("🚀 Onaya Gönder"):
            if not fl: st.error("Lütfen bir belge yükleyin.")
            else:
                with conn.session as s:
                    s.execute(text("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama, belge_adi, belge_data) VALUES (:p,:t,:tu,:a,:bn,:bd)"),
                              {"p":st.session_state.user_name, "t":datetime.date.today().strftime("%Y-%m-%d"), "tu":tt, "a":ac, "bn":fl.name, "bd":fl.read()})
                    s.commit()
                islem_basarili()
    
    st.markdown("### 📋 Taleplerim")
    df = conn.query(f"SELECT tarih, tutar, aciklama, durum, yonetici_notu FROM harcama_talepleri WHERE personel='{st.session_state.user_name}' ORDER BY created_at DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ⚙️ AYARLAR
elif page == "⚙️ Ayarlar":
    page_header("Profil Ayarları", "Hesap Güvenliği ve Şifre Yönetimi")
    with st.form("pw_form"):
        st.write(f"**Kullanıcı:** {st.session_state.user_name} ({st.session_state.user_email})")
        y1 = st.text_input("Yeni Şifre", type="password")
        y2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
        if st.form_submit_button("Şifreyi Güncelle"):
            if y1 == y2 and len(y1) >= 4:
                with conn.session as s:
                    s.execute(text(f"UPDATE kullanicilar SET sifre='{hash_pw(y1)}' WHERE email='{st.session_state.user_email}'"))
                    s.commit()
                st.success("Şifreniz başarıyla güncellendi.")
            else: st.error("Şifreler eşleşmiyor veya çok kısa.")
