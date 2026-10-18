# ZERO SYNDICATE V4.0.1 — Perbaikan Meet NARA

## Apa yang diperbaiki

- Chat tidak lagi mengambil kalender Forex Factory untuk setiap pertanyaan biasa. Kalendar tetap dicari ketika pertanyaan memang terkait berita; selebihnya memakai cache jika ada.
- Panggilan model dipindah dari operasi blocking ke thread agar server FastAPI tetap responsif ketika menunggu penyedia.
- Waktu tunggu browser diperpanjang agar lebih tahan Render Free yang bangun dari mode tidur.
- Kesalahan model kini ditampilkan sebagai kode pemeriksaan aman tanpa membocorkan API key (misalnya GEMINI_HTTP_403 atau GEMINI_HTTP_429).
- Versi backend diperbarui menjadi `4.0.1`.
- Jika key belum disetel, NARA menjawab dengan mode dasar. Untuk percakapan bebas dan pembacaan gambar, model Gemini harus aktif.

## Cara pasang

1. Buka GitHub `rezayogiana/zero-syndicate`.
2. Unggah **isi** folder `backend` dan `public` dari ZIP ke repository, menggantikan dua file ini saja:
   - `backend/server.py`
   - `public/app.js`
   File `backend/quant_engine.py` **tidak berubah** dan tidak perlu diunggah ulang.
3. Commit ke branch `main`. Tunggu deploy otomatis Cloudflare Pages dan Render sampai berhasil.
4. Pastikan `https://zero-syndicate.pages.dev/api/health` menampilkan `"version":"4.0.1"`.
5. Buka `https://zero-syndicate.pages.dev/#analyst`; tekan `Ctrl + F5` supaya JS terbaru dipakai.
6. Coba ketik: `Halo NARA, jelaskan EMA 20 untuk XAUUSD dalam 3 kalimat.`
7. Jika muncul `GEMINI_HTTP_403`, buka Render -> zero-syndicate -> Environment: pastikan `GEMINI_API_KEY` adalah **key baru** yang valid, bukan key yang pernah dibagikan. Bila muncul `GEMINI_HTTP_404`, cek `GEMINI_MODEL`.
8. Model `gemini-3.5-flash-lite` digunakan sebagai bawaan saat `GEMINI_MODEL` belum diatur. Model harus tersedia untuk akun/kuota kamu. Jika `429`, tunggu kuota atau pilih model yang masih tersedia di Google AI Studio; jangan mengarang API key.

## Penting

- Jangan sekali-kali mengirim key ke percakapan atau menyimpannya di file HTML/JS atau GitHub.
- `analyst_model_configured: true` hanya menandakan key terpasang, **bukan** bukti key diterima Google.
- Kode ini tidak menyediakan order trading otomatis.
- Tidak ada klaim menang pasti atau akurasi trading yang tervalidasi.
