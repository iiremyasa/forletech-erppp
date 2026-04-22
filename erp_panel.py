import streamlit as st
import pandas as pd
import datetime
import hashlib
import io
from sqlalchemy import text

# --- 0. SAYFA AYARLARI VE FORLE/AI ÖZEL CSS ---
st.set_page_config(page_title="Forle/AI | ERP Portal", page_icon=":material/domain:", layout="wide")

st.markdown("""
<style>
    /* Genel Arka Plan ve Font */
    .main { background-color: #f4f7f6; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    
    /* Yan Menü (Logodaki Derin Lacivert) */
    section[data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #152238 0%, #1A365D 100%); 
        border-right: 2px solid #38B2AC; 
    }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }
    
    /* Buton Tasarımları (Logodaki Turkuaz/Nane Yeşili) */
    .stButton > button { 
        background: #38B2AC; 
        color: #ffffff !important; 
        border-radius: 6px; 
        transition: all 0.3s ease; 
        border: none;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(56, 178, 172, 0.3);
    }
    .stButton > button:hover { 
        background: #2C7A7B; 
        box-shadow: 0 4px 8px rgba(44, 122, 123, 0.4); 
        transform: translateY(-2px); 
    }
    
    /* Sayfa Üst Başlık (Header) Tasarımı */
    .page-header { 
        background: linear-gradient(135deg, #152238 0%, #2B6CB0 100%); 
        color: white; 
        padding: 20px 24px; 
        border-radius: 8px; 
        margin-bottom: 24px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 6px solid #38B2AC; 
    }
    .page-header h1 { color: white; font-size: 1.8rem; margin: 0; font-weight: 700; letter-spacing: 0.5px; }
    
    /* Rol Etiketi ve Metrik Kartları */
    .role-badge { 
        padding: 4px 12px; 
        border-radius: 4px; 
        font-size: 0.75rem; 
        font-weight: 600; 
        background: rgba(56,178,172,0.15); 
        border: 1px solid #38B2AC; 
        color: #38B2AC !important; 
    }
    div[data-testid="metric-container"] {
        background-color: white;
        border-top: 4px solid #38B2AC;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tablo Tasarımı */
    [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 1. VERİTABANI BAĞLANTISI VE OTOMATİK GÜNCELLEME ---
try:
    conn = st.connection("postgresql", type="sql")
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici');
            CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar FLOAT, fatura_no TEXT, aciklama TEXT, giren TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS nir_projesi (id SERIAL PRIMARY KEY, demo_tarihi TEXT, test_sonucu TEXT, sponsorluk_durumu TEXT, cihaz_versiyonu TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS izinler (id SERIAL PRIMARY KEY, personel_adi TEXT, izin_turu TEXT, baslangic TEXT, bitis TEXT, gun_sayisi FLOAT, durum TEXT DEFAULT 'Bekliyor', talep_eden TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, okundu INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """))
        
        onarımlar = [
            "ALTER TABLE parcalar ADD COLUMN IF NOT EXISTS yazilim_versiyonu TEXT;",
            "ALTER TABLE parcalar ADD COLUMN IF NOT EXISTS bagli_cihaz TEXT;",
            "ALTER TABLE parcalar ADD COLUMN IF NOT EXISTS durum_notu TEXT;"
        ]
        for onar in onarımlar:
            try: s.execute(text(onar))
            except: pass

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

# --- 3. GİRİŞ EKRANI ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding-top:60px;color:#152238;'><h1 style='font-size:3.5rem;font-weight:800;letter-spacing:1px;'>Forle<span style='color:#38B2AC;'>/AI</span></h1><p style='color:#64748b;font-size:1.2rem;font-weight:500;'>Kurumsal Yönetim Sistemi</p></div>", unsafe_allow_html=True)
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
                        with conn.session as s:
                            s.execute(text("INSERT INTO kullanicilar (email, sifre, isim) VALUES (:e, :p, :n)"), {"e":ne, "p":hash_pw(np), "n":ni})
                            s.commit()
                        st.success("Kayıt başarılı. Giriş yapabilirsiniz.")
    st.stop()

# --- 4. SIDEBAR VE SAYFALAMA ---
with st.sidebar:
    st.markdown(f"<div style='margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin:0;font-size:1.1rem;color:white;'>{st.session_state.user_name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<span class='role-badge'>{st.session_state.user_rol}</span>", unsafe_allow_html=True)
    st.markdown(f"</div>", unsafe_allow_html=True)
    
    page = st.radio("MENÜ", [
        ":material/dashboard: Kontrol Paneli", 
        ":material/biotech: NIR Ar-Ge Modülü", 
        ":material/precision_manufacturing: Parça Yönetimi", 
        ":material/memory: Cihaz Yönetimi", 
        ":material/account_balance: Finans & Bütçe", 
        ":material/assignment: Proje & Görevler", 
        ":material/groups: İnsan Kaynakları", 
        ":material/admin_panel_settings: Sistem Logları"
    ])
    
    st.markdown("---")
    if st.button(":material/logout: Oturumu Kapat", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 5. ANA SAYFA VE MODÜLLER ---

if page == ":material/dashboard: Kontrol Paneli":
    st.markdown("<div class='page-header'><h1>Kontrol Paneli</h1></div>", unsafe_allow_html=True)
    
    # Yönetici Bildirimleri Paneli
    if st.session_state.user_rol == "Admin":
        bildirimler = conn.query("SELECT id, mesaj, created_at FROM bildirimler WHERE okundu = 0 ORDER BY id DESC", ttl=0)
        if not bildirimler.empty:
            st.warning(f"Dikkat: Bekleyen {len(bildirimler)} yeni bildiriminiz var!")
            for idx, row in bildirimler.iterrows():
                b_col1, b_col2 = st.columns([4, 1])
                b_col1.info(f"**{row['created_at'].strftime('%d-%m-%Y %H:%M')}** | {row['mesaj']}")
                if b_col2.button("Okundu İşaretle", key=f"okundu_{row['id']}"):
                    with conn.session as s:
                        s.execute(text("UPDATE bildirimler SET okundu = 1 WHERE id = :id"), {"id": row['id']})
                        s.commit()
                    st.rerun()
            st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Envanterdeki Parça", len(conn.query("SELECT id FROM parcalar", ttl=0)))
    c2.metric("Kayıtlı Cihaz", len(conn.query("SELECT id FROM cihazlar", ttl=0)))
    c3.metric("Açık Operasyonlar", len(conn.query("SELECT id FROM gorevler WHERE durum != 'Tamamlandı'", ttl=0)))
    h_toplam = conn.query("SELECT SUM(tutar) as t FROM harcamalar", ttl=0).iloc[0]['t'] or 0
    c4.metric("Toplam Çıktı", f"{h_toplam:,.2f} TL")

elif page == ":material/biotech: NIR Ar-Ge Modülü":
    st.markdown("<div class='page-header'><h1>NIR Projesi Ar-Ge Takibi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Test / Demo Kaydı"):
        with st.form("nir_form"):
            n1, n2 = st.columns(2)
            with n1:
                nt = st.date_input("Demo Tarihi")
                nv = st.text_input("Cihaz Versiyonu (Örn: v1.2)")
            with n2:
                ns = st.selectbox("Sponsorluk / Ortaklık Durumu", ["Görüşülüyor", "Protokol İmzalandı", "Beklemede", "Reddedildi"])
                nr = st.text_input("Test Sonucu Özeti")
            nn = st.text_area("Teknik Rapor ve Notlar")
            if st.form_submit_button("Ar-Ge Kaydını İşle"):
                with conn.session as s:
                    s.execute(text("INSERT INTO nir_projesi (demo_tarihi, test_sonucu, sponsorluk_durumu, cihaz_versiyonu, notlar, ekleyen) VALUES (:t,:r,:s,:v,:n,:u)"),
                              {"t":nt.strftime("%d-%m-%Y"), "r":nr, "s":ns, "v":nv, "n":nn, "u":st.session_state.user_name})
                    s.commit()
                st.success("Veri sisteme işlendi.")
                st.rerun()
    
    df_nir = conn.query("SELECT id, demo_tarihi, cihaz_versiyonu, sponsorluk_durumu, test_sonucu, notlar, ekleyen FROM nir_projesi ORDER BY id DESC", ttl=0)
    df_nir_export = df_nir.copy()
    df_nir.columns = ["Kayıt ID", "Tarih", "Versiyon", "Sponsorluk Durumu", "Sonuç", "Notlar", "Sorumlu"]
    st.dataframe(df_nir, use_container_width=True)
    st.download_button(":material/download: Raporu Excel Olarak İndir", excel_export(df_nir_export), "ForleAI_NIR_ArGe.xlsx")
    
    with st.expander(":material/delete: Hatalı Kaydı Sil"):
        sil_id = st.number_input("Silinecek Ar-Ge ID:", min_value=0, step=1, key="sil_nir")
        if st.button("Kaydı Sil", key="btn_sil_nir") and sil_id > 0:
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
    df_p.columns = ["Kayıt ID", "Varlık Etiketi", "Kayıt Tarihi", "Model", "Durum", "Seri No", "Durum Notu", "Yazılım Vers.", "Bağlı Cihaz"]
    st.dataframe(df_p, use_container_width=True)
    st.download_button(":material/download: Listeyi Excel Olarak İndir", excel_export(df_p_export), "ForleAI_Parca_Listesi.xlsx")
    
    with st.expander(":material/delete: Hatalı Kaydı Sil"):
        sil_id = st.number_input("Silinecek Parça ID:", min_value=0, step=1, key="sil_parca")
        if st.button("Kaydı Sil", key="btn_sil_parca") and sil_id > 0:
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
                
    df_c = conn.query("SELECT id, cihaz_adi, ip, model, takili_sensor_seri, anakart_seri, durum, seri_no, notlar, ekleyen FROM cihazlar ORDER BY id DESC", ttl=0)
    df_c_export = df_c.copy()
    df_c.columns = ["Kayıt ID", "Cihaz Adı", "IP Adresi", "Model", "Sensör Seri", "Anakart Seri", "Durum", "Cihaz Seri", "Notlar", "Sorumlu"]
    st.dataframe(df_c, use_container_width=True)
    st.download_button(":material/download: Listeyi Excel Olarak İndir", excel_export(df_c_export), "ForleAI_Cihazlar.xlsx")

    with st.expander(":material/delete: Hatalı Kaydı Sil"):
        sil_id = st.number_input("Silinecek Cihaz ID:", min_value=0, step=1, key="sil_cihaz")
        if st.button("Kaydı Sil", key="btn_sil_cihaz") and sil_id > 0:
            if sil_kayit("cihazlar", sil_id): st.rerun()

elif page == ":material/account_balance: Finans & Bütçe":
    st.markdown("<div class='page-header'><h1>Muhasebe: Bütçe ve Giderler</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Fiş / Fatura İşle"):
        with st.form("h_form"):
            ta, ka, tu = st.date_input("Kayıt Tarihi"), st.selectbox("Gider Kalemi", ["Ar-Ge", "Ofis", "Seyahat", "Maaş", "Vergi", "İSG", "Mutfak", "Diğer"]), st.number_input("Tutar (TL)")
            fn = st.text_input("Fatura/Fiş No")
            ac = st.text_area("İşlem Açıklaması")
            if st.form_submit_button("Muhasebeye İşle"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tarih, kategori, tutar, fatura_no, aciklama, giren) VALUES (:t, :k, :tu, :f, :a, :g)"), 
                              {"t":ta.strftime("%d-%m-%Y"), "k":ka, "tu":tu, "f":fn, "a":ac, "g":st.session_state.user_name})
                    s.commit()
                st.success("Gider işlendi.")
                st.rerun()
                
    df_h = conn.query("SELECT id, tarih, kategori, tutar, fatura_no, aciklama, giren FROM harcamalar ORDER BY id DESC", ttl=0)
    df_h_export = df_h.copy()
    df_h.columns = ["Kayıt ID", "Tarih", "Gider Kalemi", "Tutar (TL)", "Belge No", "Açıklama", "İşleyen"]
    st.dataframe(df_h, use_container_width=True)
    st.download_button(":material/download: Finans Raporunu İndir", excel_export(df_h_export), "ForleAI_Finans.xlsx")

    with st.expander(":material/delete: Hatalı Kaydı Sil"):
        sil_id = st.number_input("Silinecek Harcama ID:", min_value=0, step=1, key="sil_finans")
        if st.button("Kaydı Sil", key="btn_sil_finans") and sil_id > 0:
            if sil_kayit("harcamalar", sil_id): st.rerun()

elif page == ":material/assignment: Proje & Görevler":
    st.markdown("<div class='page-header'><h1>Operasyon: Proje & Görev Takibi</h1></div>", unsafe_allow_html=True)
    with st.expander(":material/add: Yeni Görev Ataması"):
        with st.form("gorev_form"):
            g1, g2 = st.columns(2)
            with g1:
                g_baslik = st.text_input("Operasyon Başlığı")
                g_proje = st.text_input("Bağlı Proje")
                g_atanan = st.text_input("Sorumlu Personel")
            with g2:
                g_oncelik = st.selectbox("Kritiklik Seviyesi", ["Düşük","Orta","Yüksek","Kritik"])
                g_durum = st.selectbox("Faz", ["Bekliyor","İşlemde","Test Aşamasında","Tamamlandı"])
                g_tarih = st.date_input("Termin Tarihi")
            g_acik = st.text_area("Görev Detayları")
            if st.form_submit_button("Görevi Ata"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik, aciklama, atanan, durum, oncelik, son_tarih, proje, olusturan) VALUES (:ba, :ac, :at, :du, :on, :st, :pr, :ol)"), 
                              {"ba":g_baslik, "ac":g_acik, "at":g_atanan, "du":g_durum, "on":g_oncelik, "st":g_tarih.strftime("%d-%m-%Y"), "pr":g_proje, "ol":st.session_state.user_name})
                    s.commit()
                st.success("Görev başarıyla tanımlandı.")
                st.rerun()
                
    df_g = conn.query("SELECT id, baslik, proje, atanan, oncelik, durum, son_tarih, aciklama, olusturan FROM gorevler ORDER BY id DESC", ttl=0)
    df_g_export = df_g.copy()
    df_g.columns = ["Kayıt ID", "Operasyon", "Proje", "Sorumlu", "Kritiklik", "Faz", "Termin", "Detay", "Atayan"]
    st.dataframe(df_g, use_container_width=True)
    st.download_button(":material/download: Görev Raporunu İndir", excel_export(df_g_export), "ForleAI_Operasyon.xlsx")

    with st.expander(":material/delete: Hatalı Kaydı Sil"):
        sil_id = st.number_input("Silinecek Görev ID:", min_value=0, step=1, key="sil_gorev")
        if st.button("Kaydı Sil", key="btn_sil_gorev") and sil_id > 0:
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
                    
        df_per = conn.query("SELECT id, isim, email, telefon, pozisyon, departman, ise_baslama, notlar FROM personel ORDER BY id DESC", ttl=0)
        df_per_export = df_per.copy()
        df_per.columns = ["Kayıt ID", "İsim Soyisim", "E-posta", "Telefon", "Unvan", "Departman", "Başlangıç", "Notlar"]
        st.dataframe(df_per, use_container_width=True)
        st.download_button(":material/download: Kadro Raporunu İndir", excel_export(df_per_export), "ForleAI_IK_Kadro.xlsx")
        
        with st.expander(":material/delete: Hatalı Personel Kaydını Sil"):
            sil_id = st.number_input("Silinecek Personel ID:", min_value=0, step=1, key="sil_per")
            if st.button("Kaydı Sil", key="btn_sil_per") and sil_id > 0:
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
                            # Yöneticiye Bildirim Gönder
                            s.execute(text("INSERT INTO bildirimler (tip, mesaj) VALUES ('İzin', :m)"), {"m": f"Personel {iz_per}, {gun} günlük {iz_tur} izni talep etti."})
                            s.commit()
                        st.success("İzin talebi onaya sunuldu ve yöneticilere bildirildi.")
                        st.rerun()
        
        # Yalnızca Yöneticilere Özel Onay/Ret Paneli
        if st.session_state.user_rol == "Admin":
            with st.expander("🛡️ Yönetici: İzin Onay/Reddet"):
                o1, o2 = st.columns(2)
                with o1: onay_id = st.number_input("İşlem Yapılacak İzin ID:", min_value=0, step=1, key="onay_izin_id")
                with o2: yeni_durum = st.selectbox("Yeni Durum", ["Onaylandı", "Reddedildi", "Bekliyor"], key="onay_izin_durum")
                if st.button("Durumu Güncelle", key="btn_onay_izin") and onay_id > 0:
                    with conn.session as s:
                        s.execute(text("UPDATE izinler SET durum = :durum WHERE id = :id"), {"durum": yeni_durum, "id": onay_id})
                        s.commit()
                    st.rerun()

        df_iz = conn.query("SELECT id, personel_adi, izin_turu, baslangic, bitis, gun_sayisi, durum, talep_eden FROM izinler ORDER BY id DESC", ttl=0)
        df_iz_export = df_iz.copy()
        df_iz.columns = ["Kayıt ID", "Personel", "Kategori", "Başlangıç", "Bitiş", "Süre (Gün)", "Onay Durumu", "İşleyen"]
        st.dataframe(df_iz, use_container_width=True)
        st.download_button(":material/download: İzin Raporunu İndir", excel_export(df_iz_export), "ForleAI_Izinler.xlsx")

        with st.expander(":material/delete: Hatalı İzin Kaydını Sil"):
            sil_id = st.number_input("Silinecek İzin ID:", min_value=0, step=1, key="sil_izin")
            if st.button("Kaydı Sil", key="btn_sil_izin") and sil_id > 0:
                if sil_kayit("izinler", sil_id): st.rerun()

elif page == ":material/admin_panel_settings: Sistem Logları":
    st.markdown("<div class='page-header'><h1>Sistem Güvenliği ve Denetim Logları</h1></div>", unsafe_allow_html=True)
    if st.session_state.user_rol == "Admin":
        df_log = conn.query("SELECT id, created_at, kullanici, aksiyon, detay FROM audit_log ORDER BY id DESC", ttl=0)
        df_log_export = df_log.copy()
        df_log.columns = ["Kayıt ID", "Zaman Damgası", "İşlemi Yapan", "Olay Tipi", "Teknik Detay"]
        st.dataframe(df_log, use_container_width=True)
        st.download_button(":material/download: Güvenlik Loglarını İndir", excel_export(df_log_export), "ForleAI_Audit_Log.xlsx")
    else: 
        st.error("Bu ekrana erişim yetkiniz bulunmamaktadır. Lütfen Sistem Yöneticisi ile görüşün.")
