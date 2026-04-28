# FORLE ERP - FULL PATCHED VERSION
# Senin orijinal koduna sadık kalınarak:
# ✔ Tüm modüllere silme eklendi
# ✔ Formlar aç/kapa state ile yönetildi
# ✔ Tüm ikonlar kaldırıldı

import streamlit as st
import pandas as pd
import datetime
import hashlib
import time
from sqlalchemy import text

st.set_page_config(page_title="FORLE TECH ERP", layout="wide")

conn = st.connection("postgresql", type="sql")

# ───────── GENEL FONKSİYONLAR ─────────
def load_df(q, p=None):
    with conn.session as s:
        r = s.execute(text(q), p or {})
        rows = r.fetchall()
        return pd.DataFrame(rows, columns=r.keys()) if rows else pd.DataFrame(columns=r.keys())

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ORTAK SİLME
def kayit_sil(table, key):
    df = load_df(f"SELECT id FROM {table}")
    if not df.empty:
        sil = st.selectbox("Silinecek ID", df["id"].tolist(), key=f"{key}_sec")
        if st.button("Sil", key=f"{key}_btn"):
            with conn.session as s:
                s.execute(text(f"DELETE FROM {table} WHERE id=:i"), {"i": sil})
                s.commit()
            st.success("Silindi")
            st.rerun()

# ───────── STATE ─────────
for k in ["parca","cihaz","gorev","personel","harcama"]:
    if k not in st.session_state:
        st.session_state[k] = False

# ───────── MENU ─────────
menu = st.sidebar.radio("Menu", [
    "Ana Sayfa",
    "Parca",
    "Cihaz",
    "Gorev",
    "Personel",
    "Butce"
])

# ───────── ANA SAYFA ─────────
if menu == "Ana Sayfa":
    st.title("Dashboard")
    st.write("Sistem aktif")

# ───────── PARCA ─────────
elif menu == "Parca":
    st.title("Parca Yonetimi")

    if st.button("Yeni Parca"):
        st.session_state.parca = True

    if st.session_state.parca:
        with st.form("parca_form"):
            model = st.text_input("Model")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO parcalar (model) VALUES (:m)"), {"m": model})
                    s.commit()
                st.session_state.parca = False
                st.success("Eklendi")
                st.rerun()

    df = load_df("SELECT * FROM parcalar")
    st.dataframe(df)

    with st.expander("Sil"):
        kayit_sil("parcalar","p")

# ───────── CIHAZ ─────────
elif menu == "Cihaz":
    st.title("Cihaz Yonetimi")

    if st.button("Yeni Cihaz"):
        st.session_state.cihaz = True

    if st.session_state.cihaz:
        with st.form("cihaz_form"):
            ad = st.text_input("Ad")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO cihazlar (cihaz_adi) VALUES (:c)"), {"c": ad})
                    s.commit()
                st.session_state.cihaz = False
                st.success("Eklendi")
                st.rerun()

    df = load_df("SELECT * FROM cihazlar")
    st.dataframe(df)

    with st.expander("Sil"):
        kayit_sil("cihazlar","c")

# ───────── GOREV ─────────
elif menu == "Gorev":
    st.title("Gorevler")

    if st.button("Yeni Gorev"):
        st.session_state.gorev = True

    if st.session_state.gorev:
        with st.form("gorev_form"):
            baslik = st.text_input("Baslik")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik) VALUES (:b)"), {"b": baslik})
                    s.commit()
                st.session_state.gorev = False
                st.success("Eklendi")
                st.rerun()

    df = load_df("SELECT * FROM gorevler")
    st.dataframe(df)

    with st.expander("Sil"):
        kayit_sil("gorevler","g")

# ───────── PERSONEL ─────────
elif menu == "Personel":
    st.title("Personel")

    if st.button("Yeni Personel"):
        st.session_state.personel = True

    if st.session_state.personel:
        with st.form("per_form"):
            isim = st.text_input("Isim")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO personel (isim) VALUES (:i)"), {"i": isim})
                    s.commit()
                st.session_state.personel = False
                st.success("Eklendi")
                st.rerun()

    df = load_df("SELECT * FROM personel")
    st.dataframe(df)

    with st.expander("Sil"):
        kayit_sil("personel","per")

# ───────── BUTCE ─────────
elif menu == "Butce":
    st.title("Butce")

    if st.button("Yeni Harcama"):
        st.session_state.harcama = True

    if st.session_state.harcama:
        with st.form("harcama_form"):
            tutar = st.number_input("Tutar")
            if st.form_submit_button("Kaydet"):
                with conn.session as s:
                    s.execute(text("INSERT INTO harcamalar (tutar) VALUES (:t)"), {"t": tutar})
                    s.commit()
                st.session_state.harcama = False
                st.success("Eklendi")
                st.rerun()

    df = load_df("SELECT * FROM harcamalar")
    st.dataframe(df)

    with st.expander("Sil"):
        kayit_sil("harcamalar","h")
