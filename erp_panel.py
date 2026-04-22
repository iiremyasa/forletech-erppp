import streamlit as st
import pandas as pd
import datetime
import io

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="FORLE TECH | ERP Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KURUMSAL CSS ---
st.markdown("""
<style>
    /* Ana arka plan */
    .main { background-color: #f4f6f9; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2332 0%, #243447 100%);
    }
    section[data-testid="stSidebar"] * { color: #e8edf3 !important; }
    section[data-testid="stSidebar"] .stRadio label { 
        padding: 8px 12px; 
        border-radius: 6px; 
        display: block;
        transition: background 0.2s;
    }
    section[data-testid="stSidebar"] .stRadio label:hover { 
        background: rgba(255,255,255,0.1); 
    }

    /* Metrik kartları */
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* Butonlar */
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

    /* Başlık kartı */
    .page-header {
        background: linear-gradient(135deg, #1a2332 0%, #2d4a6e 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .page-header h2 { color: white; margin: 0; font-size: 1.6rem; }
    .page-header p { color: #a0b4c8; margin: 4px 0 0 0; font-size: 0.9rem; }

    /* Bildirim banner */
    .notif-banner {
        background: #fff8e1;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .notif-banner-info {
        background: #e8f4fd;
        border-left: 4px solid #3b82f6;
    }
    .notif-banner-success {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SİSTEM HAFIZASINI BAŞLATMA ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'parca_listesi' not in st.session_state: st.session_state.parca_listesi = []
if 'cihaz_listesi' not in st.session_state: st.session_state.cihaz_listesi = []
if 'harcamalar' not in st.session_state: st.session_state.harcamalar = []
if 'bildirimler' not in st.session_state: st.session_state.bildirimler = [
    {"tip": "uyari", "mesaj": "3 parçanın garanti süresi bu ay dolacak.", "tarih": "22-04-2025"},
    {"tip": "bilgi", "mesaj": "Nisan ayı bütçe raporu hazırlanmayı bekliyor.", "tarih": "20-04-2025"},
    {"tip": "basari", "mesaj": "Sistem güncellemesi başarıyla tamamlandı.", "tarih": "18-04-2025"},
]
if 'kullanici_db' not in st.session_state:
    st.session_state.kullanici_db = {
        "admin@forleai.com": {"sifre": "admin123", "isim": "Sistem Yöneticisi", "rol": "Admin"}
    }

# --- 2. GİRİŞ EKRANI ---
if not st.session_state.authenticated:
    st.markdown("""
    <div style='text-align:center; padding: 60px 0 20px 0;'>
        <div style='font-size:3rem;'>🏢</div>
        <h1 style='color:#1a2332; font-size:2.2rem; margin:8px 0;'>FORLE TECH</h1>
        <p style='color:#64748b; font-size:1rem;'>Kurumsal ERP Portalı</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='background:white; padding:32px; border-radius:16px; 
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;'>
        """, unsafe_allow_html=True)

        tab_giris, tab_kayit = st.tabs(["Giriş Yap", "Yeni Hesap Oluştur"])

        with tab_giris:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("giris_formu"):
                login_email = st.text_input("Kurumsal E-posta", placeholder="isim@forleai.com").strip().lower()
                login_password = st.text_input("Şifre", type="password", placeholder="••••••••").strip()
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Giriş Yap", use_container_width=True):
                    if login_email in st.session_state.kullanici_db and \
                       st.session_state.kullanici_db[login_email]["sifre"] == login_password:
                        st.session_state.authenticated = True
                        st.session_state.user_name = st.session_state.kullanici_db[login_email]["isim"]
                        st.session_state.user_email = login_email
                        st.session_state.user_rol = st.session_state.kullanici_db[login_email]["rol"]
                        st.rerun()
                    else:
                        st.error("Hatalı e-posta veya şifre.")

        with tab_kayit:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("kayit_formu"):
                kayit_isim = st.text_input("Ad Soyad").strip()
                kayit_email = st.text_input("E-posta (@forleai.com)", placeholder="isim@forleai.com").strip().lower()
                kayit_sifre = st.text_input("Şifre", type="password").strip()
                kayit_sifre_tekrar = st.text_input("Şifre Tekrar", type="password").strip()
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Kayıt Ol", use_container_width=True):
                    if not kayit_email.endswith("@forleai.com"):
                        st.error("Sadece @forleai.com uzantılı e-postalar kabul edilir.")
                    elif kayit_sifre != kayit_sifre_tekrar:
                        st.error("Şifreler uyuşmuyor.")
                    elif len(kayit_sifre) < 4:
                        st.error("Şifre çok kısa.")
                    elif kayit_email in st.session_state.kullanici_db:
                        st.warning("Bu e-posta zaten kayıtlı.")
                    else:
                        st.session_state.kullanici_db[kayit_email] = {
                            "sifre": kayit_sifre, "isim": kayit_isim, "rol": "Kullanıcı"
                        }
                        st.success("Kayıt başarılı! Giriş yapabilirsin.")

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 16px 0 8px 0;'>
        <div style='font-size:2rem;'>🏢</div>
        <div style='font-weight:700; font-size:1.1rem; color:white;'>FORLE TECH</div>
        <div style='font-size:0.75rem; color:#8a9bb0; margin-top:2px;'>ERP Sistemi</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.08); border-radius:10px; padding:12px; margin-bottom:12px;'>
        <div style='font-size:0.75rem; color:#8a9bb0;'>Oturum Açık</div>
        <div style='font-weight:600; color:white;'>{st.session_state.user_name}</div>
        <div style='font-size:0.75rem; color:#64a8d8;'>{st.session_state.user_email}</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Menü", [
        "Ana Sayfa",
        "Parça Yönetimi",
        "Cihaz Yönetimi",
        "Bütçe & Harcamalar",
        "Bildirimler"
    ], label_visibility="collapsed")

    st.markdown("---")

    bildirim_sayisi = len(st.session_state.bildirimler)
    if bildirim_sayisi > 0:
        st.markdown(f"""
        <div style='background:rgba(245,158,11,0.15); border-radius:8px; padding:10px 12px; 
                    border-left:3px solid #f59e0b; margin-bottom:12px;'>
            <span style='color:#f59e0b; font-size:0.85rem;'>
                {bildirim_sayisi} okunmamış bildirim
            </span>
        </div>
        """, unsafe_allow_html=True)

    if st.button("Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- YARDIMCI FONKSİYONLAR ---
def excel_export(df, dosya_adi):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Veri')
    buffer.seek(0)
    return buffer

def page_header(baslik, aciklama):
    st.markdown(f"""
    <div class='page-header'>
        <h2>{baslik}</h2>
        <p>{aciklama}</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# --- 4. ANA SAYFA ---
# ==========================================
if page == "Ana Sayfa":
    page_header("Kontrol Paneli", "FORLE TECH ERP — Genel Bakış")

    # KPI Kartları
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Parça", len(st.session_state.parca_listesi), help="Kayıtlı parça sayısı")
    with col2:
        st.metric("Toplam Cihaz", len(st.session_state.cihaz_listesi), help="Kayıtlı cihaz sayısı")
    with col3:
        toplam_harcama = sum(h["Tutar (TL)"] for h in st.session_state.harcamalar)
        st.metric("Toplam Harcama", f"{toplam_harcama:,.0f} TL")
    with col4:
        st.metric("Bildirim", len(st.session_state.bildirimler), help="Bekleyen bildirimler")

    st.markdown("<br>", unsafe_allow_html=True)

    # Grafikler
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Kategori Bazlı Harcamalar")
        if st.session_state.harcamalar:
            df_h = pd.DataFrame(st.session_state.harcamalar)
            chart_data = df_h.groupby("Kategori")["Tutar (TL)"].sum().reset_index()
            st.bar_chart(chart_data.set_index("Kategori"), color="#2d4a6e")
        else:
            st.info("Henüz harcama verisi yok.")

    with col_b:
        st.markdown("#### Parça Durumu Dağılımı")
        if st.session_state.parca_listesi:
            df_p = pd.DataFrame(st.session_state.parca_listesi)
            durum_data = df_p["Durum"].value_counts().reset_index()
            durum_data.columns = ["Durum", "Adet"]
            st.bar_chart(durum_data.set_index("Durum"), color="#2d4a6e")
        else:
            st.info("Henüz parça verisi yok.")

    # Son eklenenler
    st.markdown("#### Son Eklenen Harcamalar")
    if st.session_state.harcamalar:
        df_son = pd.DataFrame(st.session_state.harcamalar[-5:])
        st.dataframe(df_son, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz harcama girişi yapılmamış.")

# ==========================================
# --- 5. PARÇA YÖNETİMİ ---
# ==========================================
elif page == "Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık etiketi ve envanter takibi")

    with st.expander("Yeni Parça Ekle", expanded=False):
        with st.form("parca_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_etiket = st.text_input("Varlık Etiketi")
                p_durum = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda", "Hurda"])
            with c2:
                p_tarih = st.date_input("Kayıt Tarihi", datetime.date.today())
                p_notlar = st.text_area("Notlar")
            if st.form_submit_button("Kaydet", use_container_width=True):
                tarih_str = p_tarih.strftime("%d-%m-%Y")
                st.session_state.parca_listesi.append({
                    "Etiket": p_etiket,
                    "Durum": p_durum,
                    "Tarih": tarih_str,
                    "Notlar": p_notlar
                })
                st.success("Parça eklendi.")
                st.rerun()

    st.markdown("---")

    if st.session_state.parca_listesi:
        df_parca = pd.DataFrame(st.session_state.parca_listesi)

        # Arama & Filtreleme
        col_ara, col_filtre = st.columns([2, 1])
        with col_ara:
            arama = st.text_input("Ara", placeholder="Etiket veya not ile ara...")
        with col_filtre:
            durum_filtre = st.selectbox("Duruma Göre Filtrele", ["Tümü", "Aktif", "Arızalı", "Depoda", "Hurda"])

        if arama:
            df_parca = df_parca[df_parca.apply(lambda r: arama.lower() in str(r).lower(), axis=1)]
        if durum_filtre != "Tümü":
            df_parca = df_parca[df_parca["Durum"] == durum_filtre]

        # Durum özet kartları
        col1, col2, col3, col4 = st.columns(4)
        df_all = pd.DataFrame(st.session_state.parca_listesi)
        with col1:
            st.metric("Aktif", len(df_all[df_all["Durum"] == "Aktif"]))
        with col2:
            st.metric("Arızalı", len(df_all[df_all["Durum"] == "Arızalı"]))
        with col3:
            st.metric("Depoda", len(df_all[df_all["Durum"] == "Depoda"]))
        with col4:
            st.metric("Hurda", len(df_all[df_all["Durum"] == "Hurda"]))

        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_parca, use_container_width=True, hide_index=True)

        # Excel Export
        excel_data = excel_export(df_parca, "parca_listesi")
        st.download_button(
            label="Excel Olarak İndir",
            data=excel_data,
            file_name="forletech_parca_listesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz parça eklenmemiş.")

# ==========================================
# --- 6. CİHAZ YÖNETİMİ ---
# ==========================================
elif page == "Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Cihaz montaj ve varlık takibi")

    with st.expander("Yeni Cihaz Ekle", expanded=False):
        with st.form("cihaz_form"):
            c1, c2 = st.columns(2)
            with c1:
                d_adi = st.text_input("Cihaz Adı")
                d_seri = st.text_input("Seri No")
            with c2:
                d_durum = st.selectbox("Durum", ["Aktif", "Testte", "Bakımda", "Depoda"])
                d_not = st.text_area("Notlar")
            if st.form_submit_button("Kaydet", use_container_width=True):
                st.session_state.cihaz_listesi.append({
                    "Cihaz Adı": d_adi,
                    "Seri No": d_seri,
                    "Durum": d_durum,
                    "Not": d_not
                })
                st.success("Cihaz eklendi.")
                st.rerun()

    st.markdown("---")

    if st.session_state.cihaz_listesi:
        df_cihaz = pd.DataFrame(st.session_state.cihaz_listesi)

        # Arama & Filtreleme
        col_ara, col_filtre = st.columns([2, 1])
        with col_ara:
            arama = st.text_input("Ara", placeholder="Cihaz adı veya seri no ile ara...")
        with col_filtre:
            durum_filtre = st.selectbox("Duruma Göre Filtrele", ["Tümü", "Aktif", "Testte", "Bakımda", "Depoda"])

        if arama:
            df_cihaz = df_cihaz[df_cihaz.apply(lambda r: arama.lower() in str(r).lower(), axis=1)]
        if durum_filtre != "Tümü":
            df_cihaz = df_cihaz[df_cihaz["Durum"] == durum_filtre]

        st.dataframe(df_cihaz, use_container_width=True, hide_index=True)

        excel_data = excel_export(df_cihaz, "cihaz_listesi")
        st.download_button(
            label="Excel Olarak İndir",
            data=excel_data,
            file_name="forletech_cihaz_listesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz cihaz eklenmemiş.")

# ==========================================
# --- 7. BÜTÇE & HARCAMALAR ---
# ==========================================
elif page == "Bütçe & Harcamalar":
    page_header("Bütçe & Harcamalar", "Kurumsal harcama takibi ve raporlama")

    with st.expander("Yeni Harcama Ekle", expanded=False):
        with st.form("harcama_formu"):
            h1, h2, h3 = st.columns(3)
            with h1:
                h_tarih = st.date_input("Tarih", datetime.date.today())
                h_kategori = st.selectbox("Kategori", ["Ar-Ge Alımı", "Ofis Gideri", "Seyahat", "Maaş", "Diğer"])
            with h2:
                h_tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)
                h_fatura = st.text_input("Fatura / Fiş No")
            with h3:
                h_aciklama = st.text_area("Açıklama")

            if st.form_submit_button("Harcamayı Kaydet", use_container_width=True):
                tarih_str = h_tarih.strftime("%d-%m-%Y")
                st.session_state.harcamalar.append({
                    "Tarih": tarih_str,
                    "Kategori": h_kategori,
                    "Tutar (TL)": h_tutar,
                    "Fatura No": h_fatura,
                    "Açıklama": h_aciklama,
                    "Giren": st.session_state.user_name
                })
                st.success("Harcama kaydedildi.")
                st.rerun()

    st.markdown("---")

    if st.session_state.harcamalar:
        df_h = pd.DataFrame(st.session_state.harcamalar)

        # KPI
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Harcama", f"{df_h['Tutar (TL)'].sum():,.2f} TL")
        with col2:
            st.metric("Ortalama Harcama", f"{df_h['Tutar (TL)'].mean():,.2f} TL")
        with col3:
            st.metric("Kayıt Sayısı", len(df_h))

        st.markdown("<br>", unsafe_allow_html=True)

        # Arama & Filtreleme
        col_ara, col_filtre = st.columns([2, 1])
        with col_ara:
            arama = st.text_input("Ara", placeholder="Açıklama, kategori veya fatura no ile ara...")
        with col_filtre:
            kat_filtre = st.selectbox("Kategoriye Göre", ["Tümü", "Ar-Ge Alımı", "Ofis Gideri", "Seyahat", "Maaş", "Diğer"])

        if arama:
            df_h = df_h[df_h.apply(lambda r: arama.lower() in str(r).lower(), axis=1)]
        if kat_filtre != "Tümü":
            df_h = df_h[df_h["Kategori"] == kat_filtre]

        st.dataframe(df_h, use_container_width=True, hide_index=True)

        excel_data = excel_export(df_h, "harcamalar")
        st.download_button(
            label="Excel Olarak İndir",
            data=excel_data,
            file_name="forletech_harcamalar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Henüz harcama girişi yapılmamış.")

# ==========================================
# --- 8. BİLDİRİMLER ---
# ==========================================
elif page == "Bildirimler":
    page_header("Bildirimler", "Sistem uyarıları ve güncellemeler")

    if st.session_state.bildirimler:
        for i, b in enumerate(st.session_state.bildirimler):
            tip_class = {
                "uyari": "notif-banner",
                "bilgi": "notif-banner notif-banner-info",
                "basari": "notif-banner notif-banner-success"
            }.get(b["tip"], "notif-banner")

            tip_ikon = {"uyari": "⚠️", "bilgi": "ℹ️", "basari": "✅"}.get(b["tip"], "📌")

            col_msg, col_del = st.columns([8, 1])
            with col_msg:
                st.markdown(f"""
                <div class='{tip_class}'>
                    {tip_ikon} <strong>{b['tarih']}</strong> — {b['mesaj']}
                </div>
                """, unsafe_allow_html=True)
            with col_del:
                if st.button("Sil", key=f"del_{i}"):
                    st.session_state.bildirimler.pop(i)
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Tüm Bildirimleri Temizle"):
            st.session_state.bildirimler = []
            st.rerun()
    else:
        st.success("Tüm bildirimler okundu, temiz görünüyor!")

    st.markdown("---")
    st.markdown("#### Yeni Bildirim Ekle")
    with st.form("bildirim_form"):
        b_tip = st.selectbox("Tip", ["bilgi", "uyari", "basari"])
        b_mesaj = st.text_input("Mesaj")
        if st.form_submit_button("Bildirim Ekle"):
            st.session_state.bildirimler.append({
                "tip": b_tip,
                "mesaj": b_mesaj,
                "tarih": datetime.date.today().strftime("%d-%m-%Y")
            })
            st.success("Bildirim eklendi.")
            st.rerun()
