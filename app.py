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
st.set_page_config(page_title="Generator Nota ByKamila", page_icon="🧾", layout="centered")

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

# --- 3. KONEKSI & CACHE DATA GOOGLE SHEETS (HEMAT KUOTA API) ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database_ByKamila")

@st.cache_data(ttl=45, show_spinner=False)
def load_nota_data():
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

    return data_produk, cfg_toko

# --- 4. MODE VERIFIKASI PUBLIK SAAT QR CODE DI NOTA DI-SCAN ---
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

# --- 5. AMBIL DATA PRODUK, QRIS & LOGO ---
try:
    data_produk_list, cfg_toko = load_nota_data()
except Exception as e:
    if "429" in str(e):
        st.warning("⏳ Kuota akses Google Sheets sedang penuh sementara. Tunggu 30–60 detik lalu tekan tombol **🔄 Coba Lagi**.")
        if st.button("🔄 Coba Lagi"):
            load_nota_data.clear()
            st.rerun()
    else:
        st.error(f"Gagal terhubung ke Database: {e}")
    st.stop()

# --- 6. FUNGSI RENDER NOTA PINK ESTETIK + BACKGROUND & WATERMARK ---
def tampilkan_nota_estetik(payload_nota, logo_bytes=None, bg_style="pastel"):
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

    logo_data_uri = ""
    if logo_bytes:
        b64_logo = base64.b64encode(logo_bytes).decode("utf-8")
        logo_data_uri = f"data:image/jpeg;base64,{b64_logo}"

    data_for_js = dict(payload_nota)
    data_for_js["order_id"] = order_id
    data_for_js["sig_code"] = sig_code
    data_for_js["verify_url"] = verify_url
    data_for_js["logo_data_uri"] = logo_data_uri
    data_for_js["bg_style"] = bg_style

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
                background: #ffffff;
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
            .nota-box.bg-pastel {
                background: linear-gradient(180deg, #ffffff 0%, #fff7fa 45%, #ffeef4 100%);
            }
            .nota-box.bg-polkadot {
                background-color: #fff9fb;
                background-image: radial-gradient(rgba(244, 143, 177, 0.28) 1.5px, transparent 1.5px);
                background-size: 16px 16px;
            }
            .nota-box.bg-clean {
                background: #ffffff;
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
            /* Watermark Logo Tengah (Diperjelas) */
            .wm-logo-center {
                position: absolute;
                top: 52%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 245px;
                opacity: 0.17;
                pointer-events: none;
                z-index: 0;
            }
            .wm-logo-center img {
                width: 100%;
                height: auto;
                display: block;
            }
            /* Watermark Teks Diagonal Berulang dengan ID Nota (Diperjelas) */
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
                font-size: 17px;
                font-weight: 700;
                color: rgba(216, 27, 96, 0.16);
                white-space: nowrap;
                letter-spacing: 2.5px;
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
                width: 158px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .brand-logo-wrap img {
                width: 155px;
                height: auto;
                max-height: 145px;
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
                                <div class="contact-area">
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
                                </div>
                            </div>

                            <div class="info-row">
                                <div class="info-box">Nama Customer<span id="out-nama"></span></div>
                                <div class="info-box">Tanggal Order<span id="out-tanggal"></span></div>
                            </div>

                            <table>
                                <thead>
                                    <tr>
                                        <th class="col-qty">Banyaknya</th>
                                        <th style="width:132px;">Nama Barang</th>
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
                                    <span style="font-size: 11px; font-weight: 600; color: var(--text-dark);">Semoga suka dengan produknya di Homedress bykamila</span><br>
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
            const formatRp = (n) => new Intl.NumberFormat('id-ID').format(n);
            const escHtml = (str) => String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');

            const notaEl = document.getElementById('nota-area');
            notaEl.classList.add('bg-' + (data.bg_style || 'pastel'));

            function makeLogoTransparent(dataUri, callback) {
                if (!dataUri) { callback(''); return; }
                const img = new Image();
                img.onload = function() {
                    const c = document.createElement('canvas');
                    c.width = img.width;
                    c.height = img.height;
                    const ctx = c.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    const imgData = ctx.getImageData(0, 0, c.width, c.height);
                    const d = imgData.data;
                    for (let i = 0; i < d.length; i += 4) {
                        const r = d[i], g = d[i+1], b = d[i+2];
                        if (r > 240 && g > 240 && b > 240) {
                            d[i+3] = 0;
                        } else if (r > 224 && g > 224 && b > 224) {
                            const avg = (r + g + b) / 3;
                            d[i+3] = Math.round(((240 - avg) / 16) * 255);
                        }
                    }
                    ctx.putImageData(imgData, 0, 0);
                    callback(c.toDataURL('image/png'));
                };
                img.onerror = function() { callback(dataUri); };
                img.src = dataUri;
            }

            const brandContainer = document.getElementById('brand-container');
            const wmLogoBox = document.getElementById('wm-logo-box');

            if (data.logo_data_uri) {
                brandContainer.innerHTML = `<div class="brand-logo-wrap"><img id="img-brand-logo" src="${data.logo_data_uri}" alt="Logo ByKamila"></div>`;
                makeLogoTransparent(data.logo_data_uri, (cleanUri) => {
                    const brandImg = document.getElementById('img-brand-logo');
                    if (brandImg) brandImg.src = cleanUri;
                    wmLogoBox.innerHTML = `<img src="${cleanUri}" alt="Watermark ByKamila">`;
                });
            } else {
                brandContainer.innerHTML = `<div class="brand"><h1>homedress</h1><p>♡ bykamila ♡</p></div>`;
            }

            // Watermark teks diagonal tetap memuat ID Nota
            const wmWrap = document.getElementById('wm-text-wrap');
            const wmString = `LUNAS • ${data.order_id} • BYKAMILA • `;
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
                    const lineTotal = it.qty * it.harga;
                    subtotal += lineTotal;
                    rowsHTML += `
                        <tr>
                            <td class="col-qty">${it.qty} pcs</td>
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

                    const a = document.createElement('a');
                    a.download = `Nota_${data.nama}.jpg`;
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
    st.markdown("<h3 style='color: #d81b60; font-family: cursive; margin:0;'>♡ Nota Homedress ByKamila ♡</h3>", unsafe_allow_html=True)
with col_head2:
    if st.button("🔄 Refresh", use_container_width=True, help="Perbarui daftar harga produk, logo & QRIS"):
        load_nota_data.clear()
        ambil_bytes_gambar.clear()
        st.rerun()

qris_tersimpan = cfg_toko.get("qris_url", "").strip()
info_bayar_tersimpan = cfg_toko.get("info_bayar", "").strip()
logo_tersimpan = cfg_toko.get("logo_url", "").strip()

qris_bytes = ambil_bytes_gambar(qris_tersimpan) if qris_tersimpan else None
logo_bytes = ambil_bytes_gambar(logo_tersimpan) if logo_tersimpan else None

if qris_bytes or info_bayar_tersimpan:
    with st.expander("💳 Tampilkan QRIS & Info Pembayaran", expanded=False):
        if qris_bytes:
            c_q1, c_q2, c_q3 = st.columns([1, 2.2, 1])
            with c_q2:
                st.image(qris_bytes, caption="QRIS Homedress ByKamila", use_container_width=True)
                st.download_button(
                    label="📥 Download Gambar QRIS (JPG)",
                    data=qris_bytes,
                    file_name="QRIS_Homedress_ByKamila.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
        if info_bayar_tersimpan:
            st.info(f"**Info Rekening / Pembayaran:**\n\n{info_bayar_tersimpan}")

st.divider()

# --- 8. FORM PEMBUATAN NOTA ---
st.subheader("🧾 Buat Nota Penjualan")
daftar_nama_prod = ["-- Ketik Manual --"] + [str(p["Nama Barang"]) for p in data_produk_list if str(p.get("Nama Barang", "")).strip()]

c_m1, c_m2 = st.columns(2)
with c_m1:
    m_nama = st.text_input("Nama Customer", placeholder="Contoh: Bude Heni", key="m_nama")
with c_m2:
    m_tgl = st.date_input("Tanggal Order", value=datetime.date.today(), key="m_tgl")

if "manual_row_ids" not in st.session_state or not st.session_state.manual_row_ids:
    st.session_state.manual_row_ids = [str(uuid.uuid4())[:6]]

items_manual = []
jumlah_baris_aktif = len(st.session_state.manual_row_ids)

for idx_baris, rid in enumerate(list(st.session_state.manual_row_ids)):
    c_lbl, c_del = st.columns([3.5, 1])
    with c_lbl:
        st.markdown(f"**Barang #{idx_baris + 1}**")
    with c_del:
        if jumlah_baris_aktif > 1:
            if st.button("🗑️ Hapus", key=f"del_row_{rid}", use_container_width=True):
                st.session_state.manual_row_ids.remove(rid)
                for prefix in ("sel_m_", "last_sel_", "txt_m_", "qty_m_", "hrg_m_"):
                    st.session_state.pop(f"{prefix}{rid}", None)
                st.rerun()

    col_p, col_j, col_h = st.columns([2.2, 0.9, 1.3])
    with col_p:
        pilih = st.selectbox("Pilih Katalog", daftar_nama_prod, key=f"sel_m_{rid}", label_visibility="collapsed")
        if pilih == "-- Ketik Manual --":
            nama_item_m = st.text_input("Nama Barang", placeholder="Ketik nama barang...", key=f"txt_m_{rid}", label_visibility="collapsed")
            harga_default = 0
        else:
            nama_item_m = pilih
            cocok = next((p for p in data_produk_list if str(p["Nama Barang"]) == pilih), None)
            harga_default = int(cocok["Harga"]) if cocok and str(cocok.get("Harga", "")).isdigit() else 0

        if st.session_state.get(f"last_sel_{rid}") != pilih:
            st.session_state[f"last_sel_{rid}"] = pilih
            st.session_state[f"hrg_m_{rid}"] = harga_default

    with col_j:
        qty_m = st.number_input("Banyaknya", min_value=1, value=1, key=f"qty_m_{rid}")
    with col_h:
        harga_m = st.number_input("Harga Satuan", min_value=0, step=1000, key=f"hrg_m_{rid}")

    if nama_item_m.strip() and harga_m > 0:
        items_manual.append({"nama": nama_item_m.strip(), "qty": int(qty_m), "harga": int(harga_m)})

c_add_btn, c_rst_btn = st.columns([2.5, 1.2])
with c_add_btn:
    if st.button("+ Tambah Baris Barang", use_container_width=True):
        st.session_state.manual_row_ids.append(str(uuid.uuid4())[:6])
        st.rerun()
with c_rst_btn:
    if st.button("🧹 Reset Semua", use_container_width=True):
        for rid in st.session_state.manual_row_ids:
            for prefix in ("sel_m_", "last_sel_", "txt_m_", "qty_m_", "hrg_m_"):
                st.session_state.pop(f"{prefix}{rid}", None)
        st.session_state.manual_row_ids = [str(uuid.uuid4())[:6]]
        st.session_state.nota_manual_preview = None
        st.rerun()

col_mo, col_md = st.columns(2)
with col_mo:
    m_ongkir = st.number_input("Ongkir (Rp)", min_value=0, step=1000, key="m_ongkir")
with col_md:
    m_diskon = st.number_input("Diskon (Rp)", min_value=0, step=1000, key="m_diskon")

pilihan_bg = st.selectbox(
    "🎨 Gaya Background & Watermark Nota",
    [
        "🌸 Pink Pastel Lembut + Watermark Logo",
        "🎀 Pola Polkadot Pink + Watermark Logo",
        "🤍 Putih Bersih + Watermark Logo"
    ],
    key="pilih_bg_nota"
)
map_bg = {
    "🌸 Pink Pastel Lembut + Watermark Logo": "pastel",
    "🎀 Pola Polkadot Pink + Watermark Logo": "polkadot",
    "🤍 Putih Bersih + Watermark Logo": "clean"
}

if st.button("✨ Buat Nota Sekarang", type="primary", use_container_width=True):
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
    tampilkan_nota_estetik(
        st.session_state.nota_manual_preview,
        logo_bytes=logo_bytes,
        bg_style=map_bg[pilihan_bg]
    )
