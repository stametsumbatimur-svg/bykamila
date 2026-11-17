import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
import datetime
import uuid
import re
import urllib.parse
import requests

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="Katalog Homedress ByKamila", page_icon="🌸", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .product-title {
            font-weight: 700;
            font-size: 15px;
            color: var(--text-color);
            margin-top: 8px;
            margin-bottom: 2px;
        }
        .product-price {
            font-weight: 700;
            font-size: 15px;
            color: #ff4b8b;
        }
        .stock-badge {
            display: inline-block;
            background: #fce4ec;
            color: #d81b60;
            font-size: 12px;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: 20px;
            margin-top: 4px;
            margin-bottom: 8px;
        }
        .no-photo-box {
            background: #fce4ec;
            color: #d81b60;
            border-radius: 10px;
            height: 160px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: cursive;
            font-size: 20px;
            font-weight: bold;
        }
        .qris-box {
            background: #fff8fa;
            border: 2px dashed #f48fb1;
            border-radius: 16px;
            padding: 16px;
            text-align: center;
            margin-top: 10px;
            margin-bottom: 12px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #ff4b8b; font-family: cursive; margin-bottom: 0;'>♡ Homedress ByKamila ♡</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 14px; opacity: 0.85;'>Pilih motif ready stock di bawah ini. Stok otomatis terkunci saat checkout.</p>", unsafe_allow_html=True)

# --- 2. FUNGSI AMBIL GAMBAR LEWAT SERVER (CACHE 1 JAM) ---
def format_image_url(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match and ("drive.google.com" in url or "docs.google.com" in url):
        file_id = match.group(1)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
    return url

@st.cache_data(ttl=3600, show_spinner=False)
def ambil_bytes_gambar(raw_url):
    clean_url = format_image_url(raw_url)
    if not clean_url:
        return None
    try:
        res = requests.get(clean_url, timeout=12)
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
def load_katalog_data():
    db = get_google_sheet()
    ws_produk = db.worksheet("Produk")
    data_produk = ws_produk.get_all_records()

    qris_url = str(st.secrets.get("qris_url", "")).strip()
    info_bayar = ""
    try:
        ws_cfg = db.worksheet("Pengaturan")
        cfg = {str(r["Kunci"]): str(r["Nilai"]) for r in ws_cfg.get_all_records()}
        if cfg.get("qris_url"):
            qris_url = cfg["qris_url"].strip()
        info_bayar = cfg.get("info_bayar", "").strip()
    except Exception:
        pass

    return data_produk, qris_url, info_bayar

try:
    data_produk, qris_url, info_bayar = load_katalog_data()
except Exception as e:
    if "429" in str(e):
        st.warning("⏳ Server sedang sibuk memproses banyak permintaan. Tunggu 30–60 detik lalu tekan tombol **🔄 Coba Lagi** di bawah.")
        if st.button("🔄 Coba Lagi"):
            load_katalog_data.clear()
            st.rerun()
    else:
        st.error(f"Gagal terhubung ke Database: {e}")
    st.stop()

qris_bytes = ambil_bytes_gambar(qris_url) if qris_url else None

# --- 4. PANEL KHUSUS QRIS DI HALAMAN KATALOG (AKSES TANPA CHECKOUT) ---
if qris_bytes or info_bayar:
    with st.expander("💳 Lihat QRIS & Info Pembayaran Toko", expanded=False):
        if qris_bytes:
            c_qp1, c_qp2, c_qp3 = st.columns([1, 2, 1])
            with c_qp2:
                st.image(qris_bytes, caption="QRIS Homedress ByKamila", use_container_width=True)
                st.download_button(
                    label="📥 Simpan Gambar QRIS ke HP",
                    data=qris_bytes,
                    file_name="QRIS_Homedress_ByKamila.jpg",
                    mime="image/jpeg",
                    key="dl_qris_top",
                    use_container_width=True
                )
        if info_bayar:
            st.info(f"**Info Rekening / Pembayaran:**\n\n{info_bayar}")

# --- 5. STATE KERANJANG & NOTA TERAKHIR ---
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "last_order" not in st.session_state:
    st.session_state.last_order = None

produk_ready = [p for p in data_produk if p.get('Stok Tersedia') != '' and int(p['Stok Tersedia']) > 0]

# --- 6. TAMPILKAN NOTA & QRIS PEMBAYARAN JIKA BARU SAJA CHECKOUT ---
if st.session_state.last_order:
    order = st.session_state.last_order
    st.success(f"🎉 Booking Berhasil! ID Pesanan: **{order['id']}**")

    items_rows = ""
    for idx, item in enumerate(order['items'], start=1):
        items_rows += f"""
        <tr>
            <td>{idx}</td>
            <td style="text-align:left;">{item['nama']}</td>
            <td>{item['qty']} pcs</td>
            <td style="text-align:right;">Rp {item['subtotal']:,.0f}</td>
        </tr>
        """.replace(",", ".")

    total_fmt = f"Rp {order['total']:,.0f}".replace(",", ".")

    nota_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Quicksand:wght@600;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: 'Quicksand', sans-serif; margin: 0; padding: 5px; background: transparent; }}
            .nota {{
                background: white; border: 2px solid #f48fb1; border-radius: 16px;
                padding: 20px; max-width: 420px; margin: 0 auto; color: #d81b60;
            }}
            .title {{ font-family: 'Dancing Script', cursive; font-size: 34px; text-align: center; line-height: 1; }}
            .sub {{ text-align: center; font-size: 12px; color: #666; margin-bottom: 12px; }}
            .badge {{
                background: #fff3e0; color: #e65100; padding: 5px 10px; border-radius: 20px;
                font-size: 12px; font-weight: 700; text-align: center; margin-bottom: 12px;
            }}
            .info {{ font-size: 13px; color: #333; margin-bottom: 10px; line-height: 1.5; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 10px; }}
            th, td {{ border: 1.5px solid #f48fb1; padding: 6px; text-align: center; color: #333; }}
            th {{ background: #fce4ec; color: #d81b60; }}
            .total-row {{ background: #fce4ec; font-weight: 700; font-size: 15px; color: #d81b60; }}
            .note {{ font-size: 11px; color: #666; text-align: center; margin-top: 8px; }}
            .btn {{
                display: block; width: 100%; max-width: 420px; margin: 10px auto 0;
                background: #d81b60; color: white; border: none; padding: 12px;
                border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="nota" id="nota-booking">
            <div class="title">homedress bykamila</div>
            <div class="sub">IG: @bykamila__ | WA: 0895-2608-7445</div>
            <div class="badge">⏳ BOOKING STOK (BELUM TERMASUK ONGKIR)</div>
            <div class="info">
                <b>ID Order:</b> {order['id']}<br>
                <b>Tanggal:</b> {order['tgl']}<br>
                <b>Customer:</b> {order['nama']} ({order['wa']})
            </div>
            <table>
                <thead>
                    <tr><th>No</th><th>Barang</th><th>Jml</th><th>Harga</th></tr>
                </thead>
                <tbody>
                    {items_rows}
                    <tr class="total-row">
                        <td colspan="3" style="text-align:left;">Total Barang</td>
                        <td style="text-align:right;">{total_fmt}</td>
                    </tr>
                </tbody>
            </table>
            <div class="note">
                *Stok terkunci selama 1x24 jam. Silakan konfirmasi ongkir ke Admin sebelum melakukan pembayaran.
            </div>
        </div>
        <button class="btn" onclick="simpanJPG()">📥 Simpan Gambar Nota Booking (JPG)</button>
        <script>
            function simpanJPG() {{
                html2canvas(document.getElementById('nota-booking'), {{ scale: 2, backgroundColor: "#ffffff" }}).then(canvas => {{
                    const link = document.createElement('a');
                    link.download = "Booking_{order['id']}_{order['nama']}.jpg";
                    link.href = canvas.toDataURL('image/jpeg', 0.95);
                    link.click();
                }});
            }}
        </script>
    </body>
    </html>
    """
    components.html(nota_html, height=450, scrolling=True)

    if qris_bytes or info_bayar:
        st.markdown("""
            <div class='qris-box'>
                <h4 style='color:#d81b60; margin:0 0 4px 0;'>💳 Metode Pembayaran (QRIS / Transfer)</h4>
                <p style='color:#555; font-size:12px; margin:0;'>Simpan QRIS di bawah untuk scan dari galeri m-banking / e-wallet setelah total + ongkir dikonfirmasi Admin.</p>
            </div>
        """, unsafe_allow_html=True)

        if qris_bytes:
            c_q1, c_q2, c_q3 = st.columns([1, 2, 1])
            with c_q2:
                st.image(qris_bytes, caption="QRIS Homedress ByKamila", use_container_width=True)
                st.download_button(
                    label="📥 Simpan Gambar QRIS ke HP",
                    data=qris_bytes,
                    file_name="QRIS_Homedress_ByKamila.jpg",
                    mime="image/jpeg",
                    key="dl_qris_checkout",
                    use_container_width=True
                )
        if info_bayar:
            st.info(f"**Info Rekening / Pembayaran:**\n\n{info_bayar}")

    daftar_teks = "\n".join([f"- {i['nama']} ({i['qty']} pcs)" for i in order['items']])
    pesan_wa = (
        f"Halo Kak, saya sudah booking di Katalog ByKamila:\n\n"
        f"*ID Order:* {order['id']}\n"
        f"*Nama:* {order['nama']}\n"
        f"*Pesanan:*\n{daftar_teks}\n"
        f"*Total Barang:* {total_fmt}\n\n"
        f"Mohon info ongkir dan total pembayarannya ya kak 🙏"
    )
    wa_url = f"https://wa.me/6289526087445?text={urllib.parse.quote(pesan_wa)}"
    st.link_button("📲 Konfirmasi & Tanya Ongkir via WhatsApp Admin", wa_url, type="primary", use_container_width=True)

    if st.button("🛍️ Buat Pesanan Baru", use_container_width=True):
        st.session_state.last_order = None
        st.rerun()
    st.divider()

# --- 7. TAMPILAN GALERI KATALOG PRODUK + TOMBOL REFRESH KONTEN ---
col_kat1, col_kat2 = st.columns([2.8, 1.4])
with col_kat1:
    st.subheader("👗 Katalog Ready Stock")
with col_kat2:
    if st.button("🔄 Cek Stok", use_container_width=True, help="Perbarui data stok terbaru tanpa memuat ulang halaman web"):
        load_katalog_data.clear()
        st.toast("Stok katalog sudah diperbarui!", icon="✨")
        st.rerun()

if not produk_ready:
    st.warning("Mohon maaf, saat ini semua motif sedang habis terjual 🙏")
else:
    for i in range(0, len(produk_ready), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(produk_ready):
                item = produk_ready[i + j]
                nama_brg = str(item['Nama Barang'])
                harga_brg = int(item['Harga'])
                stok_brg = int(item['Stok Tersedia'])
                img_data = ambil_bytes_gambar(item.get('Foto URL', ''))
                qty_di_cart = st.session_state.cart.get(nama_brg, 0)

                with cols[j]:
                    with st.container(border=True):
                        if img_data:
                            st.image(img_data, use_container_width=True)
                        else:
                            st.markdown("<div class='no-photo-box'>♡ ByKamila ♡</div>", unsafe_allow_html=True)

                        st.markdown(f"<div class='product-title'>{nama_brg}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='product-price'>Rp {harga_brg:,.0f}</div>".replace(",", "."), unsafe_allow_html=True)
                        st.markdown(f"<div class='stock-badge'>Ready: {stok_brg} pcs</div>", unsafe_allow_html=True)

                        if qty_di_cart >= stok_brg:
                            st.button("Stok Maksimal", key=f"btn_{i+j}", disabled=True, use_container_width=True)
                        else:
                            label_btn = f"+ Tambah ({qty_di_cart} di keranjang)" if qty_di_cart > 0 else "+ Pilih Baju Ini"
                            if st.button(label_btn, key=f"btn_{i+j}", use_container_width=True):
                                st.session_state.cart[nama_brg] = qty_di_cart + 1
                                st.rerun()

# --- 8. KERANJANG BELANJA & CHECKOUT ---
st.divider()
st.subheader("🛒 Keranjang & Checkout")

if not st.session_state.cart:
    st.info("Keranjang masih kosong. Klik tombol **+ Pilih Baju Ini** pada katalog di atas.")
else:
    total_belanja = 0
    keranjang_valid = {}

    for nama_brg, qty in list(st.session_state.cart.items()):
        detail = next((p for p in produk_ready if str(p['Nama Barang']) == nama_brg), None)
        if detail:
            maks_stok = int(detail['Stok Tersedia'])
            qty_aman = min(qty, maks_stok)
            harga_satuan = int(detail['Harga'])
            subtotal = harga_satuan * qty_aman
            total_belanja += subtotal
            keranjang_valid[nama_brg] = qty_aman

            c1, c2, c3 = st.columns([3, 1.5, 1])
            with c1:
                st.write(f"**{nama_brg}**\n\nRp {harga_satuan:,.0f} x {qty_aman} = **Rp {subtotal:,.0f}**".replace(",", "."))
            with c2:
                qty_baru = st.number_input("Jml", min_value=1, max_value=maks_stok, value=qty_aman, key=f"qty_{nama_brg}", label_visibility="collapsed")
                if qty_baru != qty_aman:
                    st.session_state.cart[nama_brg] = qty_baru
                    st.rerun()
            with c3:
                if st.button("Hapus", key=f"del_{nama_brg}"):
                    del st.session_state.cart[nama_brg]
                    st.rerun()
        else:
            del st.session_state.cart[nama_brg]

    st.markdown(f"### Total Sementara: :pink[Rp {total_belanja:,.0f}]".replace(",", "."))

    with st.form("form_checkout_final"):
        col_a, col_b = st.columns(2)
        with col_a:
            nama_pembeli = st.text_input("Nama Lengkap Anda", placeholder="Contoh: Bude Heni")
        with col_b:
            no_wa = st.text_input("Nomor WhatsApp Aktif", placeholder="08123456789")

        submit_checkout = st.form_submit_button("🔒 Checkout & Kunci Stok Sekarang", type="primary", use_container_width=True)

        if submit_checkout:
            if not nama_pembeli.strip() or not no_wa.strip():
                st.error("Nama dan Nomor WhatsApp wajib diisi ya kak!")
            else:
                with st.spinner("Sedang mengecek ketersediaan stok terbaru & mengunci pesanan..."):
                    db = get_google_sheet()
                    ws_produk = db.worksheet("Produk")
                    ws_pesanan = db.worksheet("Pesanan")
                    data_produk_terbaru = ws_produk.get_all_records()

                    stok_cukup = True
                    item_terproses = []

                    for nama_brg, qty_pesan in keranjang_valid.items():
                        detail_terbaru = next((p for p in data_produk_terbaru if str(p['Nama Barang']) == nama_brg), None)
                        if not detail_terbaru or int(detail_terbaru['Stok Tersedia']) < qty_pesan:
                            stok_cukup = False
                            st.error(f"Maaf kak, stok **{nama_brg}** baru saja berkurang dan tidak mencukupi.")
                            break
                        item_terproses.append((detail_terbaru, qty_pesan))

                    if stok_cukup and item_terproses:
                        id_pesanan = "ORD-" + str(uuid.uuid4())[:6].upper()
                        tgl_sekarang = datetime.datetime.now().strftime("%d %b %Y %H:%M")
                        ringkasan_items = []

                        for detail_brg, qty_pesan in item_terproses:
                            harga_sat = int(detail_brg['Harga'])
                            sub = harga_sat * qty_pesan
                            nama_item = str(detail_brg['Nama Barang'])

                            ws_pesanan.append_row([
                                id_pesanan, tgl_sekarang, nama_pembeli.strip(), no_wa.strip(),
                                nama_item, qty_pesan, sub, "Menunggu Verifikasi"
                            ])

                            baris_sheet = data_produk_terbaru.index(detail_brg) + 2
                            terkunci_lama = int(detail_brg['Stok Terkunci']) if detail_brg['Stok Terkunci'] != '' else 0
                            ws_produk.update_cell(baris_sheet, 6, terkunci_lama + qty_pesan)

                            ringkasan_items.append({
                                "nama": nama_item,
                                "qty": qty_pesan,
                                "harga": harga_sat,
                                "subtotal": sub
                            })

                        load_katalog_data.clear()
                        st.session_state.last_order = {
                            "id": id_pesanan,
                            "tgl": tgl_sekarang,
                            "nama": nama_pembeli.strip(),
                            "wa": no_wa.strip(),
                            "items": ringkasan_items,
                            "total": total_belanja
                        }
                        st.session_state.cart = {}
                        st.rerun()
