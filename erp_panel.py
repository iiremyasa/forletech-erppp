import streamlit as st
import pandas as pd
import datetime
import hashlib
import io
from sqlalchemy import text

# --- 0. SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="FORLE TECH | ERP Portal", page_icon="🏢", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a2332 0%, #243447 100%); }
    section[data-testid="stSidebar"] * { color: #e8edf3 !important; }
    .stButton > button { background: #1a2332; color: white !important; border-radius: 8px; transition: all 0.2s; }
    .page-header { background: linear-gradient(135deg, #1a2332 0%, #2d4a6e 100%); color: white; padding: 24px; border-radius: 16px; margin-bottom: 24px; }
    .role-badge { padding: 2px 10px; border-radius: 100px; font-size: 0.72rem; font-weight: 600; background: rgba(59,130,246,0.15); color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# --- 1. VERİTABANI BAĞLANTISI (POSTGRESQL) ---
try:
    conn = st.connection("postgresql", type="sql")
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici');
            CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar FLOAT, fatura_no TEXT, aciklama TEXT, giren TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS izinler (id SERIAL PRIMARY KEY, personel_adi TEXT, izin_turu TEXT, baslangic TEXT, bitis TEXT, gun_sayisi FLOAT, durum TEXT DEFAULT 'Bekliyor', talep_eden TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, tarih TEXT, okundu INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """))
        # Varsayılan Admin
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol) VALUES ('admin@forleai.com', :p, 'Sistem Yöneticisi', 'Admin') ON CONFLICT DO NOTHING"), {"p": pw})
        s.commit()
except Exception as e:
    st.error(f"Kritik Veritabanı Hatası: {e}")

# --- 2. YARDIMCI FONKSİYONLAR ---
def log_action(u, a, d=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:u, :a, :d)"), {"u": u, "a": a, "d": d})
        s.commit()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False)
    buf.seek(0)
    return buf

# --- 3. GİRİŞ EKRANI ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding-top:60px'><h1>FORLE TECH ERP</h1></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        t1, t2 = st.tabs(["Giriş", "Yeni Kayıt"])
        with t1:
            with st.form("l"):
                em = st.text_input("E-posta").strip().lower()
                ps = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş", use_container_width=True):
                    res = conn.query("SELECT * FROM kullanicilar WHERE email=:e AND sifre=:p", params={"e":em, "p":hash_pw(ps)})
                    if not res.empty:
                        st.session_state.update({"authenticated": True, "user_name": res.iloc[0]['isim'], "user_email": res.iloc[0]['email'], "user_rol": res.iloc[0]['rol']})
                        log_action(st.session_state.user_name, "Giriş")
                        st.rerun()
                    else: st.error("Hatalı bilgiler.")
        with t2:
            with st.form("k"):
                ni = st.text_input("Ad Soyad")
                ne = st.text_input("E-posta (@forleai.com)")
                np = st.text_input("Şifre", type="password")
                if st.form_submit_button("Kayıt Ol", use_container_width=True):
                    if not ne.endswith("@forleai.com"): st.error("Şirket maili zorunludur.")
                    else:
                        with conn.session as s:
                            s.execute(text("INSERT INTO kullanicilar (email, sifre, isim) VALUES (:e, :p, :n)"), {"e":ne, "p":hash_pw(np), "n":ni})
                            s.commit()
                        st.success("Kayıt başarılı!")
    st.stop()

# --- 4. SIDEBAR VE SAYFALAMA ---
with st.sidebar:
    st.markdown(f"**Hoş Geldin, {st.session_state.user_name}**")
    st.markdown(f"<span class='role-badge'>{st.session_state.user_rol}</span>", unsafe_allow_html=True)
    page = st.radio("Menü", ["Ana Sayfa", "Parça Yönetimi", "Cihaz Yönetimi", "Bütçe & Harcamalar", "Proje & Görevler", "İnsan Kaynakları", "Audit Log"])
    if st.button("Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 5. ANA SAYFA VE MODÜLLER ---
if page == "Ana Sayfa":
    st.title("Kontrol Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Parça", len(conn.query("SELECT id FROM parcalar")))
    c2.metric("Toplam Cihaz", len(conn.query("SELECT id FROM cihazlar")))
    c3.metric("Açık Görev", len(conn.query("SELECT id FROM gorevler WHERE durum != 'Tamamlandı'")))
    h_toplam = conn.query("SELECT SUM(tutar) as t FROM harcamalar").iloc[0]['t'] or 0
    c4.metric("Toplam Bütçe", f"{h_toplam:,.0f} ₺")
    
    st.markdown("### Son Harcamalar")
    st.dataframe(conn.query("SELECT tarih, kategori, tutar, giren FROM harcamalar ORDER BY id DESC LIMIT 5"), use_container_width=True)

elif page == "Parça Yönetimi":
    st.title("Parça Yönetimi")
    with st.expander("Yeni Ekle"):
        with st.form("p"):
            et = st.text_input("Varlık Etiketi")
            mo = st.text_input("Model")
            dr = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda"])
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO parcalar (varlik_etiketi, model, durum, ekleyen) VALUES (:e, :m, :d, :u)"), {"e":et, "m":mo, "d":dr, "u":st.session_state.user_name})
                    s.commit()
                st.success("Eklendi")
                st.rerun()
    st.dataframe(conn.query("SELECT * FROM parcalar ORDER BY id DESC"), use_container_width=True)

elif page == "Bütçe & Harcamalar":
    st.title("Bütçe Takibi")
    with st.expander("Harcama Gir"):
        with st.form("h"):
            ta, ka, tu = st.date_input("Tarih"), st.selectbox("Kategori", ["Ar-Ge", "Ofis", "Seyahat"]), st.number_input("Tutar")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, giren) VALUES (:t, :k, :tu, :g)"), {"t":ta.strftime("%Y-%m-%d"), "k":ka, "tu":tu, "g":st.session_state.user_name})
                    s.commit()
                st.success("Harcama Kaydedildi")
                st.rerun()
    df_h = conn.query("SELECT * FROM harcamalar ORDER BY id DESC")
    st.dataframe(df_h, use_container_width=True)
    st.download_button("Excel Aktar", excel_export(df_h), "harcamalar.xlsx")

elif page == "Audit Log":
    st.title("İşlem Geçmişi")
    if st.session_state.user_rol == "Admin":
        st.dataframe(conn.query("SELECT created_at, kullanici, aksiyon, detay FROM audit_log ORDER BY id DESC"), use_container_width=True)
    else: st.warning("Yetkisiz erişim.")
