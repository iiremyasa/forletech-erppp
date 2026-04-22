import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="FORLE TECH Portal", layout="wide")

# --- 1. KULLANICI VERİTABANI ---
# Buraya şirket çalışanlarının e-postalarını ve özel şifrelerini tanımlıyoruz.
KULLANICI_VERITABANI = {
    "yonetici@forleai.com": {"sifre": "patron123", "isim": "Yönetici Hesabı"},
    "abdullah.dogan@forleai.com": {"sifre": "arge2026", "isim": "Ar-Ge Mühendisi"},
    "mehmetcan.yidiz@forleai.com": {"sifre": "arge2026", "isim": "Ar-Ge Mühendisi"},
    "beyzanur.micik@forleai.com": {"sifre": "arge2026", "isim": "Ar-Ge Mühendisi"},
    "irem.yasa@forleai.com": {"sifre": "392682", "isim": "Proje Yöneticisi"} # BURAYI KENDİ BİLGİLERİNLE DEĞİŞTİR
}

# --- 2. GİRİŞ KONTROLÜ (Hata Payı Sıfırlanmış) ---
if not st.session_state.authenticated:
    with st.form("giris_formu"):
        # strip() ile boşlukları siliyoruz, lower() ile her şeyi küçük harf yapıyoruz
        input_email = st.text_input("E-posta").strip().lower()
        input_password = st.text_input("Şifre", type="password").strip()
        
        if st.form_submit_button("Giriş Yap"):
            # Kodun içindeki anahtarları da küçük harf yaparak kontrol ediyoruz
            bulundu = False
            for kayitli_mail, bilgiler in KULLANICI_VERITABANI.items():
                if kayitli_mail.lower() == input_email and bilgiler["sifre"] == input_password:
                    st.session_state.authenticated = True
                    st.session_state.user_name = bilgiler["isim"]
                    st.session_state.user_email = input_email
                    bulundu = True
                    st.rerun()
            
            if not bulundu:
                st.error("Giriş başarısız! Lütfen bilgilerinizi kontrol edin.")

# --- 3. HAFIZA BAŞLATMA (GİRİŞ YAPILDIKTAN SONRA) ---
if 'parca_listesi' not in st.session_state: st.session_state.parca_listesi = []
if 'cihaz_listesi' not in st.session_state: st.session_state.cihaz_listesi = []
if 'harcamalar' not in st.session_state: st.session_state.harcamalar = []


# --- 4. YAN MENÜ (SIDEBAR) ---
st.sidebar.title("FORLE TECH ERP")
st.sidebar.write(f"👤 **Hoş Geldin, {st.session_state.user_name}**")
st.sidebar.write(f"📧 *{st.session_state.user_email}*")
st.sidebar.write("---")

page = st.sidebar.radio("Sayfa Seçin:", ["🏠 Ana Sayfa", "⚙️ Parça Listesi", "📱 Cihaz Listesi"])

st.sidebar.write("---")
if st.sidebar.button("🚪 Güvenli Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- 5. SAYFA İÇERİKLERİ ---
if page == "🏠 Ana Sayfa":
    st.title("FORLE TECH Şirket Portalı")
    st.info("📢 **Duyuru:** Şirket içi ERP sistemimiz kişiye özel şifreleme altyapısına geçmiştir.")

elif page == "⚙️ Parça Listesi":
    st.subheader("⚙️ Parça Kayıt ve Envanter")
    with st.expander("➕ Yeni Parça Kaydet", expanded=True):
        with st.form("parca_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                p_etiket = st.text_input("Varlık Etiketi")
                p_model = st.text_input("Model")
                p_durum = st.selectbox("Durum", ["Aktif", "Arızalı", "Depoda"])
                p_seri = st.text_input("Seri Numarası")
            with c2:
                p_tarih = st.date_input("Son Tarih", datetime.date.today())
                p_yazilim = st.text_input("Yazılım Versiyonu")
                p_bagli = st.text_input("Bağlı Cihaz")
            with c3:
                p_renk = st.text_input("Renk")
                p_turu = st.text_input("Varlık Türü")
                p_notlar = st.text_area("Durum Notları")
            if st.form_submit_button("Parçayı Kaydet"):
                yeni_parca = {"Varlık Etiketi": p_etiket, "Model": p_model, "Durum": p_durum, "Seri No": p_seri, "Son Tarih": p_tarih.strftime("%d-%m-%Y"), "Yazılım Vers.": p_yazilim, "Bağlı Cihaz": p_bagli, "Renk": p_renk, "Tür": p_turu, "Notlar": p_notlar}
                st.session_state.parca_listesi.append(yeni_parca)
                st.success("Parça başarıyla eklendi!")
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
                d_seri = st.text_input("Cihaz Seri Numarası")
                d_turu = st.text_input("Varlık Türü")
                d_model = st.text_input("Model")
            with c2:
                d_sensor = st.text_input("Takılı Sensör")
                d_anakart = st.text_input("Takılı Anakart")
                d_modul = st.text_input("Takılı Modül")
                d_durum = st.selectbox("Durum", ["Aktif", "Testte", "Bakımda"])
            d_notlar = st.text_area("Durum Notları")
            if st.form_submit_button("Cihazı Kaydet"):
                st.session_state.cihaz_listesi.append({"Cihaz Adı": d_adi, "Seri No": d_seri, "Tür": d_turu, "Model": d_model, "Sensör": d_sensor, "Anakart": d_anakart, "Modül": d_modul, "Durum": d_durum, "Notlar": d_notlar})
                st.success("Cihaz başarıyla eklendi!")
    st.write("---")
    st.write("### 🗄️ FORLE TECH Cihaz Envanteri")
    if st.session_state.cihaz_listesi:
        st.data_editor(pd.DataFrame(st.session_state.cihaz_listesi), use_container_width=True, num_rows="dynamic")
