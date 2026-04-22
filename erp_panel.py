import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="FORLE TECH Portal", layout="wide")

# --- 1. SİSTEM HAFIZASINI BAŞLATMA ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'parca_listesi' not in st.session_state: st.session_state.parca_listesi = []
if 'cihaz_listesi' not in st.session_state: st.session_state.cihaz_listesi = []
if 'harcamalar' not in st.session_state: st.session_state.harcamalar = []

# Dinamik Kullanıcı Veritabanı (İlk açılışta boş kalmaması için bir yönetici hesabı ekliyoruz)
if 'kullanici_db' not in st.session_state:
    st.session_state.kullanici_db = {
        "irem.yasa@forleai.com": {"sifre": "392682", "isim": "Sistem Yöneticisi"}
    }

# --- 2. GİRİŞ VE KAYIT EKRANI ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color:#2c3e50;'>FORLE TECH</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Kurumsal Portal</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Ekranı Giriş Yap ve Kayıt Ol olarak iki sekmeye ayırıyoruz
        tab_giris, tab_kayit = st.tabs(["🔐 Giriş Yap", "📝 Yeni Kayıt Oluştur"])
        
        # --- GİRİŞ YAP SEKME ---
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

        # --- YENİ KAYIT OL SEKME ---
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
                        # Kullanıcıyı hafızadaki veritabanına ekle
                        st.session_state.kullanici_db[kayit_email] = {"sifre": kayit_sifre, "isim": kayit_isim}
                        st.success(f"Kayıt başarılı, aramıza hoş geldin {kayit_isim}! Artık 'Giriş Yap' sekmesinden girebilirsin.")
    st.stop()

# =========================================================================
# --- ANA SİSTEM (GİRİŞ YAPILDIKTAN SONRA) ---
# =========================================================================

# --- 3. YAN MENÜ (SIDEBAR) ---
st.sidebar.title("FORLE TECH ERP")
st.sidebar.write(f"👤 **Hoş Geldin, {st.session_state.user_name}**")
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
                p_notlar =
