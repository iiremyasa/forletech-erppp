import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import hashlib
import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from contextlib import contextmanager

st.set_page_config(
    page_title="FORLE TECH | ERP Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CSS & ARAYÜZ (UI/UX) TASARIMI
# ─────────────────────────────────────────
st.markdown("""
<style>
    /* Google Fonts Entegrasyonu */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Ana Arka Plan */
    .main { background-color: transparent; }
    
    /* Sidebar Geliştirmeleri */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    
    /* Radio Butonlarını Modern Menüye Çevirme */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: all 0.2s ease;
        cursor: pointer;
        background: transparent;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255,255,255,0.08);
        transform: translateX(4px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
        display: none !important; /* Yuvarlak seçim ikonunu gizler */
    }
    
    /* Ana Sayfa Metric Kartları (Animasyonlu) */
    div[data-testid="metric-container"] {
        background: var(--background-color, white);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    
    /* Standart Butonlar */
    .stButton > button {
        background: #1e293b; color: white !important; border: 1px solid #334155; 
        border-radius: 8px; font-weight: 500; letter-spacing: 0.3px; transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #3b82f6; border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.3); transform: translateY(-1px);
    }
    
    /* Sayfa Başlığı */
    .page-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white; padding: 28px 36px; border-radius: 16px; margin-bottom: 28px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-left: 6px solid #3b82f6;
    }
    .page-header h2 { color: white; margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px;}
    .page-header p  { color: #94a3b8; margin: 6px 0 0 0; font-size: 0.95rem; font-weight: 400;}
    
    /* Yetki Rozeti */
    .role-badge {
        display: inline-block; padding: 4px 12px; border-radius: 100px;
        font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.2); color: #60a5fa !important;
        letter-spacing: 0.5px; text-transform: uppercase; margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# VERİTABANI & MAİL FONKSİYONLARI
# ─────────────────────────────────────────
DB = "forletech.db"

def mail_gonder(alici, konu, icerik):
    try:
        cfg = st.secrets["smtp"]
        server = cfg["server"]
        port = int(cfg["port"])
        email = cfg["email"]
        password = cfg["password"]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = konu
        msg["From"]    = f"FORLE TECH ERP <{email}>"
        msg["To"]      = alici

        html = MIMEText(f"""
        <div style="font-family:Arial,sans-serif;max-width:
