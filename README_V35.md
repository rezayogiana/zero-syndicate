# ZERO SYNDICATE V3.5 — READY FOR CLOUDFLARE PAGES + RENDER

## Status
- Astro Matrix: ephemeris calculation via existing Python Render API. **Dinamika arah BUY/SELL ASTRO ONLY** dipicu setiap perubahan tanggal, jam, zona waktu, koordinat; alasan aspek & skor simbolik nyata. Bukan saran transaksi atau prediksi tervalidasi.
- Signal Command: panel Astro BUY/SELL, kondisi XAUUSD Quant (jika data aktual tersedia), indikator kalender news (jika feed tersedia), tombol scan, tombol sinkronisasi waktu sekarang (WIB), copy laporan, riwayat browser dan ekspor CSV.
- News Radar: mencoba feed mingguan (cakupan terbatas), filter tanggal/impact, refresh berkala saat tab aktif, TradingView sebagai cadangan resmi.
- NARA: model eksternal hanya aktif setelah **GEMINI_API_KEY** yang masih aman disetel sebagai secret Render. Tanpa model, gunakan fallback lokal yang diberi label jelas.
- Quant Lab: EMA/RSI/ATR dan analogi momentum dari candle XAUUSD berizin (adapter OANDA bila ada token dan izin) atau CSV historis. Analisis **tidak** mengirim order.
- 3D: WebGL shader independen dengan fallback; menu hamburger, sosial, VIP, WhatsApp admin.

## INSTALL (repository GitHub kamu saat ini)
1. Cabut API key Gemini yang pernah dikirim ke chat. Buat yang BARU di Google AI Studio; jangan taruh di GitHub, file HTML atau chat.
2. Pastikan Render sudah Live (`https://zero-syndicate.onrender.com/api/health`) dan Cloudflare API proxy juga bekerja (`https://zero-syndicate.pages.dev/api/health`).
3. Unduh ZIP **FULL** dan ekstrak. Upload isi folder `public/`, `functions/`, dan `backend/` ke GitHub `rezayogiana/zero-syndicate` **dengan struktur folder terjaga**. Jangan upload ZIP-nya mentah. Timpa file lama, tambahkan `public/signal35.js`.
4. Commit ke branch `main`. Tunggu Cloudflare Pages dan Render masing-masing deploy terbaru. Jika auto-deploy Render nonaktif, trigger `Manual Deploy → Deploy latest commit`.
5. Di Cloudflare Pages → Settings → Variables and Secrets (Production), `BACKEND_URL` tetap `https://zero-syndicate.onrender.com`. Simpan dan redeploy jika variabel berubah.
6. Periksa `https://zero-syndicate.pages.dev/api/health`: versi **3.5**. `analyst_model_configured` true hanya bermakna ada key, bukan jaminan API valid. Tes chat NARA.
7. Periksa `https://zero-syndicate.pages.dev/api/signal/astro?date=2026-10-18&clock=13:00&tz=Asia/Jakarta&lat=-6.2088&lon=106.8456` → direction BUY. Ubah date ke `2026-10-24` → SELL. Hasil arah bergantung pada waktu, lokasi, versi dan aturan aspek yang dikodekan.
8. Buka `https://zero-syndicate.pages.dev/#command`. Pada UI pilih tanggal & jam di Astro, klik HITUNG CHART. Lihat panel Signal Command berubah dan alasan terhitung. `SYNC JAM SEKARANG (WIB)` otomatis menghitung ulang setiap pergantian menit **saat tab terbuka**. Tidak ada background scheduler.

## Render
- GitHub repo: `rezayogiana/zero-syndicate` | Root Directory: `backend` | Python 3.
- Build: `pip install -r requirements.txt`
- Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Free instances may sleep when idle. This does **not** provide uninterrupted always-on signals.

## OPTIONAL API KEYS (Render Environment, bukan frontend)
- `GEMINI_API_KEY` = fresh, unexposed key; default model backend = `gemini-2.5-flash` (check actual availability in your Google project). Restart service and test endpoint. Set `GEMINI_MODEL` only if supported by your account.
- `OANDA_API_TOKEN` = authorized OANDA v20 API access for `XAU_USD` if provided in your region/account.
- `OANDA_API_BASE` = `https://api-fxpractice.oanda.com` for appropriate practice API; not a promise of free gold data.
- Broker Valetax referral link does not provide market data or order API.

## Modules and endpoints
- `/api/health` (version `3.5` and feature configuration states)
- `/api/astro` (actual ephemeris positions/houses/aspects)
- `/api/signal/astro` (compact symbolic BUY/SELL + reasons, no auto-trades)
- `/api/calendar` (economics if source available)
- `/api/analyst` POST (form-data; NARA fallback/model)
- `/api/xauusd/analyze` (only when legitimate price API configured)
- `/api/xauusd/csv` POST (upload OHLC file, historical research)

## Limits & safety
- BUY/SELL Astro Direction is an illustrative **symbolic** mathematical scoring rule, NOT an empirically validated XAUUSD forecast. The numbers are not confidence/win rate. "Not Financial Advice" does not make an unvalidated system reliably profitable.
- Quant dashboard does not automatically execute trades; no broker password, order placement, guaranteed profit, or fake price/news is included.
- No promise of 24/7 cron, no promise access to third-party feeds, no automatic circumvention of blocks or paywalls.
- Stored snapshots stay in this browser's localStorage (max 25, no cloud account); CSV export is user initiated.
- Swiss Ephemeris license obligations (AGPL/professional) may apply to commercial deployment. Check terms before using commercially.
- Broker cashback $9–$12/lot is described as conditional/subject to confirmation, not guaranteed.

## Single-file preview
Open `ZERO_SYNDICATE_V35_PREVIEW.html` locally. It contains computed ephemeris snapshots for **exact dates/configurations only**. Live API calls, Gemini and market data require a deployed backend; browsing other date without connection does not fabricate a new reading.
