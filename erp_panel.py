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
            "CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, para_birimi TEXT DEFAULT 'TRY', tutar_usd REAL, tutar_eur REAL, kur_usd REAL, kur_eur REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, belge_adi TEXT, belge_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS masraf_iadeleri (id SERIAL PRIMARY KEY, talep_eden TEXT, talep_eden_email TEXT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, hedef_rol TEXT DEFAULT 'Tumu', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ]
        for t in tablolar: s.execute(text(t))
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

# ── OTURUM KONTROLÜ ──
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

# ── FORM STATE KONTROLLERİ ──
for form_key in ["p_form", "c_form", "h_form", "m_form", "g_form", "per_form"]:
    if form_key not in st.session_state: st.session_state[form_key] = False

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
        for _, b in df_notif.iterrows(): st.markdown(f"<div class='notif-card'>{b['mesaj']}</div>", unsafe_allow_html=True)

# ── PARÇA YÖNETİMİ ──
elif page == "Parça Yönetimi":
    st.markdown('<div class="page-header"><h2>Parça Yönetimi</h2></div>', unsafe_allow_html=True)
    
    if (IS_YONETICI or IS_MUHENDIS):
        if st.button("Yeni Parça Ekle"): st.session_state.p_form = True
        if st.session_state.p_form:
            with st.form("parca_add_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ve = c1.text_input("Varlık Etiketi"); mo = c1.text_input("Model")
                du = c1.selectbox("Durum", ["Aktif","Arızalı","Depoda","Hurda"]); sn = c1.text_input("Seri No")
                yv = c2.text_input("Yazılım Versiyonu"); bc = c2.text_input("Bağlı Cihaz")
                dn = c2.text_area("Durum Notu"); kt = c2.date_input("Kayıt Tarihi")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("""INSERT INTO parcalar (varlik_etiketi,model,durum,seri_no,yazilim_versiyonu,bagli_cihaz,durum_notu,kayit_tarihi,ekleyen) 
                                          VALUES (:ve,:mo,:du,:sn,:yv,:bc,:dn,:kt,:ek)"""),
                                  {"ve":ve,"mo":mo,"du":du,"sn":sn,"yv":yv,"bc":bc,"dn":dn,"kt":str(kt),"ek":st.session_state.user_name})
                        s.commit()
                    st.session_state.p_form = False
                    islem_basarili("Parça eklendi!")

    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Excel Çıktısı", excel_export(df), "parcalar.xlsx")
    kayit_sil_ui(df, "parcalar", "parca")

# ── CİHAZ YÖNETİMİ ──
elif page == "Cihaz Yönetimi":
    st.markdown('<div class="page-header"><h2>Cihaz Yönetimi</h2></div>', unsafe_allow_html=True)
    if (IS_YONETICI or IS_MUHENDIS):
        if st.button("Yeni Cihaz Ekle"): st.session_state.c_form = True
        if st.session_state.c_form:
            with st.form("cihaz_add_form"):
                c1, c2 = st.columns(2)
                ca = c1.text_input("Cihaz Adı"); ip = c1.text_input("IP Adresi")
                mo = c1.text_input("Model"); du = c1.selectbox("Durum", ["Aktif","Testte","Bakımda"])
                ss = c2.text_input("Sensör Seri No"); ak = c2.text_input("Anakart Seri No")
                sn = c2.text_input("Seri No"); nt = c2.text_area("Notlar")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("""INSERT INTO cihazlar (cihaz_adi,ip,model,takili_sensor_seri,anakart_seri,durum,seri_no,notlar,ekleyen) 
                                          VALUES (:ca,:ip,:mo,:ss,:ak,:du,:sn,:nt,:ek)"""),
                                  {"ca":ca,"ip":ip,"mo":mo,"ss":ss,"ak":ak,"du":du,"sn":sn,"nt":nt,"ek":st.session_state.user_name})
                        s.commit()
                    st.session_state.c_form = False
                    islem_basarili("Cihaz eklendi!")
    
    df = load_df("SELECT * FROM cihazlar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Excel Çıktısı", excel_export(df), "cihazlar.xlsx")
    kayit_sil_ui(df, "cihazlar", "cihaz")

# ── KURUMSAL BÜTÇE ──
elif page == "Kurumsal Bütçe":
    st.markdown('<div class="page-header"><h2>Kurumsal Bütçe</h2></div>', unsafe_allow_html=True)
    kurlar = doviz_kurlari_getir()
    if st.button("Harcama Girişi Yap"): st.session_state.h_form = True
    if st.session_state.h_form:
        with st.form("h_add_form"):
            c1, c2 = st.columns(2)
            tt = c1.number_input("Tutar"); pb = c1.selectbox("Para Birimi", ["TRY","USD","EUR"])
            kt = c2.selectbox("Kategori", ["Ar-Ge","Ofis","Seyahat","Diğer"]); ac = st.text_area("Açıklama")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih,kategori,tutar,para_birimi,giren,aciklama) VALUES (:d,:k,:t,:p,:g,:a)"), 
                              {"d":str(datetime.date.today()),"k":kt,"t":tt,"p":pb,"g":st.session_state.user_name,"a":ac})
                    s.commit()
                st.session_state.h_form = False
                islem_basarili()

    df = load_df("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    st.download_button("Excel Çıktısı", excel_export(df), "butce.xlsx")
    kayit_sil_ui(df, "harcamalar", "harcama")

# ── MASRAF BEYANI ──
elif page == "Masraf Beyanı":
    st.markdown('<div class="page-header"><h2>Masraf Beyanı</h2></div>', unsafe_allow_html=True)
    if st.button("Yeni Talep Oluştur"): st.session_state.m_form = True
    if st.session_state.m_form:
        with st.form("m_add_form"):
            tu = st.number_input("Tutar"); kt = st.selectbox("Kategori", ["Yemek","Ulaşım","Diğer"])
            ac = st.text_area("Açıklama")
            if st.form_submit_button("Gönder"):
                with conn.session as s:
                    s.execute(text("INSERT INTO masraf_iadeleri (talep_eden,talep_eden_email,tarih,kategori,tutar,aciklama) VALUES (:te,:tee,:t,:k,:tu,:a)"), 
                              {"te":st.session_state.user_name,"tee":st.session_state.user_email,"t":str(datetime.date.today()),"k":kt,"tu":tu,"a":ac})
                    s.commit()
                st.session_state.m_form = False
                islem_basarili()

    df = load_df("SELECT * FROM masraf_iadeleri WHERE talep_eden_email=:e", {"e":st.session_state.user_email})
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "masraf_iadeleri", "masraf")

# ── GÖREVLER ──
elif page == "Görevler":
    st.markdown('<div class="page-header"><h2>Görevler</h2></div>', unsafe_allow_html=True)
    if st.button("Yeni Görev Tanımla"): st.session_state.g_form = True
    if st.session_state.g_form:
        with st.form("g_add_form"):
            ba = st.text_input("Görev Başlığı"); at = st.text_input("Atanan")
            pr = st.text_input("Proje"); on = st.selectbox("Öncelik", ["Düşük","Orta","Yüksek"])
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik,atanan,proje,oncelik,olusturan) VALUES (:b,:a,:p,:o,:ok)"), 
                              {"b":ba,"a":at,"p":pr,"o":on,"ok":st.session_state.user_name})
                    s.commit()
                st.session_state.g_form = False
                islem_basarili()

    df = load_df("SELECT * FROM gorevler ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "gorevler", "gorev")

# ── PERSONEL ──
elif page == "Personel":
    st.markdown('<div class="page-header"><h2>Personel Yönetimi</h2></div>', unsafe_allow_html=True)
    if IS_YONETICI and st.button("Yeni Personel Kaydı"): st.session_state.per_form = True
    if st.session_state.per_form:
        with st.form("per_add_form"):
            ni = st.text_input("Ad Soyad"); po = st.text_input("Pozisyon")
            dp = st.text_input("Departman"); te = st.text_input("Telefon")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO personel (isim,pozisyon,departman,telefon) VALUES (:i,:p,:d,:t)"), 
                              {"i":ni,"p":po,"d":dp,"t":te})
                    s.commit()
                st.session_state.per_form = False
                islem_basarili()

    df = load_df("SELECT * FROM personel ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)
    kayit_sil_ui(df, "personel", "personel")
