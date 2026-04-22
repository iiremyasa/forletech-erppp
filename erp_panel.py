import streamlit as st
import pandas as pd
import datetime
import hashlib
import io
import random
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import text
import plotly.express as px

# --- 0. SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="Forle/AI | Kurumsal Portal", page_icon=":material/domain:", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f4f7f6; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #152238 0%, #1A365D 100%); border-right: 2px solid #38B2AC; }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }
    .stButton > button { background: #38B2AC; color: #ffffff !important; border-radius: 6px; transition: all 0.3s ease; border: none; font-weight: 600; box-shadow: 0 2px 4px rgba(56, 178, 172, 0.3); }
    .stButton > button:hover { background: #2C7A7B; box-shadow: 0 4px 8px rgba(44, 122, 123, 0.4); transform: translateY(-2px); }
    .page-header { background: linear-gradient(135deg, #152238 0%, #2B6CB0 100%); color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 6px solid #38B2AC; }
    .page-header h1 { color: white; font-size: 1.8rem; margin: 0; font-weight: 700; }
    .role-badge { padding: 4px 12px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: rgba(56,178,172,0.15); border: 1px solid #38B2AC; color: #38B2AC !important; }
    div[data-testid="metric-container"] { background-color: white; border-top: 4px solid #38B2AC; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# --- E-POSTA GÖNDERİM MOTORU ---
def send_email_notification(to_email, subject, body):
    try:
        if "smtp" in st.secrets:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = st.secrets["smtp"]["email"]
            msg['To'] = to_email
            with smtplib.SMTP_SSL(st.secrets["smtp"]["server"], st.secrets["smtp"]["port"]) as server:
                server.login(st.secrets["smtp"]["email"], st.secrets["smtp"]["password"])
                server.send_message(msg)
        else:
            st.toast(f"📧 E-Posta Simülasyonu: {to_email} adresine mail gönderildi.", icon="🚀")
    except Exception as e:
        st.toast(f"E-posta gönderilemedi: {e}")

# --- 1. VERİTABANI BAĞLANTISI VE YAPILANDIRMASI ---
try:
    conn = st.connection("postgresql", type="sql")
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', dogrulandi INTEGER DEFAULT 1, kod TEXT);
            CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar FLOAT, fatura_no TEXT, aciklama TEXT, giren TEXT, belge BYTEA, dosya_adi TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS harcama_talepleri (id SERIAL PRIMARY KEY, personel TEXT, tarih TEXT, tutar FLOAT, aciklama TEXT, belge BYTEA, dosya_adi TEXT, durum TEXT DEFAULT 'Bekliyor', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS nir_projesi (id SERIAL PRIMARY KEY, demo_tarihi TEXT, test_sonucu TEXT, sponsorluk_durumu TEXT, cihaz_versiyonu TEXT, notlar TEXT, ekleyen TEXT, belge BYTEA, dosya_adi TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS izinler (id SERIAL PRIMARY KEY, personel_adi TEXT, izin_turu TEXT, baslangic TEXT, bitis TEXT, gun_sayisi FLOAT, durum TEXT DEFAULT 'Bekliyor', talep_eden TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, okundu INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """))
        
        onarımlar = [
            "ALTER TABLE harcamalar ADD COLUMN IF NOT EXISTS belge BYTEA;",
            "ALTER TABLE harcamalar ADD COLUMN IF NOT EXISTS dosya_adi TEXT;",
            "ALTER TABLE nir_projesi ADD COLUMN IF NOT EXISTS belge BYTEA;",
            "ALTER TABLE nir_projesi ADD COLUMN IF NOT EXISTS dosya_adi TEXT;",
        ]
        for onar in onarımlar:
            try: s.execute(text(onar))
            except: pass

        pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, rol, dogrulandi) VALUES ('admin@forleai.com', :p, 'Sistem Yöneticisi', 'Admin', 1) ON CONFLICT DO NOTHING"), {"p": pw})
        s.commit()
except Exception as e:
    st.error(f"Veritabanı Hatası: {e}")

# --- YARDIMCI FONKSİYONLAR ---
def log_action(u, a, d=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici, aksiyon, detay) VALUES (:u, :a, :d)"), {"u": u, "a": a, "d": d})
        s.commit()

def sil_kayit(tablo, kayit_id):
    try:
        with conn.session as s:
            s.execute(text(f"DELETE FROM {tablo} WHERE id = :id"), {"id": kayit_id})
            s.commit()
        log_action(st.session_state.user_name, f"{tablo} tablosundan kayıt silindi", f"ID: {kayit_id}")
        return True
    except Exception as e:
        return False

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False)
    buf.seek(0)
    return buf

# --- 2. GİRİŞ VE DOĞRULAMA EKRANI ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "verifying_email" not in st.session_state: st.session_state.verifying_email = None

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding-top:40px;color:#152238;'><h1 style='font-size:3.5rem;font-weight:800;'>Forle<span style='color:#38B2AC;'>/AI</span></h1><p>Kurumsal Yönetim Sistemi</p></div>", unsafe_allow_html=True)
    
    if st.session_state.verifying_email:
        _, col, _ = st.columns([1, 1, 1])
        with col:
            st.info(f"**{st.session_state.verifying_email}** adresine 6 haneli bir kod gönderildi.")
            with st.form("verify"):
                k = st.text_input("Doğrulama Kodu", max_chars=6)
                if st.form_submit_button("Doğrula ve Giriş Yap"):
                    res = conn.query("SELECT * FROM kullanicilar WHERE email=:e AND kod=:k", params={"e":st.session_state.verifying_email, "k":k}, ttl=0)
                    if not res.empty:
                        with conn.session as s:
                            s.execute(text("UPDATE kullanicilar SET dogrulandi=1, kod=NULL WHERE email=:e"), {"e":st.session_state.verifying_email})
                            s.commit()
                        st.success("E-posta doğrulandı! Giriş yapabilirsiniz.")
                        st.session_state.verifying_email = None
                        st.rerun()
                    else: st.error("Hatalı kod.")
            if st.button("İptal Et"): 
                st.session_state.verifying_email = None
                st.rerun()
        st.stop()

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        t1, t2 = st.tabs(["Sisteme Giriş", "Personel Kaydı"])
        with t1:
            with st.form("l"):
                em = st.text_input("Kurumsal E-posta").strip().lower()
                ps = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    res = conn.query("SELECT * FROM kullanicilar WHERE email=:e AND sifre=:p", params={"e":em, "p":hash_pw(ps)}, ttl=0)
                    if not res.empty:
                        if res.iloc[0]['dogrulandi'] == 0:
                            st.warning("Hesabınız doğrulanmamış. Lütfen e-postanıza gelen kodu girin.")
                        else:
                            st.session_state.update({"authenticated": True, "user_name": res.iloc[0]['isim'], "user_email": res.iloc[0]['email'], "user_rol": res.iloc[0]['rol']})
                            log_action(st.session_state.user_name, "Oturum Açıldı")
                            st.rerun()
                    else: st.error("Hatalı kimlik bilgileri.")
        with t2:
            with st.form("k"):
                ni = st.text_input("Ad Soyad")
                ne = st.text_input("E-posta (@forleai.com)")
                np = st.text_input("Şifre", type="password")
                if st.form_submit_button("Hesap Oluştur", use_container_width=True):
                    if not ne.endswith("@forleai.com"): st.error("Yalnızca şirket uzantılı adresler kabul edilmektedir.")
                    else:
                        dogrulama_kodu = str(random.randint(100000, 999999))
                        try:
                            with conn.session as s:
                                s.execute(text("INSERT INTO kullanicilar (email, sifre, isim, dogrulandi, kod) VALUES (:e, :p, :n, 0, :k)"), {"e":ne, "p":hash_pw(np), "n":ni, "k":dogrulama_kodu})
                                s.commit()
                            send_email_notification(ne, "Forle/AI Doğrulama Kodu", f"Sisteme kayıt için doğrulama kodunuz: {dogrulama_kodu}")
                            st.session_state.verifying_email = ne
                            st.rerun()
                        except Exception as e: st.error("Bu e-posta zaten kayıtlı.")
    st.stop()

# --- 3. SIDEBAR (ROL BAZLI MENÜ) ---
with st.sidebar:
    st.markdown(f"<div style='margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin:0;font-size:1.1rem;color:white;'>{st.session_state.user_name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<span class='role-badge'>{st.session_state.user_rol}</span>", unsafe_allow_html=True)
    st.markdown(f"</div>", unsafe_allow_html=True)
    
    admin_yonetici_menu = [
        ":material/dashboard: Dashboard", ":material/biotech: NIR Ar-Ge Modülü", 
        ":material/precision_manufacturing: Parça Yönetimi", ":material/memory: Cihaz Yönetimi", 
        ":material/account_balance: Finans & Bütçe", ":material/receipt_long: Masraf Onay Paneli",
        ":material/assignment: Proje & Görevler", ":material/groups: İnsan Kaynakları", 
        ":material/admin_panel_settings: Sistem Logları"
    ]
    
    kullanici_menu = [
        ":material/dashboard: Dashboard", ":material/biotech: NIR Ar-Ge Modülü", 
        ":material/precision_manufacturing: Parça Yönetimi", ":material/memory: Cihaz Yönetimi",
        ":material/request_quote: Harcama Taleplerim"
    ]

    menu_options = admin_yonetici_menu if st.session_state.user_rol in ["Admin", "Yönetici"] else kullanici_menu
    page = st.radio("MENÜ", menu_options)
    
    st.markdown("---")
    if st.button(":material/logout: Oturumu Kapat", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 4. MODÜLLER ---

if page == ":material/dashboard: Dashboard":
    st.markdown("<div class='page-header'><h1>Dashboard 2.0 (Analitik)</h1></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Envanterdeki Parça", len(conn.query("SELECT id FROM parcalar", ttl=0)))
    c2.metric("Kayıtlı Cihaz", len(conn.query("SELECT id FROM cihazlar", ttl=0)))
    c3.metric("Açık Görevler", len(conn.query("SELECT id FROM gorevler WHERE durum != 'Tamamlandı'", ttl=0)))
    h_toplam = conn.query("SELECT SUM(tutar) as t FROM harcamalar", ttl=0).iloc[0]['t'] or 0
    c4.metric("Şirket Toplam Çıktı", f"{h_toplam:,.2f} TL")

    st.markdown("---")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### Harcama Dağılımı")
        df_h_grafik = conn.query("SELECT kategori, tutar FROM harcamalar", ttl=0)
        if not df_h_grafik.empty:
            fig1 = px.pie(df_h_grafik, values='tutar', names='kategori', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig1, use_container_width=True)
        else: st.info("Yeterli harcama verisi yok.")
    
    with g2:
        st.markdown("### Proje/Görev Durumları")
        df_g_grafik = conn.query("SELECT durum, COUNT(id) as sayi FROM gorevler GROUP BY durum", ttl=0)
        if not df_g_grafik.empty:
            fig2 = px.bar(df_g_grafik, x='durum', y='sayi', color='durum', color_discrete_sequence=px.colors.sequential.Tealgrn)
            st.plotly_chart(fig2, use_container_width=True)
        else: st.info("Yeterli görev verisi yok.")

    st.markdown("---")
    # BİLDİRİMLER (KONTROL PANELİNİN EN ALTINDA)
    if st.session_state.user_rol in ["Admin", "Yönetici"]:
        st.markdown("### 🔔 Sistem Bildirimleri")
        bildirimler = conn.query("SELECT id, mesaj, created_at FROM bildirimler WHERE okundu = 0 ORDER BY id DESC", ttl=0)
        if not bildirimler.empty:
            for idx, row in bildirimler.iterrows():
                b_col1, b_col2 = st.columns([5, 1])
                b_col1.info(f"**{row['created_at'].strftime('%d-%m-%Y %H:%M')}** | {row['mesaj']}")
                if b_col2.button("Okundu İşaretle", key=f"okundu_{row['id']}", use_container_width=True):
                    with conn.session as s:
                        s.execute(text("UPDATE bildirimler SET okundu = 1 WHERE id = :id"), {"id": row['id']})
                        s.commit()
                    st.rerun()
        else:
            st.success("Tebrikler! Okunmamış yeni bildirim bulunmuyor.")

elif page == ":material/biotech: NIR Ar-Ge Modülü":
    st.markdown("<div class='page-header'><h1>NIR Projesi Ar-Ge Takibi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Test / Demo Kaydı"):
        with st.form("nir_form"):
            n1, n2 = st.columns(2)
            with n1:
                nt = st.date_input("Demo Tarihi")
                nv = st.text_input("Cihaz Versiyonu (Örn: v1.2)")
            with n2:
                ns = st.selectbox("Sponsorluk Durumu", ["Görüşülüyor", "Protokol İmzalandı", "Beklemede", "Reddedildi"])
                nr = st.text_input("Test Sonucu Özeti")
            nn = st.text_area("Teknik Notlar")
            belge = st.file_uploader("Test Raporu / Fotoğraf Ekle (Opsiyonel)", type=["pdf", "png", "jpg"])
            
            if st.form_submit_button("Ar-Ge Kaydını İşle"):
                file_bytes = belge.read() if belge else None
                file_name = belge.name if belge else None
                with conn.session as s:
                    s.execute(text("INSERT INTO nir_projesi (demo_tarihi, test_sonucu, sponsorluk_durumu, cihaz_versiyonu, notlar, belge, dosya_adi, ekleyen) VALUES (:t,:r,:s,:v,:n,:b,:dn,:u)"),
                              {"t":nt.strftime("%d-%m-%Y"), "r":nr, "s":ns, "v":nv, "n":nn, "b":file_bytes, "dn":file_name, "u":st.session_state.user_name})
                    s.commit()
                st.success("Veri ve belgeler sisteme işlendi.")
                st.rerun()
    
    df_nir = conn.query("SELECT id, demo_tarihi, cihaz_versiyonu, sponsorluk_durumu, test_sonucu, notlar, dosya_adi, ekleyen FROM nir_projesi ORDER BY id DESC", ttl=0)
    df_nir_export = df_nir.drop(columns=["dosya_adi"])
    df_nir_export.columns = ["Kayıt ID", "Tarih", "Versiyon", "Sponsorluk Durumu", "Sonuç", "Notlar", "Sorumlu"]
    st.dataframe(df_nir, use_container_width=True)
    st.download_button(":material/download: Raporu Excel İndir", excel_export(df_nir_export), "ForleAI_NIR.xlsx")
    
    with st.expander(":material/delete: Kayıt Sil"):
        sil_id = st.number_input("Silinecek Kayıt ID:", min_value=0, step=1, key="s_n")
        if st.button("Sil") and sil_id > 0:
            if sil_kayit("nir_projesi", sil_id): st.rerun()

elif page == ":material/precision_manufacturing: Parça Yönetimi":
    st.markdown("<div class='page-header'><h1>Envanter: Parça Yönetimi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Parça Girişi"):
        with st.form("p_form"):
            c1, c2 = st.columns(2)
            with c1:
                ve = st.text_input("Varlık Etiketi")
                mo = st.text_input("Model")
                sn = st.text_input("Seri No")
                yv = st.text_input("Yazılım Versiyonu")
            with c2:
                kt = st.date_input("Kayıt Tarihi")
                du = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda"])
                bc = st.text_input("Bağlı Cihaz")
                dn = st.text_area("Durum Notu")
            if st.form_submit_button("Envantere Ekle"):
                with conn.session as s:
                    s.execute(text("INSERT INTO parcalar (varlik_etiketi, kayit_tarihi, model, durum, seri_no, durum_notu, yazilim_versiyonu, bagli_cihaz, ekleyen) VALUES (:ve,:kt,:mo,:du,:sn,:dn,:yv,:bc,:u)"),
                              {"ve":ve, "kt":kt.strftime("%d-%m-%Y"), "mo":mo, "du":du, "sn":sn, "dn":dn, "yv":yv, "bc":bc, "u":st.session_state.user_name})
                    s.commit()
                st.success("Kayıt başarılı.")
                st.rerun()
                
    df_p = conn.query("SELECT id, varlik_etiketi, kayit_tarihi, model, durum, seri_no, durum_notu, yazilim_versiyonu, bagli_cihaz FROM parcalar ORDER BY id DESC", ttl=0)
    df_p_export = df_p.copy()
    df_p_export.columns = ["ID", "Etiket", "Kayıt", "Model", "Durum", "Seri No", "Not", "Yazılım", "Cihaz"]
    st.dataframe(df_p, use_container_width=True)
    st.download_button(":material/download: Listeyi İndir", excel_export(df_p_export), "ForleAI_Parcalar.xlsx")
    
    with st.expander(":material/delete: Kayıt Sil"):
        sil_id = st.number_input("Silinecek ID:", min_value=0, step=1, key="s_p")
        if st.button("Sil", key="b_p") and sil_id > 0:
            if sil_kayit("parcalar", sil_id): st.rerun()

elif page == ":material/memory: Cihaz Yönetimi":
    st.markdown("<div class='page-header'><h1>Donanım: Cihaz Yönetimi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Cihaz Tanımla"):
        with st.form("cihaz_form"):
            c1, c2 = st.columns(2)
            with c1:
                d_adi = st.text_input("Cihaz Adı")
                d_model = st.text_input("Model")
                d_seri = st.text_input("Seri No")
                d_ip = st.text_input("IP Adresi")
            with c2:
                d_sensor = st.text_input("Takılı Sensör Seri No")
                d_anakart = st.text_input("Anakart Seri No")
                d_durum = st.selectbox("Durum", ["Aktif","Testte","Bakımda","Depoda"])
                d_not = st.text_area("Donanım Notları")
            if st.form_submit_button("Cihazı Sisteme Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO cihazlar (cihaz_adi, ip, model, takili_sensor_seri, anakart_seri, durum, seri_no, notlar, ekleyen) VALUES (:ca, :ip, :mo, :ts, :as, :du, :sn, :no, :ek)"), 
                              {"ca":d_adi, "ip":d_ip, "mo":d_model, "ts":d_sensor, "as":d_anakart, "du":d_durum, "sn":d_seri, "no":d_not, "ek":st.session_state.user_name})
                    s.commit()
                st.success("Cihaz başarıyla tanımlandı.")
                st.rerun()
                
    df_c = conn.query("SELECT id, cihaz_adi, ip, model, takili_sensor_seri, anakart_seri, durum, seri_no, notlar FROM cihazlar ORDER BY id DESC", ttl=0)
    df_c_export = df_c.copy()
    df_c_export.columns = ["ID", "Cihaz", "IP", "Model", "Sensör", "Anakart", "Durum", "Seri No", "Notlar"]
    st.dataframe(df_c, use_container_width=True)
    st.download_button(":material/download: Excel İndir", excel_export(df_c_export), "ForleAI_Cihazlar.xlsx")

    with st.expander(":material/delete: Kayıt Sil"):
        sil_id = st.number_input("Silinecek ID:", min_value=0, step=1, key="s_c")
        if st.button("Sil", key="b_c") and sil_id > 0:
            if sil_kayit("cihazlar", sil_id): st.rerun()

elif page == ":material/account_balance: Finans & Bütçe":
    st.markdown("<div class='page-header'><h1>Muhasebe: Kurumsal Harcamalar</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Fatura / Fiş İşle"):
        with st.form("h_form"):
            ta, ka, tu = st.date_input("Kayıt Tarihi"), st.selectbox("Gider Kalemi", ["Ar-Ge", "Ofis", "Seyahat", "Maaş", "Vergi", "İSG", "Mutfak", "Diğer"]), st.number_input("Tutar (TL)")
            fn = st.text_input("Belge/Fiş No")
            ac = st.text_area("İşlem Açıklaması")
            belge = st.file_uploader("Fatura / Dekont Yükle", type=["pdf", "png", "jpg"])
            if st.form_submit_button("Muhasebeye İşle"):
                file_bytes = belge.read() if belge else None
                file_name = belge.name if belge else None
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, fatura_no, aciklama, belge, dosya_adi, giren) VALUES (:t, :k, :tu, :f, :a, :b, :dn, :g)"), 
                              {"t":ta.strftime("%d-%m-%Y"), "k":ka, "tu":tu, "f":fn, "a":ac, "b":file_bytes, "dn":file_name, "g":st.session_state.user_name})
                    s.commit()
                st.success("Gider işlendi.")
                st.rerun()
                
    df_h = conn.query("SELECT id, tarih, kategori, tutar, fatura_no, aciklama, dosya_adi, giren FROM harcamalar ORDER BY id DESC", ttl=0)
    df_h_export = df_h.drop(columns=["dosya_adi"])
    df_h_export.columns = ["ID", "Tarih", "Kategori", "Tutar", "Belge No", "Açıklama", "İşleyen"]
    st.dataframe(df_h, use_container_width=True)
    st.download_button(":material/download: Raporu İndir", excel_export(df_h_export), "ForleAI_Finans.xlsx")

    with st.expander(":material/delete: Kayıt Sil"):
        sil_id = st.number_input("Silinecek ID:", min_value=0, step=1, key="s_f")
        if st.button("Sil", key="b_f") and sil_id > 0:
            if sil_kayit("harcamalar", sil_id): st.rerun()

elif page == ":material/request_quote: Harcama Taleplerim":
    st.markdown("<div class='page-header'><h1>Çalışan Masraf Beyanı</h1></div>", unsafe_allow_html=True)
    st.info("Kendi cebinizden yaptığınız kurumsal harcamaları buradan yönetime iletebilirsiniz.")
    with st.form("talep_form"):
        t_tar = st.date_input("Harcama Tarihi")
        t_tut = st.number_input("Tutar (TL)", min_value=1.0)
        t_ack = st.text_area("Harcama Açıklaması (Taksi, Yemek vb.)")
        t_belge = st.file_uploader("Fiş / Fatura Fotoğrafı (Zorunlu)", type=["png", "jpg", "pdf"])
        if st.form_submit_button("Onaya Gönder"):
            if not t_belge: st.error("Lütfen harcamanın fişini/belgesini yükleyin.")
            else:
                fb = t_belge.read()
                fn = t_belge.name
                with conn.session as s:
                    s.execute(text("INSERT INTO harcama_talepleri (personel, tarih, tutar, aciklama, belge, dosya_adi) VALUES (:p, :t, :tu, :a, :b, :dn)"),
                              {"p":st.session_state.user_name, "t":t_tar.strftime("%d-%m-%Y"), "tu":t_tut, "a":t_ack, "b":fb, "dn":fn})
                    s.execute(text("INSERT INTO bildirimler (tip, mesaj) VALUES ('Masraf', :m)"), {"m": f"{st.session_state.user_name}, {t_tut} TL masraf talebi girdi."})
                    s.commit()
                send_email_notification("admin@forleai.com", "Yeni Masraf Talebi", f"{st.session_state.user_name} adlı personel {t_tut} TL değerinde masraf girişi yapmıştır.")
                st.success("Talebiniz yönetime iletildi.")
                st.rerun()
                
    df_talep_kisisel = conn.query("SELECT id, tarih, tutar, aciklama, dosya_adi, durum FROM harcama_talepleri WHERE personel = :p ORDER BY id DESC", params={"p":st.session_state.user_name}, ttl=0)
    st.markdown("### Geçmiş Taleplerim")
    st.dataframe(df_talep_kisisel, use_container_width=True)

    with st.expander(":material/delete: Hatalı Talebi Sil"):
        sil_id = st.number_input("Silinecek Talep ID:", min_value=0, step=1, key="s_talep")
        if st.button("Sil", key="b_talep") and sil_id > 0:
            if sil_kayit("harcama_talepleri", sil_id): st.rerun()

elif page == ":material/receipt_long: Masraf Onay Paneli":
    st.markdown("<div class='page-header'><h1>Yönetici: Personel Masraf Onayları</h1></div>", unsafe_allow_html=True)
    df_talepler = conn.query("SELECT id, personel, tarih, tutar, aciklama, dosya_adi, durum FROM harcama_talepleri ORDER BY id DESC", ttl=0)
    st.dataframe(df_talepler, use_container_width=True)
    
    with st.expander("✅ Talebi Onayla ve Finansa İşle"):
        islem_id = st.number_input("İşlem Yapılacak Talep ID", min_value=0, step=1)
        islem_durum = st.selectbox("Karar", ["Onaylandı", "Reddedildi"])
        if st.button("Uygula") and islem_id > 0:
            with conn.session as s:
                s.execute(text("UPDATE harcama_talepleri SET durum = :d WHERE id = :id"), {"d": islem_durum, "id": islem_id})
                if islem_durum == "Onaylandı":
                    talep_veri = conn.query("SELECT * FROM harcama_talepleri WHERE id = :id", params={"id": islem_id}).iloc[0]
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, aciklama, giren) VALUES (:t, 'Diğer (Personel)', :tu, :a, :g)"),
                              {"t": talep_veri['tarih'], "tu": talep_veri['tutar'], "a": f"{talep_veri['personel']} - {talep_veri['aciklama']}", "g": "Sistem (Onaylanan)"})
                s.commit()
            st.success(f"Talep {islem_durum}. Onaylandıysa otomatik olarak finans tablosuna işlendi.")
            st.rerun()

elif page == ":material/assignment: Proje & Görevler":
    st.markdown("<div class='page-header'><h1>Operasyon: Proje & Görev Takibi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Görev Ataması"):
        with st.form("gorev_form"):
            g_baslik = st.text_input("Operasyon Başlığı")
            g_atanan = st.text_input("Sorumlu Personel E-posta")
            g_tarih = st.date_input("Termin Tarihi")
            g_acik = st.text_area("Görev Detayları")
            if st.form_submit_button("Görevi Ata"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik, aciklama, atanan, son_tarih, olusturan) VALUES (:ba, :ac, :at, :st, :ol)"), 
                              {"ba":g_baslik, "ac":g_acik, "at":g_atanan, "st":g_tarih.strftime("%d-%m-%Y"), "ol":st.session_state.user_name})
                    s.commit()
                send_email_notification(g_atanan, "Yeni Görev Ataması", f"Size yeni bir görev atandı: {g_baslik}\nSon Tarih: {g_tarih}\nDetay: {g_acik}")
                st.success("Görev atandı ve e-posta bildirimi gönderildi.")
                st.rerun()
    df_g = conn.query("SELECT id, baslik, atanan, durum, son_tarih, aciklama, olusturan FROM gorevler ORDER BY id DESC", ttl=0)
    st.dataframe(df_g, use_container_width=True)

    with st.expander(":material/delete: Kayıt Sil"):
        sil_id = st.number_input("Silinecek ID:", min_value=0, step=1, key="s_g")
        if st.button("Sil", key="b_g") and sil_id > 0:
            if sil_kayit("gorevler", sil_id): st.rerun()

elif page == ":material/groups: İnsan Kaynakları":
    st.markdown("<div class='page-header'><h1>İnsan Kaynakları & Organizasyon</h1></div>", unsafe_allow_html=True)
    ik_tab1, ik_tab2 = st.tabs(["Kurumsal Kadro", "İzin Yönetimi"])
    
    with ik_tab1:
        with st.expander(":material/person_add: Yeni Personel Girişi"):
            with st.form("per_form"):
                p1, p2 = st.columns(2)
                with p1:
                    per_isim = st.text_input("Tam Adı")
                    per_email = st.text_input("Kurumsal E-posta")
                    per_tel = st.text_input("İletişim Numarası")
                with p2:
                    per_poz = st.text_input("Unvan / Pozisyon")
                    per_dep = st.selectbox("Departman", ["Yazılım","Donanım","Ar-Ge","Yönetim","Satış","Diğer"])
                    per_basl = st.date_input("İşe Başlama Tarihi")
                per_not = st.text_area("Özlük Notları")
                if st.form_submit_button("Personeli Kaydet"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO personel (isim, email, pozisyon, departman, ise_baslama, telefon, notlar) VALUES (:i, :e, :p, :d, :b, :t, :n)"), 
                                  {"i":per_isim, "e":per_email, "p":per_poz, "d":per_dep, "b":per_basl.strftime("%d-%m-%Y"), "t":per_tel, "n":per_not})
                        s.commit()
                    st.success("Personel eklendi.")
                    st.rerun()
                    
        df_per = conn.query("SELECT id, isim, email, telefon, pozisyon, departman, ise_baslama FROM personel ORDER BY id DESC", ttl=0)
        df_per.columns = ["ID", "İsim Soyisim", "E-posta", "Telefon", "Unvan", "Departman", "Başlangıç"]
        st.dataframe(df_per, use_container_width=True)
        st.download_button(":material/download: Kadro Raporunu İndir", excel_export(df_per), "ForleAI_IK.xlsx")
        
        with st.expander(":material/delete: Personel Kaydını Sil"):
            sil_id = st.number_input("Silinecek Personel ID:", min_value=0, step=1, key="sil_per")
            if st.button("Sil", key="btn_sil_per") and sil_id > 0:
                if sil_kayit("personel", sil_id): st.rerun()

    with ik_tab2:
        with st.expander(":material/flight_takeoff: İzin Talebi Oluştur"):
            with st.form("izin_form"):
                i1, i2 = st.columns(2)
                with i1:
                    iz_per = st.text_input("Talep Eden Personel")
                    iz_tur = st.selectbox("İzin Kategorisi", ["Yıllık","Mazeret","Sağlık","Ücretsiz"])
                with i2:
                    iz_bas = st.date_input("Başlangıç Tarihi")
                    iz_bit = st.date_input("Bitiş Tarihi")
                if st.form_submit_button("Talebi İlet"):
                    gun = (iz_bit - iz_bas).days + 1
                    if gun <= 0: st.error("Geçersiz tarih aralığı.")
                    else:
                        with conn.session as s:
                            s.execute(text("INSERT INTO izinler (personel_adi, izin_turu, baslangic, bitis, gun_sayisi, talep_eden) VALUES (:pa, :it, :ba, :bi, :gs, :te)"), 
                                      {"pa":iz_per, "it":iz_tur, "ba":iz_bas.strftime("%d-%m-%Y"), "bi":iz_bit.strftime("%d-%m-%Y"), "gs":gun, "te":st.session_state.user_name})
                            s.execute(text("INSERT INTO bildirimler (tip, mesaj) VALUES ('İzin', :m)"), {"m": f"Personel {iz_per}, {gun} günlük {iz_tur} izni talep etti."})
                            s.commit()
                        st.success("İzin talebi onaya sunuldu ve yöneticilere bildirildi.")
                        st.rerun()
                        
        df_iz = conn.query("SELECT id, personel_adi, izin_turu, baslangic, bitis, gun_sayisi, durum FROM izinler ORDER BY id DESC", ttl=0)
        df_iz.columns = ["ID", "Personel", "Kategori", "Başlangıç", "Bitiş", "Süre (Gün)", "Onay Durumu"]
        st.dataframe(df_iz, use_container_width=True)

        with st.expander(":material/delete: Hatalı İzin Kaydını Sil"):
            sil_id = st.number_input("Silinecek İzin ID:", min_value=0, step=1, key="sil_izin")
            if st.button("Sil", key="btn_sil_izin") and sil_id > 0:
                if sil_kayit("izinler", sil_id): st.rerun()

elif page == ":material/admin_panel_settings: Sistem Logları":
    st.markdown("<div class='page-header'><h1>Sistem Güvenliği ve Denetim Logları</h1></div>", unsafe_allow_html=True)
    df_log = conn.query("SELECT id, created_at, kullanici, aksiyon, detay FROM audit_log ORDER BY id DESC", ttl=0)
    df_log.columns = ["ID", "Zaman", "İşlemi Yapan", "Olay Tipi", "Teknik Detay"]
    st.dataframe(df_log, use_container_width=True)
    st.download_button(":material/download: Logları İndir", excel_export(df_log), "ForleAI_Log.xlsx")
