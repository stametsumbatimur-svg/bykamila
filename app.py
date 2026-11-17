import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
import datetime
import json
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Admin & Nota ByKamila", page_icon="🌸", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. KEAMANAN PIN ADMIN ---
# PIN bawaan adalah "1234" (bisa diubah sesuai keinginan di baris bawah ini)
PIN_ADMIN = st.secrets.get("admin_pin", "0305")

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

if not st.session_state.admin_auth:
    st.markdown("<h2 style='text-align: center; color: #d81b60; font-family: cursive;'>♡ Admin Homedress ByKamila ♡</h2>", unsafe_allow_html=True)
    with st.form("login_admin"):
        pin_input = st.text_input("Masukkan PIN Admin", type="password", placeholder="Masukkan 4 digit PIN...")
        masuk = st.form_submit_button("Masuk ke Halaman Admin", type="primary", use_container_width=True)
        if masuk:
            if pin_input == str(PIN_ADMIN):
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("PIN salah! Silakan coba lagi.")
    st.stop()

# --- 3. KONEKSI KE GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database_ByKamila")

try:
    db = get_google_sheet()
    sheet_produk = db.worksheet("Produk")
    sheet_pesanan = db.worksheet("Pesanan")
except Exception as e:
    st.error(f"Gagal terhubung ke Database: {e}")
    st.stop()

# --- 4. FUNGSI RENDER NOTA PINK ESTETIK ---
def tampilkan_nota_estetik(payload_nota):
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
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
            .header-nota { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
            .brand h1 { font-family: 'Dancing Script', cursive; font-size: 42px; line-height: 0.9; }
            .brand p { font-family: 'Dancing Script', cursive; font-size: 22px; text-align: center; }
            .contact { font-size: 13px; font-weight: 700; text-align: right; color: var(--pink-main); }
            .contact p { display: flex; align-items: center; justify-content: flex-end; gap: 6px; margin-bottom: 4px; }
            .thanks-top { font-family: 'Dancing Script', cursive; font-size: 20px; text-align: center; margin-top: 10px; }
            .info-row { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 15px; }
            .info-box {
                border: 1.5px solid var(--pink-border);
                border-radius: 25px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: 700;
                text-align: center;
                flex: 1;
                background: white;
            }
            .info-box span { display: block; color: var(--text-dark); font-size: 14px; margin-top: 3px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 15px; text-align: center; }
            table th, table td { border: 1.5px solid var(--pink-border); padding: 8px 6px; font-weight: 600; }
            table th { background-color: var(--pink-light); font-size: 13px; color: var(--pink-main); }
            table td { color: var(--text-dark); font-size: 13px; }
            .align-right { text-align: right; }
            .align-left { text-align: left; }
            .grand-total { font-family: 'Dancing Script', cursive; font-size: 28px; color: var(--pink-main); background-color: var(--pink-light); }
            .grand-total-val { font-size: 20px; color: var(--pink-main); background-color: var(--pink-light); font-weight: 700; }
            .footer-thanks { background-color: var(--pink-light); border-radius: 15px; padding: 15px; text-align: center; margin-top: 10px; }
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

            <div class="footer-thanks">
                <span style="font-family: 'Dancing Script', cursive; font-size: 24px; color: var(--pink-main);">♡ Terima kasih sudah order ♡</span><br>
                <span style="font-size: 13px; font-weight: 600; color: var(--text-dark);">- Semoga suka dengan produknya di Homedress bykamila -</span>
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

            function downloadNotaJPG() {
                html2canvas(document.getElementById('nota-area'), { scale: 2, backgroundColor: "#ffffff" }).then(canvas => {
                    const url = canvas.toDataURL('image/jpeg', 0.95);
                    document.getElementById('img-hasil').src = url;
                    document.getElementById('jpg-preview-area').style.display = 'block';

                    const a = document.createElement('a');
                    a.download = `Nota_${data.nama}.jpg`;
                    a.href = url;
                    a.click();
                });
            }
        </script>
    </body>
    </html>
    """
    final_html = html_template.replace("__DATA_JSON__", json.dumps(payload_nota))
    components.html(final_html, height=760, scrolling=True)

# --- 5. HEADER & NAVIGASI ADMIN ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown("<h2 style='color: #d81b60; font-family: cursive; margin:0;'>♡ Admin ByKamila ♡</h2>", unsafe_allow_html=True)
with col_head2:
    if st.button("🔄 Refresh"):
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 Pesanan Masuk", "🧾 Nota Manual", "📦 Cek Stok"])

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

    semua_pesanan = sheet_pesanan.get_all_records()
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
                            data_prod = sheet_produk.get_all_records()
                            # 1. Update status di sheet Pesanan menjadi Lunas
                            for r_idx in order["rows"]:
                                sheet_pesanan.update_cell(r_idx, 8, "Lunas")
                            # 2. Kurangi Stok Total (Kolom E / 5) dan Stok Terkunci (Kolom F / 6)
                            for it in order["items"]:
                                for p_idx, p in enumerate(data_prod, start=2):
                                    if str(p["Nama Barang"]) == it["nama"]:
                                        tot_lama = int(p["Stok Total"]) if p["Stok Total"] != "" else 0
                                        kunci_lama = int(p["Stok Terkunci"]) if p["Stok Terkunci"] != "" else 0
                                        sheet_produk.update_cell(p_idx, 5, max(0, tot_lama - it["qty"]))
                                        sheet_produk.update_cell(p_idx, 6, max(0, kunci_lama - it["qty"]))
                                        break

                            tgl_nota = " ".join(order["tgl"].split()[:3]) if len(order["tgl"].split()) >= 3 else order["tgl"]
                            st.session_state.nota_verified = {
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
                            data_prod = sheet_produk.get_all_records()
                            # 1. Update status di sheet Pesanan menjadi Dibatalkan
                            for r_idx in order["rows"]:
                                sheet_pesanan.update_cell(r_idx, 8, "Dibatalkan")
                            # 2. Lepaskan Stok Terkunci (Kolom F / 6) agar stok katalog kembali
                            for it in order["items"]:
                                for p_idx, p in enumerate(data_prod, start=2):
                                    if str(p["Nama Barang"]) == it["nama"]:
                                        kunci_lama = int(p["Stok Terkunci"]) if p["Stok Terkunci"] != "" else 0
                                        sheet_produk.update_cell(p_idx, 6, max(0, kunci_lama - it["qty"]))
                                        break
                            st.warning(f"Pesanan {oid} ({order['nama']}) dibatalkan. Stok otomatis kembali ke katalog!")
                            st.rerun()

# ==============================================================================
# TAB 2: BUAT NOTA MANUAL (JIKA ORDER LANGSUNG VIA CHAT WA)
# ==============================================================================
with tab2:
    st.subheader("Buat Nota Manual")
    data_prod_manual = sheet_produk.get_all_records()
    daftar_nama_prod = ["-- Ketik Manual --"] + [str(p["Nama Barang"]) for p in data_prod_manual]

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
                cocok = next((p for p in data_prod_manual if str(p["Nama Barang"]) == pilih), None)
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
                "nama": m_nama.strip(),
                "tanggal": tgl_fmt,
                "items": items_manual,
                "ongkir": int(m_ongkir),
                "diskon": int(m_diskon)
            }

    if "nota_manual_preview" in st.session_state and st.session_state.nota_manual_preview:
        tampilkan_nota_estetik(st.session_state.nota_manual_preview)

# ==============================================================================
# TAB 3: CEK STOK CEPAT DARI HP
# ==============================================================================
with tab3:
    st.subheader("Ringkasan Persediaan Barang")
    stok_list = sheet_produk.get_all_records()
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
