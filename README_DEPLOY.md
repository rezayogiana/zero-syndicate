# ZERO SYNDICATE V3 — panduan ringkas

Paket ini melanjutkan V2, **tidak** mengubah akun, repo, atau domain Cloudflare milik Anda. Fitur kuantitatif adalah **analisis riset/paper-trading, bukan auto-execution**.

## 1. Update GitHub → Cloudflare Pages
1. Unduh dan ekstrak `ZERO_SYNDICATE_V3_FULL_CODE.zip`.
2. Upload isi folder `public/`, `functions/`, dan `backend/` ke lokasi yang **sama** di repository `rezayogiana/zero-syndicate` (replace file dengan nama sama; tambahkan `quant.js` dan `quant_engine.py`). Tidak perlu menghapus folder yang lain.
3. Pastikan `public/index.html`, `public/quant.js`, `backend/quant_engine.py`, dan `functions/api/[[path]].js` masuk pada commit branch `main`. GitHub browser UI dapat memerlukan upload isi folder satu per satu dengan path yang benar. Jangan upload ZIP langsung.
4. Cloudflare Pages meng-deploy branch `main`, Framework `None`, Build Command kosong, Build output `public`, Root default. Tunggu deployment `Success` dengan commit terbaru.
5. Buka `https://zero-syndicate.pages.dev/#quant`. Panel XAUUSD Quant Lab muncul, tetapi tanpa backend dan data harga otomatis statusnya `WAIT`.

## 2. Aktifkan backend Python gratis (jika belum)
1. Daftar Render di https://dashboard.render.com/, pilih `New → Web Service` dan hubungkan repository GitHub.
2. Set Name `zero-syndicate-api`, Root Directory `backend`, Branch `main`, Language `Python 3`, Build Command `pip install -r requirements.txt`, Start Command `uvicorn server:app --host 0.0.0.0 --port $PORT`. Pilih `Free` jika tersedia.
3. Deploy sampai status `Live`, lalu cek `https://NAMA-SERVICE.onrender.com/api/health`. Respons berisi `ok: true` dan `version: 3.0`.
4. Cloudflare → Workers & Pages → ZERO SYNDICATE → Settings → Variables and Secrets → `BACKEND_URL` isi URL Render HTTPS origin saja (tanpa `/api`, tanpa trailing slash), untuk **Production**. `Save` dan deploy ulang.
5. Uji `https://zero-syndicate.pages.dev/api/health`. Kalau 503, cek secret dan deploy ulang; kalau 502, lihat log Render. Render Free tidur setelah 15 menit idle; tidak menjamin 24/7 tanpa cold start.

## 3. Pilih metode data harga XAUUSD
**Pilihan A — tanpa API:** unggah CSV OHLC dari data yang Anda miliki dan berhak pakai. CSV berisi `Time,Open,High,Low,Close`, paling sedikit 100 candle. Buka `#quant`, pilih M15/H1/H4 dan klik `SCAN CSV`. Mode ini menghasilkan riset historis dan **tidak mengklaim sinyal live**.

**Pilihan B — pembaruan otomatis saat web terbuka:** dapatkan akses API data candle XAU/USD yang legal bagi akun dan wilayah Anda. Paket contoh menyediakan adapter OANDA v20 dengan simbol `XAU_USD` **jika akun Anda benar-benar memiliki izin instrumen ini**. Di Render → Environment tambahkan `OANDA_API_TOKEN` (jangan pernah di GitHub) dan, bila perlu, `OANDA_API_BASE=https://api-fxpractice.oanda.com`. Ini membutuhkan akun dan token sendiri; layanan gratis dan instrumen gold **tidak dijamin tersedia untuk setiap pengguna/yurisdiksi**. Selanjutnya frontend memeriksa setiap ~90 detik ketika halaman dibuka; backend meng-cache candle ~75 detik. Situs tidak memproses scan terus-menerus saat tidak ada browser aktif atau Render tidur.

Jika ingin data dari broker Valetax, minta **izin API resmi** dan dokumentasi endpoint terlebih dahulu. Link referral Valetax **bukan** akses API harga. Jangan mengorek/scrape data dari sumber yang melarangnya.

## 4. News & NARA
- News Radar memakai ekspor mingguan Forex Factory bila sumber mengizinkan dan tersedia, serta widget TradingView sebagai fallback. Ketika feed gagal, engine **tidak** memberi lampu hijau otomatis pada setup XAUUSD.
- Di Render → Environment, `GEMINI_API_KEY` (jika tersedia) untuk analisis file/foto NARA. Simpan di server, bukan HTML atau source GitHub. Lihat `README_DEPLOY.md` untuk instruksi lengkap.
- Posisi Astro/Placidus dihitung di backend menggunakan Swiss Ephemeris; perhatikan ketentuan lisensi AGPL-3.0 atau lisensi profesional sebelum komersialisasi.

## 5. Interpretasi XAUUSD QUANT LAB
- Analisis: EMA20/50, RSI14, ATR14, breakout 20 candle, velocity & acceleration harga (dinormalisasi ATR), high-impact event USD ±45 menit jika feed tervalidasi.
- Output: `BUY_SETUP`, `SELL_SETUP`, atau `WAIT`. Nilai setup bukan probabilitas atau win rate. Harga referensi, SL=1.5 ATR, TP=3 ATR hanyalah *contoh* kerangka 1:2 dan belum memperhitungkan spread/slippage/komisi yang aktual.
- `WAIT` digunakan jika harga stale/tidak ada, berita belum terverifikasi, dekat rilis high-impact USD, atau tidak ada setup pasar. Tampilan astrologi tidak ikut menaikkan skor harga.
- Tidak ada fungsi `place_order()` dan tidak ada kunci broker trading yang diperlukan.
- Sebelum penggunaan nyata, lakukan backtest *out-of-sample* dengan biaya transaksi, backtest berjalan (walk-forward), paper trading, audit data, serta limit risiko. Jangan mengklaim win rate mendekati 100%.

## 6. Tes cepat
- `GET /api/health` → JSON `ok:true`, `version:3.0`, `xau_price_configured`.
- `GET /api/astro?date=2026-10-28&clock=13:00&tz=America/New_York&lat=40.7128&lon=-74.006` → data planet dan cusp rumah.
- `GET /api/xauusd/analyze?timeframe=M15` → `503` dengan pesan jelas jika data source belum tersambung; saat tersambung JSON terstruktur.
- `POST /api/xauusd/csv` berisi `file` CSV dan `timeframe` M15/H1/H4 → respons analisis historis.
- `GET /api/calendar?date=2026-10-18&tz=Asia/Jakarta` → events jika feed tersedia; jika tidak, status offline jujur.

Sumber teknis: https://developers.cloudflare.com/pages/functions/bindings/ | https://render.com/docs/free | https://developer.oanda.com/rest-live-v20/instrument-ep/ | https://threejs.org/manual/pages/installation.html
