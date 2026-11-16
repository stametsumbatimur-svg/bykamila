import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Generator Nota ByKamila",
    page_icon="🌸",
    layout="centered"
)

# Menghilangkan ruang kosong berlebih
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

html_code = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Menggunakan font Quicksand untuk kesan estetik & tidak kaku -->
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        :root {
            --pink-main: #d81b60;
            --pink-light: #fce4ec;
            --pink-border: #f48fb1; /* Warna garis yang lebih halus */
            --text-dark: #4a4a4a;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Quicksand', sans-serif;
        }
        body {
            background-color: transparent;
            color: var(--text-dark);
            padding: 5px;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
        }
        .form-section {
            background: white;
            padding: 18px;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
        }
        .form-group { margin-bottom: 12px; }
        .form-group label {
            display: block;
            margin-bottom: 4px;
            font-weight: 700;
            font-size: 13px;
            color: #555;
        }
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1.5px solid #eaeaea;
            border-radius: 10px;
            font-size: 14px;
            transition: 0.3s;
        }
        .form-group input:focus {
            border-color: var(--pink-main);
            outline: none;
        }
        .item-row {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            background: #fffafa;
            padding: 10px;
            border-radius: 10px;
            border: 1px dashed #fce4ec;
        }
        .item-row input {
            padding: 8px;
            border: 1.5px solid #eaeaea;
            border-radius: 8px;
            font-size: 13px;
            width: 100%;
        }
        button {
            background-color: var(--pink-main);
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 700;
            font-size: 14px;
            width: 100%;
            margin-top: 8px;
            transition: 0.2s;
        }
        button:active { transform: scale(0.98); }
        .btn-add { background-color: #fce4ec; color: var(--pink-main); border: 1.5px solid var(--pink-main); font-size: 13px; padding: 10px; }
        
        .preview-section {
            background: white;
            border-radius: 16px;
            box-shadow: 0 8px 25px rgba(216, 27, 96, 0.1);
            padding: 0;
            overflow: hidden;
        }
        .nota-box {
            background: white;
            width: 100%;
            max-width: 450px;
            margin: 0 auto;
            padding: 25px 20px;
            color: var(--pink-main);
            position: relative;
        }
        /* Hiasan Gradasi Estetik di Atas Nota */
        .nota-box::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 8px;
            background: linear-gradient(90deg, #fce4ec, #f48fb1, #d81b60, #f48fb1, #fce4ec);
        }
        
        .header-nota {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }
        .brand h1 {
            font-family: 'Dancing Script', cursive;
            font-size: 42px;
            line-height: 0.9;
        }
        .brand p {
            font-family: 'Dancing Script', cursive;
            font-size: 22px;
            text-align: center;
        }
        .contact {
            font-size: 13px;
            font-weight: 700;
            text-align: right;
            color: var(--pink-main);
        }
        .contact p { 
            display: flex; 
            align-items: center; 
            justify-content: flex-end; 
            gap: 6px; 
            margin-bottom: 4px; 
        }
        .thanks-top {
            font-family: 'Dancing Script', cursive;
            font-size: 20px;
            text-align: center;
            margin-top: 10px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 15px;
        }
        /* Kotak Info dibikin oval melengkung (pill shape) */
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
        .info-box span {
            display: block;
            color: var(--text-dark);
            font-size: 14px;
            margin-top: 3px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
            text-align: center;
        }
        table th, table td {
            border: 1.5px solid var(--pink-border);
            padding: 8px 6px;
            font-weight: 600;
        }
        table th {
            background-color: var(--pink-light);
            font-size: 13px;
            color: var(--pink-main);
        }
        table td { color: var(--text-dark); font-size: 13px; }
        .align-right { text-align: right; }
        .align-left { text-align: left; }
        
        .grand-total {
            font-family: 'Dancing Script', cursive;
            font-size: 28px;
            color: var(--pink-main);
            background-color: var(--pink-light);
        }
        .grand-total-val {
            font-size: 20px;
            color: var(--pink-main);
            background-color: var(--pink-light);
            font-weight: 700;
        }
        /* Footer ucapan terima kasih dibuat bubble soft */
        .footer-thanks {
            background-color: var(--pink-light);
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            margin-top: 10px;
        }
        #hasil-gambar-box {
            display: none;
            margin-top: 15px;
            padding: 12px;
            background: #fff8fa;
            border: 2px dashed var(--pink-border);
            border-radius: 12px;
            text-align: center;
        }
        #hasil-gambar-box img {
            width: 100%;
            max-width: 400px;
            border-radius: 10px;
            margin-top: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>

<div class="container">
    <div class="form-section">
        <h3 style="color: var(--pink-main); margin-bottom: 15px; font-family: 'Quicksand', sans-serif;">Input Data Nota</h3>
        <div class="form-group">
            <label>Nama Customer</label>
            <input type="text" id="in-nama" placeholder="Contoh: Bude Heni" oninput="updateNota()">
        </div>
        <div class="form-group">
            <label>Tanggal Order</label>
            <input type="text" id="in-tanggal" placeholder="Contoh: 16 Nov 2026" oninput="updateNota()">
        </div>

        <label style="font-weight: 700; font-size: 13px; color: #555; display: block; margin-bottom: 6px; margin-top: 15px;">Daftar Barang</label>
        <div id="item-container">
            <div class="item-row">
                <input type="text" class="in-barang" placeholder="Nama Barang" style="flex:2.2" oninput="updateNota()">
                <input type="number" class="in-jumlah" placeholder="Jml" style="flex:0.8" inputmode="numeric" oninput="updateNota()">
                <input type="number" class="in-harga" placeholder="Harga" style="flex:1.4" inputmode="numeric" oninput="updateNota()">
            </div>
        </div>
        <button class="btn-add" onclick="tambahBaris()">+ Tambah Barang</button>

        <div style="display: flex; gap: 10px; margin-top: 15px;">
            <div class="form-group" style="flex:1">
                <label>Diskon (Rp)</label>
                <input type="number" id="in-diskon" placeholder="Kosongkan jika tak ada" inputmode="numeric" oninput="updateNota()">
            </div>
            <div class="form-group" style="flex:1">
                <label>Ongkir (Rp)</label>
                <input type="number" id="in-ongkir" placeholder="5000" inputmode="numeric" oninput="updateNota()">
            </div>
        </div>
        
        <button onclick="simpanGambar()" style="margin-top: 15px;">Buat & Simpan Gambar JPG</button>

        <div id="hasil-gambar-box">
            <p style="font-size: 13px; font-weight: bold; color: var(--pink-main);">
                ✅ Nota siap! Tekan lama gambar di bawah lalu pilih <u>Simpan ke Foto</u>:
            </p>
            <img id="preview-jpg" alt="Hasil Nota">
        </div>
    </div>

    <div class="preview-section">
        <div class="nota-box" id="nota-area">
            <div class="header-nota">
                <div class="brand">
                    <h1>homedress</h1>
                    <p>♡ bykamila ♡</p>
                </div>
                <div>
                    <div class="contact">
                        <!-- Icon Instagram SVG -->
                        <p>
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                            </svg>
                            bykamila__
                        </p>
                        <!-- Icon WhatsApp SVG -->
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
                <div class="info-box">
                    Nama Customer
                    <span id="out-nama">-</span>
                </div>
                <div class="info-box">
                    Tanggal Order
                    <span id="out-tanggal">-</span>
                </div>
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
                    <!-- Subtotal barang -->
                    <tr>
                        <td colspan="3" class="align-left" style="background-color: var(--pink-light);">Subtotal</td>
                        <td class="align-right" style="background-color: var(--pink-light);" id="out-subtotal">Rp 0</td>
                    </tr>
                    <!-- Baris Diskon (Akan disembunyikan otomatis jika tidak ada diskon) -->
                    <tr id="row-diskon" style="display: none;">
                        <td colspan="3" class="align-left" style="color: var(--pink-main);">Diskon</td>
                        <td class="align-right" id="out-val-diskon" style="color: var(--pink-main);">- Rp 0</td>
                    </tr>
                    <tr>
                        <td colspan="3" class="align-left">Ongkir</td>
                        <td class="align-right" id="out-ongkir">Rp 0</td>
                    </tr>
                    <tr>
                        <td colspan="3" class="grand-total align-left">Total</td>
                        <td class="grand-total-val align-right" id="out-total">Rp 0</td>
                    </tr>
                </tbody>
            </table>

            <div class="footer-thanks">
                <span style="font-family: 'Dancing Script', cursive; font-size: 24px; color: var(--pink-main);">♡ Terima kasih sudah order ♡</span><br>
                <span style="font-size: 13px; font-weight: 600; color: var(--text-dark);">- Semoga suka dengan produknya di Homedress bykamila -</span>
            </div>
        </div>
    </div>
</div>

<script>
    const formatRp = (angka) => new Intl.NumberFormat('id-ID').format(angka);

    function tambahBaris() {
        const container = document.getElementById('item-container');
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <input type="text" class="in-barang" placeholder="Nama Barang" style="flex:2.2" oninput="updateNota()">
            <input type="number" class="in-jumlah" placeholder="Jml" style="flex:0.8" inputmode="numeric" oninput="updateNota()">
            <input type="number" class="in-harga" placeholder="Harga" style="flex:1.4" inputmode="numeric" oninput="updateNota()">
        `;
        container.appendChild(row);
    }

    function updateNota() {
        document.getElementById('out-nama').innerText = document.getElementById('in-nama').value || '....................';
        document.getElementById('out-tanggal').innerText = document.getElementById('in-tanggal').value || '....................';

        const barangInputs = document.querySelectorAll('.in-barang');
        const jumlahInputs = document.querySelectorAll('.in-jumlah');
        const hargaInputs = document.querySelectorAll('.in-harga');
        
        let outItemsHTML = '';
        let subtotalBarang = 0;
        let rowsCount = Math.max(3, barangInputs.length);

        for (let i = 0; i < rowsCount; i++) {
            let nama = (i < barangInputs.length) ? barangInputs[i].value : '';
            let jml = (i < jumlahInputs.length) ? (parseInt(jumlahInputs[i].value) || 0) : 0;
            let harga = (i < hargaInputs.length) ? (parseInt(hargaInputs[i].value) || 0) : 0;

            if(jml > 0 && harga > 0) {
                subtotalBarang += (jml * harga);
            }

            outItemsHTML += `
                <tr>
                    <td>${nama ? (i + 1) : ''}</td>
                    <td class="align-left">${nama}</td>
                    <td>${jml ? jml + ' pcs' : ''}</td>
                    <td class="align-right">${harga ? 'Rp ' + formatRp(harga * jml) : ''}</td>
                </tr>
            `;
        }
        
        document.getElementById('out-items').innerHTML = outItemsHTML;

        // Logika Diskon & Ongkir
        const diskonTotal = parseInt(document.getElementById('in-diskon').value) || 0;
        const ongkir = parseInt(document.getElementById('in-ongkir').value) || 0;
        const grandTotal = subtotalBarang - diskonTotal + ongkir;

        // Atur kemunculan baris Diskon
        const rowDiskon = document.getElementById('row-diskon');
        if (diskonTotal > 0) {
            rowDiskon.style.display = 'table-row';
            document.getElementById('out-val-diskon').innerText = '- Rp ' + formatRp(diskonTotal);
        } else {
            rowDiskon.style.display = 'none';
        }

        // Tampilkan Harga
        document.getElementById('out-subtotal').innerText = 'Rp ' + formatRp(subtotalBarang);
        document.getElementById('out-ongkir').innerText = 'Rp ' + formatRp(ongkir);
        document.getElementById('out-total').innerText = 'Rp ' + formatRp(grandTotal);
    }

    function simpanGambar() {
        const nota = document.getElementById('nota-area');
        let nama = document.getElementById('in-nama').value || 'Pelanggan';
        
        // Background putih solid untuk hasil canvas yang tajam
        html2canvas(nota, { scale: 2, backgroundColor: "#ffffff" }).then(canvas => {
            const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
            
            const box = document.getElementById('hasil-gambar-box');
            const img = document.getElementById('preview-jpg');
            img.src = dataUrl;
            box.style.display = 'block';
            box.scrollIntoView({ behavior: 'smooth' });

            const link = document.createElement('a');
            link.download = `Nota_${nama}.jpg`;
            link.href = dataUrl;
            link.click();
        });
    }

    updateNota();
</script>
</body>
</html>
"""

components.html(html_code, height=1150, scrolling=True)
