import streamlit as st
import pandas as pd
import datetime
import hashlib
import random
import smtplib
import time
import io
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import text

st.set_page_config(page_title="FORLE TECH | ERP Portal", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-right: 1px solid rgba(255,255,255,0.05); }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 12px 16px; border-radius: 10px; margin-bottom: 6px; transition: all 0.2s ease; cursor: pointer; }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background-color: rgba(255,255,255,0.08); transform: translateX(5px); }
    div[data-testid="metric-container"] { background: white; border: 1px solid rgba(148,163,184,0.2); border-radius: 14px; padding: 22px; transition: all 0.3s; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); border-color: #3b82f6; }
    .page-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 30px; border-radius: 18px; margin-bottom: 30px; border-left: 8px solid #3b82f6; }
    .page-header h2 { color: white; margin: 0; }
    .page-header p { color: #94a3b8; margin: 4px 0 0 0; }
    .role-badge { display: inline-block; padding: 5px 14px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; background: rgba(59,130,246,0.25); color: #60a5fa !important; text-transform: uppercase; }
    .notif-card { background: white; border-radius: 12px; padding: 14px 18px; border-left: 4px solid #f59e0b; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
    .notif-info { border-color: #3b82f6; }
    .notif-success { border-color: #22c55e; }
    .kur-box { background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border: 1px solid #bae6fd; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ── VERİTABANI ──
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        tablolar = [
            """CREATE TABLE IF NOT EXISTS kullanicilar (id SERIAL PRIMARY KEY, email TEXT UNIQUE, sifre TEXT, isim TEXT, rol TEXT DEFAULT 'Kullanici', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS dogrulama_kodlari (id SERIAL PRIMARY KEY, email TEXT, isim TEXT, sifre TEXT, kod TEXT, gecerlilik TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS parcalar (id SERIAL PRIMARY KEY, varlik_etiketi TEXT, kayit_tarihi TEXT, model TEXT, durum TEXT, seri_no TEXT, durum_notu TEXT, yazilim_versiyonu TEXT, bagli_cihaz TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS cihazlar (id SERIAL PRIMARY KEY, cihaz_adi TEXT, ip TEXT, model TEXT, takili_sensor_seri TEXT, anakart_seri TEXT, durum TEXT, seri_no TEXT, notlar TEXT, ekleyen TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS harcamalar (id SERIAL PRIMARY KEY, tarih TEXT, kategori TEXT, tutar REAL, para_birimi TEXT DEFAULT 'TRY', tutar_usd REAL, tutar_eur REAL, kur_usd REAL, kur_eur REAL, fatura_no TEXT, aciklama TEXT, giren TEXT, belge_adi TEXT, belge_data BYTEA, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS gorevler (id SERIAL PRIMARY KEY, baslik TEXT, aciklama TEXT, atanan TEXT, durum TEXT DEFAULT 'Bekliyor', oncelik TEXT DEFAULT 'Orta', son_tarih TEXT, proje TEXT, olusturan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS personel (id SERIAL PRIMARY KEY, isim TEXT, email TEXT, pozisyon TEXT, departman TEXT, ise_baslama TEXT, telefon TEXT, notlar TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS masraf_iadeleri (id SERIAL PRIMARY KEY, talep_eden TEXT, talep_eden_email TEXT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT, fisbelge_adi TEXT, fisbelge BYTEA, durum TEXT DEFAULT 'Bekliyor', yonetici_notu TEXT, dekont_adi TEXT, dekont BYTEA, odeme_tarihi TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS bildirimler (id SERIAL PRIMARY KEY, tip TEXT, mesaj TEXT, hedef_rol TEXT DEFAULT 'Tumu', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, kullanici TEXT, aksiyon TEXT, detay TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        ]
        for t in tablolar:
            s.execute(text(t))
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        s.execute(text("INSERT INTO kullanicilar (email,sifre,isim,rol) VALUES ('admin@forleai.com',:pw,'Sistem Yöneticisi','Admin') ON CONFLICT (email) DO NOTHING"), {"pw": admin_pw})
        s.commit()

init_db()

# ── YARDIMCI FONKSİYONLAR ──
def load_df(query, params=None):
    with conn.session as s:
        res = s.execute(text(query), params or {})
        rows = res.fetchall()
        return pd.DataFrame(rows, columns=res.keys()) if rows else pd.DataFrame(columns=res.keys())

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def log_action(kullanici, aksiyon, detay=""):
    with conn.session as s:
        s.execute(text("INSERT INTO audit_log (kullanici,aksiyon,detay) VALUES (:k,:a,:d)"), {"k":kullanici,"a":aksiyon,"d":detay})
        s.commit()

def bildirim_ekle(mesaj, tip="bilgi", hedef_rol="Tumu"):
    with conn.session as s:
        s.execute(text("INSERT INTO bildirimler (tip,mesaj,hedef_rol) VALUES (:t,:m,:h)"), {"t":tip,"m":mesaj,"h":hedef_rol})
        s.commit()

def islem_basarili(msg="İşlem kaydedildi!"):
    st.toast(f"✅ {msg}", icon="✅")
    time.sleep(0.4)
    st.rerun()

def excel_export(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf.read()

def page_header(title, desc):
    st.markdown(f'<div class="page-header"><h2>{title}</h2><p>{desc}</p></div>', unsafe_allow_html=True)

def excel_import_bolumu(table, col_map, key, ekstra_cols=None):
    with st.expander("📤 Excel'den Veri Aktar", expanded=False):
        sablon = pd.DataFrame(columns=list(col_map.keys()))
        st.download_button("📥 Şablon İndir", excel_export(sablon), f"sablon_{key}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"sbl_{key}")
        dosya = st.file_uploader("Excel Yükle (.xlsx)", type=["xlsx"], key=f"upl_{key}")
        if dosya:
            try:
                df_i = pd.read_excel(dosya).rename(columns=col_map)
                df_i = df_i[[c for c in col_map.values() if c in df_i.columns]]
                if ekstra_cols:
                    for k, v in ekstra_cols.items():
                        df_i[k] = v
                st.dataframe(df_i, use_container_width=True, hide_index=True)
                if st.button("İçe Aktar", key=f"imp_{key}"):
                    with conn.session as s:
                        for _, row in df_i.iterrows():
                            cols = ", ".join(row.index)
                            vals = ", ".join([f":{c}" for c in row.index])
                            s.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"), dict(row))
                        s.commit()
                    st.success(f"{len(df_i)} kayıt eklendi.")
                    st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

@st.cache_data(ttl=3600)
def doviz_kurlari_getir():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=5)
        data = r.json()
        usd = round(1 / data["rates"]["USD"], 4)
        eur = round(1 / data["rates"]["EUR"], 4)
        return {"USD": usd, "EUR": eur, "kaynak": "ExchangeRate-API", "guncelleme": datetime.datetime.now().strftime("%H:%M")}
    except:
        return {"USD": 0.028, "EUR": 0.026, "kaynak": "Varsayılan (API erişilemedi)", "guncelleme": "—"}

def yonetici_emailleri():
    df = load_df("SELECT email FROM kullanicilar WHERE rol IN ('Admin','Yonetici')")
    return df["email"].tolist() if not df.empty else []

def mail_gonder(alici, konu, icerik):
    try:
        cfg = st.secrets["smtp"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = konu
        msg["From"] = f"FORLE TECH ERP <{cfg['email']}>"
        msg["To"] = alici
        msg.attach(MIMEText(f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#0f172a;padding:24px;border-radius:12px 12px 0 0;border-left:6px solid #3b82f6;">
                <h2 style="color:white;margin:0;">🚀 FORLE TECH</h2>
                <p style="color:#94a3b8;margin:4px 0 0;">Kurumsal ERP Sistemi</p>
            </div>
            <div style="background:white;padding:24px;border:1px solid #e2e8f0;border-radius:0 0 12px 12px;">
                {icerik}
                <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
                <p style="color:#94a3b8;font-size:0.8rem;">Bu mail otomatik gönderilmiştir.</p>
            </div>
        </div>""", "html", "utf-8"))
        with smtplib.SMTP(cfg["server"], int(cfg["port"])) as s_:
            s_.ehlo(); s_.starttls()
            s_.login(cfg["email"], cfg["password"])
            s_.sendmail(cfg["email"], alici, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Mail gönderilemedi: {e}")
        return False

# ── GİRİŞ ──
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<div style='text-align:center;padding:50px 0;'><h1 style='color:#0f172a;font-size:2.5rem;'>🚀 FORLE TECH</h1><p style='color:#64748b;'>Kurumsal ERP Portalı</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Yeni Hesap"])
        with tab1:
            with st.form("login"):
                em = st.text_input("E-posta", placeholder="isim@forleai.com").strip().lower()
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("Oturum Aç", use_container_width=True):
                    user = load_df("SELECT * FROM kullanicilar WHERE email=:em AND sifre=:pw",
                                   {"em": em, "pw": hash_pw(pw)})
                    if not user.empty:
                        st.session_state.update({"authenticated": True,
                                                  "user_name": user.iloc[0]["isim"],
                                                  "user_email": user.iloc[0]["email"],
                                                  "user_rol": user.iloc[0]["rol"]})
                        log_action(user.iloc[0]["isim"], "Giriş", em)
                        st.rerun()
                    else:
                        st.error("Hatalı bilgiler.")

        with tab2:
            if "kayit_bekliyor" not in st.session_state:
                st.session_state.kayit_bekliyor = False
            if not st.session_state.kayit_bekliyor:
                with st.form("kayit"):
                    isim   = st.text_input("Ad Soyad").strip()
                    email2 = st.text_input("E-posta (@forleai.com)").strip().lower()
                    pw2    = st.text_input("Şifre", type="password").strip()
                    pw2b   = st.text_input("Şifre Tekrar", type="password").strip()
                    if st.form_submit_button("Doğrulama Kodu Gönder", use_container_width=True):
                        if not email2.endswith("@forleai.com"):
                            st.error("Sadece @forleai.com uzantısı kabul edilir.")
                        elif pw2 != pw2b:
                            st.error("Şifreler uyuşmuyor.")
                        elif len(pw2) < 4:
                            st.error("Şifre çok kısa.")
                        else:
                            mevcut = load_df("SELECT id FROM kullanicilar WHERE email=:e", {"e": email2})
                            if not mevcut.empty:
                                st.warning("Bu e-posta zaten kayıtlı.")
                            else:
                                kod = str(random.randint(100000, 999999))
                                gec = datetime.datetime.now() + datetime.timedelta(minutes=10)
                                with conn.session as s:
                                    s.execute(text("DELETE FROM dogrulama_kodlari WHERE email=:e"), {"e": email2})
                                    s.execute(text("INSERT INTO dogrulama_kodlari (email,isim,sifre,kod,gecerlilik) VALUES (:e,:i,:s,:k,:g)"),
                                              {"e": email2, "i": isim, "s": hash_pw(pw2), "k": kod, "g": gec})
                                    s.commit()
                                ok = mail_gonder(email2, "FORLE TECH ERP — Doğrulama Kodunuz",
                                    f"""<p>Merhaba <b>{isim}</b>,</p>
                                    <div style="background:#f0f4ff;border-radius:12px;padding:24px;text-align:center;margin:20px 0;">
                                        <span style="font-size:2.5rem;font-weight:800;letter-spacing:0.3em;color:#0f172a;">{kod}</span>
                                    </div>
                                    <p style="color:#64748b;">Bu kod <b>10 dakika</b> geçerlidir.</p>""")
                                if ok:
                                    st.session_state.kayit_bekliyor = True
                                    st.session_state.kayit_email = email2
                                    st.rerun()
            else:
                st.info(f"**{st.session_state.kayit_email}** adresine 6 haneli kod gönderildi.")
                with st.form("dogrulama"):
                    girilen = st.text_input("Doğrulama Kodu", max_chars=6).strip()
                    c1, c2 = st.columns(2)
                    onayla = c1.form_submit_button("Onayla", use_container_width=True)
                    iptal  = c2.form_submit_button("İptal",  use_container_width=True)
                    if onayla:
                        kayit = load_df("SELECT * FROM dogrulama_kodlari WHERE email=:e AND kod=:k",
                                        {"e": st.session_state.kayit_email, "k": girilen})
                        if kayit.empty:
                            st.error("Hatalı kod!")
                        elif datetime.datetime.now() > pd.to_datetime(kayit.iloc[0]["gecerlilik"]):
                            st.error("Kodun süresi dolmuş.")
                            st.session_state.kayit_bekliyor = False
                            st.rerun()
                        else:
                            with conn.session as s:
                                s.execute(text("INSERT INTO kullanicilar (email,sifre,isim) VALUES (:e,:s,:i) ON CONFLICT (email) DO NOTHING"),
                                          {"e": kayit.iloc[0]["email"], "s": kayit.iloc[0]["sifre"], "i": kayit.iloc[0]["isim"]})
                                s.execute(text("DELETE FROM dogrulama_kodlari WHERE email=:e"), {"e": kayit.iloc[0]["email"]})
                                s.commit()
                            st.session_state.kayit_bekliyor = False
                            st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
                            st.rerun()
                    if iptal:
                        st.session_state.kayit_bekliyor = False
                        st.rerun()
    st.stop()

# ── SIDEBAR ──
USER_ROL = st.session_state.user_rol
IS_YONETICI = USER_ROL in ["Admin", "Yönetici"]
IS_MUHENDIS = USER_ROL == "Elektrik Elektronik Mühendisi"

with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("<div style='text-align:center;padding:8px 0;font-size:1.5rem;font-weight:800;color:white;'>🚀 FORLE TECH</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.07);border-radius:10px;padding:12px;margin:8px 0 16px;text-align:center;'>
        <div style='font-weight:600;font-size:0.95rem;'>{st.session_state.user_name}</div>
        <div style='font-size:0.72rem;color:#94a3b8;margin-bottom:6px;'>{st.session_state.user_email}</div>
        <span class='role-badge'>{USER_ROL}</span>
    </div>""", unsafe_allow_html=True)

    menuler = ["📊 Ana Sayfa", "📦 Parça Yönetimi", "💻 Cihaz Yönetimi", "🧾 Masraf Beyanı", "📋 Görevler", "⚙️ Ayarlar"]
    if IS_YONETICI:
        menuler.insert(3, "💰 Kurumsal Bütçe")
        menuler += ["👥 Personel", "✅ Onay Paneli", "🛡️ Audit Log", "🔑 Yetkiler"]

    # Okunmamış bildirim sayısı
    try:
        notif_df = load_df("SELECT COUNT(*) as n FROM bildirimler")
        n_notif = int(notif_df.iloc[0]["n"]) if not notif_df.empty else 0
    except:
        n_notif = 0
    if n_notif > 0:
        st.markdown(f"<div style='background:rgba(245,158,11,0.2);border-radius:8px;padding:8px 12px;border-left:3px solid #f59e0b;margin-bottom:10px;font-size:0.82rem;color:#fcd34d;'>🔔 {n_notif} okunmamış bildirim</div>", unsafe_allow_html=True)

    page = st.radio("Menü", menuler, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        log_action(st.session_state.user_name, "Çıkış")
        st.session_state.authenticated = False
        st.rerun()

# ══════════════════════════════════════════
# ANA SAYFA
# ══════════════════════════════════════════
if page == "📊 Ana Sayfa":
    page_header("Kontrol Paneli", "Operasyonel Özet")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("📦 Parça",    load_df("SELECT COUNT(*) as n FROM parcalar").iloc[0,0])
    c2.metric("💻 Cihaz",    load_df("SELECT COUNT(*) as n FROM cihazlar").iloc[0,0])
    c3.metric("📋 Görev",    load_df("SELECT COUNT(*) as n FROM gorevler WHERE durum!='Tamamlandı'").iloc[0,0])
    c4.metric("👥 Personel", load_df("SELECT COUNT(*) as n FROM personel").iloc[0,0])
    masraf_bekleyen = load_df("SELECT COUNT(*) as n FROM masraf_iadeleri WHERE durum='Bekliyor'").iloc[0,0]
    c5.metric("🧾 Masraf Bekleyen", masraf_bekleyen)

    st.markdown("<br>", unsafe_allow_html=True)

    # Grafikler
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Parça Durum Dağılımı")
        df_p = load_df("SELECT durum, COUNT(*) as adet FROM parcalar GROUP BY durum")
        if not df_p.empty:
            st.bar_chart(df_p.set_index("durum"), color="#3b82f6")
        else:
            st.info("Veri yok.")
    with col_b:
        st.markdown("#### Görev Durumu")
        df_g = load_df("SELECT durum, COUNT(*) as adet FROM gorevler GROUP BY durum")
        if not df_g.empty:
            st.bar_chart(df_g.set_index("durum"), color="#6366f1")
        else:
            st.info("Veri yok.")

    # Bildirimler
    st.markdown("#### 🔔 Bildirimler")
    df_notif = load_df("SELECT * FROM bildirimler ORDER BY created_at DESC LIMIT 20")
    if not df_notif.empty:
        for _, b in df_notif.iterrows():
            tip_class = {"bilgi":"notif-card notif-info","uyari":"notif-card","basari":"notif-card notif-success"}.get(b["tip"],"notif-card")
            ikon = {"bilgi":"ℹ️","uyari":"⚠️","basari":"✅"}.get(b["tip"],"📌")
            col_msg, col_del = st.columns([9,1])
            with col_msg:
                st.markdown(f"<div class='{tip_class}'>{ikon} {b['mesaj']} <span style='color:#94a3b8;font-size:0.75rem;float:right;'>{str(b['created_at'])[:16]}</span></div>", unsafe_allow_html=True)
            with col_del:
                if st.button("✕", key=f"del_n_{b['id']}"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM bildirimler WHERE id=:i"), {"i": b["id"]})
                        s.commit()
                    st.rerun()
        if st.button("Tümünü Temizle"):
            with conn.session as s:
                s.execute(text("DELETE FROM bildirimler"))
                s.commit()
            st.rerun()
    else:
        st.success("Bildirim yok, her şey yolunda! ✅")

# ══════════════════════════════════════════
# PARÇA YÖNETİMİ
# ══════════════════════════════════════════
elif page == "📦 Parça Yönetimi":
    page_header("Parça Yönetimi", "Varlık ve Ar-Ge Envanteri")

    # Sadece Admin, Yönetici ve Mühendis ekleyebilir
    if IS_YONETICI or IS_MUHENDIS:
        with st.expander("➕ Yeni Parça Ekle", expanded=False):
            with st.form("p_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ve = c1.text_input("Varlık Etiketi"); mo = c1.text_input("Model")
                du = c1.selectbox("Durum", ["Aktif","Arızalı","Depoda","Hurda"]); sn = c1.text_input("Seri No")
                yv = c2.text_input("Yazılım Versiyonu"); bc = c2.text_input("Bağlı Cihaz")
                dn = c2.text_area("Durum Notu"); kt = c2.date_input("Kayıt Tarihi")
                if st.form_submit_button("Kaydet", use_container_width=True):
                    with conn.session as s:
                        s.execute(text("""INSERT INTO parcalar (varlik_etiketi,model,durum,seri_no,yazilim_versiyonu,
                                         bagli_cihaz,durum_notu,kayit_tarihi,ekleyen)
                                         VALUES (:ve,:mo,:du,:sn,:yv,:bc,:dn,:kt,:ek)"""),
                                  {"ve":ve,"mo":mo,"du":du,"sn":sn,"yv":yv,"bc":bc,"dn":dn,"kt":str(kt),"ek":st.session_state.user_name})
                        s.commit()
                    log_action(st.session_state.user_name, "Parça Eklendi", ve)
                    bildirim_ekle(f"{st.session_state.user_name} yeni parça ekledi: {ve}", "bilgi", "Admin")
                    islem_basarili("Parça eklendi!")

        excel_import_bolumu("parcalar", {
            "Varlık Etiketi":"varlik_etiketi","Model":"model","Durum":"durum","Seri No":"seri_no",
            "Yazılım Versiyonu":"yazilim_versiyonu","Bağlı Cihaz":"bagli_cihaz","Durum Notu":"durum_notu","Kayıt Tarihi":"kayit_tarihi"
        }, "parca", {"ekleyen": st.session_state.user_name})

    # Arama & Filtre
    col_ara, col_f = st.columns([2,1])
    with col_ara: ara = st.text_input("🔍 Ara", placeholder="Etiket, model, seri no...", key="p_ara")
    with col_f: df_f = st.selectbox("Durum Filtrele", ["Tümü","Aktif","Arızalı","Depoda","Hurda"])

    df = load_df("SELECT * FROM parcalar ORDER BY id DESC")
    if not df.empty:
        if ara: df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if df_f != "Tümü": df = df[df["durum"] == df_f]

        # Özet metrikler
        df_all = load_df("SELECT durum FROM parcalar")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Aktif",   len(df_all[df_all["durum"]=="Aktif"]))
        m2.metric("Arızalı", len(df_all[df_all["durum"]=="Arızalı"]))
        m3.metric("Depoda",  len(df_all[df_all["durum"]=="Depoda"]))
        m4.metric("Hurda",   len(df_all[df_all["durum"]=="Hurda"]))
        st.markdown("<br>", unsafe_allow_html=True)

        disp = df.drop(columns=["id","created_at"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "parcalar.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Silme — sadece Admin ve Yönetici
        if IS_YONETICI or IS_MUHENDIS:
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Parça ID", df["id"].tolist(), key="p_sil")
                if st.button("Seçili Kaydı Sil", key="p_sil_btn"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM parcalar WHERE id=:i"), {"i": sil_id})
                        s.commit()
                    log_action(st.session_state.user_name, "Parça Silindi", f"ID:{sil_id}")
                    islem_basarili("Parça silindi!")
    else:
        st.info("Henüz parça eklenmemiş.")

# ══════════════════════════════════════════
# CİHAZ YÖNETİMİ
# ══════════════════════════════════════════
elif page == "💻 Cihaz Yönetimi":
    page_header("Cihaz Yönetimi", "Donanım İzleme")

    if IS_YONETICI or IS_MUHENDIS:
        with st.expander("➕ Yeni Cihaz Ekle", expanded=False):
            with st.form("c_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ca = c1.text_input("Cihaz Adı"); ip = c1.text_input("IP Adresi")
                mo = c1.text_input("Model"); du = c1.selectbox("Durum", ["Aktif","Testte","Bakımda","Depoda"])
                ss = c2.text_input("Sensör Seri No"); ak = c2.text_input("Anakart Seri No")
                sn = c2.text_input("Seri No"); nt = c2.text_area("Notlar")
                if st.form_submit_button("Kaydet", use_container_width=True):
                    with conn.session as s:
                        s.execute(text("""INSERT INTO cihazlar (cihaz_adi,ip,model,takili_sensor_seri,
                                         anakart_seri,durum,seri_no,notlar,ekleyen)
                                         VALUES (:ca,:ip,:mo,:ss,:ak,:du,:sn,:nt,:ek)"""),
                                  {"ca":ca,"ip":ip,"mo":mo,"ss":ss,"ak":ak,"du":du,"sn":sn,"nt":nt,"ek":st.session_state.user_name})
                        s.commit()
                    log_action(st.session_state.user_name, "Cihaz Eklendi", ca)
                    bildirim_ekle(f"{st.session_state.user_name} yeni cihaz ekledi: {ca}", "bilgi", "Admin")
                    islem_basarili("Cihaz eklendi!")

        excel_import_bolumu("cihazlar", {
            "Cihaz Adı":"cihaz_adi","IP":"ip","Model":"model","Sensör Seri":"takili_sensor_seri",
            "Anakart Seri":"anakart_seri","Durum":"durum","Seri No":"seri_no","Notlar":"notlar"
        }, "cihaz", {"ekleyen": st.session_state.user_name})

    col_ara, col_f = st.columns([2,1])
    with col_ara: ara = st.text_input("🔍 Ara", key="c_ara")
    with col_f: df_f = st.selectbox("Durum", ["Tümü","Aktif","Testte","Bakımda","Depoda"])

    df = load_df("SELECT * FROM cihazlar ORDER BY id DESC")
    if not df.empty:
        if ara: df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if df_f != "Tümü": df = df[df["durum"] == df_f]
        disp = df.drop(columns=["id","created_at"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "cihazlar.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if IS_YONETICI or IS_MUHENDIS:
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Cihaz ID", df["id"].tolist(), key="c_sil")
                if st.button("Seçili Kaydı Sil", key="c_sil_btn"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM cihazlar WHERE id=:i"), {"i": sil_id})
                        s.commit()
                    log_action(st.session_state.user_name, "Cihaz Silindi", f"ID:{sil_id}")
                    islem_basarili("Cihaz silindi!")
    else:
        st.info("Henüz cihaz eklenmemiş.")

# ══════════════════════════════════════════
# KURUMSAL BÜTÇE
# ══════════════════════════════════════════
elif page == "💰 Kurumsal Bütçe":
    page_header("Kurumsal Bütçe", "Şirket Harcamaları")

    # Döviz Kuru Bilgisi
    kurlar = doviz_kurlari_getir()
    st.markdown(f"""
    <div class='kur-box'>
        <b>💱 Anlık Döviz Kurları</b> &nbsp;|&nbsp; 
        1 TL = <b>${kurlar['USD']}</b> USD &nbsp;|&nbsp; 
        1 TL = <b>€{kurlar['EUR']}</b> EUR &nbsp;|&nbsp;
        <span style='color:#64748b;font-size:0.8rem;'>Kaynak: {kurlar['kaynak']} | {kurlar['guncelleme']}</span>
    </div>""", unsafe_allow_html=True)

    with st.expander("➕ Yeni Harcama Girişi", expanded=False):
        with st.form("h_form", clear_on_submit=True):
            h1, h2, h3 = st.columns(3)
            with h1:
                h_tarih = st.date_input("Tarih", datetime.date.today())
                h_kat   = st.selectbox("Kategori", ["Ar-Ge Alımı","Ofis Gideri","Seyahat","Maaş","Diğer"])
            with h2:
                h_pb    = st.selectbox("Para Birimi", ["TRY (₺)","USD ($)","EUR (€)"])
                h_tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
            with h3:
                h_fatura = st.text_input("Fatura / Fiş No")
                h_acik   = st.text_area("Açıklama")
            h_belge = st.file_uploader("Belge Ekle (opsiyonel)", type=["pdf","jpg","jpeg","png"])

            if st.form_submit_button("Kaydet", use_container_width=True):
                pb_kod = h_pb.split(" ")[0]
                # Tutarı TL'ye çevir
                if pb_kod == "TRY":
                    tutar_tl = h_tutar
                elif pb_kod == "USD":
                    tutar_tl = h_tutar / kurlar["USD"]
                else:
                    tutar_tl = h_tutar / kurlar["EUR"]

                tutar_usd = tutar_tl * kurlar["USD"]
                tutar_eur = tutar_tl * kurlar["EUR"]

                belge_d = h_belge.read() if h_belge else None
                belge_a = h_belge.name  if h_belge else None

                with conn.session as s:
                    s.execute(text("""INSERT INTO harcamalar
                        (tarih,kategori,tutar,para_birimi,tutar_usd,tutar_eur,kur_usd,kur_eur,
                         fatura_no,aciklama,giren,belge_adi,belge_data)
                        VALUES (:t,:k,:tu,:pb,:tusd,:teur,:kusd,:keur,:f,:a,:g,:ba,:bd)"""),
                        {"t":str(h_tarih),"k":h_kat,"tu":tutar_tl,"pb":pb_kod,
                         "tusd":round(tutar_usd,2),"teur":round(tutar_eur,2),
                         "kusd":kurlar["USD"],"keur":kurlar["EUR"],
                         "f":h_fatura,"a":h_acik,"g":st.session_state.user_name,
                         "ba":belge_a,"bd":belge_d})
                    s.commit()
                log_action(st.session_state.user_name, "Harcama Eklendi", f"{h_kat} - {h_tutar} {pb_kod}")
                islem_basarili("Harcama kaydedildi!")

    excel_import_bolumu("harcamalar", {
        "Tarih":"tarih","Kategori":"kategori","Tutar (TL)":"tutar","Para Birimi":"para_birimi",
        "Fatura No":"fatura_no","Açıklama":"aciklama"
    }, "harcama", {"giren": st.session_state.user_name})

    st.markdown("---")
    df = load_df("SELECT id,tarih,kategori,tutar,para_birimi,tutar_usd,tutar_eur,kur_usd,fatura_no,aciklama,giren FROM harcamalar ORDER BY id DESC")
    if not df.empty:
        # Özet
        toplam_tl  = df["tutar"].sum()
        toplam_usd = df["tutar_usd"].sum() if "tutar_usd" in df.columns else 0
        toplam_eur = df["tutar_eur"].sum() if "tutar_eur" in df.columns else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Toplam (₺)", f"{toplam_tl:,.2f} ₺")
        c2.metric("Toplam ($)", f"${toplam_usd:,.2f}")
        c3.metric("Toplam (€)", f"€{toplam_eur:,.2f}")
        st.markdown("<br>", unsafe_allow_html=True)

        # Filtre
        col_ara, col_f = st.columns([2,1])
        with col_ara: ara = st.text_input("🔍 Ara", key="h_ara")
        with col_f: kat_f = st.selectbox("Kategori", ["Tümü","Ar-Ge Alımı","Ofis Gideri","Seyahat","Maaş","Diğer"])
        if ara: df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        if kat_f != "Tümü": df = df[df["kategori"] == kat_f]

        disp = df.drop(columns=["id"], errors="ignore")
        disp.columns = ["Tarih","Kategori","Tutar (₺)","Para Birimi","Tutar ($)","Tutar (€)","USD Kuru","Fatura No","Açıklama","Giren"]
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "butce.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if IS_YONETICI:
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek ID", df["id"].tolist() if "id" in df.columns else [], key="h_sil")
                if st.button("Sil", key="h_sil_btn"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM harcamalar WHERE id=:i"), {"i": sil_id})
                        s.commit()
                    islem_basarili("Kayıt silindi!")
    else:
        st.info("Henüz harcama kaydı yok.")

# ══════════════════════════════════════════
# MASRAF BEYANI
# ══════════════════════════════════════════
elif page == "🧾 Masraf Beyanı":
    page_header("Masraf Beyanı", "Bireysel Harcama İade Talebi")
    is_yon = IS_YONETICI
    tab1, tab2 = st.tabs(["📤 Talebim", "🗂️ Yönetim Paneli"])

    with tab1:
        with st.expander("➕ Yeni Masraf Talebi", expanded=True):
            with st.form("m_form"):
                m1, m2 = st.columns(2)
                with m1:
                    m_tarih = st.date_input("Harcama Tarihi", datetime.date.today())
                    m_kat   = st.selectbox("Kategori", ["Yemek","Ulaşım","Konaklama","Ofis Malzemesi","Müşteri Ağırlama","Eğitim","Diğer"])
                    m_tutar = st.number_input("Tutar (₺)", min_value=0.0, step=10.0)
                with m2:
                    m_acik  = st.text_area("Açıklama", height=100)
                    m_dosya = st.file_uploader("Fiş / Fatura", type=["jpg","jpeg","png","pdf"])
                if st.form_submit_button("Onaya Gönder", use_container_width=True):
                    if m_tutar <= 0:
                        st.error("Tutar 0'dan büyük olmalı.")
                    else:
                        d_data = m_dosya.read() if m_dosya else None
                        d_adi  = m_dosya.name  if m_dosya else None
                        with conn.session as s:
                            s.execute(text("""INSERT INTO masraf_iadeleri
                                (talep_eden,talep_eden_email,tarih,kategori,tutar,aciklama,fisbelge_adi,fisbelge)
                                VALUES (:te,:tee,:t,:k,:tu,:a,:da,:dd)"""),
                                {"te":st.session_state.user_name,"tee":st.session_state.user_email,
                                 "t":str(m_tarih),"k":m_kat,"tu":m_tutar,"a":m_acik,"da":d_adi,"dd":d_data})
                            s.commit()
                        log_action(st.session_state.user_name, "Masraf Talebi", f"{m_kat} - {m_tutar}₺")
                        for ym in yonetici_emailleri():
                            mail_gonder(ym, "Yeni Masraf İade Talebi",
                                f"""<p><b>{st.session_state.user_name}</b> masraf talebi gönderdi:</p>
                                <p><b>Kategori:</b> {m_kat} | <b>Tutar:</b> {m_tutar:,.2f}₺</p>""")
                        bildirim_ekle(f"{st.session_state.user_name} masraf talebi gönderdi ({m_tutar:,.0f}₺)", "uyari", "Admin")
                        islem_basarili("Talep gönderildi!")

        df = load_df("SELECT tarih,kategori,tutar,aciklama,durum,yonetici_notu,odeme_tarihi FROM masraf_iadeleri WHERE talep_eden_email=:e ORDER BY id DESC",
                     {"e": st.session_state.user_email})
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 Excel İndir", excel_export(df), "masraf_taleplerim.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Henüz masraf talebiniz yok.")

    with tab2:
        if not is_yon:
            st.warning("Bu sekmeye sadece yöneticiler erişebilir.")
        else:
            df = load_df("SELECT * FROM masraf_iadeleri ORDER BY id DESC")
            if df.empty:
                st.info("Henüz talep yok.")
            else:
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Toplam", len(df))
                c2.metric("Bekleyen", len(df[df["durum"]=="Bekliyor"]))
                c3.metric("Onaylanan", len(df[df["durum"]=="Onaylandı"]))
                c4.metric("Ödenen", f"{df[df['durum']=='Ödendi']['tutar'].sum():,.0f}₺")
                st.markdown("---")

                filtre = st.selectbox("Durum", ["Tümü","Bekliyor","Onaylandı","Reddedildi","Ödendi"])
                goster = df if filtre == "Tümü" else df[df["durum"]==filtre]

                for _, r in goster.iterrows():
                    dr = {"Bekliyor":"#f59e0b","Onaylandı":"#3b82f6","Reddedildi":"#ef4444","Ödendi":"#22c55e"}.get(r["durum"],"#64748b")
                    st.markdown(f"""
                    <div style='background:white;border-radius:12px;padding:16px 20px;border:1px solid #e2e8f0;
                                margin-bottom:10px;border-left:4px solid {dr};'>
                        <div style='display:flex;justify-content:space-between;'>
                            <b>{r['talep_eden']}</b>
                            <span style='background:{dr};color:white;padding:2px 12px;border-radius:100px;font-size:0.75rem;'>{r['durum']}</span>
                        </div>
                        <div style='color:#64748b;font-size:0.85rem;margin-top:4px;'>
                            {r['kategori']} | {r['tutar']:,.2f}₺ | {str(r['tarih'])[:10]}
                        </div>
                        <div style='color:#475569;font-size:0.85rem;'>{r['aciklama'] or ''}</div>
                    </div>""", unsafe_allow_html=True)

                    if r["durum"] == "Bekliyor":
                        col_not, col_on, col_red = st.columns([3,1,1])
                        with col_not: yon_not = st.text_input("Not", key=f"mn_{r['id']}")
                        with col_on:
                            if st.button("✅ Onayla", key=f"mon_{r['id']}"):
                                with conn.session as s:
                                    s.execute(text("UPDATE masraf_iadeleri SET durum='Onaylandı',yonetici_notu=:n WHERE id=:i"),
                                              {"n": yon_not, "i": r["id"]})
                                    s.commit()
                                mail_gonder(r["talep_eden_email"], "Masraf Talebiniz Onaylandı ✅",
                                    f"""<p>Merhaba <b>{r['talep_eden']}</b>,<br>
                                    <b>{r['tutar']:,.2f}₺</b> tutarındaki talebiniz onaylandı.</p>
                                    {f"<p>Not: {yon_not}</p>" if yon_not else ""}""")
                                log_action(st.session_state.user_name, "Masraf Onaylandı", f"ID:{r['id']}")
                                st.rerun()
                        with col_red:
                            if st.button("❌ Reddet", key=f"mred_{r['id']}"):
                                with conn.session as s:
                                    s.execute(text("UPDATE masraf_iadeleri SET durum='Reddedildi',yonetici_notu=:n WHERE id=:i"),
                                              {"n": yon_not, "i": r["id"]})
                                    s.commit()
                                mail_gonder(r["talep_eden_email"], "Masraf Talebiniz Reddedildi",
                                    f"""<p>Merhaba <b>{r['talep_eden']}</b>,<br>
                                    <b>{r['tutar']:,.2f}₺</b> tutarındaki talebiniz reddedildi.</p>
                                    {f"<p>Neden: {yon_not}</p>" if yon_not else ""}""")
                                log_action(st.session_state.user_name, "Masraf Reddedildi", f"ID:{r['id']}")
                                st.rerun()

                    elif r["durum"] == "Onaylandı":
                        dekont_f = st.file_uploader("Dekont Yükle", type=["jpg","jpeg","png","pdf"], key=f"dek_{r['id']}")
                        if dekont_f and st.button("💰 Ödendi Olarak İşaretle", key=f"ode_{r['id']}"):
                            odeme_t = str(datetime.date.today())
                            with conn.session as s:
                                s.execute(text("UPDATE masraf_iadeleri SET durum='Ödendi',dekont=:d,dekont_adi=:da,odeme_tarihi=:ot WHERE id=:i"),
                                          {"d": dekont_f.read(), "da": dekont_f.name, "ot": odeme_t, "i": r["id"]})
                                s.commit()
                            mail_gonder(r["talep_eden_email"], "Masraf İadeniz Ödendi 💰",
                                f"""<p>Merhaba <b>{r['talep_eden']}</b>,<br>
                                <b>{r['tutar']:,.2f}₺</b> tutarındaki masraf iadeniz ödendi.<br>
                                Ödeme Tarihi: <b>{odeme_t}</b></p>""")
                            bildirim_ekle(f"{r['talep_eden']} masraf iadesi ödendi ({r['tutar']:,.0f}₺)", "basari", "Tumu")
                            log_action(st.session_state.user_name, "Masraf Ödendi", f"ID:{r['id']}, {r['tutar']}₺")
                            st.rerun()
                    st.markdown("---")

                exp_df = goster[["talep_eden","tarih","kategori","tutar","durum","yonetici_notu","odeme_tarihi"]].copy()
                exp_df.columns = ["Çalışan","Tarih","Kategori","Tutar (₺)","Durum","Yönetici Notu","Ödeme Tarihi"]
                st.download_button("📥 Excel İndir", excel_export(exp_df), "masraf_iadeleri.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════
# GÖREVLER
# ══════════════════════════════════════════
elif page == "📋 Görevler":
    page_header("Proje & Görev Takibi", "Kanban Board")
    with st.expander("➕ Yeni Görev", expanded=False):
        with st.form("g_form", clear_on_submit=True):
            g1, g2 = st.columns(2)
            gb = g1.text_input("Görev Başlığı"); gp = g1.text_input("Proje"); ga = g1.text_input("Atanan")
            go = g2.selectbox("Öncelik", ["Düşük","Orta","Yüksek","Kritik"])
            gd = g2.selectbox("Durum", ["Bekliyor","Devam Ediyor","İncelemede","Tamamlandı"])
            gt = g2.date_input("Son Tarih"); gac = st.text_area("Açıklama")
            if st.form_submit_button("Ekle", use_container_width=True):
                with conn.session as s:
                    s.execute(text("INSERT INTO gorevler (baslik,aciklama,atanan,durum,oncelik,son_tarih,proje,olusturan) VALUES (:b,:ac,:a,:d,:o,:t,:p,:ok)"),
                              {"b":gb,"ac":gac,"a":ga,"d":gd,"o":go,"t":str(gt),"p":gp,"ok":st.session_state.user_name})
                    s.commit()
                log_action(st.session_state.user_name, "Görev Eklendi", gb)
                islem_basarili("Görev eklendi!")

    excel_import_bolumu("gorevler", {
        "Başlık":"baslik","Proje":"proje","Atanan":"atanan",
        "Öncelik":"oncelik","Durum":"durum","Son Tarih":"son_tarih","Açıklama":"aciklama"
    }, "gorev", {"olusturan": st.session_state.user_name})

    df = load_df("SELECT * FROM gorevler ORDER BY id DESC")
    if not df.empty:
        st.markdown("#### Kanban")
        renk = {"Düşük":"#22c55e","Orta":"#f59e0b","Yüksek":"#ef4444","Kritik":"#7c3aed"}
        k_cols = st.columns(4)
        for i, durum in enumerate(["Bekliyor","Devam Ediyor","İncelemede","Tamamlandı"]):
            with k_cols[i]:
                st.markdown(f"**{durum}**")
                for _, g in df[df["durum"]==durum].iterrows():
                    r = renk.get(g["oncelik"],"#64748b")
                    st.markdown(f"""
                    <div style='background:white;border-radius:10px;padding:12px;margin-bottom:8px;
                                border-left:4px solid {r};box-shadow:0 1px 4px rgba(0,0,0,0.08)'>
                        <div style='font-weight:600;font-size:0.88rem;'>{g['baslik']}</div>
                        <div style='font-size:0.75rem;color:#64748b;margin-top:4px;'>
                            👤 {g['atanan'] or '—'} | 📅 {str(g['son_tarih'])[:10] if g['son_tarih'] else '—'}
                        </div>
                    </div>""", unsafe_allow_html=True)
        st.markdown("---")
        disp = df.drop(columns=["id","created_at"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "gorevler.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if IS_YONETICI:
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Görev ID", df["id"].tolist(), key="g_sil")
                if st.button("Sil", key="g_sil_btn"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM gorevler WHERE id=:i"), {"i": sil_id})
                        s.commit()
                    islem_basarili("Görev silindi!")
    else:
        st.info("Henüz görev yok.")

# ══════════════════════════════════════════
# PERSONEL
# ══════════════════════════════════════════
elif page == "👥 Personel":
    page_header("İnsan Kaynakları", "Personel Listesi")
    with st.expander("➕ Yeni Personel Ekle", expanded=False):
        with st.form("per_form", clear_on_submit=True):
            p1, p2 = st.columns(2)
            pi = p1.text_input("Ad Soyad"); pe = p1.text_input("E-posta"); pt = p1.text_input("Telefon")
            pp = p2.text_input("Pozisyon")
            pd_ = p2.selectbox("Departman", ["Yazılım","Donanım","Ar-Ge","Yönetim","Satış","Diğer"])
            pb = p2.date_input("İşe Başlama"); pn = st.text_area("Notlar")
            if st.form_submit_button("Kaydet", use_container_width=True):
                with conn.session as s:
                    s.execute(text("INSERT INTO personel (isim,email,pozisyon,departman,ise_baslama,telefon,notlar) VALUES (:i,:e,:p,:d,:b,:t,:n)"),
                              {"i":pi,"e":pe,"p":pp,"d":pd_,"b":str(pb),"t":pt,"n":pn})
                    s.commit()
                log_action(st.session_state.user_name, "Personel Eklendi", pi)
                islem_basarili("Personel eklendi!")

    excel_import_bolumu("personel", {
        "Ad Soyad":"isim","E-posta":"email","Pozisyon":"pozisyon",
        "Departman":"departman","İşe Başlama":"ise_baslama","Telefon":"telefon","Notlar":"notlar"
    }, "personel")

    df = load_df("SELECT * FROM personel ORDER BY id DESC")
    if not df.empty:
        disp = df.drop(columns=["id","created_at"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "personel.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if IS_YONETICI:
            with st.expander("🗑️ Kayıt Sil"):
                sil_id = st.selectbox("Silinecek Personel ID", df["id"].tolist(), key="per_sil")
                if st.button("Sil", key="per_sil_btn"):
                    with conn.session as s:
                        s.execute(text("DELETE FROM personel WHERE id=:i"), {"i": sil_id})
                        s.commit()
                    islem_basarili("Personel silindi!")
    else:
        st.info("Henüz personel eklenmemiş.")

# ══════════════════════════════════════════
# ONAY PANELİ
# ══════════════════════════════════════════
elif page == "✅ Onay Paneli":
    page_header("Onay Paneli", "Masraf Onayları")
    df = load_df("SELECT * FROM masraf_iadeleri WHERE durum='Bekliyor' ORDER BY id DESC")
    if not df.empty:
        for _, row in df.iterrows():
            col_info, col_not, col_on, col_red = st.columns([3,3,1,1])
            with col_info:
                st.markdown(f"**{row['talep_eden']}** — {row['tutar']:,.2f}₺ — {row['kategori']}")
                st.caption(f"{row['aciklama'] or ''}")
            with col_not:
                not_ = st.text_input("Yönetici Notu", key=f"n_{row['id']}")
            with col_on:
                if st.button("✅ Onayla", key=f"o_{row['id']}"):
                    with conn.session as s:
                        s.execute(text("UPDATE masraf_iadeleri SET durum='Onaylandı',yonetici_notu=:n WHERE id=:i"),
                                  {"n":not_,"i":row["id"]})
                        s.commit()
                    mail_gonder(row["talep_eden_email"], "Masraf Talebiniz Onaylandı ✅",
                        f"<p>Merhaba <b>{row['talep_eden']}</b>, {row['tutar']:,.2f}₺ tutarındaki talebiniz onaylandı.</p>")
                    log_action(st.session_state.user_name, "Masraf Onaylandı", f"ID:{row['id']}")
                    st.rerun()
            with col_red:
                if st.button("❌ Reddet", key=f"r_{row['id']}"):
                    with conn.session as s:
                        s.execute(text("UPDATE masraf_iadeleri SET durum='Reddedildi',yonetici_notu=:n WHERE id=:i"),
                                  {"n":not_,"i":row["id"]})
                        s.commit()
                    log_action(st.session_state.user_name, "Masraf Reddedildi", f"ID:{row['id']}")
                    st.rerun()
            st.markdown("---")
    else:
        st.success("✅ Bekleyen masraf talebi yok!")

# ══════════════════════════════════════════
# AUDİT LOG
# ══════════════════════════════════════════
elif page == "🛡️ Audit Log":
    page_header("Audit Log", "Sistem İşlem Geçmişi")
    df = load_df("SELECT * FROM audit_log ORDER BY id DESC LIMIT 500")
    if not df.empty:
        ara = st.text_input("🔍 Ara")
        if ara: df = df[df.apply(lambda r: ara.lower() in str(r).lower(), axis=1)]
        disp = df.drop(columns=["id"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("📥 Excel İndir", excel_export(disp), "audit_log.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Log kaydı yok.")

# ══════════════════════════════════════════
# YETKİLER
# ══════════════════════════════════════════
elif page == "🔑 Yetkiler":
    page_header("Yetkilendirme", "Kullanıcı Rol Yönetimi")
    df = load_df("SELECT id, email, isim, rol FROM kullanicilar ORDER BY id")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("#### Rol Güncelle")
        with st.form("y_form"):
            uid = st.selectbox("Kullanıcı", df["id"].tolist(),
                               format_func=lambda x: df[df["id"]==x]["isim"].values[0] + " — " + df[df["id"]==x]["email"].values[0])
            rol = st.selectbox("Yeni Rol", ["Kullanici","Elektrik Elektronik Mühendisi","Yönetici","Admin"])
            if st.form_submit_button("Güncelle", use_container_width=True):
                with conn.session as s:
                    s.execute(text("UPDATE kullanicilar SET rol=:r WHERE id=:i"), {"r": rol, "i": uid})
                    s.commit()
                log_action(st.session_state.user_name, "Rol Güncellendi", f"ID:{uid} → {rol}")
                islem_basarili("Rol güncellendi!")

# ══════════════════════════════════════════
# AYARLAR
# ══════════════════════════════════════════
elif page == "⚙️ Ayarlar":
    page_header("Ayarlar", "Profil & Şifre Yönetimi")
    st.markdown(f"**İsim:** {st.session_state.user_name}")
    st.markdown(f"**E-posta:** {st.session_state.user_email}")
    st.markdown(f"**Rol:** {USER_ROL}")
    st.markdown("---")
    with st.form("pw_form"):
        y1 = st.text_input("Yeni Şifre", type="password")
        y2 = st.text_input("Yeni Şifre Tekrar", type="password")
        if st.form_submit_button("Şifreyi Güncelle", use_container_width=True):
            if y1 == y2 and len(y1) >= 4:
                with conn.session as s:
                    s.execute(text("UPDATE kullanicilar SET sifre=:s WHERE email=:e"),
                              {"s": hash_pw(y1), "e": st.session_state.user_email})
                    s.commit()
                log_action(st.session_state.user_name, "Şifre Güncellendi")
                islem_basarili("Şifre güncellendi!")
            else:
                st.error("Şifreler uyuşmuyor veya çok kısa.")
