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
import time
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Admin & Nota ByKamila", page_icon="🌸", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .login-card {
            background: #fff8fa;
            border: 1.5px solid #f48fb1;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            margin-bottom: 15px;
        }
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
    </style>
""", unsafe_allow_html=True)

# --- 2. KUNCI KEAMANAN & FUNGSI TANDA TANGAN DIGITAL ---
PIN_ADMIN = str(st.secrets.get("admin_pin", "0305")).strip()
SALT_KEY = str(st.secrets.get("gcp_service_account", {}).get("private_key_id", "bykamila_secret"))
SESSION_TOKEN = hashlib.sha256(f"{PIN_ADMIN}:{SALT_KEY}".encode()).hexdigest()[:24]

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

# --- 3. KONEKSI & CACHE DATA GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database_ByKamila")

@st.cache_data(ttl=45, show_spinner=False)
def load_admin_data():
    db = get_google_sheet()
    ws_produk = db.worksheet("Produk")
    ws_pesanan = db.worksheet("Pesanan")

    # Pastikan header kolom H (Keterangan) tersedia otomatis
    header_produk = ws_produk.row_values(1)
    if len(header_produk) < 8 or str(header_produk[7]).strip() != "Keterangan":
        ws_produk.update_cell(1, 8, "Keterangan")

    data_produk = ws_produk.get_all_records()
    data_pesanan = ws_pesanan.get_all_records()

    try:
        ws_cfg = db.worksheet("Pengaturan")
    except gspread.WorksheetNotFound:
        ws_cfg = db.add_worksheet(title="Pengaturan", rows=10, cols=2)
        ws_cfg.append_row(["Kunci", "Nilai"])
        ws_cfg.append_row(["qris_url", ""])
        ws_cfg.append_row(["info_bayar", ""])
        ws_cfg.append_row(["admin_url", ""])
    cfg_toko = {str(r["Kunci"]): str(r["Nilai"]) for r in ws_cfg.get_all_records()}

    return data_produk, data_pesanan, cfg_toko

def simpan_pengaturan(kunci, nilai):
    db = get_google_sheet()
    ws_cfg = db.worksheet("Pengaturan")
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

# --- 4. MODE VERIFIKASI PUBLIK SAAT QR CODE DI NOTA LUNAS DI-SCAN ---
if "cek" in st.query_params:
    cek_id = str(st.query_params.get("cek", "")).strip()
    cek_sig = str(st.query_params.get("sig", "")).strip().upper()
    cek_nama = str(st.query_params.get("n", "")).strip()
    cek_tot = int(st.query_params.get("t", "0")) if str(st.query_params.get("t", "0")).isdigit() else 0

    st.markdown("<h2 style='text-align: center; color: #d81b60; font-family: cursive;'>♡ Verifikasi Nota ByKamila ♡</h2>", unsafe_allow_html=True)

    expected_sig = buat_signature_nota(cek_id, cek_nama, cek_tot)
    sig_cocok = (cek_sig == expected_sig and cek_tot > 0)

    if cek_id.startswith("ORD-"):
        try:
            _, semua_order, _ = load_admin_data()
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
            st.markdown("""
                <div class='verify-invalid'>
                    <h3 style='margin-top:0;'>❌ NOTA TIDAK VALID / DATA TELAH DIUBAH</h3>
                    <p>Kode validasi tidak cocok dengan catatan resmi Homedress ByKamila.</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        if sig_cocok:
            st.markdown(f"""
                <div class='verify-valid'>
                    <h3 style='margin-top:0;'>✅ NOTA RESMI TERVERIFIKASI LUNAS</h3>
                    <p><b>No. Referensi:</b> {cek_id}<br>
                    <b>Kode Validasi:</b> {cek_sig}<br>
                    <b>Nama Customer:</b> {cek_nama}<br>
                    <b>Total Sah:</b> Rp {cek_tot:,.0f}</p>
                </div>
            """.replace(",", "."), unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class='verify-invalid'>
                    <h3 style='margin-top:0;'>❌ NOTA TIDAK VALID / DATA TELAH DIUBAH</h3>
                    <p>Kode validasi tidak cocok dengan tanda tangan digital resmi ByKamila.</p>
                </div>
            """, unsafe_allow_html=True)

    st.stop()

# --- 5. SISTEM LOGIN, LOGOUT & KEAMANAN PIN ADMIN ---
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "lockout_until" not in st.session_state:
    st.session_state.lockout_until = 0.0

if not st.session_state.admin_auth:
    if st.query_params.get("token") == SESSION_TOKEN:
        st.session_state.admin_auth = True

if not st.session_state.admin_auth:
    st.markdown("""
        <div class='login-card'>
            <h2 style='color: #d81b60; font-family: cursive; margin-bottom: 4px;'>♡ Admin ByKamila ♡</h2>
            <p style='color: #666; font-size: 13px; margin: 0;'>Silakan masukkan PIN untuk mengelola pesanan & stok</p>
        </div>
    """, unsafe_allow_html=True)

    sisa_kunci = int(st.session_state.lockout_until - time.time())
    if sisa_kunci > 0:
        st.error(f"Terlalu banyak percobaan salah. Coba lagi dalam {sisa_kunci} detik.")
        st.stop()

    with st.form("form_login_admin"):
        pin_input = st.text_input("PIN Admin", type="password", placeholder="Masukkan PIN...")
        ingat_saya = st.checkbox("Ingat saya di HP ini (tidak perlu ketik PIN tiap buka)", value=True)
        btn_masuk = st.form_submit_button("🔓 Masuk ke Halaman Admin", type="primary", use_container_width=True)

        if btn_masuk:
            if pin_input.strip() == PIN_ADMIN:
                st.session_state.admin_auth = True
                st.session_state.login_attempts = 0
                if ingat_saya:
                    st.query_params["token"] = SESSION_TOKEN
                else:
                    if "token" in st.query_params:
                        del st.query_params["token"]
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                sisa_coba = 5 - st.session_state.login_attempts
                if sisa_coba <= 0:
                    st.session_state.lockout_until = time.time() + 30
                    st.session_state.login_attempts = 0
                    st.error("PIN salah 5 kali. Halaman dikunci selama 30 detik.")
                else:
                    st.error(f"PIN salah! Sisa percobaan: {sisa_coba} kali.")
    st.stop()

def proses_logout():
    st.session_state.admin_auth = False
    st.session_state.nota_verified = None
    st.session_state.nota_manual_preview = None
    if "token" in st.query_params:
        del st.query_params["token"]
    st.rerun()

# --- AMBIL DATA ADMIN DARI CACHE ---
try:
    data_produk_admin, semua_pesanan, cfg_toko = load_admin_data()
except Exception as e:
    if "429" in str(e):
        st.warning("⏳ Kuota akses Google Sheets sedang penuh sementara. Tunggu 30–60 detik lalu tekan tombol **🔄 Coba Lagi**.")
        if st.button("🔄 Coba Lagi"):
            load_admin_data.clear()
            st.rerun()
    else:
        st.error(f"Gagal terhubung ke Database: {e}")
    st.stop()

# --- 6. FUNGSI UPLOAD FOTO KE IMGBB ---
def upload_foto_galeri(uploaded_file):
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
        return None, f"Gagal upload ke ImgBB: {hasil.get('error', {}).get('message', 'Error tidak diketahui')}"
    except Exception as e:
        return None, f"Koneksi upload gagal: {e}"

# --- 7. FUNGSI RENDER NOTA PINK ESTETIK + QR KEASLIAN + WATERMARK ---
def tampilkan_nota_estetik(payload_nota):
    subtotal_calc = sum(int(it["qty"]) * int(it["harga"]) for it in payload_nota["items"])
    total_akhir_calc = subtotal_calc - int(payload_nota["diskon"]) + int(payload_nota["ongkir"])
    order_id = payload_nota.get("order_id", "MAN-" + str(uuid.uuid4())[:6].upper())
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

    data_for_js = dict(payload_nota)
    data_for_js["order_id"] = order_id
    data_for_js["sig_code"] = sig_code
    data_for_js["verify_url"] = verify_url

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
            body { background: transparent; padding: 5px; }
            .nota-box {
                background: white;
                width: 100%;
                max-width: 450px;
                margin: 0 auto;
                padding: 25px 20px;
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
            }
            .watermark {
                position: absolute;
                top: 46%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-24deg);
                font-size: 28px;
                font-weight: 700;
                color: rgba(216, 27, 96, 0.06);
                white-space: nowrap;
                pointer-events: none;
                z-index: 0;
                letter-spacing: 3px;
            }
            .content-layer { position: relative; z-index: 1; }
            .header-nota { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
            .brand h1 { font-family: 'Dancing Script', cursive; font-size: 42px; line-height: 0.9; }
            .brand p { font-family: 'Dancing Script', cursive; font-size: 22px; text-align: center; }
            .contact { font-size: 13px; font-weight: 700; text-align: right; color: var(--pink-main); }
            .contact p { display: flex; align-items: center; justify-content: flex-end; gap: 6px; margin-bottom: 4px; }
            .thanks-top { font-family: 'Dancing Script', cursive; font-size: 20px; text-align: center; margin-top: 8px; }
            .info-row { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
            .info-box {
                border: 1.5px solid var(--pink-border);
                border-radius: 25px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: 700;
                text-align: center;
                flex: 1;
                background: rgba(255,255,255,0.85);
            }
            .info-box span { display: block; color: var(--text-dark); font-size: 14px; margin-top: 3px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 14px; text-align: center; background: rgba(255,255,255,0.85); }
            table th, table td { border: 1.5px solid var(--pink-border); padding: 8px 6px; font-weight: 600; }
            table th { background-color: var(--pink-light); font-size: 13px; color: var(--pink-main); }
            table td { color: var(--text-dark); font-size: 13px; }
            .align-right { text-align: right; }
            .align-left { text-align: left; }
            .grand-total { font-family: 'Dancing Script', cursive; font-size: 28px; color: var(--pink-main); background-color: var(--pink-light); }
            .grand-total-val { font-size: 20px; color: var(--pink-main); background-color: var(--pink-light); font-weight: 700; }
            .footer-area {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                background-color: var(--pink-light);
                border-radius: 15px;
                padding: 12px 14px;
                margin-top: 8px;
            }
            .footer-text { text-align: left; flex: 1; }
            .auth-badge {
                display: inline-block;
                margin-top: 5px;
                font-size: 10px;
                font-weight: 700;
                color: #2e7d32;
                background: #e8f5e9;
                border: 1px solid #a5d6a7;
                padding: 2px 8px;
                border-radius: 10px;
            }
            #qrcode-box {
                background: white;
                padding: 5px;
                border-radius: 8px;
                border: 1px solid var(--pink-border);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .btn-dl {
                display: block; width: 100%; max-width: 450px; margin: 14px auto 0;
                background-color: #2e7d32; color: white; border: none; padding: 13px;
                border-radius: 12px; font-weight: 700; font-size: 15px; cursor: pointer;
            }
            .btn-dl:active { transform: scale(0.98); }
            #jpg-preview-area {
                display: none; max-width: 450px; margin: 12px auto 0; text-align: center;
                background: #fff8fa; border: 2px dashed var(--pink-border); border-radius: 12px; padding: 10px;
            }
            #jpg-preview-area img { width: 100%; border-radius: 8px; margin-top: 6px; }
        </style>
    </head>
    <body>
        <div class="nota-box" id="nota-area">
            <div class="watermark" id="wm-text">LUNAS • BYKAMILA</div>
            <div class="content-layer">
                <div class="header-nota">
                    <div class="brand">
                        <h1>homedress</h1>
                        <p>♡ bykamila ♡</p>
                    </div>
                    <div>
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
                        <div class="thanks-top">Terima Kasih<br>Sudah Belanja ♡</div>
                    </div>
                </div>

                <div class="info-row">
                    <div class="info-box">Nama Customer<span id="out-nama"></span></div>
                    <div class="info-box">Tanggal Order<span id="out-tanggal"></span></div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th width="10%">No</th>
                            <th width="45%">Nama Barang</th>
                            <th width="20%">Jumlah</th>
                            <th width="25%">Harga</th>
                        </tr>
                    </thead>
                    <tbody id="out-items"></tbody>
                    <tbody>
                        <tr>
                            <td colspan="3" class="align-left" style="background-color: var(--pink-light);">Subtotal</td>
                            <td class="align-right" style="background-color: var(--pink-light);" id="out-subtotal"></td>
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
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-dark);">Semoga suka dengan produknya di Homedress bykamila</span><br>
                        <span class="auth-badge" id="out-auth">✔ LUNAS • AUTH: </span>
                    </div>
                    <div id="qrcode-box"></div>
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
            const formatRp = (n) => new Intl.NumberFormat('id-ID').format(n);

            document.getElementById('out-nama').innerText = data.nama;
            document.getElementById('out-tanggal').innerText = data.tanggal;
            document.getElementById('wm-text').innerText = `LUNAS • ${data.order_id} • BYKAMILA`;
            document.getElementById('out-auth').innerText = `✔ LUNAS • ${data.order_id} • AUTH: ${data.sig_code}`;

            let rowsHTML = '';
            let subtotal = 0;
            const minRows = Math.max(3, data.items.length);

            for (let i = 0; i < minRows; i++) {
                if (i < data.items.length) {
                    const it = data.items[i];
                    const lineTotal = it.qty * it.harga;
                    subtotal += lineTotal;
                    rowsHTML += `
                        <tr>
                            <td>${i + 1}</td>
                            <td class="align-left">${it.nama}</td>
                            <td>${it.qty} pcs</td>
                            <td class="align-right">Rp ${formatRp(lineTotal)}</td>
                        </tr>`;
                } else {
                    rowsHTML += `<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>`;
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
            document.getElementById('out-total').innerText = 'Rp ' + formatRp(totalAkhir);

            new QRCode(document.getElementById("qrcode-box"), {
                text: data.verify_url,
                width: 64,
                height: 64,
                colorDark: "#d81b60",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });

            function downloadNotaJPG() {
                html2canvas(document.getElementById('nota-area'), { scale: 2, backgroundColor: "#ffffff" }).then(canvas => {
                    const url = canvas.toDataURL('image/jpeg', 0.95);
                    document.getElementById('img-hasil').src = url;
                    document.getElementById('jpg-preview-area').style.display = 'block';

                    const a = document.createElement('a');
                    a.download = `Nota_Lunas_${data.nama}.jpg`;
                    a.href = url;
                    a.click();
                });
            }
        </script>
    </body>
    </html>
    """
    final_html = html_template.replace("__DATA_JSON__", json.dumps(data_for_js))
    components.html(final_html, height=780, scrolling=True)

# --- 8. HEADER & TOMBOL REFRESH / LOGOUT ---
col_head1, col_head2, col_head3 = st.columns([3.2, 1.1, 1.1])
with col_head1:
    st.markdown("<h3 style='color: #d81b60; font-family: cursive; margin:0;'>♡ Admin ByKamila ♡</h3>", unsafe_allow_html=True)
with col_head2:
    if st.button("🔄 Refresh", use_container_width=True):
        load_admin_data.clear()
        st.rerun()
with col_head3:
    if st.button("🚪 Logout", use_container_width=True):
        proses_logout()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Pesanan", "🧾 Nota", "📦 Stok", "💳 QRIS"])

# ==============================================================================
# TAB 1: VERIFIKASI & CANCEL PESANAN DARI KATALOG
# ==============================================================================
with tab1:
    if "nota_verified" in st.session_state and st.session_state.nota_verified:
        st.success("✅ Pesanan berhasil diverifikasi Lunas & stok otomatis diperbarui!")
        tampilkan_nota_estetik(st.session_state.nota_verified)
        if st.button("⬅️ Kembali ke Daftar Pesanan Masuk", use_container_width=True):
            st.session_state.nota_verified = None
            st.rerun()
        st.divider()

    pesanan_pending = {}

    for idx, row in enumerate(semua_pesanan, start=2):
        if str(row.get("Status", "")).strip() == "Menunggu Verifikasi":
            oid = str(row["ID Pesanan"])
            if oid not in pesanan_pending:
                pesanan_pending[oid] = {
                    "id": oid,
                    "tgl": str(row["Tgl"]),
                    "nama": str(row["Nama Customer"]),
                    "wa": str(row["No WA"]),
                    "items": [],
                    "rows": []
                }
            qty = int(row["Jml"])
            tot = int(row["Total Harga"])
            harga_satuan = int(tot / qty) if qty > 0 else 0
            pesanan_pending[oid]["items"].append({
                "nama": str(row["Nama Barang"]),
                "qty": qty,
                "harga": harga_satuan,
                "subtotal": tot
            })
            pesanan_pending[oid]["rows"].append(idx)

    if not pesanan_pending:
        st.info("Belum ada pesanan baru yang menunggu verifikasi.")
    else:
        st.write(f"Ditemukan **{len(pesanan_pending)}** pesanan menunggu konfirmasi:")
        for oid, order in pesanan_pending.items():
            with st.container(border=True):
                c_info, c_wa = st.columns([3, 1.3])
                with c_info:
                    st.markdown(f"**{order['nama']}** (`{oid}`)")
                    st.caption(f"Waktu Booking: {order['tgl']} | WA: {order['wa']}")
                with c_wa:
                    wa_clean = order['wa'].strip().lstrip("0")
                    if not wa_clean.startswith("62"):
                        wa_clean = "62" + wa_clean
                    st.link_button("💬 Chat WA", f"https://wa.me/{wa_clean}", use_container_width=True)

                total_brg = 0
                for it in order["items"]:
                    st.write(f"• {it['nama']} — **{it['qty']} pcs** (Rp {it['subtotal']:,.0f})".replace(",", "."))
                    total_brg += it["subtotal"]
                st.markdown(f"**Subtotal Barang: Rp {total_brg:,.0f}**".replace(",", "."))

                c_ongkir, c_diskon = st.columns(2)
                with c_ongkir:
                    ongkir_in = st.number_input("Ongkir (Rp)", min_value=0, step=1000, key=f"ong_{oid}")
                with c_diskon:
                    diskon_in = st.number_input("Diskon (Rp)", min_value=0, step=1000, key=f"dis_{oid}")

                btn_verif, btn_cancel = st.columns(2)
                with btn_verif:
                    if st.button("✅ Verifikasi Lunas", key=f"ok_{oid}", type="primary", use_container_width=True):
                        with st.spinner("Memproses verifikasi & mengurangi stok..."):
                            db = get_google_sheet()
                            ws_produk = db.worksheet("Produk")
                            ws_pesanan = db.worksheet("Pesanan")
                            data_prod = ws_produk.get_all_records()

                            for r_idx in order["rows"]:
                                ws_pesanan.update_cell(r_idx, 8, "Lunas")
                            for it in order["items"]:
                                for p_idx, p in enumerate(data_prod, start=2):
                                    if str(p["Nama Barang"]) == it["nama"]:
                                        tot_lama = int(p["Stok Total"]) if p["Stok Total"] != "" else 0
                                        kunci_lama = int(p["Stok Terkunci"]) if p["Stok Terkunci"] != "" else 0
                                        ws_produk.update_cell(p_idx, 5, max(0, tot_lama - it["qty"]))
                                        ws_produk.update_cell(p_idx, 6, max(0, kunci_lama - it["qty"]))
                                        break

                            load_admin_data.clear()
                            tgl_nota = " ".join(order["tgl"].split()[:3]) if len(order["tgl"].split()) >= 3 else order["tgl"]
                            st.session_state.nota_verified = {
                                "order_id": oid,
                                "nama": order["nama"],
                                "tanggal": tgl_nota,
                                "items": order["items"],
                                "ongkir": int(ongkir_in),
                                "diskon": int(diskon_in)
                            }
                            st.rerun()

                with btn_cancel:
                    if st.button("❌ Cancel Pesanan", key=f"no_{oid}", use_container_width=True):
                        with st.spinner("Membatalkan pesanan & mengembalikan stok..."):
                            db = get_google_sheet()
                            ws_produk = db.worksheet("Produk")
                            ws_pesanan = db.worksheet("Pesanan")
                            data_prod = ws_produk.get_all_records()

                            for r_idx in order["rows"]:
                                ws_pesanan.update_cell(r_idx, 8, "Dibatalkan")
                            for it in order["items"]:
                                for p_idx, p in enumerate(data_prod, start=2):
                                    if str(p["Nama Barang"]) == it["nama"]:
                                        kunci_lama = int(p["Stok Terkunci"]) if p["Stok Terkunci"] != "" else 0
                                        ws_produk.update_cell(p_idx, 6, max(0, kunci_lama - it["qty"]))
                                        break

                            load_admin_data.clear()
                            st.warning(f"Pesanan {oid} ({order['nama']}) dibatalkan. Stok otomatis kembali ke katalog!")
                            st.rerun()

# ==============================================================================
# TAB 2: BUAT NOTA MANUAL (JIKA ORDER LANGSUNG VIA CHAT WA)
# ==============================================================================
with tab2:
    st.subheader("Buat Nota Manual")
    daftar_nama_prod = ["-- Ketik Manual --"] + [str(p["Nama Barang"]) for p in data_produk_admin]

    c_m1, c_m2 = st.columns(2)
    with c_m1:
        m_nama = st.text_input("Nama Customer", placeholder="Contoh: Bude Heni", key="m_nama")
    with c_m2:
        m_tgl = st.date_input("Tanggal Order", value=datetime.date.today(), key="m_tgl")

    if "manual_rows" not in st.session_state:
        st.session_state.manual_rows = 1

    items_manual = []
    for i in range(st.session_state.manual_rows):
        st.markdown(f"**Barang #{i+1}**")
        col_p, col_j, col_h = st.columns([2.2, 0.9, 1.3])
        with col_p:
            pilih = st.selectbox("Pilih Katalog", daftar_nama_prod, key=f"sel_m_{i}", label_visibility="collapsed")
            if pilih == "-- Ketik Manual --":
                nama_item_m = st.text_input("Nama Barang", placeholder="Ketik nama barang...", key=f"txt_m_{i}", label_visibility="collapsed")
                harga_default = 0
            else:
                nama_item_m = pilih
                cocok = next((p for p in data_produk_admin if str(p["Nama Barang"]) == pilih), None)
                harga_default = int(cocok["Harga"]) if cocok else 0
        with col_j:
            qty_m = st.number_input("Jml", min_value=1, value=1, key=f"qty_m_{i}")
        with col_h:
            harga_m = st.number_input("Harga Satuan", min_value=0, value=harga_default, step=1000, key=f"hrg_m_{i}")

        if nama_item_m.strip() and harga_m > 0:
            items_manual.append({"nama": nama_item_m.strip(), "qty": int(qty_m), "harga": int(harga_m)})

    if st.button("+ Tambah Baris Barang"):
        st.session_state.manual_rows += 1
        st.rerun()

    col_mo, col_md = st.columns(2)
    with col_mo:
        m_ongkir = st.number_input("Ongkir (Rp)", min_value=0, step=1000, key="m_ongkir")
    with col_md:
        m_diskon = st.number_input("Diskon (Rp)", min_value=0, step=1000, key="m_diskon")

    if st.button("1. Buat Pratinjau Nota", type="primary", use_container_width=True):
        if not m_nama.strip() or not items_manual:
            st.error("Isi Nama Customer dan minimal 1 barang terlebih dahulu.")
        else:
            bulan_id = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
            tgl_fmt = f"{m_tgl.day} {bulan_id[m_tgl.month - 1]} {m_tgl.year}"
            st.session_state.nota_manual_preview = {
                "order_id": "MAN-" + str(uuid.uuid4())[:6].upper(),
                "nama": m_nama.strip(),
                "tanggal": tgl_fmt,
                "items": items_manual,
                "ongkir": int(m_ongkir),
                "diskon": int(m_diskon)
            }

    if "nota_manual_preview" in st.session_state and st.session_state.nota_manual_preview:
        tampilkan_nota_estetik(st.session_state.nota_manual_preview)

# ==============================================================================
# TAB 3: KELOLA STOK, UPLOAD FOTO & KETERANGAN PRODUK
# ==============================================================================
with tab3:
    stok_list = data_produk_admin

    with st.expander("➕ Tambah Produk Baru ke Katalog", expanded=True):
        with st.form("form_tambah_produk", clear_on_submit=True):
            nama_baru = st.text_input("Nama Barang / Motif", placeholder="Contoh: Mecca Prayer Set")
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                harga_baru = st.number_input("Harga Satuan (Rp)", min_value=0, step=5000, value=115000)
            with c_t2:
                stok_baru = st.number_input("Jumlah Stok Awal (pcs)", min_value=1, step=1, value=1)

            ket_baru = st.text_area(
                "Keterangan / Detail Produk (Bisa copy-paste dari WhatsApp)",
                height=140,
                placeholder="Contoh:\nBahan : Rayon Premium\nAll size muat BB sd 100 kg\n\nSize Chart:\nPj Depan +- 118 cm\nBerat : +- 600gr"
            )

            foto_file = st.file_uploader("Upload Foto dari Galeri HP", type=["jpg", "jpeg", "png", "webp"])
            foto_link_manual = st.text_input("Atau Tempel Link Foto (Opsional jika tidak upload)")

            simpan_produk = st.form_submit_button("💾 Simpan Produk ke Katalog", type="primary", use_container_width=True)

            if simpan_produk:
                if not nama_baru.strip():
                    st.error("Nama barang wajib diisi!")
                else:
                    url_foto_final = foto_link_manual.strip()
                    lanjut_simpan = True

                    if foto_file is not None:
                        with st.spinner("Mengunggah foto ke server..."):
                            url_uploaded, err_msg = upload_foto_galeri(foto_file)
                            if err_msg:
                                st.error(err_msg)
                                lanjut_simpan = False
                            else:
                                url_foto_final = url_uploaded

                    if lanjut_simpan:
                        with st.spinner("Menyimpan ke database..."):
                            db = get_google_sheet()
                            ws_produk = db.worksheet("Produk")
                            id_prd = "PRD-" + str(uuid.uuid4())[:4].upper()
                            baris_baru = len(ws_produk.get_all_values()) + 1
                            rumus_tersedia = f"=E{baris_baru}-F{baris_baru}"
                            ws_produk.append_row(
                                [
                                    id_prd,
                                    nama_baru.strip(),
                                    int(harga_baru),
                                    url_foto_final,
                                    int(stok_baru),
                                    0,
                                    rumus_tersedia,
                                    ket_baru.strip()
                                ],
                                value_input_option="USER_ENTERED"
                            )
                            load_admin_data.clear()
                            st.success(f"✅ **{nama_baru}** berhasil ditambahkan ke katalog!")
                            st.rerun()

    with st.expander("✏️ Update Stok, Harga & Keterangan Produk Lama", expanded=False):
        if not stok_list:
            st.info("Belum ada produk di database.")
        else:
            pilihan_edit = [str(p["Nama Barang"]) for p in stok_list]
            nama_diedit = st.selectbox("Pilih Produk yang Ingin Diubah", pilihan_edit, key="edit_pilih_prd")
            idx_edit = pilihan_edit.index(nama_diedit)
            data_lama = stok_list[idx_edit]
            baris_sheet_edit = idx_edit + 2

            st.caption(
                f"Info saat ini — Terkunci: **{data_lama.get('Stok Terkunci', 0)} pcs** | "
                f"Tersedia di Katalog: **{data_lama.get('Stok Tersedia', 0)} pcs**"
            )

            with st.form(f"form_edit_produk_{idx_edit}"):
                c_e1, c_e2 = st.columns(2)
                with c_e1:
                    harga_edit = st.number_input("Harga Satuan (Rp)", min_value=0, step=5000, value=int(data_lama.get("Harga", 0)))
                with c_e2:
                    stok_tot_edit = st.number_input("Stok Total (pcs)", min_value=0, step=1, value=int(data_lama.get("Stok Total", 0)))

                ket_edit = st.text_area(
                    "Keterangan / Detail Produk",
                    value=str(data_lama.get("Keterangan", "")),
                    height=140,
                    placeholder="Isi keterangan bahan, ukuran, berat, dll..."
                )

                foto_ganti = st.file_uploader("Ganti Foto Baru (Biarkan kosong jika tidak diganti)", type=["jpg", "jpeg", "png", "webp"], key=f"ganti_foto_{idx_edit}")

                c_btn_e1, c_btn_e2 = st.columns(2)
                with c_btn_e1:
                    btn_simpan_edit = st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True)
                with c_btn_e2:
                    btn_hapus_prd = st.form_submit_button("🗑️ Hapus Produk", use_container_width=True)

                if btn_simpan_edit:
                    url_foto_baru = str(data_lama.get("Foto URL", ""))
                    ok_update = True
                    if foto_ganti is not None:
                        with st.spinner("Mengunggah foto baru..."):
                            url_up, err_up = upload_foto_galeri(foto_ganti)
                            if err_up:
                                st.error(err_up)
                                ok_update = False
                            else:
                                url_foto_baru = url_up

                    if ok_update:
                        with st.spinner("Memperbarui data produk..."):
                            db = get_google_sheet()
                            ws_produk = db.worksheet("Produk")
                            ws_produk.update_cell(baris_sheet_edit, 3, int(harga_edit))
                            ws_produk.update_cell(baris_sheet_edit, 4, url_foto_baru)
                            ws_produk.update_cell(baris_sheet_edit, 5, int(stok_tot_edit))
                            if ket_edit.strip() == "":
                                try:
                                    ws_produk.batch_clear([f"H{baris_sheet_edit}"])
                                except Exception:
                                    ws_produk.update_cell(baris_sheet_edit, 8, "")
                            else:
                                ws_produk.update_cell(baris_sheet_edit, 8, ket_edit.strip())
                            load_admin_data.clear()
                            st.success(f"✅ Data **{nama_diedit}** berhasil diperbarui!")
                            st.rerun()

                if btn_hapus_prd:
                    db = get_google_sheet()
                    ws_produk = db.worksheet("Produk")
                    ws_produk.delete_rows(baris_sheet_edit)
                    load_admin_data.clear()
                    st.warning(f"Produk **{nama_diedit}** telah dihapus dari katalog.")
                    st.rerun()

    st.subheader("Daftar Persediaan Saat Ini")
    if stok_list:
        tampil_stok = [
            {
                "Nama Barang": p.get("Nama Barang"),
                "Harga": f"Rp {int(p.get('Harga', 0)):,.0f}".replace(",", "."),
                "Total": p.get("Stok Total"),
                "Terkunci": p.get("Stok Terkunci"),
                "Tersedia": p.get("Stok Tersedia")
            }
            for p in stok_list
        ]
        st.dataframe(tampil_stok, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 4: PANEL KHUSUS QRIS TOKO (TANPA PERLU CHECKOUT)
# ==============================================================================
with tab4:
    st.subheader("💳 Kartu QRIS & Rekening Toko")
    qris_tersimpan = cfg_toko.get("qris_url", "").strip()
    info_bayar_tersimpan = cfg_toko.get("info_bayar", "").strip()
    qris_bytes_admin = ambil_bytes_gambar(qris_tersimpan) if qris_tersimpan else None

    if qris_bytes_admin:
        with st.container(border=True):
            st.success("✅ QRIS aktif dan tersimpan permanen di database.")
            c_q1, c_q2, c_q3 = st.columns([1, 2.2, 1])
            with c_q2:
                st.image(qris_bytes_admin, caption="QRIS Homedress ByKamila", use_container_width=True)
                st.download_button(
                    label="📥 Download Gambar QRIS (JPG)",
                    data=qris_bytes_admin,
                    file_name="QRIS_Homedress_ByKamila.jpg",
                    mime="image/jpeg",
                    type="primary",
                    use_container_width=True
                )
            st.caption("Tips iPhone: Tekan lama pada gambar QRIS di atas jika ingin langsung memilih 'Simpan ke Foto'.")
    else:
        st.warning("Belum ada gambar QRIS yang di-upload. Silakan upload pada formulir di bawah ini (cukup 1 kali saja).")

    if info_bayar_tersimpan:
        with st.container(border=True):
            st.info(f"**Info Rekening / Pembayaran Aktif:**\n\n{info_bayar_tersimpan}")
            if st.button("🗑️ Hapus Info Rekening", use_container_width=True):
                simpan_pengaturan("info_bayar", "")
                load_admin_data.clear()
                st.success("✅ Info rekening berhasil dihapus!")
                st.rerun()

    with st.expander("⚙️ Upload / Ganti QRIS & Pengaturan Link", expanded=(not bool(qris_bytes_admin))):
        rek_widget_key = f"rek_in_{hashlib.md5(info_bayar_tersimpan.encode()).hexdigest()[:6]}"
        with st.form("form_pengaturan_qris"):
            qris_file = st.file_uploader("Pilih Gambar QRIS dari Galeri HP", type=["jpg", "jpeg", "png", "webp"])
            info_rek_in = st.text_area(
                "Info Rekening Tambahan (Kosongkan jika ingin menghapus)",
                value=info_bayar_tersimpan,
                key=rek_widget_key,
                placeholder="Contoh: BCA 1234567890 a.n. Kamila"
            )
            admin_url_in = st.text_input(
                "Link Web Admin Ini (Untuk tujuan scan QR Keaslian Nota)",
                value=cfg_toko.get("admin_url", ""),
                placeholder="Contoh: https://bykamila.streamlit.app"
            )
            simpan_qris = st.form_submit_button("💾 Simpan QRIS & Pengaturan", type="primary", use_container_width=True)

            if simpan_qris:
                qris_url_final = qris_tersimpan
                ok_qris = True
                if qris_file is not None:
                    with st.spinner("Mengunggah gambar QRIS permanen..."):
                        up_qris, err_qris = upload_foto_galeri(qris_file)
                        if err_qris:
                            st.error(err_qris)
                            ok_qris = False
                        else:
                            qris_url_final = up_qris

                if ok_qris:
                    simpan_pengaturan("qris_url", qris_url_final)
                    simpan_pengaturan("info_bayar", info_rek_in.strip())
                    simpan_pengaturan("admin_url", admin_url_in.strip())
                    ambil_bytes_gambar.clear()
                    load_admin_data.clear()
                    st.success("✅ QRIS & pengaturan pembayaran berhasil disimpan!")
                    st.rerun()
