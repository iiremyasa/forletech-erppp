import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="FORLE TECH Portal", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>FORLE TECH Kurumsal Giriş</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        email = st.text_input("Kurumsal E-posta (@forleai.com)")
        password = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            if email.lower().endswith("@forleai.com") and password == "forle2026":
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Yetkisiz erişim! Sadece @forleai.com uzantılı adresler girebilir.")
    st.stop()

if 'parca_listesi' not in st.session_state: st.session_state.parca_listesi = []
if 'cihaz_listesi' not in st.session_state: st.session_state.cihaz_listesi = []

st.sidebar.title("FORLE TECH ERP")
page = st.sidebar.radio("Sayfa Seçin:", ["🏠 Ana Sayfa", "⚙️ Parça Listesi", "📱 Cihaz Listesi"])

if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

if page == "🏠 Ana Sayfa":
    st.title("FORLE TECH Şirket Portalı")
    st.info("📢 **Duyuru:** NIR Sensörlerinin v2.1 yazılım güncellemeleri tüm cihazlar için zorunludur.")

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
