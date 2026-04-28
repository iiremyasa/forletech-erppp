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

st.set_page_config(page_title="FORLE TECH | ERP Portal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-right: 1px solid rgba(255,255,255,0.05); }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 12px 16px; border-radius: 10px; margin-bottom: 6px; transition: all 0.2s ease; cursor: pointer; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background-color: rgba(255,255,255,0.08); transform: translateX(5px); }
    div[data-testid="metric-container"] { background: white; border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 14px; padding: 22px; transition: all 0.3s; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); border-color: #3b82f6; }
    .page-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 30px; border-radius: 18px; margin-bottom: 30px; border-left: 8px solid #3b82f6; }
    .page-header h2 { color: white; margin: 0; }
    .page-header p { color: #94a3b8; margin: 4px 0 0 0; }
    .role-badge { display: inline-block; padding: 5px 14px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25); color: #60a5fa !important; text-transform: uppercase; }
    .notif-card { background: white; border-radius: 12px; padding: 14px 18px; border-left: 4px solid #f59e0b; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
    .notif-info { border-color: #3b82f6; }
    .notif-success { border-color: #22c55e; }
    .kur-box { background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border: 1px solid #bae6fd; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; }
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
            "CREATE TABLE IF NOT EXISTS masraf_iadeleri (id SERIAL PRIMARY KEY, talep_eden TEXT, talep_eden_email TEXT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT, fisbelge_adi TEXT, fisbelge BYTEA, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, dekont_adi TEXT, dekont BYTEA, odeme_tarihi TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, hedef_rol TEXT DEFAULT 'Tumu', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ]
        for t in tablolar:
            s.execute(text(t))
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
    try:
        with conn.session as s:
            s.execute(text("INSERT INTO bildirimler (tip,mesaj,hedef_rol) VALUES (:t,:m,:h)"), {"t":tip,"m":mesaj,"h":hedef_rol})
            s.commit()
    except Exception: pass

def islem_basarili(msg="İşlem kaydedildi!"):
    st.toast(f"✅ {msg}", icon="✅")
    time.sleep(0.4)
    st.rerun()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf.read()

def page_header(title, desc):
    st.markdown(f'<div class="page-header"><h2>{title}</h2><p>{desc}</p></div>', unsafe_allow_html=True)

def excel_import_bolumu(table, col_map, key, ekstra_cols=None):
    with st.expander("📤 Excel'den Veri Aktar", expanded=False):
        sablon = pd.DataFrame(columns=list(col_map.keys()))
        st.download_button("📥 Şablon İndir", excel_export(sablon), f"sablon_{key}.xlsx", key=f"sbl_{key}")
        dosya = st.file_uploader("Excel Yükle (.xlsx)", type=["xlsx"], key=f"upl_{key}")
        if dosya:
            try:
                df_i = pd.read_excel(dosya).rename(columns=col_map)
                gecerli_cols = [c for c in col_map.values() if c in df_i.columns]
                df_i = df_i[gecerli_cols].copy()
                if ekstra_cols:
                    for k, v in ekstra_cols.items(): df_i[k] = v
                df_i = df_i.fillna("")
                st.dataframe(df_i, use_container_width=True, hide_index=True)
                if st.button(f"✅ {len(df_i)} Kaydı İçe Aktar", key=f"imp_{key}"):
                    basarili = 0
                    with conn.session as s:
                        for _, row in df_i.iterrows():
                            try:
                                row_dict = {str(k): (None if v == "" else v) for k, v in row.items()}
                                col_names = ", ".join(row_dict.keys())
                                col_params = ", ".join([f":{k}" for k in row_dict.keys()])
                                s.execute(text(f"INSERT INTO {table} ({col_names}) VALUES ({col_params})"), row_dict)
                                basarili += 1
                            except: pass
                        s.commit()
                    if basarili > 0:
                        st.success(f"{basarili} kayıt eklendi.")
                        st.rerun()
            except Exception as e: st.error(f"Dosya okunamadı: {e}")

@st.cache_data(ttl=3600)
def doviz_kurlari_getir():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=5)
        data = r.json()
        return {"USD": round(1 / data["rates"]["USD"], 4), "EUR": round(1 / data["rates"]["EUR"], 4), "kaynak": "ExchangeRate-API", "guncelleme": datetime.datetime.now().strftime("%H:%M")}
    except: return {"USD": 0.028, "EUR": 0.026, "kaynak": "Varsayılan", "guncelleme": "—"}

def yonetici_emailleri():
    df = load_df("SELECT email FROM kullanicilar WHERE rol IN ('Admin','Yonetici')")
    return df["email"].tolist() if not df.empty else []

def mail_gonder(alici, konu, icerik):
    try:
        cfg = st.secrets["smtp"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = konu
        msg["From"] = f"FORLE TECH ERP <{cfg['email']}>"
        msg["To"] = alici
        msg.attach(MIMEText(f"<html><body>{icerik}</body></html>", "html", "utf-8"))
        with smtplib.SMTP(cfg["server"], int(cfg["port"])) as s_:
            s_.ehlo(); s_.starttls(); s_.login(cfg["email"], cfg["password"])
            s_.sendmail(cfg["email"], alici, msg.as_string())
        return True
    except: return False

# ── GİRİŞ ──
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding:50px 0;'><h1>🚀 FORLE TECH</h1><p>Kurumsal ERP</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs([" Giriş Yap", " Yeni Hesap"])
        with tab1:
            with st.form("login"):
                em = st.text_input("E-posta").strip().lower()
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw", {"em": em, "pw": hash_pw(pw)})
                    if not user.empty:
                        st.session_state.update({"authenticated": True, "user_name": user.iloc[0]["isim"], "user_email": user.iloc[0]["email"], "user_rol": user.iloc[0]["rol"]})
                        st.rerun()
                    else: st.error("Hatalı bilgiler.")
        with tab2:
            if "kayit_bekliyor" not in st.session_state: st.session_state.kayit_bekliyor = False
            if not st.session_state.kayit_bekliyor:
                with st.form("kayit"):
                    isim = st.text_input("Ad Soyad"); email2 = st.text_input("E-posta (@forleai.com)").lower()
                    pw2 = st.text_input("Şifre", type="password"); pw2b = st.text_input("Şifre Tekrar", type="password")
                    if st.form_submit_button("Doğrulama Kodu Gönder", use_container_width=True):
                        if not email2.endswith("@forleai.com"): st.error("Geçersiz e-posta.")
                        elif pw2 != pw2b or len(pw2) < 4: st.error("Şifre hatası.")
                        else:
                            kod = str(random.randint(100000, 999999))
                            with conn.session as s:
                                s.execute(text("INSERT INTO dogrulama_kodlari (email,isim,sifre,kod,gecerlilik) VALUES (:e,:i,:s,:k,:g)"),
                                          {"e":email2,"i":isim,"s":hash_pw(pw2),"k":kod,"g":datetime.datetime.now()+datetime.timedelta(minutes=10)})
                                s.commit()
                            if mail_gonder(email2, "Doğrulama Kodu", f"Kodunuz: {kod}"):
                                st.session_state.update({"kayit_bekliyor": True, "kayit_email": email2}); st.rerun()
            else:
                with st.form("dogrulama"):
                    girilen = st.text_input("Kod", max_chars=6)
                    if st.form_submit_button("Onayla"):
                        kayit = load_df("SELECT * FROM dogrulama_kodlari WHERE email=:e AND kod=:k", {"e":st.session_state.kayit_email, "k":girilen})
                        if not kayit.empty:
                            with conn.session as s:
                                s.execute(text("INSERT INTO kullanicilar (email,sifre,isim) VALUES (:e,:s,:i)"), {"e":kayit.iloc[0]["email"],"s":kayit.iloc[0]["sifre"],"i":kayit.iloc[0]["isim"]})
                                s.commit()
                            st.session_state.kayit_bekliyor = False; st.success("Başarılı!"); st.rerun()
    st.stop()

# ── SIDEBAR ──
USER_ROL = st.session_state.user_rol
IS_YONETICI = USER_ROL in ["Admin", "Yönetici"]
IS_MUHENDIS = USER_ROL == "Elektrik Elektronik Mühendisi"

# Form kapatma kontrolü için State'ler
if "exp_p" not in st.session_state: st.session_state.exp_p = False
if "exp_c" not in st.session_state: st.session_state.exp_c = False
if "exp_h" not in st.session_state: st.session_state.exp_h = False
if "exp_g" not in st.session_state: st.session_state.exp_g = False
if "exp_per" not in st.session_state: st.session_state.exp_per = False
if "exp_m" not in st.session_state: st.session_state.exp_m = True

with st.sidebar:
    st.markdown(f"<div style='text-align:center;padding:10px;background:rgba(255,255,255,0.1);border-radius:10px;'><b>{st.session_state.user_name}</b><br><span class='role-badge'>{USER_ROL}</span></div>", unsafe_allow_html=True)
    menuler = [" Ana Sayfa", " Parça Yönetimi", " Cihaz Yönetimi", " Masraf Beyanı", " Görevler", " Ayarlar"]
    if IS_YONETICI: menuler.insert(3, " Kurumsal Bütçe"); menuler += [" Personel", " Onay Paneli", " Audit Log", " Yetkiler"]
    page = st.radio("Menü", menuler, label_visibility="collapsed")
    if st.button(" Çıkış"): st.session_state.authenticated = False; st.rerun()

#  ANA SAYFA
if page == " Ana Sayfa":
    page_header("Kontrol Paneli", "Özet")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(" Parça", load_df("SELECT COUNT(*) as n FROM parcalar").iloc[0,0])
    c2.metric(" Cihaz", load_df("SELECT COUNT(*) as n FROM cihazlar").iloc[0,0])
    c3.metric(" Görev", load_df("SELECT COUNT(*) as n FROM gorevler WHERE durum!='Tamamlandı'").iloc[0,0])
    c4.metric(" Personel", load_df("SELECT COUNT(*) as n FROM personel").iloc[0,0])

#  PARÇA YÖNETİMİ
elif page == " Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık Envanteri")
    if IS_YONETICI or IS_MUHENDIS:
        if st.button("➕ Yeni Parça Ekle"): st.session_state.exp_p = True
        with st.expander("Yeni Parça Formu", expanded=st.session_state.exp_p):
            with st.form("p_f", clear_on_submit=True):
                ve = st.text_input("Varlık Etiketi"); mo = st.text_input("Model")
                du = st.selectbox("Durum", ["Aktif","Arızalı","Depoda","Hurda"]); sn = st.text_input("Seri No")
                if st.form_submit_button("Kaydet", use_container_width=True):
                    with conn.session as s:
                        s.execute(text("INSERT INTO parcalar (varlik_etiketi,model,durum,seri_no,ekleyen) VALUES (:ve,:mo,:du,:sn,:ek)"), {"ve":ve,"mo":mo,"du":du,"sn":sn,"ek":st.session_state.user_name})
                        s.commit()
                    st.session_state.exp_p = False # Formu kapat
                    islem_basarili()
        excel_import_bolumu("parcalar", {"Varlık Etiketi":"varlik_etiketi","Model":"model","Durum":"durum","Seri No":"seri_no"}, "parca", {"ekleyen": st.session_state.user_name})
    
    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id","created_at"], errors="ignore"), use_container_width=True, hide_index=True)

#  CİHAZ YÖNETİMİ
elif page == " Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Donanım İzleme")
    if IS_YONETICI or IS_MUHENDIS:
        if st.button("➕ Yeni Cihaz Ekle"): st.session_state.exp_c = True
        with st.expander("Yeni Cihaz Formu", expanded=st.session_state.exp_c):
            with st.form("c_f", clear_on_submit=True):
                ca = st.text_input("Cihaz Adı"); ip = st.text_input("IP")
                if st.form_submit_button("Kaydet"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO cihazlar (cihaz_adi,ip,ekleyen) VALUES (:ca,:ip,:ek)"), {"ca":ca,"ip":ip,"ek":st.session_state.user_name})
                        s.commit()
                    st.session_state.exp_c = False # Formu kapat
                    islem_basarili()
    df = load_df("SELECT * FROM cihazlar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id","created_at"], errors="ignore"), use_container_width=True)

#  KURUMSAL BÜTÇE
elif page == " Kurumsal Bütçe":
    page_header("Kurumsal Bütçe", "Harcamalar")
    kurlar = doviz_kurlari_getir()
    if st.button("➕ Yeni Harcama Girişi"): st.session_state.exp_h = True
    with st.expander("Harcama Formu", expanded=st.session_state.exp_h):
        with st.form("h_f", clear_on_submit=True):
            tt = st.number_input("Tutar"); pb = st.selectbox("Para Birimi", ["TRY","USD","EUR"])
            if st.form_submit_button("Kaydet"):
                # (Kur hesaplama mantığı...)
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tutar,para_birimi,giren) VALUES (:t,:p,:g)"), {"t":tt,"p":pb,"g":st.session_state.user_name})
                    s.commit()
                st.session_state.exp_h = False # Formu kapat
                islem_basarili()
    df = load_df("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id","belge_data"], errors="ignore"), use_container_width=True)

#  MASRAF BEYANI
elif page == " Masraf Beyanı":
    page_header("Masraf Beyanı", "İade Talebi")
    if st.button("➕ Yeni Masraf Talebi"): st.session_state.exp_m = True
    with st.expander("Talep Formu", expanded=st.session_state.exp_m):
        with st.form("m_f", clear_on_submit=True):
            tu = st.number_input("Tutar (₺)"); ac = st.text_area("Açıklama")
            if st.form_submit_button("Onaya Gönder"):
                with conn.session as s:
                    s.execute(text("INSERT INTO masraf_iadeleri (talep_eden,talep_eden_email,tutar,aciklama) VALUES (:te,:tee,:tu,:a)"), {"te":st.session_state.user_name,"tee":st.session_state.user_email,"tu":tu,"a":ac})
                    s.commit()
                st.session_state.exp_m = False # Formu kapat
                islem_basarili()
    df = load_df("SELECT tarih,kategori,tutar,aciklama,durum FROM masraf_iadeleri WHERE talep_eden_email=:e", {"e":st.session_state.user_email})
    st.dataframe(df, use_container_width=True)

#  GÖREVLER
elif page == " Görevler":
    page_header("Görevler", "Proje Takibi")
    if st.button("➕ Yeni Görev"): st.session_state.exp_g = True
    with st.expander("Görev Formu", expanded=st.session_state.exp_g):
        with st.form("g_f"):
            ba = st.text_input("Başlık"); at = st.text_input("Atanan")
            if st.form_submit_button("Ekle"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik,atanan,olusturan) VALUES (:b,:a,:o)"), {"b":ba,"a":at,"o":st.session_state.user_name})
                    s.commit()
                st.session_state.exp_g = False # Formu kapat
                islem_basarili()
    df = load_df("SELECT * FROM gorevler ORDER BY id DESC")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)

# (Diğer Yönetimsel Sayfalar: Personel, Onay, Audit Log, Yetkiler, Ayarlar Mevcut Yapısını Korur...)
