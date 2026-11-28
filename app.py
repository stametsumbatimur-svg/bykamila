import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
import datetime
import json
import uuid
import base64
import requests
import hashlib
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Generator Nota & Pembukuan ByKamila", page_icon="🧾", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .verify-valid {
            background: #e8f5e9;
            border: 2px solid #2e7d32;
            border-radius: 16px;
            padding: 20px;
            color: #1b5e20;
        }
        .verify-invalid {
            background: #ffebee;
            border: 2px solid #c62828;
            border-radius: 16px;
            padding: 20px;
            color: #b71c1c;
        }
        .metric-card {
            background: #fff8fa;
            border: 1.5px solid #f48fb1;
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 8px;
        }
        .metric-label {
            font-size: 12px;
            font-weight: 700;
            color: #ad1457;
            margin-bottom: 2px;
        }
        .metric-val {
            font-size: 18px;
            font-weight: 800;
            color: #222;
        }
        .metric-sub {
            font-size: 11px;
            color: #666;
            margin-top: 2px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. KUNCI TANDA TANGAN DIGITAL NOTA ---
SALT_KEY = str(st.secrets.get("gcp_service_account", {}).get("private_key_id", "bykamila_secret"))

def buat_signature_nota(order_id, nama, total_akhir):
    raw = f"{order_id.strip()}|{nama.strip().lower()}|{int(total_akhir)}|{SALT_KEY}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8].upper()

@st.cache_data(ttl=3600, show_spinner=False)
def ambil_bytes_gambar(url):
    if not url or not isinstance(url, str):
        return None
    try:
        res = requests.get(url.strip(), timeout=12)
        if res.status_code == 200 and res.content:
            return res.content
    except Exception:
        pass
    return None

def upload_gambar_imgbb(uploaded_file):
    api_key = st.secrets.get("imgbb_api_key", "")
    if not api_key:
        return None, "API Key ImgBB belum dipasang di Secrets Streamlit."
    try:
        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key, "image": img_b64},
            timeout=25
        )
        hasil = res.json()
        if hasil.get("success"):
            return hasil["data"]["url"], None
        return None, f"Gagal upload gambar: {hasil.get('error', {}).get('message', 'Error tidak diketahui')}"
    except Exception as e:
        return None, f"Koneksi upload gagal: {e}"

# --- 3. KONEKSI & CACHE DATA GOOGLE SHEETS (HEMAT KUOTA API) ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database_ByKamila")

HEADER_PEMBUKUAN = [
    "ID", "Tanggal", "Toko", "Jenis", "Keterangan",
    "Qty", "Modal Barang", "Harga Jual", "Untung", "Catatan"
]

@st.cache_data(ttl=45, show_spinner=False)
def load_all_data():
    db = get_google_sheet()

    data_produk = []
    try:
        ws_produk = db.worksheet("Produk")
        data_produk = ws_produk.get_all_records()
    except Exception:
        pass

    cfg_toko = {}
    try:
        ws_cfg = db.worksheet("Pengaturan")
        cfg_toko = {str(r["Kunci"]): str(r["Nilai"]) for r in ws_cfg.get_all_records()}
    except Exception:
        pass

    data_buku = []
    try:
        ws_buku = db.worksheet("Pembukuan")
    except gspread.WorksheetNotFound:
        ws_buku = db.add_worksheet(title="Pembukuan", rows=500, cols=10)
        ws_buku.append_row(HEADER_PEMBUKUAN)

    try:
        raw_rows = ws_buku.get_all_values()
        if not raw_rows:
            ws_buku.append_row(HEADER_PEMBUKUAN)
        elif len(raw_rows) > 1:
            for idx_sheet, row in enumerate(raw_rows[1:], start=2):
                padded = row + [""] * (10 - len(row))
                def to_int(v):
                    try:
                        return int(float(str(v).replace(".", "").replace(",", "").strip()))
                    except Exception:
                        return 0
                data_buku.append({
                    "row_num": idx_sheet,
                    "ID": str(padded[0]).strip(),
                    "Tanggal": str(padded[1]).strip(),
                    "Toko": str(padded[2]).strip() or "Homedress",
                    "Jenis": str(padded[3]).strip() or "Penjualan",
                    "Keterangan": str(padded[4]).strip(),
                    "Qty": max(1, to_int(padded[5])) if str(padded[5]).strip() != "" else 1,
                    "Modal Barang": to_int(padded[6]),
                    "Harga Jual": to_int(padded[7]),
                    "Untung": to_int(padded[8]),
                    "Catatan": str(padded[9]).strip()
                })
    except Exception:
        pass

    return data_produk, cfg_toko, data_buku

def simpan_pengaturan(kunci, nilai):
    db = get_google_sheet()
    try:
        ws_cfg = db.worksheet("Pengaturan")
    except gspread.WorksheetNotFound:
        ws_cfg = db.add_worksheet(title="Pengaturan", rows=10, cols=2)
        ws_cfg.append_row(["Kunci", "Nilai"])

    all_vals = ws_cfg.get_all_values()
    for idx, row in enumerate(all_vals, start=1):
        if len(row) > 0 and str(row[0]).strip() == kunci:
            if nilai == "":
                try:
                    ws_cfg.batch_clear([f"B{idx}"])
                except Exception:
                    ws_cfg.update_cell(idx, 2, "")
            else:
                ws_cfg.update_cell(idx, 2, nilai)
            return
    if nilai != "":
        ws_cfg.append_row([kunci, nilai])

def hitung_untung_entri(jenis, modal_brg, harga_jual):
    if jenis in ("Modal Awal", "Tarik Dana"):
        return 0
    elif jenis == "Penjualan":
        return int(harga_jual) - int(modal_brg)
    else:
        return -int(modal_brg)

def tambah_entri_pembukuan(tgl_str, toko, jenis, keterangan, qty, modal_brg, harga_jual, catatan=""):
    db = get_google_sheet()
    ws_buku = db.worksheet("Pembukuan")
    id_tx = "TRX-" + str(uuid.uuid4())[:6].upper()

    if jenis == "Tarik Dana":
        toko = "Gabungan QRIS"
    if jenis in ("Modal Awal", "Tarik Dana", "Belanja Stok", "Operasional"):
        harga_jual = 0
    untung = hitung_untung_entri(jenis, modal_brg, harga_jual)

    ws_buku.append_row([
        id_tx, tgl_str, toko, jenis, keterangan,
        int(qty), int(modal_brg), int(harga_jual), int(untung), catatan
    ])
    load_all_data.clear()
    return id_tx

def tambah_banyak_entri_pembukuan(rows_list):
    """Menyimpan banyak baris sekaligus dalam 1 panggilan API Google Sheets."""
    if not rows_list:
        return
    db = get_google_sheet()
    ws_buku = db.worksheet("Pembukuan")
    formatted_rows = []
    for item in rows_list:
        id_tx = "TRX-" + str(uuid.uuid4())[:6].upper()
        jenis = item["jenis"]
        toko = "Gabungan QRIS" if jenis == "Tarik Dana" else item["toko"]
        modal_brg = int(item["modal_brg"])
        harga_jual = 0 if jenis in ("Modal Awal", "Tarik Dana", "Belanja Stok", "Operasional") else int(item["harga_jual"])
        untung = hitung_untung_entri(jenis, modal_brg, harga_jual)
        formatted_rows.append([
            id_tx,
            item["tgl_str"],
            toko,
            jenis,
            item["keterangan"],
            int(item["qty"]),
            modal_brg,
            harga_jual,
            untung,
            item.get("catatan", "")
        ])
    ws_buku.append_rows(formatted_rows)
    load_all_data.clear()

def update_entri_pembukuan(row_num, id_tx, tgl_str, toko, jenis, keterangan, qty, modal_brg, harga_jual, catatan=""):
    db = get_google_sheet()
    ws_buku = db.worksheet("Pembukuan")

    if jenis == "Tarik Dana":
        toko = "Gabungan QRIS"
    if jenis in ("Modal Awal", "Tarik Dana", "Belanja Stok", "Operasional"):
        harga_jual = 0
    untung = hitung_untung_entri(jenis, modal_brg, harga_jual)

    ws_buku.update(
        f"A{row_num}:J{row_num}",
        [[id_tx, tgl_str, toko, jenis, keterangan, int(qty), int(modal_brg), int(harga_jual), int(untung), catatan]]
    )
    load_all_data.clear()

def hapus_entri_pembukuan(row_num):
    db = get_google_sheet()
    ws_buku = db.worksheet("Pembukuan")
    ws_buku.delete_rows(row_num)
    load_all_data.clear()

# --- 4. MODE VERIFIKASI PUBLIK SAAT QR CODE DI NOTA DI-SCAN ---
if "cek" in st.query_params:
    cek_id = str(st.query_params.get("cek", "")).strip()
    cek_sig = str(st.query_params.get("sig", "")).strip().upper()
    cek_nama = str(st.query_params.get("n", "")).strip()
    cek_tot = int(st.query_params.get("t", "0")) if str(st.query_params.get("t", "0")).isdigit() else 0

    judul_toko = "Foodies ByKamila" if cek_id.startswith("FOD-") else "Homedress ByKamila"
    st.markdown(f"<h2 style='text-align: center; color: #d81b60; font-family: cursive;'>♡ Verifikasi Nota {judul_toko} ♡</h2>", unsafe_allow_html=True)

    expected_sig = buat_signature_nota(cek_id, cek_nama, cek_tot)
    sig_cocok = (cek_sig == expected_sig and cek_tot > 0)

    if cek_id.startswith("ORD-"):
        try:
            db = get_google_sheet()
            semua_order = db.worksheet("Pesanan").get_all_records()
        except Exception as e:
            st.error(f"Gagal membaca database: {e}")
            st.stop()

        cocok_rows = [r for r in semua_order if str(r.get("ID Pesanan", "")).strip() == cek_id]

        if cocok_rows and sig_cocok:
            status_db = str(cocok_rows[0].get("Status", "")).strip()
            nama_db = str(cocok_rows[0].get("Nama Customer", ""))
            tgl_db = str(cocok_rows[0].get("Tgl", ""))
            daftar_item_html = "".join([f"<li>{r['Nama Barang']} ({r['Jml']} pcs)</li>" for r in cocok_rows])

            if status_db == "Lunas":
                st.markdown(f"""
                    <div class='verify-valid'>
                        <h3 style='margin-top:0;'>✅ NOTA SAH & TERVERIFIKASI LUNAS</h3>
                        <p><b>ID Pesanan:</b> {cek_id}<br>
                        <b>Kode Validasi:</b> {cek_sig}<br>
                        <b>Nama Customer:</b> {nama_db}<br>
                        <b>Tanggal Order:</b> {tgl_db}<br>
                        <b>Total Dibayar:</b> Rp {cek_tot:,.0f}</p>
                        <b>Rincian Barang:</b>
                        <ul>{daftar_item_html}</ul>
                    </div>
                """.replace(",", "."), unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='verify-invalid'>
                        <h3 style='margin-top:0;'>⚠️ STATUS PESANAN BELUM LUNAS</h3>
                        <p>Pesanan <b>{cek_id}</b> tercatat dengan status: <b>{status_db}</b>.</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='verify-invalid'>
                    <h3 style='margin-top:0;'>❌ NOTA TIDAK VALID / DATA TELAH DIUBAH</h3>
                    <p>Kode validasi tidak cocok dengan catatan resmi {judul_toko}.</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        if sig_cocok:
            st.markdown(f"""
                <div class='verify-valid'>
                    <h3 style='margin-top:0;'>✅ NOTA RESMI TERVERIFIKASI LUNAS</h3>
                    <p><b>Toko:</b> {judul_toko}<br>
                    <b>No. Referensi:</b> {cek_id}<br>
                    <b>Kode Validasi:</b> {cek_sig}<br>
                    <b>Nama Customer:</b> {cek_nama}<br>
                    <b>Total Sah:</b> Rp {cek_tot:,.0f}</p>
                </div>
            """.replace(",", "."), unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='verify-invalid'>
                    <h3 style='margin-top:0;'>❌ NOTA TIDAK VALID / DATA TELAH DIUBAH</h3>
                    <p>Kode validasi tidak cocok dengan tanda tangan digital resmi {judul_toko}.</p>
                </div>
            """, unsafe_allow_html=True)

    st.stop()

# --- 5. AMBIL DATA PRODUK, QRIS, LOGO & PEMBUKUAN ---
try:
    data_produk_list, cfg_toko, data_pembukuan = load_all_data()
except Exception as e:
    if "429" in str(e):
        st.warning("⏳ Kuota akses Google Sheets sedang penuh sementara. Tunggu 30–60 detik lalu tekan tombol **🔄 Coba Lagi**.")
        if st.button("🔄 Coba Lagi"):
            load_all_data.clear()
            st.rerun()
    else:
        st.error(f"Gagal terhubung ke Database: {e}")
    st.stop()

# --- HELPER: BANGUN KATALOG PINTAR (DARI SHEET PRODUK + RIWAYAT PEMBUKUAN) ---
def get_katalog_pintar(toko_name):
    katalog = {}
    if toko_name == "Homedress":
        for p in data_produk_list:
            nm = str(p.get("Nama Barang", "")).strip()
            if nm:
                hrg = int(p["Harga"]) if str(p.get("Harga", "")).isdigit() else 0
                katalog[nm] = {"modal_satuan": 0, "jual_satuan": hrg}

    for r in data_pembukuan:
        if r.get("Toko") != toko_name:
            continue
        if r.get("Jenis") not in ("Penjualan", "Belanja Stok"):
            continue
        ket = str(r.get("Keterangan", "")).strip()
        if not ket:
            continue

        nm_pokok = ket.split(" [", 1)[0].strip() if " [" in ket else ket

        if str(r.get("Catatan", "")).startswith("Nota ") and " - " in nm_pokok and "," in nm_pokok:
            bagian_item = nm_pokok.split(" - ", 1)[1]
            for part in bagian_item.split(", "):
                nm_clean = part.rsplit(" (", 1)[0].strip() if " (" in part else part.strip()
                if nm_clean and nm_clean not in katalog:
                    katalog[nm_clean] = {"modal_satuan": 0, "jual_satuan": 0}
        else:
            qty = max(1, int(r.get("Qty", 1)))
            mod_tot = int(r.get("Modal Barang", 0))
            jual_tot = int(r.get("Harga Jual", 0))

            prev = katalog.get(nm_pokok, {"modal_satuan": 0, "jual_satuan": 0})
            mod_sat = int(round(mod_tot / qty)) if mod_tot > 0 else prev["modal_satuan"]
            jual_sat = int(round(jual_tot / qty)) if jual_tot > 0 else prev["jual_satuan"]
            katalog[nm_pokok] = {"modal_satuan": mod_sat, "jual_satuan": jual_sat}

    return katalog

# --- 6. FUNGSI RENDER NOTA ---
def tampilkan_nota_estetik(payload_nota, logo_bytes=None, brand_type="homedress"):
    subtotal_calc = sum(int(it["qty"]) * int(it["harga"]) for it in payload_nota["items"])
    total_akhir_calc = subtotal_calc - int(payload_nota["diskon"]) + int(payload_nota["ongkir"])
    default_prefix = "FOD-" if brand_type == "foodies" else "MAN-"
    order_id = payload_nota.get("order_id", default_prefix + str(uuid.uuid4())[:6].upper())
    sig_code = buat_signature_nota(order_id, payload_nota["nama"], total_akhir_calc)

    base_admin_url = cfg_toko.get("admin_url", "").strip().rstrip("/")
    if not base_admin_url:
        base_admin_url = "https://share.streamlit.io"

    params_qr = urllib.parse.urlencode({
        "cek": order_id,
        "n": payload_nota["nama"],
        "t": total_akhir_calc,
        "sig": sig_code
    })
    verify_url = f"{base_admin_url}/?{params_qr}"

    logo_data_uri = ""
    if logo_bytes:
        b64_logo = base64.b64encode(logo_bytes).decode("utf-8")
        logo_data_uri = f"data:image/jpeg;base64,{b64_logo}"

    data_for_js = dict(payload_nota)
    data_for_js["order_id"] = order_id
    data_for_js["sig_code"] = sig_code
    data_for_js["verify_url"] = verify_url
    data_for_js["logo_data_uri"] = logo_data_uri
    data_for_js["brand_type"] = brand_type

    extra_rows = max(0, len(payload_nota["items"]) - 3)
    iframe_height = 830 + (extra_rows * 38)

    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            :root {
                --pink-main: #d81b60;
                --pink-light: #fce4ec;
                --pink-border: #f48fb1;
                --text-dark: #4a4a4a;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Quicksand', sans-serif; }
            body { background: transparent; padding: 4px; }

            #nota-viewport {
                width: 100%;
                display: flex;
                justify-content: center;
                overflow: hidden;
            }
            #nota-scaler {
                width: 440px;
                transform-origin: top center;
            }

            .nota-box {
                background: linear-gradient(180deg, #ffffff 0%, #fff7fa 45%, #ffeef4 100%);
                width: 440px;
                min-width: 440px;
                max-width: 440px;
                margin: 0 auto;
                padding: 12px 10px 14px;
                color: var(--pink-main);
                position: relative;
                border-radius: 16px;
                box-shadow: 0 6px 20px rgba(216, 27, 96, 0.12);
                overflow: hidden;
            }
            .nota-box::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 8px;
                background: linear-gradient(90deg, #fce4ec, #f48fb1, #d81b60, #f48fb1, #fce4ec);
                z-index: 3;
            }
            .inner-frame {
                border: 1.5px solid rgba(244, 143, 177, 0.65);
                border-radius: 12px;
                padding: 12px 8.5px 14px;
                position: relative;
                overflow: hidden;
            }
            .wm-logo-center {
                position: absolute;
                top: 52%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 240px;
                opacity: 0.16;
                pointer-events: none;
                z-index: 0;
            }
            .wm-logo-center img {
                width: 100%;
                height: auto;
                display: block;
            }
            .wm-text-wrap {
                position: absolute;
                top: 18%;
                left: -15%;
                right: -15%;
                bottom: 10%;
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                align-items: center;
                transform: rotate(-22deg);
                pointer-events: none;
                z-index: 0;
            }
            .wm-line {
                font-size: 16.5px;
                font-weight: 700;
                color: rgba(216, 27, 96, 0.15);
                white-space: nowrap;
                letter-spacing: 2.2px;
            }
            .content-layer { position: relative; z-index: 1; }
            .header-nota {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                margin-bottom: 14px;
            }
            .brand-logo-wrap {
                width: 152px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .brand-logo-wrap img {
                width: 148px;
                height: auto;
                max-height: 144px;
                object-fit: contain;
                display: block;
            }
            .brand h1 { font-family: 'Dancing Script', cursive; font-size: 42px; line-height: 0.9; white-space: nowrap; }
            .brand p { font-family: 'Dancing Script', cursive; font-size: 22px; text-align: center; white-space: nowrap; }
            .contact-area {
                flex: 1;
                text-align: right;
            }
            .contact { font-size: 13px; font-weight: 700; text-align: right; color: var(--pink-main); white-space: nowrap; }
            .contact p { display: flex; align-items: center; justify-content: flex-end; gap: 6px; margin-bottom: 4px; }
            .tagline-top {
                font-family: 'Dancing Script', cursive;
                font-size: 21px;
                text-align: right;
                margin-top: 8px;
                line-height: 1.15;
                color: var(--pink-main);
            }
            .foodies-header-right {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                justify-content: center;
                gap: 4px;
            }
            .foodies-title {
                font-family: 'Dancing Script', cursive;
                font-size: 32px;
                line-height: 1;
                color: var(--pink-main);
            }
            .foodies-sub {
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                color: #ad1457;
                text-transform: uppercase;
            }
            .foodies-divider {
                width: 100%;
                height: 1.5px;
                background: linear-gradient(90deg, transparent, #f48fb1, #d81b60);
                margin: 3px 0;
            }
            .foodies-wa {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 5px;
                font-size: 12.5px;
                font-weight: 700;
                color: var(--pink-main);
            }
            .foodies-pill {
                margin-top: 3px;
                background: rgba(252, 228, 236, 0.92);
                border: 1px solid #f48fb1;
                color: #d81b60;
                font-size: 10.5px;
                font-weight: 700;
                padding: 4px 11px;
                border-radius: 20px;
                white-space: nowrap;
            }
            .info-row { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
            .info-box {
                border: 1.5px solid var(--pink-border);
                border-radius: 25px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 700;
                text-align: center;
                flex: 1;
                background: rgba(255, 255, 255, 0.58);
                overflow: hidden;
            }
            .info-box span {
                display: block;
                color: var(--text-dark);
                font-size: 14px;
                margin-top: 3px;
                word-break: break-word;
            }
            table {
                width: 400px;
                table-layout: fixed;
                border-collapse: collapse;
                margin-bottom: 14px;
                text-align: center;
                background: rgba(255, 255, 255, 0.48);
            }
            table th, table td {
                border: 1.5px solid var(--pink-border);
                padding: 8px 6px;
                font-weight: 600;
                vertical-align: middle;
            }
            table th {
                background-color: rgba(252, 228, 236, 0.85);
                font-size: 11.5px;
                color: var(--pink-main);
                white-space: nowrap;
            }
            table td { color: var(--text-dark); font-size: 12.5px; }
            .col-qty { width: 70px; white-space: nowrap; }
            .col-nama { width: 132px; text-align: left; word-break: break-word; }
            .col-hrg { width: 90px; text-align: right; white-space: nowrap; }
            .col-jml { width: 108px; text-align: right; white-space: nowrap; }
            .align-right { text-align: right; white-space: nowrap; }
            .align-left { text-align: left; }
            .grand-total {
                font-family: 'Dancing Script', cursive;
                font-size: 26px;
                color: var(--pink-main);
                background-color: rgba(252, 228, 236, 0.85);
                padding: 6px 8px;
            }
            .grand-total-val {
                font-size: 14.5px;
                color: var(--pink-main);
                background-color: rgba(252, 228, 236, 0.85);
                font-weight: 700;
                white-space: nowrap;
                padding: 8px 6px;
            }
            .footer-area {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                background-color: rgba(252, 228, 236, 0.92);
                border-radius: 15px;
                padding: 12px 14px;
                margin-top: 8px;
            }
            .footer-text { text-align: left; flex: 1; }
            .lunas-badge {
                display: inline-block;
                margin-top: 6px;
                font-size: 11px;
                font-weight: 700;
                color: #2e7d32;
                background: #e8f5e9;
                border: 1.5px solid #81c784;
                padding: 3px 12px;
                border-radius: 12px;
                letter-spacing: 0.6px;
                white-space: nowrap;
            }
            #qrcode-box {
                width: 76px;
                height: 76px;
                flex-shrink: 0;
                background: white;
                padding: 5px;
                border-radius: 8px;
                border: 1px solid var(--pink-border);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .btn-dl {
                display: block; width: 100%; max-width: 440px; margin: 14px auto 0;
                background-color: #2e7d32; color: white; border: none; padding: 13px;
                border-radius: 12px; font-weight: 700; font-size: 15px; cursor: pointer;
            }
            .btn-dl:active { transform: scale(0.98); }
            #jpg-preview-area {
                display: none; max-width: 440px; margin: 12px auto 0; text-align: center;
                background: #fff8fa; border: 2px dashed var(--pink-border); border-radius: 12px; padding: 10px;
            }
            #jpg-preview-area img { width: 100%; border-radius: 8px; margin-top: 6px; }
        </style>
    </head>
    <body>
        <div id="nota-viewport">
            <div id="nota-scaler">
                <div class="nota-box" id="nota-area">
                    <div class="inner-frame">
                        <div class="wm-logo-center" id="wm-logo-box"></div>
                        <div class="wm-text-wrap" id="wm-text-wrap"></div>

                        <div class="content-layer">
                            <div class="header-nota">
                                <div id="brand-container"></div>
                                <div class="contact-area" id="contact-container"></div>
                            </div>

                            <div class="info-row">
                                <div class="info-box">Nama Customer<span id="out-nama"></span></div>
                                <div class="info-box">Tanggal Order<span id="out-tanggal"></span></div>
                            </div>

                            <table>
                                <thead>
                                    <tr>
                                        <th class="col-qty">Banyaknya</th>
                                        <th style="width:132px;" id="th-nama-item">Nama Barang</th>
                                        <th style="width:90px;">Harga</th>
                                        <th style="width:108px;">Jumlah</th>
                                    </tr>
                                </thead>
                                <tbody id="out-items"></tbody>
                                <tbody>
                                    <tr>
                                        <td colspan="3" class="align-left" style="background-color: rgba(252, 228, 236, 0.85);">Subtotal</td>
                                        <td class="align-right" style="background-color: rgba(252, 228, 236, 0.85);" id="out-subtotal"></td>
                                    </tr>
                                    <tr id="row-diskon" style="display: none;">
                                        <td colspan="3" class="align-left" style="color: var(--pink-main);">Diskon</td>
                                        <td class="align-right" id="out-val-diskon" style="color: var(--pink-main);"></td>
                                    </tr>
                                    <tr>
                                        <td colspan="3" class="align-left">Ongkir</td>
                                        <td class="align-right" id="out-ongkir"></td>
                                    </tr>
                                    <tr>
                                        <td colspan="3" class="grand-total align-left">Total</td>
                                        <td class="grand-total-val align-right" id="out-total"></td>
                                    </tr>
                                </tbody>
                            </table>

                            <div class="footer-area">
                                <div class="footer-text">
                                    <span style="font-family: 'Dancing Script', cursive; font-size: 22px; color: var(--pink-main);">♡ Terima kasih sudah order ♡</span><br>
                                    <span style="font-size: 11px; font-weight: 600; color: var(--text-dark);" id="out-footer-sub"></span><br>
                                    <span class="lunas-badge">✔ LUNAS</span>
                                </div>
                                <div id="qrcode-box"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <button class="btn-dl" onclick="downloadNotaJPG()">📥 Download Gambar Nota (JPG)</button>
        <div id="jpg-preview-area">
            <p style="font-size: 12px; font-weight: 700; color: #d81b60;">Untuk pengguna iPhone: Tekan lama gambar di bawah lalu pilih <u>Simpan ke Foto</u></p>
            <img id="img-hasil" alt="Nota JPG">
        </div>

        <script>
            const data = __DATA_JSON__;
            const isFoodies = (data.brand_type === 'foodies');
            const formatRp = (n) => new Intl.NumberFormat('id-ID').format(n);
            const escHtml = (str) => String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');

            function cleanLogoOuterBg(dataUri, callback) {
                if (!dataUri) { callback(''); return; }
                const img = new Image();
                img.onload = function() {
                    const maxDim = 420;
                    let w = img.width, h = img.height;
                    if (w > maxDim || h > maxDim) {
                        if (w >= h) { h = Math.round(h * maxDim / w); w = maxDim; }
                        else { w = Math.round(w * maxDim / h); h = maxDim; }
                    }
                    const c = document.createElement('canvas');
                    c.width = w;
                    c.height = h;
                    const ctx = c.getContext('2d');
                    ctx.drawImage(img, 0, 0, w, h);
                    const imgData = ctx.getImageData(0, 0, w, h);
                    const d = imgData.data;
                    const total = w * h;
                    const visited = new Uint8Array(total);
                    const queue = new Int32Array(total);
                    let head = 0, tail = 0;

                    const isNearWhite = (idx) => {
                        const p = idx * 4;
                        return d[p] > 232 && d[p+1] > 232 && d[p+2] > 232;
                    };

                    for (let x = 0; x < w; x++) {
                        const top = x;
                        const bot = (h - 1) * w + x;
                        if (!visited[top] && isNearWhite(top)) { visited[top] = 1; queue[tail++] = top; }
                        if (!visited[bot] && isNearWhite(bot)) { visited[bot] = 1; queue[tail++] = bot; }
                    }
                    for (let y = 0; y < h; y++) {
                        const left = y * w;
                        const right = y * w + (w - 1);
                        if (!visited[left] && isNearWhite(left)) { visited[left] = 1; queue[tail++] = left; }
                        if (!visited[right] && isNearWhite(right)) { visited[right] = 1; queue[tail++] = right; }
                    }

                    while (head < tail) {
                        const curr = queue[head++];
                        d[curr * 4 + 3] = 0;
                        const cx = curr % w;
                        const cy = (curr - cx) / w;

                        if (cx > 0) { const n = curr - 1; if (!visited[n] && isNearWhite(n)) { visited[n] = 1; queue[tail++] = n; } }
                        if (cx < w - 1) { const n = curr + 1; if (!visited[n] && isNearWhite(n)) { visited[n] = 1; queue[tail++] = n; } }
                        if (cy > 0) { const n = curr - w; if (!visited[n] && isNearWhite(n)) { visited[n] = 1; queue[tail++] = n; } }
                        if (cy < h - 1) { const n = curr + w; if (!visited[n] && isNearWhite(n)) { visited[n] = 1; queue[tail++] = n; } }
                    }

                    ctx.putImageData(imgData, 0, 0);
                    callback(c.toDataURL('image/png'));
                };
                img.onerror = function() { callback(dataUri); };
                img.src = dataUri;
            }

            const brandContainer = document.getElementById('brand-container');
            const wmLogoBox = document.getElementById('wm-logo-box');
            const contactContainer = document.getElementById('contact-container');

            if (isFoodies) {
                if (data.logo_data_uri) {
                    brandContainer.innerHTML = `<div class="brand-logo-wrap"><img id="img-brand-logo" src="${data.logo_data_uri}" alt="Logo Foodies ByKamila"></div>`;
                    cleanLogoOuterBg(data.logo_data_uri, (cleanUri) => {
                        const brandImg = document.getElementById('img-brand-logo');
                        if (brandImg) brandImg.src = cleanUri;
                        wmLogoBox.innerHTML = `<img src="${cleanUri}" alt="Watermark Foodies ByKamila">`;
                    });
                } else {
                    brandContainer.innerHTML = `<div class="brand"><h1>foodies</h1><p>♡ bykamila ♡</p></div>`;
                }

                contactContainer.innerHTML = `
                    <div class="foodies-header-right">
                        <div class="foodies-title">Nota Pesanan</div>
                        <div class="foodies-sub">FOODIES BYKAMILA</div>
                        <div class="foodies-divider"></div>
                        <div class="foodies-wa">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                            </svg>
                            <span>0812-8886-0421</span>
                        </div>
                        <div class="foodies-pill">♡ Fresh &amp; Homemade Setiap Hari ♡</div>
                    </div>
                `;
                document.getElementById('th-nama-item').innerText = 'Nama Menu';
                document.getElementById('out-footer-sub').innerText = 'Semoga suka dengan makanannya di Foodies bykamila';
            } else {
                if (data.logo_data_uri) {
                    brandContainer.innerHTML = `<div class="brand-logo-wrap"><img id="img-brand-logo" src="${data.logo_data_uri}" alt="Logo Homedress ByKamila"></div>`;
                    cleanLogoOuterBg(data.logo_data_uri, (cleanUri) => {
                        const brandImg = document.getElementById('img-brand-logo');
                        if (brandImg) brandImg.src = cleanUri;
                        wmLogoBox.innerHTML = `<img src="${cleanUri}" alt="Watermark Homedress ByKamila">`;
                    });
                } else {
                    brandContainer.innerHTML = `<div class="brand"><h1>homedress</h1><p>♡ bykamila ♡</p></div>`;
                }

                contactContainer.innerHTML = `
                    <div class="contact">
                        <p>
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                            </svg>
                            bykamila__
                        </p>
                        <p>
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                            </svg>
                            0895-2608-7445
                        </p>
                    </div>
                    <div class="tagline-top">Nyaman &amp; Cantik<br>di Rumah ♡</div>
                `;
                document.getElementById('th-nama-item').innerText = 'Nama Barang';
                document.getElementById('out-footer-sub').innerText = 'Semoga suka dengan produknya di Homedress bykamila';
            }

            const wmWrap = document.getElementById('wm-text-wrap');
            const wmBrandLabel = isFoodies ? 'FOODIES BYKAMILA' : 'BYKAMILA';
            const wmString = `LUNAS • ${data.order_id} • ${wmBrandLabel} • `;
            wmWrap.innerHTML = `
                <div class="wm-line">${wmString.repeat(2)}</div>
                <div class="wm-line">${wmString.repeat(2)}</div>
                <div class="wm-line">${wmString.repeat(2)}</div>
                <div class="wm-line">${wmString.repeat(2)}</div>
            `;

            document.getElementById('out-nama').innerText = data.nama;
            document.getElementById('out-tanggal').innerText = data.tanggal;

            new QRCode(document.getElementById("qrcode-box"), {
                text: data.verify_url,
                width: 64,
                height: 64,
                colorDark: "#d81b60",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });

            let rowsHTML = '';
            let subtotal = 0;
            const minRows = Math.max(3, data.items.length);

            for (let i = 0; i < minRows; i++) {
                if (i < data.items.length) {
                    const it = data.items[i];
                    const unitLabel = it.unit || 'pcs';
                    const lineTotal = it.qty * it.harga;
                    subtotal += lineTotal;
                    rowsHTML += `
                        <tr>
                            <td class="col-qty">${it.qty} ${escHtml(unitLabel)}</td>
                            <td class="col-nama">${escHtml(it.nama)}</td>
                            <td class="col-hrg">Rp ${formatRp(it.harga)}</td>
                            <td class="col-jml">Rp ${formatRp(lineTotal)}</td>
                        </tr>`;
                } else {
                    rowsHTML += `<tr><td class="col-qty">&nbsp;</td><td class="col-nama"></td><td class="col-hrg"></td><td class="col-jml"></td></tr>`;
                }
            }
            document.getElementById('out-items').innerHTML = rowsHTML;

            if (data.diskon > 0) {
                document.getElementById('row-diskon').style.display = 'table-row';
                document.getElementById('out-val-diskon').innerText = '- Rp ' + formatRp(data.diskon);
            }

            const totalAkhir = subtotal - data.diskon + data.ongkir;
            document.getElementById('out-subtotal').innerText = 'Rp ' + formatRp(subtotal);
            document.getElementById('out-ongkir').innerText = 'Rp ' + formatRp(data.ongkir);

            const elTotal = document.getElementById('out-total');
            elTotal.innerText = 'Rp ' + formatRp(totalAkhir);
            if (totalAkhir >= 10000000) {
                elTotal.style.fontSize = '13px';
            }

            function fitNotaToScreen() {
                const vp = document.getElementById('nota-viewport');
                const scaler = document.getElementById('nota-scaler');
                const box = document.getElementById('nota-area');
                scaler.style.transform = 'none';
                const availWidth = vp.clientWidth;
                if (availWidth > 0 && availWidth < 440) {
                    const ratio = availWidth / 440;
                    scaler.style.transform = `scale(${ratio})`;
                    vp.style.height = (box.offsetHeight * ratio + 8) + 'px';
                } else {
                    scaler.style.transform = 'none';
                    vp.style.height = 'auto';
                }
            }

            window.addEventListener('load', fitNotaToScreen);
            window.addEventListener('resize', fitNotaToScreen);
            setTimeout(fitNotaToScreen, 180);

            function downloadNotaJPG() {
                const scaler = document.getElementById('nota-scaler');
                const prevTransform = scaler.style.transform;
                scaler.style.transform = 'none';

                html2canvas(document.getElementById('nota-area'), {
                    scale: 2,
                    width: 440,
                    backgroundColor: "#ffffff"
                }).then(canvas => {
                    scaler.style.transform = prevTransform;
                    fitNotaToScreen();

                    const url = canvas.toDataURL('image/jpeg', 0.95);
                    document.getElementById('img-hasil').src = url;
                    document.getElementById('jpg-preview-area').style.display = 'block';

                    const filePrefix = isFoodies ? 'Nota_Foodies' : 'Nota_Homedress';
                    const a = document.createElement('a');
                    a.download = `${filePrefix}_${data.nama}.jpg`;
                    a.href = url;
                    a.click();
                }).catch(() => {
                    scaler.style.transform = prevTransform;
                    fitNotaToScreen();
                });
            }
        </script>
    </body>
    </html>
    """
    final_html = html_template.replace("__DATA_JSON__", json.dumps(data_for_js))
    components.html(final_html, height=iframe_height, scrolling=True)

# --- 7. HEADER & PANEL QRIS ---
col_head1, col_head2 = st.columns([3.5, 1.2])
with col_head1:
    st.markdown("<h3 style='color: #d81b60; font-family: cursive; margin:0;'>♡ Generator Nota ByKamila ♡</h3>", unsafe_allow_html=True)
with col_head2:
    if st.button("🔄 Refresh", use_container_width=True, help="Perbarui daftar harga produk, logo & QRIS"):
        load_all_data.clear()
        ambil_bytes_gambar.clear()
        st.rerun()

qris_tersimpan = cfg_toko.get("qris_url", "").strip()
info_bayar_tersimpan = cfg_toko.get("info_bayar", "").strip()
logo_homedress_url = cfg_toko.get("logo_url", "").strip()
logo_foodies_url = cfg_toko.get("logo_foodies_url", "").strip()

qris_bytes = ambil_bytes_gambar(qris_tersimpan) if qris_tersimpan else None
logo_homedress_bytes = ambil_bytes_gambar(logo_homedress_url) if logo_homedress_url else None
logo_foodies_bytes = ambil_bytes_gambar(logo_foodies_url) if logo_foodies_url else None

if qris_bytes or info_bayar_tersimpan:
    with st.expander("💳 Tampilkan QRIS & Info Pembayaran", expanded=False):
        if qris_bytes:
            c_q1, c_q2, c_q3 = st.columns([1, 2.2, 1])
            with c_q2:
                st.image(qris_bytes, caption="QRIS ByKamila", use_container_width=True)
                st.download_button(
                    label="📥 Download Gambar QRIS (JPG)",
                    data=qris_bytes,
                    file_name="QRIS_ByKamila.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
        if info_bayar_tersimpan:
            st.info(f"**Info Rekening / Pembayaran:**\n\n{info_bayar_tersimpan}")

katalog_homedress = get_katalog_pintar("Homedress")
katalog_foodies = get_katalog_pintar("Foodies")

# --- 8. TAB PILIHAN: HOMEDRESS, FOODIES & PEMBUKUAN ---
tab_hd, tab_fd, tab_buku = st.tabs(["👗 Nota Homedress", "🍽️ Nota Foodies", "📒 Pembukuan"])

# ==============================================================================
# TAB 1: NOTA HOMEDRESS BYKAMILA
# ==============================================================================
with tab_hd:
    st.subheader("🧾 Buat Nota Homedress ByKamila")
    daftar_nama_hd = ["-- Ketik Manual --"] + sorted(katalog_homedress.keys())

    c_m1, c_m2 = st.columns(2)
    with c_m1:
        m_nama = st.text_input("Nama Customer", placeholder="Contoh: Bude Heni", key="hd_nama")
    with c_m2:
        m_tgl = st.date_input("Tanggal Order", value=datetime.date.today(), key="hd_tgl")

    if "hd_row_ids" not in st.session_state or not st.session_state.hd_row_ids:
        st.session_state.hd_row_ids = [str(uuid.uuid4())[:6]]

    items_hd = []
    jumlah_baris_hd = len(st.session_state.hd_row_ids)

    for idx_baris, rid in enumerate(list(st.session_state.hd_row_ids)):
        c_lbl, c_del = st.columns([3.5, 1])
        with c_lbl:
            st.markdown(f"**Barang #{idx_baris + 1}**")
        with c_del:
            if jumlah_baris_hd > 1:
                if st.button("🗑️ Hapus", key=f"hd_del_{rid}", use_container_width=True):
                    st.session_state.hd_row_ids.remove(rid)
                    for prefix in ("hd_sel_", "hd_last_", "hd_txt_", "hd_qty_", "hd_hrg_"):
                        st.session_state.pop(f"{prefix}{rid}", None)
                    st.rerun()

        col_p, col_j, col_h = st.columns([2.2, 0.9, 1.3])
        with col_p:
            pilih = st.selectbox("Pilih Katalog", daftar_nama_hd, key=f"hd_sel_{rid}", label_visibility="collapsed")
            if pilih == "-- Ketik Manual --":
                nama_item_m = st.text_input("Nama Barang", placeholder="Ketik nama barang...", key=f"hd_txt_{rid}", label_visibility="collapsed")
                harga_default = 0
            else:
                nama_item_m = pilih
                harga_default = katalog_homedress.get(pilih, {}).get("jual_satuan", 0)

            if st.session_state.get(f"hd_last_{rid}") != pilih:
                st.session_state[f"hd_last_{rid}"] = pilih
                st.session_state[f"hd_hrg_{rid}"] = harga_default

        with col_j:
            qty_m = st.number_input("Banyaknya", min_value=1, value=1, key=f"hd_qty_{rid}")
        with col_h:
            harga_m = st.number_input("Harga Satuan", min_value=0, step=1000, key=f"hd_hrg_{rid}")

        if nama_item_m.strip() and harga_m > 0:
            items_hd.append({"nama": nama_item_m.strip(), "qty": int(qty_m), "unit": "pcs", "harga": int(harga_m)})

    c_add_btn, c_rst_btn = st.columns([2.5, 1.2])
    with c_add_btn:
        if st.button("+ Tambah Baris Barang", key="hd_add_row", use_container_width=True):
            st.session_state.hd_row_ids.append(str(uuid.uuid4())[:6])
            st.rerun()
    with c_rst_btn:
        if st.button("🧹 Reset Semua", key="hd_rst_all", use_container_width=True):
            for rid in st.session_state.hd_row_ids:
                for prefix in ("hd_sel_", "hd_last_", "hd_txt_", "hd_qty_", "hd_hrg_"):
                    st.session_state.pop(f"{prefix}{rid}", None)
            st.session_state.hd_row_ids = [str(uuid.uuid4())[:6]]
            st.session_state.hd_nota_preview = None
            st.rerun()

    col_mo, col_md = st.columns(2)
    with col_mo:
        m_ongkir = st.number_input("Ongkir (Rp)", min_value=0, step=1000, key="hd_ongkir")
    with col_md:
        m_diskon = st.number_input("Diskon (Rp)", min_value=0, step=1000, key="hd_diskon")

    if st.button("✨ Buat Nota Homedress", type="primary", key="hd_submit", use_container_width=True):
        if not m_nama.strip() or not items_hd:
            st.error("Isi Nama Customer dan minimal 1 barang terlebih dahulu.")
        else:
            bulan_id = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
            tgl_fmt = f"{m_tgl.day} {bulan_id[m_tgl.month - 1]} {m_tgl.year}"
            st.session_state.hd_nota_preview = {
                "order_id": "MAN-" + str(uuid.uuid4())[:6].upper(),
                "nama": m_nama.strip(),
                "tanggal": tgl_fmt,
                "tgl_iso": m_tgl.strftime("%Y-%m-%d"),
                "items": items_hd,
                "ongkir": int(m_ongkir),
                "diskon": int(m_diskon)
            }

    if "hd_nota_preview" in st.session_state and st.session_state.hd_nota_preview:
        prev_hd = st.session_state.hd_nota_preview
        tampilkan_nota_estetik(
            prev_hd,
            logo_bytes=logo_homedress_bytes,
            brand_type="homedress"
        )
        with st.expander("📥 Simpan Transaksi Ini ke Pembukuan Homedress (Rincian Per Barang)", expanded=False):
            st.caption("Isi harga modal satuan tiap barang di bawah ini (otomatis terisi jika sudah pernah dicatat):")
            with st.form(f"form_catat_hd_{prev_hd['order_id']}"):
                modal_inputs_hd = []
                sisa_diskon_hd = int(prev_hd["diskon"])

                for idx_it, it in enumerate(prev_hd["items"]):
                    est_mod_sat = katalog_homedress.get(it["nama"], {}).get("modal_satuan", 0)
                    jual_baris = it["qty"] * it["harga"]
                    potongan = min(jual_baris, sisa_diskon_hd)
                    sisa_diskon_hd -= potongan
                    jual_bersih_baris = jual_baris - potongan

                    c_i1, c_i2 = st.columns([2, 1.3])
                    with c_i1:
                        st.markdown(
                            f"**{it['nama']}** ({it['qty']} pcs)\n\n"
                            f"Jual: Rp {jual_bersih_baris:,.0f}".replace(",", ".")
                        )
                    with c_i2:
                        mod_sat_in = st.number_input(
                            "Modal Satuan (Rp)",
                            min_value=0,
                            step=5000,
                            value=int(est_mod_sat),
                            key=f"mod_sat_hd_{prev_hd['order_id']}_{idx_it}"
                        )
                    modal_inputs_hd.append((it, mod_sat_in, jual_bersih_baris))

                btn_catat_hd = st.form_submit_button("💾 Masukkan Semua Item ke Pembukuan", type="primary", use_container_width=True)
                if btn_catat_hd:
                    with st.spinner("Menyimpan rincian ke pembukuan..."):
                        rows_to_add = []
                        tgl_tx = prev_hd.get("tgl_iso", datetime.date.today().strftime("%Y-%m-%d"))
                        for it, mod_sat_in, jual_bersih_baris in modal_inputs_hd:
                            rows_to_add.append({
                                "tgl_str": tgl_tx,
                                "toko": "Homedress",
                                "jenis": "Penjualan",
                                "keterangan": it["nama"],
                                "qty": int(it["qty"]),
                                "modal_brg": int(mod_sat_in) * int(it["qty"]),
                                "harga_jual": int(jual_bersih_baris),
                                "catatan": f"Nota {prev_hd['order_id']} ({prev_hd['nama']})"
                            })
                        tambah_banyak_entri_pembukuan(rows_to_add)
                        st.success(f"✅ {len(rows_to_add)} item berhasil dicatat ke tab Pembukuan!")

# ==============================================================================
# TAB 2: NOTA MANUAL FOODIES BYKAMILA
# ==============================================================================
with tab_fd:
    if not logo_foodies_bytes:
        with st.expander("🖼️ Upload Logo Foodies ByKamila (Cukup 1 kali saja)", expanded=True):
            with st.form("form_upload_logo_foodies"):
                fd_logo_file = st.file_uploader(
                    "Pilih Gambar Logo Foodies ByKamila",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="fd_logo_uploader"
                )
                simpan_fd_logo = st.form_submit_button("💾 Simpan Logo Foodies", type="primary", use_container_width=True)

                if simpan_fd_logo:
                    if fd_logo_file is None:
                        st.error("Pilih file gambar logo Foodies terlebih dahulu.")
                    else:
                        with st.spinner("Mengunggah & menyimpan logo Foodies permanen..."):
                            url_fd_baru, err_fd = upload_gambar_imgbb(fd_logo_file)
                            if err_fd:
                                st.error(err_fd)
                            else:
                                simpan_pengaturan("logo_foodies_url", url_fd_baru)
                                load_all_data.clear()
                                ambil_bytes_gambar.clear()
                                st.success("✅ Logo Foodies berhasil disimpan!")
                                st.rerun()

    st.subheader("🧾 Buat Nota Foodies ByKamila")
    daftar_nama_fd = ["-- Ketik Menu Baru --"] + sorted(katalog_foodies.keys())

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        f_nama = st.text_input("Nama Customer", placeholder="Contoh: Kak Rina", key="fd_nama")
    with c_f2:
        f_tgl = st.date_input("Tanggal Order", value=datetime.date.today(), key="fd_tgl")

    if "fd_row_ids" not in st.session_state or not st.session_state.fd_row_ids:
        st.session_state.fd_row_ids = [str(uuid.uuid4())[:6]]

    items_fd = []
    jumlah_baris_fd = len(st.session_state.fd_row_ids)
    pilihan_satuan = ["pcs", "box", "porsi", "pack", "cup", "toples"]

    for idx_baris, rid in enumerate(list(st.session_state.fd_row_ids)):
        c_lbl, c_del = st.columns([3.5, 1])
        with c_lbl:
            st.markdown(f"**Menu #{idx_baris + 1}**")
        with c_del:
            if jumlah_baris_fd > 1:
                if st.button("🗑️ Hapus", key=f"fd_del_{rid}", use_container_width=True):
                    st.session_state.fd_row_ids.remove(rid)
                    for prefix in ("fd_sel_", "fd_last_", "fd_txt_", "fd_qty_", "fd_unit_", "fd_hrg_"):
                        st.session_state.pop(f"{prefix}{rid}", None)
                    st.rerun()

        pilih_fd = st.selectbox("Pilih Menu", daftar_nama_fd, key=f"fd_sel_{rid}", label_visibility="collapsed")
        if pilih_fd == "-- Ketik Menu Baru --":
            nama_menu = st.text_input(
                "Nama Menu",
                placeholder="Ketik nama menu baru (misal: Pempek Lenjer / Brownies)...",
                key=f"fd_txt_{rid}",
                label_visibility="collapsed"
            )
            harga_fd_def = 0
        else:
            nama_menu = pilih_fd
            harga_fd_def = katalog_foodies.get(pilih_fd, {}).get("jual_satuan", 0)

        if st.session_state.get(f"fd_last_{rid}") != pilih_fd:
            st.session_state[f"fd_last_{rid}"] = pilih_fd
            st.session_state[f"fd_hrg_{rid}"] = harga_fd_def

        col_fq, col_fu, col_fh = st.columns([1, 1, 1.5])
        with col_fq:
            qty_f = st.number_input("Banyaknya", min_value=1, value=1, key=f"fd_qty_{rid}")
        with col_fu:
            unit_f = st.selectbox("Satuan", pilihan_satuan, key=f"fd_unit_{rid}")
        with col_fh:
            harga_f = st.number_input("Harga Satuan (Rp)", min_value=0, step=1000, key=f"fd_hrg_{rid}")

        if nama_menu.strip() and harga_f > 0:
            items_fd.append({"nama": nama_menu.strip(), "qty": int(qty_f), "unit": unit_f, "harga": int(harga_f)})

    c_fadd, c_frst = st.columns([2.5, 1.2])
    with c_fadd:
        if st.button("+ Tambah Baris Menu", key="fd_add_row", use_container_width=True):
            st.session_state.fd_row_ids.append(str(uuid.uuid4())[:6])
            st.rerun()
    with c_frst:
        if st.button("🧹 Reset Semua", key="fd_rst_all", use_container_width=True):
            for rid in st.session_state.fd_row_ids:
                for prefix in ("fd_sel_", "fd_last_", "fd_txt_", "fd_qty_", "fd_unit_", "fd_hrg_"):
                    st.session_state.pop(f"{prefix}{rid}", None)
            st.session_state.fd_row_ids = [str(uuid.uuid4())[:6]]
            st.session_state.fd_nota_preview = None
            st.rerun()

    col_fo, col_fd_disc = st.columns(2)
    with col_fo:
        f_ongkir = st.number_input("Ongkir (Rp)", min_value=0, step=1000, key="fd_ongkir")
    with col_fd_disc:
        f_diskon = st.number_input("Diskon (Rp)", min_value=0, step=1000, key="fd_diskon")

    if st.button("✨ Buat Nota Foodies", type="primary", key="fd_submit", use_container_width=True):
        if not f_nama.strip() or not items_fd:
            st.error("Isi Nama Customer dan minimal 1 menu terlebih dahulu.")
        else:
            bulan_id = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
            tgl_fmt = f"{f_tgl.day} {bulan_id[f_tgl.month - 1]} {f_tgl.year}"
            st.session_state.fd_nota_preview = {
                "order_id": "FOD-" + str(uuid.uuid4())[:6].upper(),
                "nama": f_nama.strip(),
                "tanggal": tgl_fmt,
                "tgl_iso": f_tgl.strftime("%Y-%m-%d"),
                "items": items_fd,
                "ongkir": int(f_ongkir),
                "diskon": int(f_diskon)
            }

    if "fd_nota_preview" in st.session_state and st.session_state.fd_nota_preview:
        prev_fd = st.session_state.fd_nota_preview
        tampilkan_nota_estetik(
            prev_fd,
            logo_bytes=logo_foodies_bytes,
            brand_type="foodies"
        )
        with st.expander("📥 Simpan Transaksi Ini ke Pembukuan Foodies (Rincian Per Menu)", expanded=False):
            st.caption("Isi harga modal bahan satuan tiap menu di bawah ini:")
            with st.form(f"form_catat_fd_{prev_fd['order_id']}"):
                modal_inputs_fd = []
                sisa_diskon_fd = int(prev_fd["diskon"])

                for idx_it, it in enumerate(prev_fd["items"]):
                    est_mod_sat = katalog_foodies.get(it["nama"], {}).get("modal_satuan", 0)
                    jual_baris = it["qty"] * it["harga"]
                    potongan = min(jual_baris, sisa_diskon_fd)
                    sisa_diskon_fd -= potongan
                    jual_bersih_baris = jual_baris - potongan

                    c_i1, c_i2 = st.columns([2, 1.3])
                    with c_i1:
                        st.markdown(
                            f"**{it['nama']}** ({it['qty']} {it.get('unit', 'pcs')})\n\n"
                            f"Jual: Rp {jual_bersih_baris:,.0f}".replace(",", ".")
                        )
                    with c_i2:
                        mod_sat_in = st.number_input(
                            "Modal Satuan (Rp)",
                            min_value=0,
                            step=2000,
                            value=int(est_mod_sat),
                            key=f"mod_sat_fd_{prev_fd['order_id']}_{idx_it}"
                        )
                    modal_inputs_fd.append((it, mod_sat_in, jual_bersih_baris))

                btn_catat_fd = st.form_submit_button("💾 Masukkan Semua Menu ke Pembukuan", type="primary", use_container_width=True)
                if btn_catat_fd:
                    with st.spinner("Menyimpan rincian ke pembukuan..."):
                        rows_to_add = []
                        tgl_tx = prev_fd.get("tgl_iso", datetime.date.today().strftime("%Y-%m-%d"))
                        for it, mod_sat_in, jual_bersih_baris in modal_inputs_fd:
                            rows_to_add.append({
                                "tgl_str": tgl_tx,
                                "toko": "Foodies",
                                "jenis": "Penjualan",
                                "keterangan": it["nama"],
                                "qty": int(it["qty"]),
                                "modal_brg": int(mod_sat_in) * int(it["qty"]),
                                "harga_jual": int(jual_bersih_baris),
                                "catatan": f"Nota {prev_fd['order_id']} ({prev_fd['nama']})"
                            })
                        tambah_banyak_entri_pembukuan(rows_to_add)
                        st.success(f"✅ {len(rows_to_add)} menu berhasil dicatat ke tab Pembukuan!")

# ==============================================================================
# TAB 3: PEMBUKUAN KEUANGAN (1 REKENING QRIS GABUNGAN UNTUK TARIK DANA)
# ==============================================================================
with tab_buku:
    st.subheader("📒 Pembukuan & Arus Kas QRIS")

    filter_toko = st.radio(
        "Filter Kinerja Toko:",
        ["Semua Toko", "Homedress", "Foodies"],
        horizontal=True,
        key="filter_buku_toko"
    )

    if filter_toko == "Semua Toko":
        buku_filtered = list(data_pembukuan)
    else:
        # Tetap sertakan transaksi Tarik Dana (Gabungan QRIS) di riwayat agar terlihat pencairan dari rekening bersama
        buku_filtered = [r for r in data_pembukuan if r["Toko"] in (filter_toko, "Gabungan QRIS")]

    # Kinerja per filter toko
    total_modal_awal = sum(r["Modal Barang"] for r in buku_filtered if r["Jenis"] == "Modal Awal")
    total_omzet = sum(r["Harga Jual"] for r in buku_filtered if r["Jenis"] == "Penjualan")
    total_hpp_terjual = sum(r["Modal Barang"] for r in buku_filtered if r["Jenis"] == "Penjualan")
    total_belanja_stok = sum(r["Modal Barang"] for r in buku_filtered if r["Jenis"] == "Belanja Stok")
    total_operasional = sum(r["Modal Barang"] for r in buku_filtered if r["Jenis"] == "Operasional")
    total_untung_bersih = (total_omzet - total_hpp_terjual) - total_operasional

    # Saldo Akhir Kas QRIS selalu dihitung dari 1 rekening gabungan (Homedress + Foodies - Belanja - Ops - Tarik Dana)
    semua_modal_awal = sum(r["Modal Barang"] for r in data_pembukuan if r["Jenis"] == "Modal Awal")
    semua_omzet = sum(r["Harga Jual"] for r in data_pembukuan if r["Jenis"] == "Penjualan")
    semua_belanja = sum(r["Modal Barang"] for r in data_pembukuan if r["Jenis"] == "Belanja Stok")
    semua_ops = sum(r["Modal Barang"] for r in data_pembukuan if r["Jenis"] == "Operasional")
    semua_tarik_dana = sum(r["Modal Barang"] for r in data_pembukuan if r["Jenis"] == "Tarik Dana")
    saldo_akhir_qris = semua_modal_awal + semua_omzet - semua_belanja - semua_ops - semua_tarik_dana

    fmt_rp = lambda n: f"Rp {int(n):,.0f}".replace(",", ".")

    c_k1, c_k2 = st.columns(2)
    with c_k1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>💰 MODAL AWAL ({filter_toko.upper()})</div>
                <div class='metric-val'>{fmt_rp(total_modal_awal)}</div>
                <div class='metric-sub'>Belanja Stok: {fmt_rp(total_belanja_stok)}</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>📈 UNTUNG BERSIH ({filter_toko.upper()})</div>
                <div class='metric-val' style='color:{"#2e7d32" if total_untung_bersih >= 0 else "#c62828"};'>{fmt_rp(total_untung_bersih)}</div>
                <div class='metric-sub'>Operasional: {fmt_rp(total_operasional)}</div>
            </div>
        """, unsafe_allow_html=True)
    with c_k2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>🛍️ OMZET ({filter_toko.upper()})</div>
                <div class='metric-val'>{fmt_rp(total_omzet)}</div>
                <div class='metric-sub'>Modal Barang Terjual: {fmt_rp(total_hpp_terjual)}</div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <div class='metric-card' style='background:#fce4ec;'>
                <div class='metric-label'>🏦 SALDO AKHIR REKENING QRIS</div>
                <div class='metric-val' style='color:#d81b60;'>{fmt_rp(saldo_akhir_qris)}</div>
                <div class='metric-sub'>Total Ditarik: {fmt_rp(semua_tarik_dana)}</div>
            </div>
        """, unsafe_allow_html=True)

    # --- FORM TAMBAH CATATAN BARU (TARIK DANA TANPA PILIH TOKO) ---
    with st.expander("➕ Tambah Catatan Pembukuan / Tarik Dana QRIS", expanded=True):
        jenis_pilihan = st.selectbox(
            "Jenis Transaksi",
            ["Penjualan", "Tarik Dana", "Modal Awal", "Belanja Stok", "Operasional"],
            format_func=lambda x: {
                "Penjualan": "🛍️ Penjualan Barang (Bisa banyak item & harga berbeda-beda)",
                "Tarik Dana": "💸 Tarik Saldo QRIS (1 Rekening Gabungan — Tanpa Pilih Toko)",
                "Modal Awal": "💰 Modal Awal / Tambah Saldo Kas",
                "Belanja Stok": "📦 Belanja Stok / Bahan Baku (Bisa banyak item & harga berbeda)",
                "Operasional": "🧾 Biaya Operasional / Kemasan / Ongkir"
            }[x],
            key="bk_jenis"
        )

        # Jika Tarik Dana, tidak perlu pilih toko karena 1 rekening QRIS bersama
        if jenis_pilihan == "Tarik Dana":
            b_tgl = st.date_input("Tanggal Penarikan", value=datetime.date.today(), key="bk_tgl_tarik")
            st.info(f"🏦 **Saldo Rekening QRIS Gabungan Saat Ini:** **{fmt_rp(saldo_akhir_qris)}**")

            b_ket = st.text_input(
                "Tujuan Penarikan Dana",
                value="Tarik Saldo QRIS ke Rekening",
                placeholder="Contoh: Tarik QRIS ke BCA / Ambil Uang Tunai",
                key="bk_ket_tarik"
            )
            b_modal = st.number_input("Nominal Dana yang Ditarik (Rp)", min_value=0, step=50000, key="bk_nom_tarik")
            b_catatan = st.text_input("Catatan Tambahan (Opsional)", placeholder="Contoh: Cair ke BCA a.n. Kamila", key="bk_catatan_tarik")

            if b_modal > 0:
                sisa_setelah_tarik = saldo_akhir_qris - int(b_modal)
                st.caption(f"Perkiraan Sisa Saldo QRIS Setelah Penarikan: **{fmt_rp(sisa_setelah_tarik)}**")

            if st.button("💸 Catat Tarik Saldo QRIS", type="primary", key="bk_submit_tarik", use_container_width=True):
                if not b_ket.strip() or b_modal == 0:
                    st.error("Tujuan penarikan dan nominal wajib diisi!")
                else:
                    with st.spinner("Mencatat penarikan dana ke Google Sheets..."):
                        tambah_entri_pembukuan(
                            tgl_str=b_tgl.strftime("%Y-%m-%d"),
                            toko="Gabungan QRIS",
                            jenis="Tarik Dana",
                            keterangan=b_ket.strip(),
                            qty=1,
                            modal_brg=int(b_modal),
                            harga_jual=0,
                            catatan=b_catatan.strip()
                        )
                        st.success(f"✅ Penarikan saldo QRIS sebesar {fmt_rp(b_modal)} berhasil dicatat!")
                        st.rerun()

        else:
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                b_tgl = st.date_input("Tanggal", value=datetime.date.today(), key="bk_tgl")
            with c_b2:
                idx_toko_def = 1 if filter_toko == "Foodies" else 0
                b_toko = st.selectbox("Toko", ["Homedress", "Foodies"], index=idx_toko_def, key="bk_toko")

            katalog_aktif = katalog_homedress if b_toko == "Homedress" else katalog_foodies
            label_baru = "-- Ketik Set Baju / Barang Baru --" if b_toko == "Homedress" else "-- Ketik Menu Foodies Baru --"
            daftar_opsi_item = [label_baru] + sorted(katalog_aktif.keys())

            if jenis_pilihan in ("Penjualan", "Belanja Stok"):
                if "bk_row_ids" not in st.session_state or not st.session_state.bk_row_ids:
                    st.session_state.bk_row_ids = [str(uuid.uuid4())[:6]]

                entri_siap_simpan = []
                jumlah_baris_bk = len(st.session_state.bk_row_ids)
                grand_modal_bk = 0
                grand_jual_bk = 0

                for idx_bk, rid in enumerate(list(st.session_state.bk_row_ids)):
                    c_lbl, c_del = st.columns([3.5, 1])
                    with c_lbl:
                        st.markdown(f"**Item #{idx_bk + 1}**")
                    with c_del:
                        if jumlah_baris_bk > 1:
                            if st.button("🗑️ Hapus", key=f"bk_del_{rid}", use_container_width=True):
                                st.session_state.bk_row_ids.remove(rid)
                                for prefix in ("bk_sel_", "bk_last_", "bk_txt_", "bk_qty_", "bk_mod_sat_", "bk_jual_sat_"):
                                    st.session_state.pop(f"{prefix}{rid}", None)
                                st.rerun()

                    pilih_item_bk = st.selectbox(
                        "Pilih Barang/Menu",
                        daftar_opsi_item,
                        key=f"bk_sel_{rid}",
                        label_visibility="collapsed"
                    )
                    if pilih_item_bk == label_baru:
                        nama_item_bk = st.text_input(
                            "Ketik Nama Baru",
                            placeholder="Contoh: Setelan Rayon Kanaya" if b_toko == "Homedress" else "Contoh: Pempek Kapal Selam",
                            key=f"bk_txt_{rid}",
                            label_visibility="collapsed"
                        )
                        mod_sat_def = 0
                        jual_sat_def = 0
                    else:
                        nama_item_bk = pilih_item_bk
                        info_item = katalog_aktif.get(pilih_item_bk, {})
                        mod_sat_def = int(info_item.get("modal_satuan", 0))
                        jual_sat_def = int(info_item.get("jual_satuan", 0))

                    key_trigger = f"{b_toko}|{pilih_item_bk}"
                    if st.session_state.get(f"bk_last_{rid}") != key_trigger:
                        st.session_state[f"bk_last_{rid}"] = key_trigger
                        st.session_state[f"bk_mod_sat_{rid}"] = mod_sat_def
                        st.session_state[f"bk_jual_sat_{rid}"] = jual_sat_def

                    if jenis_pilihan == "Penjualan":
                        cq, cm, cj = st.columns([0.8, 1.3, 1.3])
                        with cq:
                            qty_bk = st.number_input("Jml", min_value=1, value=1, key=f"bk_qty_{rid}")
                        with cm:
                            mod_sat_in = st.number_input("Modal Satuan (Rp)", min_value=0, step=1000, key=f"bk_mod_sat_{rid}")
                        with cj:
                            jual_sat_in = st.number_input("Jual Satuan (Rp)", min_value=0, step=1000, key=f"bk_jual_sat_{rid}")

                        sub_mod = int(qty_bk) * int(mod_sat_in)
                        sub_jual = int(qty_bk) * int(jual_sat_in)
                        sub_untung = sub_jual - sub_mod
                        grand_modal_bk += sub_mod
                        grand_jual_bk += sub_jual

                        st.caption(
                            f"Subtotal Item #{idx_bk + 1}: Modal **Rp {sub_mod:,.0f}** | "
                            f"Jual **Rp {sub_jual:,.0f}** | Untung **Rp {sub_untung:,.0f}**".replace(",", ".")
                        )
                    else:
                        cq, cm = st.columns([0.8, 2.6])
                        with cq:
                            qty_bk = st.number_input("Jml", min_value=1, value=1, key=f"bk_qty_{rid}")
                        with cm:
                            mod_sat_in = st.number_input("Harga Beli Satuan (Rp)", min_value=0, step=1000, key=f"bk_mod_sat_{rid}")
                        jual_sat_in = 0
                        sub_mod = int(qty_bk) * int(mod_sat_in)
                        sub_jual = 0
                        grand_modal_bk += sub_mod
                        st.caption(f"Subtotal Belanja Item #{idx_bk + 1}: **Rp {sub_mod:,.0f}**".replace(",", "."))

                    if nama_item_bk.strip() and (sub_mod > 0 or sub_jual > 0):
                        entri_siap_simpan.append({
                            "nama": nama_item_bk.strip(),
                            "qty": int(qty_bk),
                            "modal_brg": sub_mod,
                            "harga_jual": sub_jual
                        })

                c_bk_add, c_bk_rst = st.columns([2.5, 1.2])
                with c_bk_add:
                    if st.button("+ Tambah Baris Item (Harga Berbeda)", key="bk_add_row", use_container_width=True):
                        st.session_state.bk_row_ids.append(str(uuid.uuid4())[:6])
                        st.rerun()
                with c_bk_rst:
                    if st.button("🧹 Reset Baris", key="bk_rst_rows", use_container_width=True):
                        for rid in st.session_state.bk_row_ids:
                            for prefix in ("bk_sel_", "bk_last_", "bk_txt_", "bk_qty_", "bk_mod_sat_", "bk_jual_sat_"):
                                st.session_state.pop(f"{prefix}{rid}", None)
                        st.session_state.bk_row_ids = [str(uuid.uuid4())[:6]]
                        st.rerun()

                if jenis_pilihan == "Penjualan":
                    st.info(
                        f"**Total Keseluruhan Transaksi:** Modal **Rp {grand_modal_bk:,.0f}** | "
                        f"Jual **Rp {grand_jual_bk:,.0f}** | Untung **Rp {grand_jual_bk - grand_modal_bk:,.0f}**".replace(",", ".")
                    )
                else:
                    st.info(f"**Total Belanja Stok:** **Rp {grand_modal_bk:,.0f}**".replace(",", "."))

                b_catatan = st.text_input("Catatan Tambahan (Opsional)", placeholder="Contoh: Pembeli Bude Heni / Transfer BCA", key="bk_catatan")

                if st.button("💾 Simpan ke Pembukuan", type="primary", key="bk_submit_multi", use_container_width=True):
                    if not entri_siap_simpan:
                        st.error("Isi minimal 1 barang/menu beserta nominal harganya.")
                    else:
                        with st.spinner("Menyimpan seluruh item ke Google Sheets..."):
                            rows_payload = []
                            tgl_str_save = b_tgl.strftime("%Y-%m-%d")
                            for item in entri_siap_simpan:
                                rows_payload.append({
                                    "tgl_str": tgl_str_save,
                                    "toko": b_toko,
                                    "jenis": jenis_pilihan,
                                    "keterangan": item["nama"],
                                    "qty": item["qty"],
                                    "modal_brg": item["modal_brg"],
                                    "harga_jual": item["harga_jual"],
                                    "catatan": b_catatan.strip()
                                })
                            tambah_banyak_entri_pembukuan(rows_payload)
                            for rid in st.session_state.bk_row_ids:
                                for prefix in ("bk_sel_", "bk_last_", "bk_txt_", "bk_qty_", "bk_mod_sat_", "bk_jual_sat_"):
                                    st.session_state.pop(f"{prefix}{rid}", None)
                            st.session_state.bk_row_ids = [str(uuid.uuid4())[:6]]
                            st.success(f"✅ {len(rows_payload)} item berhasil disimpan ke pembukuan!")
                            st.rerun()

            elif jenis_pilihan == "Modal Awal":
                b_ket = st.text_input("Keterangan Modal", value="Modal Awal Kas", key="bk_ket_modal")
                b_modal = st.number_input("Nominal Modal Awal (Rp)", min_value=0, step=50000, key="bk_nom_modal")
                b_catatan = st.text_input("Catatan Tambahan (Opsional)", placeholder="Contoh: Modal awal dari tabungan", key="bk_catatan_mod")

                if st.button("💾 Simpan Modal Awal", type="primary", key="bk_submit_mod", use_container_width=True):
                    if not b_ket.strip() or b_modal == 0:
                        st.error("Keterangan dan nominal modal wajib diisi!")
                    else:
                        with st.spinner("Menyimpan ke pembukuan..."):
                            tambah_entri_pembukuan(
                                tgl_str=b_tgl.strftime("%Y-%m-%d"),
                                toko=b_toko,
                                jenis="Modal Awal",
                                keterangan=b_ket.strip(),
                                qty=1,
                                modal_brg=int(b_modal),
                                harga_jual=0,
                                catatan=b_catatan.strip()
                            )
                            st.success("✅ Modal awal berhasil disimpan!")
                            st.rerun()
            else:
                b_ket = st.text_input("Keterangan Biaya Operasional", placeholder="Contoh: Plastik Packing / Lakban / Ongkir", key="bk_ket_ops")
                c_o1, c_o2 = st.columns([0.8, 2.2])
                with c_o1:
                    b_qty = st.number_input("Jml", min_value=1, value=1, key="bk_qty_ops")
                with c_o2:
                    b_modal = st.number_input("Nominal Biaya (Rp)", min_value=0, step=5000, key="bk_nom_ops")
                b_catatan = st.text_input("Catatan Tambahan (Opsional)", placeholder="Contoh: Beli di toko plastik", key="bk_catatan_ops")

                if st.button("💾 Simpan Biaya Operasional", type="primary", key="bk_submit_ops", use_container_width=True):
                    if not b_ket.strip() or b_modal == 0:
                        st.error("Keterangan dan nominal biaya wajib diisi!")
                    else:
                        with st.spinner("Menyimpan ke pembukuan..."):
                            tambah_entri_pembukuan(
                                tgl_str=b_tgl.strftime("%Y-%m-%d"),
                                toko=b_toko,
                                jenis="Operasional",
                                keterangan=b_ket.strip(),
                                qty=int(b_qty),
                                modal_brg=int(b_modal),
                                harga_jual=0,
                                catatan=b_catatan.strip()
                            )
                            st.success("✅ Biaya operasional berhasil disimpan!")
                            st.rerun()

    # --- TABEL RIWAYAT PEMBUKUAN ---
    st.subheader("📋 Riwayat Transaksi")
    if not buku_filtered:
        st.info("Belum ada catatan pembukuan. Mulai dengan menambahkan **Modal Awal** atau transaksi penjualan di atas.")
    else:
        buku_tampil = list(reversed(buku_filtered))
        tabel_ringkas = []
        for r in buku_tampil:
            tabel_ringkas.append({
                "ID": r["ID"],
                "Tanggal": r["Tanggal"],
                "Toko": r["Toko"],
                "Jenis": r["Jenis"],
                "Barang / Keterangan": f"{r['Keterangan']} ({r['Qty']}x)" if r["Qty"] > 1 else r["Keterangan"],
                "Modal/Keluar/Tarik": fmt_rp(r["Modal Barang"]) if r["Modal Barang"] > 0 else "-",
                "Harga Jual": fmt_rp(r["Harga Jual"]) if r["Harga Jual"] > 0 else "-",
                "Untung": fmt_rp(r["Untung"]) if r["Jenis"] == "Penjualan" else "-"
            })
        st.dataframe(tabel_ringkas, use_container_width=True, hide_index=True)

        # --- EDIT / HAPUS CATATAN PEMBUKUAN ---
        with st.expander("✏️ Edit atau Hapus Catatan Pembukuan", expanded=False):
            opsi_edit = [
                f"{r['ID']} | {r['Tanggal']} | [{r['Toko']}] {r['Keterangan']}"
                for r in buku_tampil
            ]
            pilih_tx_label = st.selectbox("Pilih Transaksi yang Ingin Diedit / Dihapus", opsi_edit, key="pilih_edit_buku")
            idx_dipilih = opsi_edit.index(pilih_tx_label)
            tx_lama = buku_tampil[idx_dipilih]

            try:
                tgl_default_edit = datetime.date.fromisoformat(tx_lama["Tanggal"])
            except Exception:
                tgl_default_edit = datetime.date.today()

            list_jenis = ["Penjualan", "Tarik Dana", "Modal Awal", "Belanja Stok", "Operasional"]
            idx_jenis_lama = list_jenis.index(tx_lama["Jenis"]) if tx_lama["Jenis"] in list_jenis else 0
            list_toko_edit = ["Homedress", "Foodies", "Gabungan QRIS"]
            idx_toko_lama = list_toko_edit.index(tx_lama["Toko"]) if tx_lama["Toko"] in list_toko_edit else 0

            with st.form(f"form_edit_buku_{tx_lama['ID']}"):
                ce1, ce2, ce3 = st.columns(3)
                with ce1:
                    e_tgl = st.date_input("Tanggal", value=tgl_default_edit)
                with ce2:
                    e_toko = st.selectbox("Toko / Sumber", list_toko_edit, index=idx_toko_lama)
                with ce3:
                    e_jenis = st.selectbox("Jenis", list_jenis, index=idx_jenis_lama)

                e_ket = st.text_input("Nama Barang / Keterangan", value=tx_lama["Keterangan"])

                ce4, ce5, ce6 = st.columns([0.8, 1.3, 1.3])
                with ce4:
                    e_qty = st.number_input("Jml", min_value=1, value=max(1, int(tx_lama["Qty"])))
                with ce5:
                    e_modal = st.number_input("Modal / Keluar / Tarik (Rp)", min_value=0, step=1000, value=int(tx_lama["Modal Barang"]))
                with ce6:
                    e_jual = st.number_input("Total Harga Jual (Rp)", min_value=0, step=1000, value=int(tx_lama["Harga Jual"]))

                e_catatan = st.text_input("Catatan", value=tx_lama["Catatan"])

                cb_save, cb_del = st.columns(2)
                with cb_save:
                    btn_update_tx = st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True)
                with cb_del:
                    btn_hapus_tx = st.form_submit_button("🗑️ Hapus Transaksi", use_container_width=True)

                if btn_update_tx:
                    if not e_ket.strip():
                        st.error("Nama barang / keterangan tidak boleh kosong.")
                    else:
                        with st.spinner("Memperbarui catatan..."):
                            update_entri_pembukuan(
                                row_num=tx_lama["row_num"],
                                id_tx=tx_lama["ID"],
                                tgl_str=e_tgl.strftime("%Y-%m-%d"),
                                toko="Gabungan QRIS" if e_jenis == "Tarik Dana" else e_toko,
                                jenis=e_jenis,
                                keterangan=e_ket.strip(),
                                qty=int(e_qty),
                                modal_brg=int(e_modal),
                                harga_jual=int(e_jual),
                                catatan=e_catatan.strip()
                            )
                            st.success(f"✅ Transaksi {tx_lama['ID']} berhasil diperbarui!")
                            st.rerun()

                if btn_hapus_tx:
                    with st.spinner("Menghapus catatan..."):
                        hapus_entri_pembukuan(tx_lama["row_num"])
                        st.warning(f"Transaksi {tx_lama['ID']} telah dihapus.")
                        st.rerun()
