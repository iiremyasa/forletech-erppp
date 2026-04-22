import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import hashlib
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
    section[data-testid="stSidebar"] .stRadio label {
        padding: 8px 12px;
        border-radius: 6px;
        display: block;
    }
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stButton > button {
        background: #1a2332;
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #243447;
        box-shadow: 0 4px 12px rgba(26,35,50,0.3);
        transform: translateY(-1px);
    }
    .page-header {
        background: linear-gradient(135deg, #1a2332 0%, #2d4a6e 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .page-header h2 { color: white; margin: 0; font-size: 1.6rem; }
    .page-header p  { color: #a0b4c8; margin: 4px 0 0 0; font-size: 0.9rem; }
    .notif-banner {
        background: #fff8e1;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 0.9rem;
    }
    .notif-info    { background: #e8f4fd; border-color: #3b82f6; }
    .notif-basari  { background: #f0fdf4; border-color: #22c55e; }
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 600;
        background: rgba(59,130,246,0.15);
        color: #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────
DB = "forletech.db"

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
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL,
            isim TEXT NOT NULL,
            rol TEXT DEFAULT 'Kullanici',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS parcalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            varlik_etiketi TEXT,
            kayit_tarihi TEXT,
            model TEXT,
            durum TEXT,
            seri_no TEXT,
            durum_notu TEXT,
            yazilim_versiyonu TEXT,
            bagli_cihaz TEXT,
            ekleyen TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS cihazlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cihaz_adi TEXT,
            ip TEXT,
            model TEXT,
            takili_sensor_seri TEXT,
            anakart_seri TEXT,
            durum TEXT,
            seri_no TEXT,
            notlar TEXT,
            ekleyen TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS harcamalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            kategori TEXT,
            tutar REAL,
            fatura_no TEXT,
            aciklama TEXT,
            giren TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS gorevler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT,
            aciklama TEXT,
            atanan TEXT,
            durum TEXT DEFAULT 'Bekliyor',
            oncelik TEXT DEFAULT 'Orta',
            son_tarih TEXT,
            proje TEXT,
            olusturan TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS personel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT,
            email TEXT,
            pozisyon TEXT,
            departman TEXT,
            ise_baslama TEXT,
            telefon TEXT,
            notlar TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS izinler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT,
            izin_turu TEXT,
            baslangic TEXT,
            bitis TEXT,
            gun_sayisi REAL,
            durum TEXT DEFAULT 'Bekliyor',
            talep_eden TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS bildirimler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip TEXT,
            mesaj TEXT,
            tarih TEXT,
            okundu INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici TEXT,
            aksiyon TEXT,
            detay TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        """)

        # Varsayılan admin
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("""
            INSERT OR IGNORE INTO kullanicilar (email, sifre, isim, rol)
            VALUES (?, ?, ?, ?)
        """, ("admin@forleai.com", pw, "Sistem Yöneticisi", "Admin"))

        # Örnek bildirimler
        c.execute("SELECT COUNT(*) FROM bildirimler")
        if c.fetchone()[0] == 0:
            sample_notifs = [
                ("uyari",  "3 parçanın garanti süresi bu ay dolacak.",        "22-04-2025"),
                ("bilgi",  "Nisan ayı bütçe raporu hazırlanmayı bekliyor.",   "20-04-2025"),
                ("basari", "Sistem güncellemesi başarıyla tamamlandı.",        "18-04-2025"),
            ]
            c.executemany(
                "INSERT INTO bildirimler (tip, mesaj, tarih) VALUES (?,?,?)",
                sample_notifs
            )

def log_action(kullanici, aksiyon, detay=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (?,?,?)",
            (kullanici, aksiyon, detay)
        )

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

init_db()

# ─────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────
def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf

def page_header(title, desc):
    st.markdown(f"""
    <div class="page-header">
        <h2>{title}</h2>
        <p>{desc}</p>
    </div>""", unsafe_allow_html=True)

def load_df(table, cols=None):
    with get_conn() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY created_at DESC", conn)
    if cols:
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
    return df

# ─────────────────────────────────────────
# GİRİŞ EKRANI
# ─────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <div style='text-align:center;padding:60px 0 20px'>
        <div style='font-size:3rem'>🏢</div>
        <h1 style='color:#1a2332;font-size:2.2rem;margin:8px 0'>FORLE TECH</h1>
        <p style='color:#64748b'>Kurumsal ERP Portalı</p>
    </div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["Giriş Yap", "Yeni Hesap"])

        with tab1:
            with st.form("giris"):
                email = st.text_input("E-posta", placeholder="isim@forleai.com").strip().lower()
                pw    = st.text_input("Şifre", type="password").strip()
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    with get_conn() as conn:
                        row = conn.execute(
                            "SELECT * FROM kullanicilar WHERE email=? AND sifre=?",
                            (email, hash_pw(pw))
                        ).fetchone()
                    if row:
                        st.session_state.authenticated = True
                        st.session_state.user_name  = row["isim"]
                        st.session_state.user_email = row["email"]
                        st.session_state.user_rol   = row["rol"]
                        log_action(row["isim"], "Giriş", email)
                        st.rerun()
                    else:
                        st.error("Hatalı e-posta veya şifre.")

        with tab2:
            with st.form("kayit"):
                isim   = st.text_input("Ad Soyad").strip()
                email2 = st.text_input("E-posta (@forleai.com)").strip().lower()
                pw2    = st.text_input("Şifre", type="password").strip()
                pw2b   = st.text_input("Şifre Tekrar", type="password").strip()
                if st.form_submit_button("Kayıt Ol", use_container_width=True):
                    if not email2.endswith("@forleai.com"):
                        st.error("Sadece @forleai.com uzantısı kabul edilir.")
                    elif pw2 != pw2b:
                        st.error("Şifreler uyuşmuyor.")
                    elif len(pw2) < 4:
                        st.error("Şifre çok kısa.")
                    else:
                        try:
                            with get_conn() as conn:
                                conn.execute(
                                    "INSERT INTO kullanicilar (email,sifre,isim) VALUES (?,?,?)",
                                    (email2, hash_pw(pw2), isim)
                                )
                            st.success("Kayıt başarılı! Giriş yapabilirsin.")
                        except sqlite3.IntegrityError:
                            st.warning("Bu e-posta zaten kayıtlı.")
    st.stop()

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:16px 0 8px'>
        <div style='font-size:2rem'>🏢</div>
        <div style='font-weight:700;font-size:1.1rem;color:white'>FORLE TECH</div>
        <div style='font-size:0.75rem;color:#8a9bb0'>ERP Sistemi</div>
    </div>
    <div style='background:rgba(255,255,255,0.08);border-radius:10px;padding:12px;margin:8px 0 16px'>
        <div style='font-size:0.72rem;color:#8a9bb0'>Oturum Açık</div>
        <div style='font-weight:600;color:white'>{st.session_state.user_name}</div>
        <div style='font-size:0.72rem;color:#64a8d8'>{st.session_state.user_email}</div>
        <div style='margin-top:6px'><span class='role-badge'>{st.session_state.user_rol}</span></div>
    </div>""", unsafe_allow_html=True)

    page = st.radio("Menü", [
        "Ana Sayfa",
        "Parça Yönetimi",
        "Cihaz Yönetimi",
        "Bütçe & Harcamalar",
        "Proje & Görevler",
        "İnsan Kaynakları",
        "Bildirimler",
        "Audit Log",
    ], label_visibility="collapsed")

    st.markdown("---")
    notif_count = 0
    with get_conn() as conn:
        notif_count = conn.execute("SELECT COUNT(*) FROM bildirimler WHERE okundu=0").fetchone()[0]
    if notif_count:
        st.markdown(f"""
        <div style='background:rgba(245,158,11,0.15);border-radius:8px;padding:10px 12px;
                    border-left:3px solid #f59e0b;margin-bottom:12px'>
            <span style='color:#f59e0b;font-size:0.85rem'>{notif_count} okunmamış bildirim</span>
        </div>""", unsafe_allow_html=True)

    if st.button("Çıkış Yap", use_container_width=True):
        log_action(st.session_state.user_name, "Çıkış")
        st.session_state.authenticated = False
        st.rerun()

# ─────────────────────────────────────────
# ANA SAYFA
# ─────────────────────────────────────────
if page == "Ana Sayfa":
    page_header("Kontrol Paneli", "FORLE TECH ERP — Genel Bakış")

    with get_conn() as conn:
        n_parca   = conn.execute("SELECT COUNT(*) FROM parcalar").fetchone()[0]
        n_cihaz   = conn.execute("SELECT COUNT(*) FROM cihazlar").fetchone()[0]
        n_gorev   = conn.execute("SELECT COUNT(*) FROM gorevler WHERE durum != 'Tamamlandı'").fetchone()[0]
        n_personel= conn.execute("SELECT COUNT(*) FROM personel").fetchone()[0]
        toplam_h  = conn.execute("SELECT COALESCE(SUM(tutar),0) FROM harcamalar").fetchone()[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Parça", n_parca)
    c2.metric("Cihaz", n_cihaz)
    c3.metric("Açık Görev", n_gorev)
    c4.metric("Personel", n_personel)
    c5.metric("Toplam Harcama", f"{toplam_h:,.0f} ₺")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Kategori Bazlı Harcamalar")
        df_h = load_df("harcamalar", ["kategori", "tutar"])
        if not df_h.empty:
            chart = df_h.groupby("kategori")["tutar"].sum().reset_index()
            st.bar_chart(chart.set_index("kategori"), color="#2d4a6e")
        else:
            st.info("Henüz harcama yok.")

    with col_b:
        st.markdown("#### Parça Durum Dağılımı")
        df_p = load_df("parcalar", ["durum"])
        if not df_p.empty:
            durum = df_p["durum"].value_counts().reset_index()
            durum.columns = ["Durum", "Adet"]
            st.bar_chart(durum.set_index("Durum"), color="#2d4a6e")
        else:
            st.info("Henüz parça yok.")

    st.markdown("#### Son Eklenen Harcamalar")
    df_son = load_df("harcamalar", ["tarih", "kategori", "tutar", "fatura_no", "giren"])
    if not df_son.empty:
        st.dataframe(df_son.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("Henüz harcama yok.")

# ─────────────────────────────────────────
# PARÇA YÖNETİMİ
# ─────────────────────────────────────────
elif page == "Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık etiketi ve envanter takibi")

    with st.expander("Yeni Parça Ekle", expanded=False):
        with st.form("parca_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_etiket   = st.text_input("Varlık Etiketi")
                p_model    = st.text_input("Model")
                p_seri     = st.text_input("Seri No")
                p_yazilim  = st.text_input("Yazılım Versiyonu")
            with c2:
                p_tarih    = st.date_input("Kayıt Tarihi", datetime.date.today())
                p_durum    = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda", "Hurda"])
                p_bagli    = st.text_input("Bağlı Cihaz")
                p_not      = st.text_area("Durum Notu")
            if st.form_submit_button("Kaydet", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("""
                        INSERT INTO parcalar
                        (varlik_etiketi,kayit_tarihi,model,durum,seri_no,
                         durum_notu,yazilim_versiyonu,bagli_cihaz,ekleyen)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (p_etiket, p_tarih.strftime("%d-%m-%Y"), p_model,
                          p_durum, p_seri, p_not, p_yazilim, p_bagli,
                          st.session_state.user_name))
                log_action(st.session_state.user_name, "Parça Eklendi", p_etiket)
                st.success("Parça eklendi.")
                st.rerun()

    st.markdown("---")
    df = load_df("parcalar", ["id","varlik_etiketi","kayit_tarihi","model","durum",
                              "seri_no","durum_notu","yazilim_versiyonu","bagli_cihaz","ekleyen"])

    if not df.empty:
        col_ara, col_f = st.columns([2, 1])
        with col_ara:
            ara = st.text_input("Ara", placeholder="Etiket, model, seri no...")
        with col_f:
            df_filtre = st.selectbox("Durum Filtrele", ["Tümü","Aktif","Arızalı","Depoda","Hurda"])

        if ara:
            df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if df_filtre != "Tümü":
            df = df[df["durum"] == df_filtre]

        c1, c2, c3, c4 = st.columns(4)
        df_all = load_df("parcalar", ["durum"])
        c1.metric("Aktif",   len(df_all[df_all["durum"]=="Aktif"]))
        c2.metric("Arızalı", len(df_all[df_all["durum"]=="Arızalı"]))
        c3.metric("Depoda",  len(df_all[df_all["durum"]=="Depoda"]))
        c4.metric("Hurda",   len(df_all[df_all["durum"]=="Hurda"]))

        st.markdown("<br>", unsafe_allow_html=True)

        display_df = df.drop(columns=["id"], errors="ignore")
        display_df.columns = ["Varlık Etiketi","Kayıt Tarihi","Model","Durum","Seri No",
                               "Durum Notu","Yazılım Ver.","Bağlı Cihaz","Ekleyen"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Excel İndir", excel_export(display_df),
            "forletech_parca.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Silme
        if st.session_state.user_rol == "Admin":
            st.markdown("---")
            sil_id = st.number_input("Silmek için Parça ID", min_value=1, step=1)
            if st.button("Parçayı Sil"):
                with get_conn() as conn:
                    conn.execute("DELETE FROM parcalar WHERE id=?", (sil_id,))
                log_action(st.session_state.user_name, "Parça Silindi", f"ID:{sil_id}")
                st.success("Silindi.")
                st.rerun()
    else:
        st.info("Henüz parça eklenmemiş.")

# ─────────────────────────────────────────
# CİHAZ YÖNETİMİ
# ─────────────────────────────────────────
elif page == "Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Cihaz montaj ve varlık takibi")

    with st.expander("Yeni Cihaz Ekle", expanded=False):
        with st.form("cihaz_form"):
            c1, c2 = st.columns(2)
            with c1:
                d_adi    = st.text_input("Cihaz Adı")
                d_model  = st.text_input("Model")
                d_seri   = st.text_input("Seri No")
                d_ip     = st.text_input("IP Adresi")
            with c2:
                d_sensor = st.text_input("Takılı Sensör Seri No")
                d_anakart= st.text_input("Anakart Seri No")
                d_durum  = st.selectbox("Durum", ["Aktif","Testte","Bakımda","Depoda"])
                d_not    = st.text_area("Notlar")
            if st.form_submit_button("Kaydet", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("""
                        INSERT INTO cihazlar
                        (cihaz_adi,ip,model,takili_sensor_seri,anakart_seri,
                         durum,seri_no,notlar,ekleyen)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (d_adi, d_ip, d_model, d_sensor, d_anakart,
                          d_durum, d_seri, d_not, st.session_state.user_name))
                log_action(st.session_state.user_name, "Cihaz Eklendi", d_adi)
                st.success("Cihaz eklendi.")
                st.rerun()

    st.markdown("---")
    df = load_df("cihazlar", ["id","cihaz_adi","ip","model","takili_sensor_seri",
                              "anakart_seri","durum","seri_no","notlar","ekleyen"])

    if not df.empty:
        col_ara, col_f = st.columns([2, 1])
        with col_ara:
            ara = st.text_input("Ara", placeholder="Cihaz adı, IP, seri no...")
        with col_f:
            df_filtre = st.selectbox("Durum Filtrele", ["Tümü","Aktif","Testte","Bakımda","Depoda"])

        if ara:
            df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if df_filtre != "Tümü":
            df = df[df["durum"] == df_filtre]

        display_df = df.drop(columns=["id"], errors="ignore")
        display_df.columns = ["Cihaz Adı","IP","Model","Sensör Seri","Anakart Seri",
                               "Durum","Seri No","Notlar","Ekleyen"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Excel İndir", excel_export(display_df),
            "forletech_cihaz.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.session_state.user_rol == "Admin":
            st.markdown("---")
            sil_id = st.number_input("Silmek için Cihaz ID", min_value=1, step=1)
            if st.button("Cihazı Sil"):
                with get_conn() as conn:
                    conn.execute("DELETE FROM cihazlar WHERE id=?", (sil_id,))
                log_action(st.session_state.user_name, "Cihaz Silindi", f"ID:{sil_id}")
                st.success("Silindi.")
                st.rerun()
    else:
        st.info("Henüz cihaz eklenmemiş.")

# ─────────────────────────────────────────
# BÜTÇE & HARCAMALAR
# ─────────────────────────────────────────
elif page == "Bütçe & Harcamalar":
    page_header("Bütçe & Harcamalar", "Kurumsal harcama takibi")

    with st.expander("Yeni Harcama Ekle", expanded=False):
        with st.form("harcama_form"):
            h1, h2, h3 = st.columns(3)
            with h1:
                h_tarih = st.date_input("Tarih", datetime.date.today())
                h_kat   = st.selectbox("Kategori", ["Ar-Ge Alımı","Ofis Gideri","Seyahat","Maaş","Diğer"])
            with h2:
                h_tutar  = st.number_input("Tutar (₺)", min_value=0.0, step=100.0)
                h_fatura = st.text_input("Fatura / Fiş No")
            with h3:
                h_acik = st.text_area("Açıklama")
            if st.form_submit_button("Kaydet", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("""
                        INSERT INTO harcamalar (tarih,kategori,tutar,fatura_no,aciklama,giren)
                        VALUES (?,?,?,?,?,?)
                    """, (h_tarih.strftime("%d-%m-%Y"), h_kat, h_tutar,
                          h_fatura, h_acik, st.session_state.user_name))
                log_action(st.session_state.user_name, "Harcama Eklendi",
                           f"{h_kat} - {h_tutar}₺")
                st.success("Harcama kaydedildi.")
                st.rerun()

    st.markdown("---")
    df = load_df("harcamalar", ["tarih","kategori","tutar","fatura_no","aciklama","giren"])

    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam", f"{df['tutar'].sum():,.2f} ₺")
        c2.metric("Ortalama", f"{df['tutar'].mean():,.2f} ₺")
        c3.metric("Kayıt", len(df))

        st.markdown("<br>", unsafe_allow_html=True)
        col_ara, col_f = st.columns([2, 1])
        with col_ara:
            ara = st.text_input("Ara", placeholder="Açıklama, kategori, fatura no...")
        with col_f:
            kat_f = st.selectbox("Kategori", ["Tümü","Ar-Ge Alımı","Ofis Gideri","Seyahat","Maaş","Diğer"])

        if ara:
            df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if kat_f != "Tümü":
            df = df[df["kategori"] == kat_f]

        df.columns = ["Tarih","Kategori","Tutar (₺)","Fatura No","Açıklama","Giren"]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Excel İndir", excel_export(df),
            "forletech_harcamalar.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz harcama yok.")

# ─────────────────────────────────────────
# PROJE & GÖREVLER
# ─────────────────────────────────────────
elif page == "Proje & Görevler":
    page_header("Proje & Görev Takibi", "Görev atama, önceliklendirme ve durum takibi")

    with st.expander("Yeni Görev Ekle", expanded=False):
        with st.form("gorev_form"):
            g1, g2 = st.columns(2)
            with g1:
                g_baslik  = st.text_input("Görev Başlığı")
                g_proje   = st.text_input("Proje Adı")
                g_atanan  = st.text_input("Atanan Kişi")
            with g2:
                g_oncelik = st.selectbox("Öncelik", ["Düşük","Orta","Yüksek","Kritik"])
                g_durum   = st.selectbox("Durum", ["Bekliyor","Devam Ediyor","İncelemede","Tamamlandı"])
                g_tarih   = st.date_input("Son Tarih", datetime.date.today())
            g_acik = st.text_area("Açıklama")
            if st.form_submit_button("Görev Ekle", use_container_width=True):
                with get_conn() as conn:
                    conn.execute("""
                        INSERT INTO gorevler
                        (baslik,aciklama,atanan,durum,oncelik,son_tarih,proje,olusturan)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (g_baslik, g_acik, g_atanan, g_durum, g_oncelik,
                          g_tarih.strftime("%d-%m-%Y"), g_proje,
                          st.session_state.user_name))
                log_action(st.session_state.user_name, "Görev Eklendi", g_baslik)
                st.success("Görev eklendi.")
                st.rerun()

    st.markdown("---")

    # Kanban
    df = load_df("gorevler", ["id","baslik","proje","atanan","oncelik","durum","son_tarih","olusturan"])
    if not df.empty:
        st.markdown("#### Kanban Görünümü")
        kolonlar = ["Bekliyor","Devam Ediyor","İncelemede","Tamamlandı"]
        k_cols = st.columns(4)
        renk = {"Düşük":"#22c55e","Orta":"#f59e0b","Yüksek":"#ef4444","Kritik":"#7c3aed"}

        for i, durum in enumerate(kolonlar):
            with k_cols[i]:
                st.markdown(f"**{durum}**")
                gorevler = df[df["durum"] == durum]
                if gorevler.empty:
                    st.markdown("<div style='color:#94a3b8;font-size:0.8rem'>Görev yok</div>", unsafe_allow_html=True)
                for _, g in gorevler.iterrows():
                    r = renk.get(g["oncelik"], "#64748b")
                    st.markdown(f"""
                    <div style='background:white;border-radius:10px;padding:12px;
                                margin-bottom:8px;border-left:4px solid {r};
                                box-shadow:0 1px 4px rgba(0,0,0,0.08)'>
                        <div style='font-weight:600;font-size:0.88rem;color:#1e293b'>{g["baslik"]}</div>
                        <div style='font-size:0.75rem;color:#64748b;margin-top:4px'>
                            👤 {g["atanan"] or "—"} &nbsp;|&nbsp; 📅 {g["son_tarih"] or "—"}
                        </div>
                        <div style='font-size:0.72rem;color:#94a3b8;margin-top:2px'>
                            {g["proje"] or ""}
                        </div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Tüm Görevler")
        display = df.drop(columns=["id"], errors="ignore")
        display.columns = ["Başlık","Proje","Atanan","Öncelik","Durum","Son Tarih","Oluşturan"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Excel İndir", excel_export(display),
            "forletech_gorevler.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz görev eklenmemiş.")

# ─────────────────────────────────────────
# İNSAN KAYNAKLARI
# ─────────────────────────────────────────
elif page == "İnsan Kaynakları":
    page_header("İnsan Kaynakları", "Personel yönetimi ve izin takibi")

    ik_tab1, ik_tab2 = st.tabs(["Personel", "İzin Yönetimi"])

    with ik_tab1:
        with st.expander("Yeni Personel Ekle", expanded=False):
            with st.form("personel_form"):
                p1, p2 = st.columns(2)
                with p1:
                    per_isim  = st.text_input("Ad Soyad")
                    per_email = st.text_input("E-posta")
                    per_tel   = st.text_input("Telefon")
                with p2:
                    per_poz   = st.text_input("Pozisyon")
                    per_dep   = st.selectbox("Departman", ["Yazılım","Donanım","Ar-Ge","Yönetim","Satış","Diğer"])
                    per_basl  = st.date_input("İşe Başlama", datetime.date.today())
                per_not = st.text_area("Notlar")
                if st.form_submit_button("Kaydet", use_container_width=True):
                    with get_conn() as conn:
                        conn.execute("""
                            INSERT INTO personel
                            (isim,email,pozisyon,departman,ise_baslama,telefon,notlar)
                            VALUES (?,?,?,?,?,?,?)
                        """, (per_isim, per_email, per_poz, per_dep,
                              per_basl.strftime("%d-%m-%Y"), per_tel, per_not))
                    log_action(st.session_state.user_name, "Personel Eklendi", per_isim)
                    st.success("Personel eklendi.")
                    st.rerun()

        df = load_df("personel", ["isim","email","pozisyon","departman","ise_baslama","telefon","notlar"])
        if not df.empty:
            df.columns = ["İsim","E-posta","Pozisyon","Departman","İşe Başlama","Telefon","Notlar"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Excel İndir", excel_export(df),
                "forletech_personel.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Henüz personel eklenmemiş.")

    with ik_tab2:
        with st.expander("Yeni İzin Talebi", expanded=False):
            with st.form("izin_form"):
                i1, i2 = st.columns(2)
                with i1:
                    iz_per  = st.text_input("Personel Adı")
                    iz_tur  = st.selectbox("İzin Türü", ["Yıllık","Mazeret","Hastalık","Ücretsiz"])
                with i2:
                    iz_bas  = st.date_input("Başlangıç", datetime.date.today())
                    iz_bit  = st.date_input("Bitiş", datetime.date.today())
                if st.form_submit_button("Talep Oluştur", use_container_width=True):
                    gun = (iz_bit - iz_bas).days + 1
                    if gun <= 0:
                        st.error("Bitiş tarihi başlangıçtan önce olamaz.")
                    else:
                        with get_conn() as conn:
                            conn.execute("""
                                INSERT INTO izinler
                                (personel_adi,izin_turu,baslangic,bitis,gun_sayisi,talep_eden)
                                VALUES (?,?,?,?,?,?)
                            """, (iz_per, iz_tur,
                                  iz_bas.strftime("%d-%m-%Y"),
                                  iz_bit.strftime("%d-%m-%Y"),
                                  gun, st.session_state.user_name))
                        log_action(st.session_state.user_name, "İzin Talebi", f"{iz_per} - {gun} gün")
                        st.success(f"{gun} günlük izin talebi oluşturuldu.")
                        st.rerun()

        df = load_df("izinler", ["id","personel_adi","izin_turu","baslangic","bitis","gun_sayisi","durum","talep_eden"])
        if not df.empty:
            if st.session_state.user_rol == "Admin":
                st.markdown("**Onay Bekleyen Talepler**")
                bekleyenler = df[df["durum"] == "Bekliyor"]
                for _, row in bekleyenler.iterrows():
                    col_info, col_onay, col_red = st.columns([4, 1, 1])
                    with col_info:
                        st.markdown(f"**{row['personel_adi']}** — {row['izin_turu']} — {row['gun_sayisi']} gün ({row['baslangic']} → {row['bitis']})")
                    with col_onay:
                        if st.button("Onayla", key=f"on_{row['id']}"):
                            with get_conn() as conn:
                                conn.execute("UPDATE izinler SET durum='Onaylandı' WHERE id=?", (row["id"],))
                            st.rerun()
                    with col_red:
                        if st.button("Reddet", key=f"red_{row['id']}"):
                            with get_conn() as conn:
                                conn.execute("UPDATE izinler SET durum='Reddedildi' WHERE id=?", (row["id"],))
                            st.rerun()
                st.markdown("---")

            display = df.drop(columns=["id"], errors="ignore")
            display.columns = ["Personel","İzin Türü","Başlangıç","Bitiş","Gün","Durum","Talep Eden"]
            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz izin talebi yok.")

# ─────────────────────────────────────────
# BİLDİRİMLER
# ─────────────────────────────────────────
elif page == "Bildirimler":
    page_header("Bildirimler", "Sistem uyarıları ve güncellemeler")

    df = load_df("bildirimler")
    if not df.empty:
        for _, b in df.iterrows():
            tip_class = {"uyari": "notif-banner", "bilgi": "notif-banner notif-info",
                         "basari": "notif-banner notif-basari"}.get(b["tip"], "notif-banner")
            ikon = {"uyari": "⚠️", "bilgi": "ℹ️", "basari": "✅"}.get(b["tip"], "📌")
            col_msg, col_del = st.columns([8, 1])
            with col_msg:
                st.markdown(f"""
                <div class='{tip_class}'>
                    {ikon} <strong>{b['tarih']}</strong> — {b['mesaj']}
                </div>""", unsafe_allow_html=True)
            with col_del:
                if st.button("Sil", key=f"del_{b['id']}"):
                    with get_conn() as conn:
                        conn.execute("DELETE FROM bildirimler WHERE id=?", (b["id"],))
                    st.rerun()

        if st.button("Tümünü Temizle"):
            with get_conn() as conn:
                conn.execute("DELETE FROM bildirimler")
            st.rerun()
    else:
        st.success("Tüm bildirimler okundu!")

    st.markdown("---")
    st.markdown("#### Yeni Bildirim")
    with st.form("bildirim_form"):
        b_tip  = st.selectbox("Tip", ["bilgi","uyari","basari"])
        b_msg  = st.text_input("Mesaj")
        if st.form_submit_button("Ekle"):
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO bildirimler (tip,mesaj,tarih) VALUES (?,?,?)",
                    (b_tip, b_msg, datetime.date.today().strftime("%d-%m-%Y"))
                )
            st.success("Bildirim eklendi.")
            st.rerun()

# ─────────────────────────────────────────
# AUDİT LOG
# ─────────────────────────────────────────
elif page == "Audit Log":
    page_header("Audit Log", "Tüm sistem işlem geçmişi")

    if st.session_state.user_rol != "Admin":
        st.warning("Bu sayfaya sadece Admin erişebilir.")
        st.stop()

    df = load_df("audit_log")
    if not df.empty:
        ara = st.text_input("Ara", placeholder="Kullanıcı, aksiyon veya detay...")
        if ara:
            df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        display = df[["created_at","kullanici","aksiyon","detay"]]
        display.columns = ["Tarih/Saat","Kullanıcı","Aksiyon","Detay"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Excel İndir", excel_export(display),
            "forletech_auditlog.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz log kaydı yok.")
