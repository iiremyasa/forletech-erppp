import streamlit as st
import pandas as pd
import datetime
import hashlib
import random
import smtplib
import time
import io
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import text

st.set_page_config(page_title="FORLE TECH | ERP Portal", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-right: 1px solid rgba(255,255,255,0.05); }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    div[data-testid="metric-container"] { background: white; border: 1px solid rgba(148,163,184,0.2); border-radius: 14px; padding: 22px; transition: all 0.3s; }
    .page-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 30px; border-radius: 18px; margin-bottom: 30px; border-left: 8px solid #3b82f6; }
    .role-badge { display: inline-block; padding: 5px 14px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25); color: #60a5fa !important; text-transform: uppercase; }
    .notif-card { background: white; border-radius: 12px; padding: 14px 18px; border-left: 4px solid #f59e0b; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
</style>
""", unsafe_allow_html=True)

# ── VERİTABANI ──
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        tablolar = [
            "CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS dogrulama_kodlari (id SERIAL PRIMARY KEY, email TEXT, isim TEXT, sifre TEXT, kod TEXT, gecerlilik TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, model TEXT, seri_no TEXT, durum TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, para_birimi TEXT DEFAULT 'TRY', tutar_usd REAL, tutar_eur REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS masraf_iadeleri (id SERIAL PRIMARY KEY, talep_eden TEXT, talep_eden_email TEXT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, hedef_rol TEXT DEFAULT 'Tumu', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ]
        for t in tablolar: s.execute(text(t))
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email,sifre,isim,rol) VALUES ('admin@forleai.com',:pw,'Sistem Yöneticisi','Admin') ON CONFLICT (email) DO NOTHING"), {"pw": admin_pw})
        s.commit()

init_db()

# ── YARDIMCI FONKSİYONLAR ──
def load_df(query, params=None):
    with conn.session as s:
        res = s.execute(text(query), params or {})
        rows = res.fetchall()
        return pd.DataFrame(rows, columns=res.keys()) if rows else pd.DataFrame(columns=res.keys())

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def log_action(kullanici, aksiyon, detay=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici,aksiyon,detay) VALUES (:k,:a,:d)"), {"k":kullanici,"a":aksiyon,"d":detay})
        s.commit()

def bildirim_ekle(mesaj, tip="bilgi", hedef_rol="Tumu"):
    with conn.session as s:
        s.execute(text("INSERT INTO bildirimler (tip,mesaj,hedef_rol) VALUES (:t,:m,:h)"), {"t":tip,"m":mesaj,"h":hedef_rol})
        s.commit()

def islem_basarili(msg="İşlem kaydedildi!"):
    st.toast(f"{msg}")
    time.sleep(0.4)
    st.rerun()

def kayit_sil_ui(df, table, key_prefix):
    if not df.empty:
        with st.expander("Kayıt Sil"):
            sil_id = st.selectbox("Silinecek ID", df["id"].tolist(), key=f"{key_prefix}_sil")
            if st.button("Sil", key=f"{key_prefix}_btn"):
                with conn.session as s:
                    s.execute(text(f"DELETE FROM {table} WHERE id=:i"), {"i": sil_id})
                    s.commit()
                log_action(st.session_state.user_name, f"{table} silindi", f"ID:{sil_id}")
                st.success("Kayıt silindi")
                st.rerun()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False)
    return buf.getvalue()

@st.cache_data(ttl=3600)
def doviz_kurlari_getir():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=5)
        data = r.json()
        return {"USD": round(1 / data["rates"]["USD"], 4), "EUR": round(1 / data["rates"]["EUR"], 4)}
    except: return {"USD": 0.03, "EUR": 0.028}

# ── OTURUM & GİRİŞ ──
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>FORLE TECH ERP</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login"):
            em = st.text_input("E-posta").strip().lower()
            pw = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hash_pw(pw)})
                if not user.empty:
                    st.session_state.update({"authenticated": True, "user_name": user.iloc[0]["isim"], "user_email": user.iloc[0]["email"], "user_rol": user.iloc[0]["rol"]})
                    st.rerun()
                else: st.error("Hatalı bilgiler.")
    st.stop()

# ── SIDEBAR ──
USER_ROL = st.session_state.user_rol
IS_YONETICI = USER_ROL in ["Admin", "Yönetici"]
IS_MUHENDIS = USER_ROL == "Elektrik Elektronik Mühendisi"

with st.sidebar:
    st.markdown(f"**{st.session_state.user_name}** \n<span class='role-badge'>{USER_ROL}</span>", unsafe_allow_html=True)
    menuler = ["Ana Sayfa", "Parça Yönetimi", "Cihaz Yönetimi", "Masraf Beyanı", "Görevler", "Ayarlar"]
    if IS_YONETICI: 
        menuler.insert(3, "Kurumsal Bütçe")
        menuler += ["Personel", "Onay Paneli", "Audit Log", "Yetkiler"]
    page = st.radio("Menü", menuler)
    if st.button("Çıkış Yap"):
        st.session_state.authenticated = False
        st.rerun()

# ── ANA SAYFA ──
if page == "Ana Sayfa":
    st.markdown('<div class="page-header"><h2>Ana Sayfa</h2><p>Operasyonel Özet</p></div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Parça", load_df("SELECT COUNT(*) FROM parcalar").iloc[0,0])
    c2.metric("Cihaz", load_df("SELECT COUNT(*) FROM cihazlar").iloc[0,0])
    c3.metric("Görev", load_df("SELECT COUNT(*) FROM gorevler WHERE durum!='Tamamlandı'").iloc[0,0])
    c4.metric("Bekleyen Masraf", load_df("SELECT COUNT(*) FROM masraf_iadeleri WHERE durum='Bekliyor'").iloc[0,0])

    st.markdown("#### Bildirimler")
    df_notif = load_df("SELECT * FROM bildirimler ORDER BY created_at DESC LIMIT 10")
    if not df_notif.empty:
        for _, b in df_notif.iterrows():
            st.markdown(f"<div class='notif-card'>{b['mesaj']}</div>", unsafe_allow_html=True)

# ── PARÇA YÖNETİMİ ──
elif page == "Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    if "p_form" not in st.session_state: st.session_state.p_form = False
    
    if (IS_YONETICI or IS_MUHENDIS) and st.button("Yeni Parça Ekle"): st.session_state.p_form = True
    
    if st.session_state.p_form:
        with st.form("p_add", clear_on_submit=True):
            ve = st.text_input("Varlık Etiketi"); mo = st.text_input("Model"); du = st.selectbox("Durum", ["Aktif","Arızalı","Depoda"])
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO parcalar (varlik_etiketi,model,durum,ekleyen) VALUES (:v,:m,:d,:e)"), {"v":ve,"m":mo,"d":du,"e":st.session_state.user_name})
                    s.commit()
                st.session_state.p_form = False
                islem_basarili()
    
    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    kayit_sil_ui(df, "parcalar", "parca")

# ── CİHAZ YÖNETİMİ ──
elif page == "Cihaz Yönetimi":
    st.markdown('<div class="page-header"><h2>Cihaz Yönetimi</h2></div>', unsafe_allow_html=True)
    if "c_form" not in st.session_state: st.session_state.c_form = False
    
    if (IS_YONETICI or IS_MUHENDIS) and st.button("Yeni Cihaz Ekle"): st.session_state.c_form = True
    
    if st.session_state.c_form:
        with st.form("c_add"):
            ca = st.text_input("Cihaz Adı"); ip = st.text_input("IP Adresi")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO cihazlar (cihaz_adi,ip,ekleyen) VALUES (:ca,:ip,:ek)"), {"ca":ca,"ip":ip,"ek":st.session_state.user_name})
                    s.commit()
                st.session_state.c_form = False
                islem_basarili()
    
    df = load_df("SELECT * FROM cihazlar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    kayit_sil_ui(df, "cihazlar", "cihaz")

# ── KURUMSAL BÜTÇE ──
elif page == "Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>Kurumsal Bütçe</h2></div>', unsafe_allow_html=True)
    if "h_form" not in st.session_state: st.session_state.h_form = False
    
    if st.button("Yeni Harcama Girişi"): st.session_state.h_form = True
    
    if st.session_state.h_form:
        with st.form("h_add"):
            tt = st.number_input("Tutar"); pb = st.selectbox("Para Birimi", ["TRY","USD","EUR"])
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih,tutar,para_birimi,giren) VALUES (:d,:t,:p,:g)"), {"d":str(datetime.date.today()),"t":tt,"p":pb,"g":st.session_state.user_name})
                    s.commit()
                st.session_state.h_form = False
                islem_basarili()

    df = load_df("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "harcamalar", "harcama")

# ── MASRAF BEYANI ──
elif page == "Masraf Beyanı":
    st.markdown('<div class="page-header"><h2>Masraf Beyanı</h2></div>', unsafe_allow_html=True)
    if "m_form" not in st.session_state: st.session_state.m_form = False
    
    if st.button("Yeni Masraf Talebi"): st.session_state.m_form = True
    
    if st.session_state.m_form:
        with st.form("m_add"):
            tu = st.number_input("Tutar (TRY)"); ac = st.text_area("Açıklama")
            if st.form_submit_button("Onaya Gönder"):
                with conn.session as s:
                    s.execute(text("INSERT INTO masraf_iadeleri (talep_eden,talep_eden_email,tutar,aciklama) VALUES (:te,:tee,:tu,:a)"), {"te":st.session_state.user_name,"tee":st.session_state.user_email,"tu":tu,"a":ac})
                    s.commit()
                st.session_state.m_form = False
                islem_basarili()

    df = load_df("SELECT * FROM masraf_iadeleri WHERE talep_eden_email=:e", {"e":st.session_state.user_email})
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "masraf_iadeleri", "masraf")

# ── GÖREVLER ──
elif page == "Görevler":
    st.markdown('<div class="page-header"><h2>Görevler</h2></div>', unsafe_allow_html=True)
    if "g_form" not in st.session_state: st.session_state.g_form = False
    
    if st.button("Yeni Görev"): st.session_state.g_form = True
    
    if st.session_state.g_form:
        with st.form("g_add"):
            ba = st.text_input("Başlık"); at = st.text_input("Atanan")
            if st.form_submit_button("Ekle"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik,atanan,olusturan) VALUES (:b,:a,:o)"), {"b":ba,"a":at,"o":st.session_state.user_name})
                    s.commit()
                st.session_state.g_form = False
                islem_basarili()

    df = load_df("SELECT * FROM gorevler ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "gorevler", "gorev")

# ── PERSONEL ──
elif page == "Personel":
    st.markdown('<div class="page-header"><h2>Personel Listesi</h2></div>', unsafe_allow_html=True)
    if "per_form" not in st.session_state: st.session_state.per_form = False
    
    if IS_YONETICI and st.button("Yeni Personel Ekle"): st.session_state.per_form = True
    
    if st.session_state.per_form:
        with st.form("per_add"):
            i = st.text_input("Ad Soyad"); p = st.text_input("Pozisyon")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO personel (isim,pozisyon) VALUES (:i,:p)"), {"i":i,"p":p})
                    s.commit()
                st.session_state.per_form = False
                islem_basarili()

    df = load_df("SELECT * FROM personel ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "personel", "personel")

# ── DİĞER YÖNETİM SAYFALARI ──
elif page == "Audit Log":
    st.markdown('<div class="page-header"><h2>Audit Log</h2></div>', unsafe_allow_html=True)
    st.dataframe(load_df("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100"), use_container_width=True)

elif page == "Yetkiler":
    st.markdown('<div class="page-header"><h2>Yetki Yönetimi</h2></div>', unsafe_allow_html=True)
    df = load_df("SELECT id, email, isim, rol FROM kullanicilar")
    st.dataframe(df, use_container_width=True)
    if IS_YONETICI:
        with st.form("y_up"):
            uid = st.selectbox("ID", df["id"].tolist()); rol = st.selectbox("Rol", ["Kullanici","Elektrik Elektronik Mühendisi","Yönetici","Admin"])
            if st.form_submit_button("Güncelle"):
                with conn.session as s: s.execute(text("UPDATE kullanicilar SET rol=:r WHERE id=:i"), {"r":rol,"i":uid}); s.commit()
                islem_basarili()
