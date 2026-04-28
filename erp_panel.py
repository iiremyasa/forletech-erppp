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
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    
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
    
    div[data-testid="metric-container"] {
        background: white; border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px; padding: 22px; transition: all 0.3s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px); border-color: #3b82f6;
    }
    
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
# VERİTABANI BAĞLANTISI (SUPABASE)
# ─────────────────────────────────────────
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        tablolar = [
            "CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, belge_adi TEXT, belge_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih TEXT, tutar REAL, aciklama TEXT, belge_adi TEXT, belge_data BYTEA, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, dekont_adi TEXT, dekont_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
        ]
        for t in tablolar:
            s.execute(text(t))
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

def page_header(title, desc):
    st.markdown(f'<div class="page-header"><h2>{title}</h2><p>{desc}</p></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# OTURUM KONTROLÜ
# ─────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding:50px 0;'><h1 style='color:#0f172a;'>FORLE TECH</h1><p>Kurumsal ERP Portalı</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt"])
        with tab1:
            with st.form("login"):
                em = st.text_input("E-posta").strip().lower()
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hashlib.sha256(pw.encode()).hexdigest()})
                    if not user.empty:
                        st.session_state.update({"authenticated": True, "user_name": user.iloc[0]['isim'], "user_email": user.iloc[0]['email'], "user_rol": user.iloc[0]['rol']})
                        st.rerun()
                    else: st.error("Hatalı bilgiler.")
    st.stop()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("FORLE TECH")
    st.markdown(f"<div style='text-align:center;margin-bottom:20px;'><span class='role-badge'>{st.session_state.user_rol}</span></div>", unsafe_allow_html=True)
    
    menuler = ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "🧾 Masraf Beyanı", "📋 Görevler", "⚙️ Ayarlar"]
    if st.session_state.user_rol in ["Admin", "Yönetici"]:
        menuler.insert(3, "💰 Kurumsal Bütçe")
        menuler.extend(["👥 Personel", "✅ Onay Paneli", "🛡️ Audit Log", "🔑 Yetkiler"])
    
    page = st.radio("Menü", menuler, label_visibility="collapsed")
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# SAYFALAR
# ─────────────────────────────────────────

# 1. Ana Sayfa
if page == "📊 Ana Sayfa":
    page_header("Kontrol Paneli", "Operasyonel Özet")
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Parça", load_df("SELECT count(*) FROM parcalar").iloc[0,0])
    c2.metric("💻 Cihaz", load_df("SELECT count(*) FROM cihazlar").iloc[0,0])
    c3.metric("📋 Görev", load_df("SELECT count(*) FROM gorevler WHERE durum != 'Tamamlandı'").iloc[0,0])

# 2. Parça Yönetimi (Tüm Detaylar Geri Geldi)
elif page == "📦 Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık ve Ar-Ge Envanteri")
    if st.session_state.user_rol in ["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]:
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
                                  {"ve":ve,"mo":mo,"du":du,"sn":sn,"yv":yv,"bc":bc,"dn":dn,"kt":str(kt),"ek":st.session_state.user_name})
                        s.commit()
                    islem_basarili()

    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)
    if not df.empty:
        st.download_button("📥 Excel İndir", excel_export(df), "parcalar.xlsx")
        if st.session_state.user_rol in ["Admin", "Yönetici"]:
            with st.expander("🗑️ Kayıt Sil"):
                sid = st.selectbox("Silinecek ID", df["id"].tolist())
                if st.button("Seçili Kaydı Sil"):
                    with conn.session as s:
                        s.execute(text(f"DELETE FROM parcalar WHERE id={sid}"))
                        s.commit()
                    islem_basarili()

# 3. Cihaz Yönetimi
elif page == "💻 Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Donanım İzleme")
    if st.session_state.user_rol in ["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]:
        with st.expander("➕ Yeni Cihaz Ekle"):
            with st.form("c_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ca = c1.text_input("Cihaz Adı")
                ip = c1.text_input("IP")
                mo = c1.text_input("Model")
                du = c1.selectbox("Durum", ["Aktif","Testte","Bakımda"])
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
    df = load_df("SELECT * FROM cihazlar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)
    if not df.empty: st.download_button("📥 Excel İndir", excel_export(df), "cihazlar.xlsx")

# 4. Kurumsal Bütçe
elif page == "💰 Kurumsal Bütçe":
    page_header("Kurumsal Bütçe", "Şirket Harcamaları")
    with st.expander("➕ Harcama Girişi"):
        with st.form("h_form"):
            t, k, tt = st.date_input("Tarih"), st.selectbox("Kategori", ["Ar-Ge", "Ofis", "Seyahat", "Maaş"]), st.number_input("Tutar")
            f, a = st.text_input("Fatura No"), st.text_area("Açıklama")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, fatura_no, aciklama, giren) VALUES (:t,:k,:tt,:f,:a,:g)"),
                              {"t":str(t),"k":k,"tt":tt,"f":f,"a":a,"g":st.session_state.user_name})
                    s.commit()
                islem_basarili()
    df = load_df("SELECT id, tarih, kategori, tutar, fatura_no, aciklama, giren FROM harcamalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)
    if not df.empty: st.download_button("📥 Excel İndir", excel_export(df), "butce.xlsx")

# 5. Masraf Beyanı
elif page == "🧾 Masraf Beyanı":
    page_header("Masraf Beyanı", "Bireysel Harcama İadesi")
    with st.form("m_form"):
        tt, ac = st.number_input("Tutar"), st.text_area("Açıklama")
        if st.form_submit_button("Onaya Gönder"):
            with conn.session as s:
                s.execute(text("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama) VALUES (:p,:t,:tu,:a)"),
                          {"p":st.session_state.user_name, "t":str(datetime.date.today()), "tu":tt, "a":ac})
                s.commit()
            islem_basarili()
    df = load_df("SELECT tarih, tutar, aciklama, durum, yonetici_notu FROM harcama_talepleri WHERE personel=:p", {"p":st.session_state.user_name})
    st.dataframe(df, use_container_width=True, hide_index=True)

# 6. Personel
elif page == "👥 Personel":
    page_header("İnsan Kaynakları", "Personel Listesi")
    with st.expander("➕ Yeni Personel"):
        with st.form("per_form"):
            i, e, p = st.text_input("Ad Soyad"), st.text_input("E-posta"), st.text_input("Pozisyon")
            d, t = st.selectbox("Departman", ["Yazılım","Donanım","Ar-Ge"]), st.text_input("Telefon")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO personel (isim, email, pozisyon, departman, telefon) VALUES (:i,:e,:p,:d,:t)"),
                              {"i":i,"e":e,"p":p,"d":d,"t":t})
                    s.commit()
                islem_basarili()
    df = load_df("SELECT * FROM personel ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True, hide_index=True)

# 7. Onay Paneli
elif page == "✅ Onay Paneli":
    page_header("Onay Paneli", "Masraf Onayları")
    df = load_df("SELECT * FROM harcama_talepleri WHERE durum='Bekliyor'")
    if not df.empty:
        for idx, row in df.iterrows():
            with st.container():
                st.write(f"**{row['personel']}** - {row['tutar']}₺")
                not_ = st.text_input("Not", key=f"n_{row['id']}")
                c1, c2 = st.columns(2)
                if c1.button("Onayla", key=f"o_{row['id']}"):
                    with conn.session as s:
                        s.execute(text(f"UPDATE harcama_talepleri SET durum='Onaylandı', yonetici_notu='{not_}' WHERE id={row['id']}"))
                        s.commit()
                    st.rerun()
                if c2.button("Reddet", key=f"r_{row['id']}"):
                    with conn.session as s:
                        s.execute(text(f"UPDATE harcama_talepleri SET durum='Reddedildi', yonetici_notu='{not_}' WHERE id={row['id']}"))
                        s.commit()
                    st.rerun()
    else: st.info("Bekleyen talep yok.")

# 8. Audit Log
elif page == "🛡️ Audit Log":
    page_header("Audit Log", "Sistem İşlem Geçmişi")
    df = load_df("SELECT * FROM audit_log ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)

# 9. Yetkiler
elif page == "🔑 Yetkiler":
    page_header("Yetkilendirme", "Kullanıcı Rol Yönetimi")
    df = load_df("SELECT id, email, isim, rol FROM kullanicilar")
    st.dataframe(df, use_container_width=True, hide_index=True)
    with st.form("y_form"):
        uid = st.selectbox("Kullanıcı ID", df["id"].tolist())
        rol = st.selectbox("Yeni Rol", ["Kullanici", "Elektrik Elektronik Mühendisi", "Yönetici", "Admin"])
        if st.form_submit_button("Güncelle"):
            with conn.session as s:
                s.execute(text(f"UPDATE kullanicilar SET rol='{rol}' WHERE id={uid}"))
                s.commit()
            islem_basarili()

# 10. Ayarlar
elif page == "⚙️ Ayarlar":
    page_header("Ayarlar", "Profil Yönetimi")
    with st.form("pw_f"):
        y1 = st.text_input("Yeni Şifre", type="password")
        y2 = st.text_input("Yeni Şifre Tekrar", type="password")
        if st.form_submit_button("Şifreyi Güncelle"):
            if y1 == y2 and len(y1) >= 4:
                with conn.session as s:
                    s.execute(text(f"UPDATE kullanicilar SET sifre='{hash_pw(y1)}' WHERE email='{st.session_state.user_email}'"))
                    s.commit()
                st.success("Şifre güncellendi.")
            else: st.error("Hata!")
