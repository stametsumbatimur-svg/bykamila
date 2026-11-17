import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import uuid

# --- 1. SETUP TAMPILAN ---
st.set_page_config(page_title="Katalog Homedress ByKamila", page_icon="🛍️", layout="centered")
st.markdown("<h1 style='text-align: center; color: #d81b60; font-family: cursive;'>♡ Katalog ByKamila ♡</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Pilih produk ready stock di bawah ini. Stok otomatis terkunci setelah checkout.</p>", unsafe_allow_html=True)

# --- 2. KONEKSI KE GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database_ByKamila") # Pastikan nama ini sama persis dengan nama file Google Sheets Anda

try:
    db = get_google_sheet()
    sheet_produk = db.worksheet("Produk")
    sheet_pesanan = db.worksheet("Pesanan")
    st.success("✅ Berhasil terhubung ke Database!") # Tanda API berhasil
except Exception as e:
    st.error(f"Gagal terhubung ke Database. Cek kembali Secrets atau akses Editor. Error: {e}")
    st.stop()

# --- 3. AMBIL DATA PRODUK ---
data_produk = sheet_produk.get_all_records()
# Filter hanya barang yang stoknya lebih dari 0
produk_ready = [p for p in data_produk if p['Stok Tersedia'] != '' and int(p['Stok Tersedia']) > 0]

if not produk_ready:
    st.warning("Mohon maaf, semua stok sedang habis 🙏")
    st.stop()

# --- 4. TAMPILAN KATALOG & CHECKOUT ---
pilihan_nama = [p['Nama Barang'] for p in produk_ready]

with st.form("form_checkout"):
    st.subheader("🛒 Form Pemesanan")
    
    col1, col2 = st.columns(2)
    with col1:
        nama_pembeli = st.text_input("Nama Anda", placeholder="Contoh: Bude Heni")
    with col2:
        no_wa = st.text_input("Nomor WhatsApp", placeholder="0812345...")
        
    barang_dipilih = st.selectbox("Pilih Barang", pilihan_nama)
    jumlah_pesan = st.number_input("Jumlah (pcs)", min_value=1, max_value=10, value=1)
    
    tombol_pesan = st.form_submit_button("Checkout & Kunci Stok 🔒")

# --- 5. LOGIKA KETIKA TOMBOL CHECKOUT DITEKAN ---
if tombol_pesan:
    if not nama_pembeli or not no_wa:
        st.error("Nama dan No WA wajib diisi!")
    else:
        # Cari data detail barang yang dipilih
        detail_barang = next(item for item in produk_ready if item["Nama Barang"] == barang_dipilih)
        
        if jumlah_pesan > int(detail_barang['Stok Tersedia']):
            st.error(f"Gagal! Stok {barang_dipilih} sisa {detail_barang['Stok Tersedia']} pcs.")
        else:
            with st.spinner('Mengunci stok pesanan Anda...'):
                # a. Hitung Harga
                total_harga = int(detail_barang['Harga']) * jumlah_pesan
                id_pesanan = "ORD-" + str(uuid.uuid4())[:6].upper()
                tgl_sekarang = datetime.datetime.now().strftime("%d-%b-%Y %H:%M")
                
                # b. Tulis ke Sheet Pesanan
                sheet_pesanan.append_row([
                    id_pesanan, tgl_sekarang, nama_pembeli, no_wa, 
                    barang_dipilih, jumlah_pesan, total_harga, "Menunggu Verifikasi"
                ])
                
                # c. Update Stok Terkunci di Sheet Produk
                # Cari baris ke berapa produk ini berada di sheet (tambah 2 karena header dan index)
                baris_produk = data_produk.index(detail_barang) + 2 
                stok_terkunci_lama = int(detail_barang['Stok Terkunci']) if detail_barang['Stok Terkunci'] != '' else 0
                stok_terkunci_baru = stok_terkunci_lama + jumlah_pesan
                
                # Update cell di kolom 'Stok Terkunci' (Kolom F / Kolom ke-6)
                sheet_produk.update_cell(baris_produk, 6, stok_terkunci_baru)
                
                st.success(f"🎉 Yeay! Booking berhasil. Total: Rp {total_harga:,} (Belum Ongkir).")
                st.info("Sistem telah mengunci stok Anda. Admin akan segera menghubungi via WhatsApp.")
