import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="FORLE TECH Portal", layout="wide")

# --- 1. SİSTEM HAFIZASINI BAŞLATMA ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'parca_listesi' not in st.session_state:
    st.session_state.parca_listesi = []
if 'cihaz_listesi' not in st.session_state:
    st.session_state.cihaz_listesi = []
if 'harcamalar' not in st.session_state:
    st.session_state.harcamalar = []

if 'kullanici_db' not in st.session_state:
    st.session_state.kullanici_db = {
        "admin@forleai.com": {"sifre": "admin123", "isim": "Sistem Yöneticisi"}
    }

# --- 2. GİRİŞ VE KAYIT EKRANI ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color:#2c3e50;'>FORLE TECH</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Kurumsal Portal</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_giris, tab_kayit = st.tabs(["🔐 Giriş Yap", "📝 Yeni Kayıt Oluştur"])

        with tab_giris:
            with st.form("giris_formu"):
                login_email = st.text_input("Kurumsal E-posta").strip().lower()
                login_password = st.text_input("Şifre", type="password").strip()

                if st.form_submit_button("Sisteme Giriş Yap"):
                    if login_email in st.session_state.kullanici_db and st.session_state.kullanici_db[login_email]["sifre"] == login_password:
                        st.session_state.authenticated = True
                        st.session_state.user_name = st.session_state.kullanici_db[login_email]["isim"]
                        st.session_state.user_email = login_email
                        st.rerun()
                    else:
                        st.error("Hatalı e-posta veya şifre!")

        with tab_kayit:
            with st.form("kayit_formu"):
                kayit_isim = st.text_input("Adınız Soyadınız").strip()
                kayit_email = st.text_input("Yeni E-posta Adresiniz (@forleai.com)").strip().lower()
                kayit_sifre = st.text_input("Yeni Şifre Belirleyin", type="password").strip()
                kayit_sifre_tekrar = st.text_input("Şifreyi Tekrar Girin", type="password").strip()

                if st.form_submit_button("Kayıt Ol"):
                    if not kayit_email.endswith("@forleai.com"):
                        st.error("Sadece @forleai.com uzantılı şirket personeli kayıt olabilir!")
                    elif kayit_sifre != kayit_sifre_tekrar:
                        st.error("Şifreler birbiriyle uyuşmuyor!")
                    elif len(kayit_sifre) < 4:
                        st.error("Şifreniz çok kısa, lütfen daha güvenli bir şifre seçin.")
                    elif kayit_email in st.session_state.kullanici_db:
                        st.warning("Bu e-posta adresi sistemde zaten kayıtlı!")
                    else:
                        st.session_state.kullanici_db[kayit_email] = {"sifre": kayit_sifre, "isim": kayit_isim}
                        st.success("Kayıt başarılı, aramıza hoş geldin " + kayit_isim + "! Artık 'Giriş Yap' sekmesinden girebilirsin.")
    st.stop()

# --- 3. YAN MENÜ (SIDEBAR) ---
st.sidebar.title("FORLE TECH ERP")
st.sidebar.write("👤 **Hoş Geldin, " + st.session_state.user_name + "**")
st.sidebar.write("---")

page = st.sidebar.radio("Sayfa Seçin:", ["🏠 Ana Sayfa", "⚙️ Parça Listesi", "📱 Cihaz Listesi", "💰 Bütçe & Harcamalar"])

st.sidebar.write("---")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- 4. SAYFA İÇERİKLERİ ---
if page == "🏠 Ana Sayfa":
    st.title("FORLE TECH Şirket Portalı")
    st.info("📢 **Sistem Güncellemesi:** Yeni kullanıcı kayıt sistemi ve Harcama modülü aktif edilmiştir.")

elif page == "⚙️ Parça Listesi":
    st.subheader("⚙️ Parça Kayıt ve Envanter")
    with st.expander("➕ Yeni Parça Kaydet", expanded=True):
        with st.form("parca_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_etiket = st.text_input("Varlık Etiketi")
                p_durum = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda"])
            with c2:
                p_tarih = st.date_input("Kayıt Tarihi", datetime.date.today())
                p_notlar = st.text_area("Durum Notları")
            if st.form_submit_button("Parçayı Kaydet"):
                tarih_str = p_tarih.strftime("%d-%m-%Y")
                st.session_state.parca_listesi.append({
                    "Etiket": p_etiket,
                    "Durum": p_durum,
                    "Tarih": tarih_str,
                    "Notlar": p_notlar
                })
                st.success("Eklendi!")
    st.write("---")
    st.write("### 📋 Güncel Parça Listesi")
    if st.session_state.parca_listesi:
        st.data_editor(pd.DataFrame(st.session_state.parca_listesi), use_container_width=True, num_rows="dynamic")

elif page == "📱 Cihaz Listesi":
    st.subheader("📱 Cihaz Montaj ve Varlık Yönetimi")
    with st.expander("➕ Yeni Cihaz Kaydet", expanded=True):
        with st.form("cihaz_form"):
            c1, c2 = st.columns(2)
            with c1:
                d_adi = st.text_input("Cihaz Adı")
                d_seri = st.text_input("Cihaz Seri No")
            with c2:
                d_durum = st.selectbox("Durum", ["Aktif", "Testte", "Bakımda"])
                d_not = st.text_area("Notlar")
            if st.form_submit_button("Cihazı Kaydet"):
                st.session_state.cihaz_listesi.append({
                    "Cihaz Adı": d_adi,
                    "Seri No": d_seri,
                    "Durum": d_durum,
                    "Not": d_not
                })
                st.success("Eklendi!")
    st.write("---")
    st.write("### 🗄️ FORLE TECH Cihaz Envanteri")
    if st.session_state.cihaz_listesi:
        st.data_editor(pd.DataFrame(st.session_state.cihaz_listesi), use_container_width=True, num_rows="dynamic")

elif page == "💰 Bütçe & Harcamalar":
    st.subheader("💰 Kurumsal Harcama Takibi")
    with st.expander("➕ Yeni Harcama Fişi Gir", expanded=True):
        with st.form("harcama_formu"):
            h1, h2, h3 = st.columns(3)
            with h1:
                h_tarih = st.date_input("Harcama Tarihi", datetime.date.today())
                h_kategori = st.selectbox("Kategori", ["Ar-Ge Alımı", "Ofis Gideri", "Seyahat", "Maaş", "Diğer"])
            with h2:
                h_tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)
                h_fatura = st.text_input("Fatura/Fiş No")
            with h3:
                h_aciklama = st.text_area("Harcama Açıklaması")

            if st.form_submit_button("Harcamayı Sisteme İşle"):
                tarih_str = h_tarih.strftime("%d-%m-%Y")
                st.session_state.harcamalar.append({
                    "Tarih": tarih_str,
                    "Kategori": h_kategori,
                    "Tutar (TL)": h_tutar,
                    "Fatura No": h_fatura,
                    "Açıklama": h_aciklama,
                    "Giren Kişi": st.session_state.user_name
                })
                st.success("Harcama başarıyla eklendi!")

    st.write("---")
    st.write("### 📊 Tüm Harcamalar Listesi")
    if st.session_state.harcamalar:
        df_harcamalar = pd.DataFrame(st.session_state.harcamalar)
        st.data_editor(df_harcamalar, use_container_width=True, num_rows="dynamic")

        toplam = df_harcamalar["Tutar (TL)"].sum()
        st.metric(label="Toplam Kayıtlı Harcama", value=f"{toplam:,.2f} TL")
    else:
        st.info("Henüz sisteme işlenmiş bir harcama bulunmuyor.")
