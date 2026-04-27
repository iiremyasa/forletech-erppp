import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import hashlib
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from contextlib import contextmanager

st.set_page_config(
    page_title="FORLE TECH | ERP Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2332 0%, #243447 100%);
    }
    section[data-testid="stSidebar"] * { color: #e8edf3 !important; }
    div[data-testid="metric-container"] {
        background: white; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stButton > button {
        background: #1a2332; color: white !important; border: none; border-radius: 8px;
        font-weight: 500; transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #243447; box-shadow: 0 4px 12px rgba(26,35,50,0.3); transform: translateY(-1px);
    }
    .page-header {
        background: linear-gradient(135deg, #1a2332 0%, #2d4a6e 100%); color: white;
        padding: 24px 32px; border-radius: 16px; margin-bottom: 24px;
    }
    .page-header h2 { color: white; margin: 0; font-size: 1.6rem; }
    .page-header p  { color: #a0b4c8; margin: 4px 0 0 0; font-size: 0.9rem; }
    .role-badge {
        display: inline-block; padding: 2px 10px; border-radius: 100px;
        font-size: 0.72rem; font-weight: 600; background: rgba(59,130,246,0.15); color: #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİTABANI & MAİL FONKSİYONLARI
# ─────────────────────────────────────────
DB = "forletech.db"

def mail_gonder(alici, konu, icerik):
    try:
        cfg = st.secrets["smtp"]
        server = cfg["server"]
        port = int(cfg["port"])
        email = cfg["email"]
        password = cfg["password"]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = konu
        msg["From"]    = f"FORLE TECH ERP <{email}>"
        msg["To"]      = alici

        html = MIMEText(f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#1a2332;padding:24px;border-radius:12px 12px 0 0;">
                <h2 style="color:white;margin:0;">🏢 FORLE TECH</h2>
            </div>
            <div style="background:white;padding:24px;border:1px solid #e2e8f0;border-radius:0 0 12px 12px;">
                {icerik}
            </div>
        </div>
        """, "html", "utf-8")

        msg.attach(html)
        with smtplib.SMTP(server, port) as s:
            s.ehlo()
            s.starttls()
            s.login(email, password)
            s.sendmail(email, alici, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Mail gönderilemedi: {e}")
        return False

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS dogrulama_kodlari (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, isim TEXT NOT NULL, sifre TEXT NOT NULL, kod TEXT NOT NULL, gecerlilik TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS kullanicilar (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, sifre TEXT NOT NULL, isim TEXT NOT NULL, rol TEXT DEFAULT 'Kullanici', created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS parcalar (id INTEGER PRIMARY KEY AUTOINCREMENT, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS cihazlar (id INTEGER PRIMARY KEY AUTOINCREMENT, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS harcamalar (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, kategori TEXT, tutar REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS gorevler (id INTEGER PRIMARY KEY AUTOINCREMENT, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS personel (id INTEGER PRIMARY KEY AUTOINCREMENT, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS izinler (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_adi TEXT, izin_turu TEXT, baslangic TEXT, bitis TEXT, gun_sayisi REAL, durum TEXT DEFAULT 'Bekliyor', talep_eden TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS bildirimler (id INTEGER PRIMARY KEY AUTOINCREMENT, tip TEXT, mesaj TEXT, tarih TEXT, okundu INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS harcama_talepleri (id INTEGER PRIMARY KEY AUTOINCREMENT, personel TEXT, tarih TEXT, tutar REAL, aciklama TEXT, belge_adi TEXT, belge_data BLOB, durum TEXT DEFAULT 'Bekliyor', dekont_adi TEXT, dekont_data BLOB, created_at TEXT DEFAULT (datetime('now','localtime')));
        """)
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO kullanicilar (email, sifre, isim, rol) VALUES (?, ?, ?, ?)", ("admin@forleai.com", pw, "Sistem Yöneticisi", "Admin"))

def log_action(kullanici, aksiyon, detay=""):
    with get_conn() as conn:
        conn.execute("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (?,?,?)", (kullanici, aksiyon, detay))

def sys_bildirim(tip, mesaj):
    with get_conn() as conn:
        conn.execute("INSERT INTO bildirimler (tip,mesaj,tarih) VALUES (?,?,?)", (tip, mesaj, datetime.date.today().strftime("%d-%m-%Y")))

def sil_kayit(tablo, kayit_id):
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {tablo} WHERE id=?", (kayit_id,))
    log_action(st.session_state.user_name, f"{tablo} Silindi", f"Kayıt ID: {kayit_id}")

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

init_db()

# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR & YETKİLENDİRME
# ─────────────────────────────────────────
def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf

def page_header(title, desc):
    st.markdown(f'<div class="page-header"><h2>{title}</h2><p>{desc}</p></div>', unsafe_allow_html=True)

def load_df(table, cols=None, where_clause="", params=()):
    with get_conn() as conn:
        query = f"SELECT * FROM {table} {where_clause} ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn, params=params)
    if cols:
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
    return df

def yetki_kontrol(izin_verilen_roller):
    return st.session_state.user_rol in izin_verilen_roller

def excel_import_ui(tablo_adi):
    with st.expander(f"📁 Excel'den Toplu {tablo_adi.capitalize()} İçe Aktar", expanded=False):
        st.info("Sistemden indirdiğiniz Excel dosyasına verilerinizi doldurup buradan tek seferde yükleyebilirsiniz.")
        uploaded_file = st.file_uploader(f"Excel Dosyası Yükle ({tablo_adi})", type=["xlsx", "xls"], key=f"file_{tablo_adi}")
        if uploaded_file and st.button("İçeri Aktar", key=f"btn_{tablo_adi}"):
            try:
                df_import = pd.read_excel(uploaded_file)
                if "id" in df_import.columns: df_import = df_import.drop(columns=["id"])
                if "created_at" in df_import.columns: df_import = df_import.drop(columns=["created_at"])
                with get_conn() as conn:
                    df_import.to_sql(tablo_adi, conn, if_exists="append", index=False)
                log_action(st.session_state.user_name, "Excel İçe Aktarım", tablo_adi)
                st.success(f"{len(df_import)} kayıt başarıyla eklendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Hata oluştu! Detay: {e}")

# ─────────────────────────────────────────
# GİRİŞ EKRANI
# ─────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding:60px 0 20px'><div style='font-size:3rem'>🏢</div><h1 style='color:#1a2332;'>FORLE TECH</h1><p>Kurumsal ERP Portalı</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["Giriş Yap", "Yeni Hesap"])
        with tab1:
            with st.form("giris"):
                email = st.text_input("E-posta").strip().lower()
                pw = st.text_input("Şifre", type="password").strip()
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    with get_conn() as conn:
                        row = conn.execute("SELECT * FROM kullanicilar WHERE email=? AND sifre=?", (email, hash_pw(pw))).fetchone()
                    if row:
                        st.session_state.update({"authenticated": True, "user_name": row["isim"], "user_email": row["email"], "user_rol": row["rol"]})
                        log_action(row["isim"], "Giriş", email)
                        st.rerun()
                    else:
                        st.error("Hatalı e-posta veya şifre.")
        with tab2:
            if "kayit_dogrulama_bekleniyor" not in st.session_state:
                st.session_state.kayit_dogrulama_bekleniyor = False
            if not st.session_state.kayit_dogrulama_bekleniyor:
                with st.form("kayit"):
                    isim = st.text_input("Ad Soyad").strip()
                    email2 = st.text_input("E-posta (@forleai.com)").strip().lower()
                    pw2 = st.text_input("Şifre", type="password").strip()
                    pw2b = st.text_input("Şifre Tekrar", type="password").strip()
                    if st.form_submit_button("Doğrulama Kodu Gönder", use_container_width=True):
                        if not email2.endswith("@forleai.com"): st.error("Sadece @forleai.com uzantısı kabul edilir.")
                        elif pw2 != pw2b: st.error("Şifreler uyuşmuyor.")
                        else:
                            with get_conn() as conn:
                                mevcut = conn.execute("SELECT id FROM kullanicilar WHERE email=?", (email2,)).fetchone()
                            if mevcut: st.warning("Bu e-posta zaten kayıtlı.")
                            else:
                                kod = str(random.randint(100000, 999999))
                                gecerlilik = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
                                with get_conn() as conn:
                                    conn.execute("DELETE FROM dogrulama_kodlari WHERE email=?", (email2,))
                                    conn.execute("INSERT INTO dogrulama_kodlari (email, isim, sifre, kod, gecerlilik) VALUES (?,?,?,?,?)", (email2, isim, hash_pw(pw2), kod, gecerlilik))
                                gonderildi = mail_gonder(email2, "FORLE TECH ERP — Doğrulama Kodunuz", f"<h2>{kod}</h2><p>Bu kod 10 dakika geçerlidir.</p>")
                                if gonderildi:
                                    st.session_state.kayit_dogrulama_bekleniyor = True
                                    st.session_state.kayit_email = email2
                                    st.rerun()
            else:
                st.info(f"**{st.session_state.kayit_email}** adresine kod gönderildi.")
                with st.form("dogrulama"):
                    girilen_kod = st.text_input("Doğrulama Kodu", max_chars=6).strip()
                    if st.form_submit_button("Hesabı Onayla", use_container_width=True):
                        with get_conn() as conn:
                            kayit = conn.execute("SELECT * FROM dogrulama_kodlari WHERE email=? AND kod=?", (st.session_state.kayit_email, girilen_kod)).fetchone()
                        if not kayit: st.error("Hatalı kod!")
                        else:
                            with get_conn() as conn:
                                conn.execute("INSERT INTO kullanicilar (email,sifre,isim) VALUES (?,?,?)", (kayit["email"], kayit["sifre"], kayit["isim"]))
                                conn.execute("DELETE FROM dogrulama_kodlari WHERE email=?", (kayit["email"],))
                            st.session_state.kayit_dogrulama_bekleniyor = False
                            st.success("Hesabınız doğrulandı! Giriş yapabilirsiniz.")
                            st.rerun()
                    if st.form_submit_button("İptal"):
                        st.session_state.kayit_dogrulama_bekleniyor = False
                        st.rerun()
    st.stop()

# ─────────────────────────────────────────
# DİNAMİK YETKİ KONTROLLÜ SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='text-align:center;padding:16px 0'><div style='font-weight:700;font-size:1.1rem;color:white'>FORLE TECH</div><span class='role-badge'>{st.session_state.user_rol}</span></div>", unsafe_allow_html=True)
    
    # Standart Yetkiler (Herkesin görebildiği)
    menuler = ["Ana Sayfa", "Parça Yönetimi", "Cihaz Yönetimi", "Çalışan Masraf Beyanı", "Proje & Görevler"]
    
    # Admin / Yönetici Özel Yetkileri (İnsan Kaynakları, Bütçe vb.)
    if yetki_kontrol(["Admin", "Yönetici"]):
        menuler.insert(3, "Kurumsal Bütçe")
        menuler.extend(["İnsan Kaynakları", "Masraf Onay Paneli", "Bildirimler", "Audit Log", "Yetkilendirme Paneli"])
    
    page = st.radio("Menü", menuler, label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# ANA SAYFA (Rol Bazlı Gizlilik)
# ─────────────────────────────────────────
if page == "Ana Sayfa":
    page_header("Kontrol Paneli", "FORLE TECH ERP — Genel Bakış")
    
    with get_conn() as conn:
        n_parca = conn.execute("SELECT COUNT(*) FROM parcalar").fetchone()[0]
        n_cihaz = conn.execute("SELECT COUNT(*) FROM cihazlar").fetchone()[0]
        n_gorev = conn.execute("SELECT COUNT(*) FROM gorevler WHERE durum != 'Tamamlandı'").fetchone()[0]
        
        if yetki_kontrol(["Admin", "Yönetici"]):
            n_personel = conn.execute("SELECT COUNT(*) FROM personel").fetchone()[0]
            toplam_h = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM harcamalar").fetchone()[0]
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Kayıtlı Parça", n_parca)
            c2.metric("Kayıtlı Cihaz", n_cihaz)
            c3.metric("Açık Görev", n_gorev)
            c4.metric("Kayıtlı Personel", n_personel)
            c5.metric("Toplam Harcama", f"{toplam_h:,.0f} ₺")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Kayıtlı Parça", n_parca)
            c2.metric("Kayıtlı Cihaz", n_cihaz)
            c3.metric("Açık Görev", n_gorev)

# ─────────────────────────────────────────
# PARÇA YÖNETİMİ 
# ─────────────────────────────────────────
elif page == "Parça Yönetimi":
    page_header("Parça Yönetimi", "Envanter takibi")
    
    if yetki_kontrol(["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]):
        with st.expander("Yeni Parça Ekle"):
            with st.form("parca_form"):
                c1, c2 = st.columns(2)
                ve = c1.text_input("Varlık Etiketi")
                mo = c1.text_input("Model")
                du = c2.selectbox("Durum", ["Aktif", "Arızalı", "Depoda", "Hurda"])
                sn = c2.text_input("Seri No")
                if st.form_submit_button("Kaydet"):
                    with get_conn() as conn:
                        conn.execute("INSERT INTO parcalar (varlik_etiketi, model, durum, seri_no) VALUES (?,?,?,?)", (ve, mo, du, sn))
                    st.success("Parça eklendi.")
                    st.rerun()
        excel_import_ui("parcalar")
    else:
        st.info("💡 Sadece Yöneticiler ve Elektrik Elektronik Mühendisleri sisteme yeni parça ekleyebilir.")

    df = load_df("parcalar")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty: 
        st.download_button("Excel İndir", excel_export(df.drop(columns=["id"], errors="ignore")), "parcalar.xlsx")
        
        # SİLME YETKİSİ
        if yetki_kontrol(["Admin", "Yönetici"]):
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Parça ID", df["id"].tolist(), key="sil_p")
                if st.button("Seçili Parçayı Sil"):
                    sil_kayit("parcalar", sil_id)
                    st.success("Kayıt silindi.")
                    st.rerun()

# ─────────────────────────────────────────
# CİHAZ YÖNETİMİ
# ─────────────────────────────────────────
elif page == "Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Donanım varlık takibi")
    
    if yetki_kontrol(["Admin", "Yönetici", "Elektrik Elektronik Mühendisi"]):
        with st.expander("Yeni Cihaz Ekle"):
            with st.form("cihaz_form"):
                ca = st.text_input("Cihaz Adı")
                mo = st.text_input("Model")
                du = st.selectbox("Durum", ["Aktif","Testte","Bakımda","Depoda"])
                if st.form_submit_button("Kaydet"):
                    with get_conn() as conn:
                        conn.execute("INSERT INTO cihazlar (cihaz_adi, model, durum) VALUES (?,?,?)", (ca, mo, du))
                    st.success("Cihaz eklendi.")
                    st.rerun()
        excel_import_ui("cihazlar")
    else:
        st.info("💡 Sadece Yöneticiler ve Elektrik Elektronik Mühendisleri sisteme yeni cihaz ekleyebilir.")
        
    df = load_df("cihazlar")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty: 
        st.download_button("Excel İndir", excel_export(df.drop(columns=["id"], errors="ignore")), "cihazlar.xlsx")
        
        # SİLME YETKİSİ
        if yetki_kontrol(["Admin", "Yönetici"]):
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Cihaz ID", df["id"].tolist(), key="sil_c")
                if st.button("Seçili Cihazı Sil"):
                    sil_kayit("cihazlar", sil_id)
                    st.success("Kayıt silindi.")
                    st.rerun()

# ─────────────────────────────────────────
# KURUMSAL BÜTÇE (Sadece Yönetici)
# ─────────────────────────────────────────
elif page == "Kurumsal Bütçe":
    page_header("Kurumsal Bütçe", "Şirket içi genel giderler (Yönetici Görünümü)")
    
    with st.expander("Yeni Harcama Ekle"):
        with st.form("harcama_form"):
            h1, h2, h3 = st.columns(3)
            h_tarih = h1.date_input("Tarih", datetime.date.today())
            h_kat   = h1.selectbox("Kategori", ["Ar-Ge Alımı","Ofis Gideri","Seyahat","Maaş","Diğer"])
            h_tutar = h2.number_input("Tutar (₺)", min_value=0.0, step=100.0)
            h_fatura = h2.text_input("Fatura / Fiş No")
            h_acik = h3.text_area("Açıklama")
            if st.form_submit_button("Kaydet"):
                with get_conn() as conn:
                    conn.execute("INSERT INTO harcamalar (tarih,kategori,tutar,fatura_no,aciklama,giren) VALUES (?,?,?,?,?,?)",
                                 (h_tarih.strftime("%d-%m-%Y"), h_kat, h_tutar, h_fatura, h_acik, st.session_state.user_name))
                st.success("Harcama kaydedildi.")
                st.rerun()

    excel_import_ui("harcamalar")
    df = load_df("harcamalar")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty: 
        st.download_button("Excel İndir", excel_export(df.drop(columns=["id"], errors="ignore")), "kurumsal_harcamalar.xlsx")
        with st.expander("🗑️ Kayıt Sil"):
            sil_id = st.selectbox("Silinecek Harcama ID", df["id"].tolist(), key="sil_h")
            if st.button("Seçili Harcamayı Sil"):
                sil_kayit("harcamalar", sil_id)
                st.success("Kayıt silindi.")
                st.rerun()

# ─────────────────────────────────────────
# İNSAN KAYNAKLARI (Sadece Yönetici)
# ─────────────────────────────────────────
elif page == "İnsan Kaynakları":
    page_header("İnsan Kaynakları", "Personel ve özlük hakları (Yönetici Görünümü)")
    
    with st.expander("Yeni Personel Ekle"):
        with st.form("personel_form"):
            p1, p2 = st.columns(2)
            per_isim  = p1.text_input("Ad Soyad")
            per_email = p1.text_input("E-posta")
            per_tel   = p1.text_input("Telefon")
            per_poz   = p2.text_input("Pozisyon")
            per_dep   = p2.selectbox("Departman", ["Yazılım","Donanım","Ar-Ge","Yönetim","Satış","Diğer"])
            per_basl  = p2.date_input("İşe Başlama", datetime.date.today())
            per_not = st.text_area("Notlar")
            if st.form_submit_button("Kaydet"):
                with get_conn() as conn:
                    conn.execute("INSERT INTO personel (isim,email,pozisyon,departman,ise_baslama,telefon,notlar) VALUES (?,?,?,?,?,?,?)",
                                 (per_isim, per_email, per_poz, per_dep, per_basl.strftime("%d-%m-%Y"), per_tel, per_not))
                st.success("Personel eklendi.")
                st.rerun()

    excel_import_ui("personel")
    p_df = load_df("personel")
    st.dataframe(p_df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not p_df.empty: 
        st.download_button("Excel İndir", excel_export(p_df.drop(columns=["id"], errors="ignore")), "personel.xlsx")
        with st.expander("🗑️ Kayıt Sil"):
            sil_id = st.selectbox("Silinecek Personel ID", p_df["id"].tolist(), key="sil_per")
            if st.button("Seçili Personeli Sil"):
                sil_kayit("personel", sil_id)
                st.success("Kayıt silindi.")
                st.rerun()

# ─────────────────────────────────────────
# PROJE & GÖREVLER (Herkese Açık Ekleme)
# ─────────────────────────────────────────
elif page == "Proje & Görevler":
    page_header("Proje & Görev Takibi", "Görev atama, önceliklendirme ve durum takibi")
    
    with st.expander("Yeni Görev Ekle"):
        with st.form("gorev_form"):
            g1, g2 = st.columns(2)
            g_baslik  = g1.text_input("Görev Başlığı")
            g_proje   = g1.text_input("Proje Adı")
            g_atanan  = g1.text_input("Atanan Kişi")
            g_oncelik = g2.selectbox("Öncelik", ["Düşük","Orta","Yüksek","Kritik"])
            g_durum   = g2.selectbox("Durum", ["Bekliyor","Devam Ediyor","İncelemede","Tamamlandı"])
            g_tarih   = g2.date_input("Son Tarih", datetime.date.today())
            g_acik = st.text_area("Açıklama")
            if st.form_submit_button("Görev Ekle", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("""
                        INSERT INTO gorevler (baslik,aciklama,atanan,durum,oncelik,son_tarih,proje,olusturan)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (g_baslik, g_acik, g_atanan, g_durum, g_oncelik, g_tarih.strftime("%d-%m-%Y"), g_proje, st.session_state.user_name))
                st.success("Görev eklendi.")
                st.rerun()

    df = load_df("gorevler")
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
    if not df.empty:
        st.download_button("Excel İndir", excel_export(df.drop(columns=["id"], errors="ignore")), "gorevler.xlsx")
        
        # SİLME YETKİSİ
        if yetki_kontrol(["Admin", "Yönetici"]):
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Görev ID", df["id"].tolist(), key="sil_g")
                if st.button("Seçili Görevi Sil"):
                    sil_kayit("gorevler", sil_id)
                    st.success("Kayıt silindi.")
                    st.rerun()

# ─────────────────────────────────────────
# BİLDİRİMLER (Sadece Yönetici)
# ─────────────────────────────────────────
elif page == "Bildirimler":
    page_header("Bildirimler", "Sisteme manuel bildirim ekle veya sil")
    
    with st.form("bildirim_form"):
        b_tip  = st.selectbox("Tip", ["bilgi","uyari","basari"])
        b_msg  = st.text_input("Mesaj")
        if st.form_submit_button("Bildirim Gönder"):
            sys_bildirim(b_tip, b_msg)
            st.success("Bildirim eklendi.")
            st.rerun()
            
    b_df = load_df("bildirimler")
    st.dataframe(b_df, use_container_width=True)
    if not b_df.empty:
        with st.expander("🗑️ Bildirim Sil"):
            sil_id = st.selectbox("Silinecek Bildirim ID", b_df["id"].tolist(), key="sil_b")
            if st.button("Seçili Bildirimi Sil"):
                sil_kayit("bildirimler", sil_id)
                st.success("Kayıt silindi.")
                st.rerun()

# ─────────────────────────────────────────
# ÇALIŞAN MASRAF BEYANI
# ─────────────────────────────────────────
elif page == "Çalışan Masraf Beyanı":
    page_header("Masraf Beyanı", "Cebinizden yaptığınız kurumsal harcamaları yönetime iletin")
    with st.form("masraf_form"):
        st.info("Fiş veya fatura fotoğrafını yüklemek zorunludur.")
        t_tar = st.date_input("Harcama Tarihi")
        t_tut = st.number_input("Tutar (₺)", min_value=1.0, step=50.0)
        t_ack = st.text_area("Harcama Açıklaması (Yemek, Taksi, Malzeme vb.)")
        t_belge = st.file_uploader("Fiş / Fatura Yükle", type=["png", "jpg", "pdf"])
        if st.form_submit_button("Onaya Gönder"):
            if not t_belge: st.error("Lütfen harcamanın belgesini yükleyin.")
            else:
                belge_bytes = t_belge.read()
                with get_conn() as conn:
                    conn.execute("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama, belge_adi, belge_data) VALUES (?,?,?,?,?,?)", 
                                 (st.session_state.user_name, t_tar.strftime("%d-%m-%Y"), t_tut, t_ack, t_belge.name, belge_bytes))
                sys_bildirim("bilgi", f"Yeni Masraf Talebi: {st.session_state.user_name} ({t_tut} ₺)")
                st.success("Talebiniz yönetime iletildi.")
                st.rerun()

    st.markdown("### Geçmiş Taleplerim")
    df_talepler = load_df("harcama_talepleri", where_clause="WHERE personel=?", params=(st.session_state.user_name,))
    if not df_talepler.empty:
        display_df = df_talepler[["tarih", "tutar", "aciklama", "durum", "belge_adi", "dekont_adi"]]
        st.dataframe(display_df, use_container_width=True)
        sec_id = st.selectbox("Dekontunu indirmek istediğiniz onaylı masrafı seçin:", df_talepler[df_talepler["durum"] == "Ödendi"]["id"].tolist(), format_func=lambda x: f"Talep ID: {x}")
        if sec_id:
            row = df_talepler[df_talepler["id"] == sec_id].iloc[0]
            if row["dekont_data"]:
                st.download_button(f"🧾 Dekontu İndir ({row['dekont_adi']})", data=row["dekont_data"], file_name=row["dekont_adi"])
    else:
        st.info("Henüz masraf talebiniz bulunmuyor.")

# ─────────────────────────────────────────
# MASRAF ONAY PANELİ (Sadece Yönetici)
# ─────────────────────────────────────────
elif page == "Masraf Onay Paneli":
    page_header("Masraf Onay Paneli", "Personel masraf beyanlarını incele ve öde")
    df_all = load_df("harcama_talepleri")
    if not df_all.empty:
        st.dataframe(df_all[["id", "personel", "tarih", "tutar", "aciklama", "durum", "belge_adi", "dekont_adi"]], use_container_width=True)
        st.download_button("Excel İndir", excel_export(df_all.drop(columns=["belge_data", "dekont_data"], errors="ignore")), "personel_masraflari.xlsx")
        
        st.markdown("---")
        with st.form("onay_form"):
            islem_id = st.selectbox("İşlem Yapılacak Talep ID", df_all["id"].tolist())
            secilen = df_all[df_all["id"] == islem_id].iloc[0]
            yeni_durum = st.selectbox("Karar", ["Bekliyor", "Onaylandı", "Reddedildi", "Ödendi"])
            dekont_file = st.file_uploader("Dekont Yükle (Eğer 'Ödendi' seçtiyseniz)", type=["pdf", "png", "jpg"])
            
            if st.form_submit_button("Durumu Güncelle"):
                d_bytes = dekont_file.read() if dekont_file else secilen["dekont_data"]
                d_name = dekont_file.name if dekont_file else secilen["dekont_adi"]
                with get_conn() as conn:
                    conn.execute("UPDATE harcama_talepleri SET durum=?, dekont_adi=?, dekont_data=? WHERE id=?", (yeni_durum, d_name, d_bytes, islem_id))
                    if yeni_durum == "Ödendi":
                        conn.execute("INSERT INTO harcamalar (tarih, kategori, tutar, aciklama, giren) VALUES (?,?,?,?,?)",
                                     (datetime.date.today().strftime("%d-%m-%Y"), "Personel Masrafı", secilen["tutar"], f"{secilen['personel']} - {secilen['aciklama']}", st.session_state.user_name))
                sys_bildirim("basari", f"{secilen['personel']} kişisinin masraf talebi '{yeni_durum}' olarak güncellendi.")
                st.success("İşlem kaydedildi.")
                st.rerun()
        
        indirme_id = st.selectbox("İncelemek için Talep ID seçin:", df_all["id"].tolist(), key="indir_box")
        if indirme_id:
            row_indir = df_all[df_all["id"] == indirme_id].iloc[0]
            if row_indir["belge_data"]:
                st.download_button(f"📥 Fişi/Faturayı İndir ({row_indir['belge_adi']})", data=row_indir["belge_data"], file_name=row_indir["belge_adi"])
                
        with st.expander("🗑️ Kayıt Sil"):
            sil_id = st.selectbox("Silinecek Talep ID", df_all["id"].tolist(), key="sil_talep")
            if st.button("Seçili Talebi Sil"):
                sil_kayit("harcama_talepleri", sil_id)
                st.success("Kayıt silindi.")
                st.rerun()
    else:
        st.info("Kayıtlı masraf talebi yok.")

# ─────────────────────────────────────────
# AUDİT LOG & YETKİLENDİRME PANELİ (Sadece Yönetici)
# ─────────────────────────────────────────
elif page == "Audit Log":
    page_header("Sistem Logları", "Tüm sistem işlem geçmişi")
    df = load_df("audit_log")
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("Excel İndir", excel_export(df), "audit_log.xlsx")

elif page == "Yetkilendirme Paneli":
    page_header("Kullanıcı Yetkilendirme", "Sisteme kayıtlı personellerin rollerini belirle")
    with get_conn() as conn:
        k_df = pd.read_sql_query("SELECT id, email, isim, rol FROM kullanicilar", conn)
    st.dataframe(k_df, use_container_width=True)
    
    with st.form("yetki_form"):
        y_id = st.selectbox("Yetkisi Değişecek Kullanıcı Seç (ID)", k_df["id"].tolist())
        yeni_rol = st.selectbox("Yeni Rol Ata", ["Kullanici", "Elektrik Elektronik Mühendisi", "Yönetici", "Admin"])
        if st.form_submit_button("Rolü Güncelle"):
            with get_conn() as conn:
                conn.execute("UPDATE kullanicilar SET rol=? WHERE id=?", (yeni_rol, y_id))
            st.success("Rol başarıyla güncellendi.")
            st.rerun()
