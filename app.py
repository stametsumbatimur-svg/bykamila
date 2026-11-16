import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Generator Nota ByKamila",
    page_icon="🧾",
    layout="centered"
)

# Menghilangkan ruang kosong berlebih di atas layar HP
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
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Nunito:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        :root {
            --pink-main: #d81b60;
            --pink-light: #fce4ec;
            --pink-border: #e91e63;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Nunito', sans-serif;
        }
        body {
            background-color: transparent;
            color: #333;
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
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #f0f0f0;
        }
        .form-group { margin-bottom: 12px; }
        .form-group label {
            display: block;
            margin-bottom: 4px;
            font-weight: 700;
            font-size: 13px;
            color: #444;
        }
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 15px;
        }
        .item-row {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            background: #fafafa;
            padding: 8px;
            border-radius: 8px;
        }
        .item-row input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            width: 100%;
        }
        button {
            background-color: var(--pink-main);
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 700;
            font-size: 15px;
            width: 100%;
            margin-top: 8px;
        }
        button:active { background-color: #ad1457; }
        .btn-add { background-color: #2e7d32; font-size: 14px; padding: 10px; }
        
        .preview-section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 12px;
        }
        .nota-box {
            background: white;
            width: 100%;
            max-width: 450px;
            margin: 0 auto;
            padding: 18px;
            color: var(--pink-main);
        }
        .header-nota {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .brand h1 {
            font-family: 'Dancing Script', cursive;
            font-size: 38px;
            line-height: 1;
        }
        .brand p {
            font-family: 'Dancing Script', cursive;
            font-size: 22px;
            text-align: center;
        }
        .contact {
            font-size: 13px;
            font-weight: bold;
            text-align: right;
        }
        .contact p { margin-bottom: 2px; }
        .thanks-top {
            font-family: 'Dancing Script', cursive;
            font-size: 20px;
            text-align: center;
            margin-top: 6px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            gap: 5px;
            margin-bottom: 10px;
        }
        .info-box {
            border: 2px solid var(--pink-border);
            border-radius: 8px;
            padding: 5px 8px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
            flex: 1;
        }
        .info-box span {
            display: block;
            color: #333;
            font-size: 14px;
            margin-top: 2px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
            text-align: center;
        }
        table th, table td {
            border: 2px solid var(--pink-border);
            padding: 7px 5px;
            font-weight: bold;
        }
        table th {
            background-color: var(--pink-light);
            font-size: 13px;
        }
        table td { color: #333; font-size: 13px; }
        .align-right { text-align: right; }
        .align-left { text-align: left; }
        .discount-text {
            font-size: 11px;
            color: var(--pink-main);
        }
        .grand-total {
            font-family: 'Dancing Script', cursive;
            font-size: 28px;
            color: var(--pink-main);
        }
        .grand-total-val {
            font-size: 20px;
            color: var(--pink-main);
        }
        .footer-info {
            display: flex;
            gap: 8px;
            margin-bottom: 10px;
        }
        .footer-info .info-box {
            text-align: left;
            display: flex;
            align-items: center;
            padding: 8px;
        }
        .footer-thanks {
            border: 2px solid var(--pink-border);
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            font-family: 'Dancing Script', cursive;
            font-size: 18px;
        }
        #hasil-gambar-box {
            display: none;
            margin-top: 15px;
            padding: 12px;
            background: #fff8fa;
            border: 2px dashed var(--pink-border);
            border-radius: 10px;
            text-align: center;
        }
        #hasil-gambar-box img {
            width: 100%;
            max-width: 400px;
            border-radius: 8px;
            margin-top: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
    </style>
</head>
<body>

<div class="container">
    <div class="form-section">
        <h3 style="color: var(--pink-main); margin-bottom: 12px;">Input Data Nota</h3>
        <div class="form-group">
            <label>Nama Customer</label>
            <input type="text" id="in-nama" placeholder="Contoh: Bude Heni" oninput="updateNota()">
        </div>
        <div class="form-group">
            <label>Tanggal Order</label>
            <input type="text" id="in-tanggal" placeholder="Contoh: 16 Nov 2026" oninput="updateNota()">
        </div>

        <label style="font-weight: 700; font-size: 13px; color: #444; display: block; margin-bottom: 6px;">Daftar Barang</label>
        <div id="item-container">
            <div class="item-row">
                <input type="text" class="in-barang" placeholder="Nama Barang" style="flex:2.2" oninput="updateNota()">
                <input type="number" class="in-jumlah" placeholder="Jml" style="flex:0.8" inputmode="numeric" oninput="updateNota()">
                <input type="number" class="in-harga" placeholder="Harga" style="flex:1.4" inputmode="numeric" oninput="updateNota()">
            </div>
        </div>
        <button class="btn-add" onclick="tambahBaris()">+ Tambah Barang</button>

        <div style="display: flex; gap: 8px; margin-top: 12px;">
            <div class="form-group" style="flex:1">
                <label>Potongan / Item (Rp)</label>
                <input type="number" id="in-diskon" placeholder="10000" inputmode="numeric" oninput="updateNota()">
            </div>
            <div class="form-group" style="flex:1">
                <label>Ongkir (Rp)</label>
                <input type="number" id="in-ongkir" placeholder="5000" inputmode="numeric" oninput="updateNota()">
            </div>
        </div>
        
        <div style="display: flex; gap: 8px;">
            <div class="form-group" style="flex:1">
                <label>Berat (Kg)</label>
                <input type="text" id="in-berat" placeholder="1" oninput="updateNota()">
            </div>
            <div class="form-group" style="flex:1">
                <label>Jml Paket</label>
                <input type="text" id="in-paket" placeholder="1" oninput="updateNota()">
            </div>
        </div>

        <button onclick="simpanGambar()">Buat & Simpan Gambar JPG</button>

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
                        <p>◎ bykamila__</p>
                        <p>✆ 0895-2608-7445</p>
                    </div>
                    <div class="thanks-top">Terima Kasih<br>Sudah Belanja ♡</div>
                </div>
            </div>

            <div class="info-row">
                <div class="info-box">
                    Nama Customer :
                    <span id="out-nama">....................</span>
                </div>
                <div class="info-box">
                    Tanggal Order :
                    <span id="out-tanggal">....................</span>
                </div>
                <div class="info-box">
                    Status :
                    <span>☑ Selesai</span>
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
                    <tr>
                        <td colspan="2" class="discount-text align-left" id="out-teks-diskon">
                            Potongan Reseller : Rp 0 / item<br>( 0 x 0 = Rp 0 )
                        </td>
                        <td style="background-color: var(--pink-light);">Subtotal</td>
                        <td class="align-right" id="out-subtotal">Rp 0</td>
                    </tr>
                    <tr>
                        <td colspan="3" class="align-left" style="color: var(--pink-main);">Ongkir</td>
                        <td class="align-right" id="out-ongkir">Rp 0</td>
                    </tr>
                    <tr>
                        <td colspan="3" class="grand-total align-left" style="background-color: var(--pink-light);">Total</td>
                        <td class="grand-total-val align-right" style="background-color: var(--pink-light);" id="out-total">Rp 0</td>
                    </tr>
                </tbody>
            </table>

            <div class="footer-info">
                <div class="info-box" style="flex:1">Berat (Kg) : <span id="out-berat" style="margin-left: 8px; font-weight:normal;"></span></div>
                <div class="info-box" style="flex:1">Jml Paket : <span id="out-paket" style="margin-left: 8px; font-weight:normal;"></span></div>
            </div>

            <div class="footer-thanks">
                ♡ Terima kasih sudah order di Homedress bykamila ♡<br>
                <span style="font-size: 14px; font-family: 'Nunito', sans-serif;">- Semoga suka dengan produknya -</span>
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
        document.getElementById('out-berat').innerText = document.getElementById('in-berat').value || '';
        document.getElementById('out-paket').innerText = document.getElementById('in-paket').value || '';

        const barangInputs = document.querySelectorAll('.in-barang');
        const jumlahInputs = document.querySelectorAll('.in-jumlah');
        const hargaInputs = document.querySelectorAll('.in-harga');
        
        let outItemsHTML = '';
        let totalHargaBarang = 0;
        let totalPieces = 0;
        let rowsCount = Math.max(3, barangInputs.length);

        for (let i = 0; i < rowsCount; i++) {
            let nama = (i < barangInputs.length) ? barangInputs[i].value : '';
            let jml = (i < jumlahInputs.length) ? (parseInt(jumlahInputs[i].value) || 0) : 0;
            let harga = (i < hargaInputs.length) ? (parseInt(hargaInputs[i].value) || 0) : 0;

            if(jml > 0 && harga > 0) {
                totalHargaBarang += (jml * harga);
                totalPieces += jml;
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

        const diskonPerItem = parseInt(document.getElementById('in-diskon').value) || 0;
        const totalDiskon = totalPieces * diskonPerItem;
        const subtotalAkhir = totalHargaBarang - totalDiskon;
        const ongkir = parseInt(document.getElementById('in-ongkir').value) || 0;
        const grandTotal = subtotalAkhir + ongkir;

        document.getElementById('out-teks-diskon').innerHTML = `Potongan Reseller : Rp ${formatRp(diskonPerItem)} / item<br>( ${totalPieces} x ${formatRp(diskonPerItem)} = Rp ${formatRp(totalDiskon)} )`;
        document.getElementById('out-subtotal').innerText = 'Rp ' + formatRp(subtotalAkhir);
        document.getElementById('out-ongkir').innerText = 'Rp ' + formatRp(ongkir);
        document.getElementById('out-total').innerText = 'Rp ' + formatRp(grandTotal);
    }

    function simpanGambar() {
        const nota = document.getElementById('nota-area');
        let nama = document.getElementById('in-nama').value || 'Pelanggan';
        
        html2canvas(nota, { scale: 2, backgroundColor: "#ffffff" }).then(canvas => {
            const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
            
            // Tampilkan gambar di layar agar mudah disimpan ke Galeri iPhone
            const box = document.getElementById('hasil-gambar-box');
            const img = document.getElementById('preview-jpg');
            img.src = dataUrl;
            box.style.display = 'block';
            box.scrollIntoView({ behavior: 'smooth' });

            // Tetap picu unduhan otomatis untuk browser desktop/Android
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

components.html(html_code, height=1350, scrolling=True)
