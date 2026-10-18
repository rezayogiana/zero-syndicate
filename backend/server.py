"""ZERO SYNDICATE API. Run: uvicorn server:app --host 127.0.0.1 --port 8000"""
from __future__ import annotations
import base64, csv, io, json, math, os, re, threading, time, asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import swisseph as swe
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request

BASE = Path(__file__).resolve().parent
app = FastAPI(title='ZERO SYNDICATE Market Desk', version='4.0.1')
_rate_guard = {}  # best-effort process-local public API guard; not a substitute for Cloudflare rate limiting
NAMES = [
 ('Sun','☉',swe.SUN), ('Moon','☽',swe.MOON), ('Mercury','☿',swe.MERCURY),
 ('Venus','♀',swe.VENUS), ('Mars','♂',swe.MARS), ('Jupiter','♃',swe.JUPITER),
 ('Saturn','♄',swe.SATURN), ('Uranus','♅',swe.URANUS), ('Neptune','♆',swe.NEPTUNE),
 ('Pluto','♇',swe.PLUTO), ('North Node','☊',swe.MEAN_NODE)
]
SIGNS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
ASPECTS = [('conjunction',0,7), ('sextile',60,4), ('square',90,5), ('trine',120,5), ('opposition',180,7)]
FEED_URLS = [
 'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
 'https://nfs.faireconomy.media/ff_calendar_nextweek.json',
]
_cache = {'at': 0., 'events': [], 'errors': [], 'fetched': None}
_cache_lock = threading.Lock()

@app.get('/')
def api_home(): return {'service': 'ZERO SYNDICATE API', 'health': '/api/health'}

@app.get('/api/health')
def health(): return {'ok': True, 'version':'4.0.1', 'astro_engine': 'Swiss Ephemeris / Moshier', 'calendar_cache_seconds': 900, 'analyst_model_configured': bool(os.getenv('GEMINI_API_KEY') or os.getenv('CHAT_API_KEY') or os.getenv('OPENAI_API_KEY')), 'calendar_source':'Forex Factory weekly public export; availability not guaranteed', 'xau_price_configured':bool(os.getenv('OANDA_API_TOKEN'))}

def wrap_delta(a,b): return abs((a-b+180)%360-180)


# XAUUSD / Astro Matrix directional *research* label.
# Arbitrary predeclared symbolic weights; NOT a demonstrated predictive model.
# No order placement or price recommendations. Calculated from genuine ephemeris only.
_ASTRO_RULES = {
    frozenset(('Moon', 'Jupiter')): {'trine': 3, 'sextile': 2, 'square': -2, 'opposition': -2, 'conjunction': 1},
    frozenset(('Moon', 'Saturn')): {'trine': 1, 'sextile': 1, 'square': -3, 'opposition': -3, 'conjunction': -2},
    frozenset(('Moon', 'Mars')): {'trine': 1, 'sextile': 1, 'square': -2, 'opposition': -2, 'conjunction': -1},
    frozenset(('Sun', 'Jupiter')): {'trine': 2, 'sextile': 2, 'square': -1, 'opposition': -1, 'conjunction': 1},
    frozenset(('Sun', 'Saturn')): {'trine': 1, 'sextile': 1, 'square': -2, 'opposition': -2, 'conjunction': -1},
    frozenset(('Moon', 'Venus')): {'trine': 2, 'sextile': 1, 'square': -1, 'opposition': -1, 'conjunction': 1},
}
_ASTRO_ASPECT_ID = {'trine': 'trigon', 'sextile': 'sekstil', 'square': 'kuadrat', 'opposition': 'oposisi', 'conjunction': 'konjungsi'}
_ASTRO_BODY_ID = {'Moon':'Bulan','Sun':'Matahari','Jupiter':'Jupiter','Saturn':'Saturnus','Mars':'Mars','Venus':'Venus'}

def directional_astro_research(planets: list[dict], aspects: list[dict]) -> dict:
    """Reproducible BUY/SELL *symbolic label*, not predictive price signal.

    Each recognised aspect contributes a disclosed signed weight. A deterministic
    waxing/waning Moon-Sun ecliptic separation breaks ties so every complete
    ephemeris has a direction. Never infer win rate/confidence from the score.
    """
    by_name={p['name']:p for p in planets}
    if not {'Moon','Sun','Jupiter','Saturn','Mars','Venus'} <= by_name.keys():
        raise ValueError('Posisi planet yang dibutuhkan belum lengkap')
    moon=by_name['Moon']['longitude']
    sun=by_name['Sun']['longitude']
    moon_sun_delta=(moon-sun)%360
    phase_word='waxing (sudut Bulan–Matahari 0–180°)' if moon_sun_delta < 180 else 'waning (sudut Bulan–Matahari 180–360°)'
    phase_weight=0.5 if moon_sun_delta < 180 else -0.5
    drivers=[]
    score=0
    for a in aspects:
        if not (isinstance(a,dict) and isinstance(a.get('a'),int) and isinstance(a.get('b'),int)):
            continue
        if a['a']<0 or a['b']<0 or a['a']>=len(planets) or a['b']>=len(planets):
            continue
        n1=planets[a['a']]['name']; n2=planets[a['b']]['name']
        weights=_ASTRO_RULES.get(frozenset((n1,n2)))
        if not weights: continue
        w=weights.get(a.get('type'),0)
        if not w: continue
        score+=w
        wording=f"{_ASTRO_BODY_ID.get(n1,n1)}–{_ASTRO_BODY_ID.get(n2,n2)} {_ASTRO_ASPECT_ID.get(a['type'],a['type'])}, orb {a['orb']}°"
        drivers.append({'aspect':wording, 'direction':'BUY' if w>0 else 'SELL', 'weight':w})
    drivers.sort(key=lambda a:(-abs(a['weight']), a['aspect']))
    total=score+phase_weight
    direction='BUY' if total>0 else 'SELL'
    reason_lines=[f"{d['aspect']}: bobot {d['weight']:+d} ({d['direction']})." for d in drivers[:5]]
    if not drivers:
        reason_lines=['Tidak ada aspek berbobot pada orb yang dipilih; arah ditentukan hanya oleh aturan pemutus seri fase.']
    reason_lines.append(f"Pemisahan ekliptika Bulan–Matahari {moon_sun_delta:.1f}° ({phase_word}); aturan pemutus seri {phase_weight:+.1f}.")
    confidence='HIGH PROBABILITY' if abs(total)>=1.5 else ('WATCH' if abs(total)<1 else 'ACTIVE')
    headline=f"{confidence} {direction}"
    return {
        'direction':direction,
        'headline':headline,
        'confidence_label':confidence,
        'score':round(total,1),
        'aspects_score':score,
        'phase_score':phase_weight,
        'drivers':reason_lines,
        'moon_sign':by_name['Moon']['sign'],
        'sun_sign':by_name['Sun']['sign'],
        'method':'ASTRO_SYMBOLIC_V1',
        'status':'ASTRO VIEW',
        'disclaimer':'NOT FINANCIAL ADVICE — hasil ini adalah pembacaan astro, bukan instruksi transaksi.'
    }

@app.get('/api/astro')
def astro(date: str, clock: str='13:00', tz: str='Asia/Jakarta', lat: float=-6.2088, lon: float=106.8456, houses: str='P'):
    if not -89.9 <= lat <= 89.9 or not -180 <= lon <= 180: raise HTTPException(400,'Koordinat tidak valid')
    if tz not in ['Asia/Jakarta','Asia/Makassar','Asia/Jayapura','UTC','America/New_York','Europe/London','Asia/Tokyo']:
        raise HTTPException(400,'Zona waktu tidak tersedia')
    if houses not in ['P', 'W']: raise HTTPException(400,'Sistem rumah tidak tersedia')
    try:
        d = datetime.strptime(date+' '+clock, '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
        if not 1900 <= d.year <= 2100: raise ValueError('range')
        jd = swe.julday(d.year, d.month, d.day, d.hour+d.minute/60+d.second/3600)
        cusps, anchors = swe.houses_ex(jd, lat, lon, houses.encode())
        planets=[]
        for name,glyph,code in NAMES:
            p, flag = swe.calc_ut(jd, code, swe.FLG_MOSEPH | swe.FLG_SPEED)
            lng = round(float(p[0])%360,5)
            planets.append({'name':name,'symbol':glyph,'longitude':lng,'sign':SIGNS[int(lng//30)],'degree':round(lng%30,2),'retrograde':p[3]<0})
        aspects=[]
        for i in range(len(planets)):
            for j in range(i+1,len(planets)):
                if i==len(planets)-1 or j==len(planets)-1: continue
                delta=wrap_delta(planets[i]['longitude'],planets[j]['longitude'])
                for name,target,orb in ASPECTS:
                    if abs(delta-target)<=orb:
                        aspects.append({'a':i,'b':j,'type':name,'orb':round(abs(delta-target),2)})
                        break
        astro_research = directional_astro_research(planets, aspects)
        astro_bias = astro_research['direction']
        return {'date_local': date, 'time_local':clock,'timezone':tz,'utc':d.isoformat(), 'location':{'lat':lat,'lon':lon},
                'house_system':'Placidus' if houses=='P' else 'Whole Sign', 'asc':round(anchors[0],5), 'mc':round(anchors[1],5),
                'cusps':[round(x,5) for x in cusps], 'planets':planets, 'aspects':aspects,'astro_bias':astro_bias,
                'astro_bias_details':astro_research,
                'bias_explanation':f"{astro_research['headline']}. Skor {astro_research['score']:+.1f}; aspek {astro_research['aspects_score']:+d}, fase {astro_research['phase_score']:+.1f}. Cocokkan dengan harga dan news.",
                'signal':astro_research['headline'],'signal_reason':'Gunakan pembacaan ini sebagai bias awal, lalu cocokkan dengan harga, struktur, dan agenda news.',
                'engine':'Swiss Ephemeris / Moshier; posisi geosentris tropikal'}
    except HTTPException: raise
    except Exception as e: raise HTTPException(400,f'Gagal menghitung chart: {str(e)[:140]}')

@app.get('/api/signal/astro')
def astro_direction(date: str, clock: str='13:00', tz: str='Asia/Jakarta', lat: float=-6.2088, lon: float=106.8456, houses: str='P'):
    """Return calculated ephemeris-derived symbolic BUY/SELL, never a trade order."""
    data = astro(date, clock, tz, lat, lon, houses)
    return {
        'ok': True, 'version': '4.0', 'instrument': 'XAUUSD',
        'direction': data['astro_bias'], 'research_only': True,
        'calculated_for': {'date':date, 'time':clock, 'timezone':tz, 'lat':lat, 'lon':lon},
        'house_system': data['house_system'], 'astro': data['astro_bias_details'],
        'as_of_utc': data['utc'], 'engine':data['engine'],
        'not_financial_advice': True, 'auto_entry_enabled':False,
    }

def clean_event(ev):
    try:
        raw_date=str(ev.get('date') or '').strip()
        d=datetime.fromisoformat(raw_date.replace('Z','+00:00'))
        # Provider's weekly JSON is commonly ISO8601, including UTC offsets.
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        when=d.astimezone(timezone.utc)
        impact=str(ev.get('impact') or 'Unknown')
        return {'title':str(ev.get('title') or 'Unnamed event')[:200],
                'country':str(ev.get('country') or '')[:15], 'impact':impact[:30],
                'actual':str(ev.get('actual') or '')[:60], 'forecast':str(ev.get('forecast') or '')[:60],
                'previous':str(ev.get('previous') or '')[:60], 'at':when.isoformat()}
    except (ValueError,TypeError,AttributeError): return None

def calendar_raw():
    now=time.time()
    with _cache_lock:
        if now-_cache['at'] < 900: return dict(_cache)
        events, errors=[] ,[]
        for url in FEED_URLS:
            try:
                res=requests.get(url,timeout=8,headers={'User-Agent':'ZERO-SYNDICATE-DASHBOARD/1.0 (calendar display)'})
                res.raise_for_status()
                payload=res.json()
                if not isinstance(payload,list): raise ValueError('Format kalender tidak didukung')
                for entry in payload:
                    if isinstance(entry,dict):
                        clean=clean_event(entry)
                        if clean: events.append(clean)
            except Exception as e: errors.append(f'{url.rsplit("/",1)[-1]}: {type(e).__name__}')
        seen=set(); dedup=[]
        for e in sorted(events,key=lambda x:x['at']):
            k=(e['at'],e['title'],e['country'])
            if k not in seen: seen.add(k); dedup.append(e)
        _cache.update({'at':now,'events':dedup,'errors':errors,'fetched':datetime.now(timezone.utc).isoformat() if dedup else None})
        return dict(_cache)

@app.get('/api/calendar')
def calendar(date: str, tz: str='Asia/Jakarta', impact: str='all'):
    try:
        target=datetime.strptime(date,'%Y-%m-%d').date(); zone=ZoneInfo(tz)
    except (ValueError,KeyError): raise HTTPException(400,'Tanggal / zona waktu tidak valid')
    data=calendar_raw()
    subset=[]
    for e in data['events']:
        localized=datetime.fromisoformat(e['at']).astimezone(zone)
        if localized.date()==target and (impact=='all' or e['impact'].lower()==impact.lower()):
            subset.append({**e,'time_local':localized.strftime('%H:%M'),'date_local':localized.date().isoformat()})
    return {'events':subset,'date':date,'timezone':tz,'live':bool(data['events']), 'last_updated':data['fetched'],
            'source':'Forex Factory weekly JSON export (Fair Economy)', 'source_url':'https://www.forexfactory.com/calendar',
            'notice': ('Feed tidak tersedia atau server tidak dapat menjangkau sumber. Tidak ada data yang direka.' if not data['events']
                        else 'Feed mingguan tidak mencakup semua tanggal historis atau masa depan; kosong belum tentu tidak ada news.'),
            'errors':data['errors']}

def read_csv_zones(binary: bytes):
    try:
        text=binary.decode('utf-8-sig',errors='replace')
        rows=list(csv.DictReader(io.StringIO(text)))
        if not rows: return 'CSV tidak memiliki data.'
        keys={k.lower().strip():k for k in rows[0].keys() if k}
        if not all(k in keys for k in ['high','low','close']): return 'CSV harus berisi kolom High, Low, Close (opsional Open/Time).'
        bars=[]
        for row in rows[-2000:]:
            try:
                h,l,c=(float(str(row[keys[k]]).replace(',','')) for k in ('high','low','close'))
                if math.isfinite(h) and math.isfinite(l) and math.isfinite(c) and l<=c<=h:
                    bars.append({'high':h,'low':l,'close':c})
            except (ValueError,TypeError): pass
        if len(bars)<20: return 'Minimal 20 candle OHLC valid untuk mencari zona.'
        ranges=[]
        for i,b in enumerate(bars):
            prev=bars[i-1]['close'] if i else b['close']
            ranges.append(max(b['high']-b['low'],abs(b['high']-prev),abs(b['low']-prev)))
        atr=sum(ranges[-14:])/14
        look=bars[-min(len(bars),160):]
        sw_high=[]; sw_low=[]
        for i in range(3,len(look)-3):
            b=look[i]
            if all(b['high']>=look[x]['high'] for x in range(i-3,i+4) if x!=i): sw_high.append(b['high'])
            if all(b['low']<=look[x]['low'] for x in range(i-3,i+4) if x!=i): sw_low.append(b['low'])
        price=look[-1]['close']; demand=max([p for p in sw_low if p<price],default=min(b['low'] for b in look[-30:]))
        supply=min([p for p in sw_high if p>price],default=max(b['high'] for b in look[-30:]))
        prev=look[-min(21,len(look))]['close']; slope='naik' if price>prev else 'turun' if price<prev else 'datar'
        return (f'ANALISIS OHLC (metode pivot 3 candle, bukan order flow): {len(bars)} candle; '
                f'Close terakhir {price:.5f}; tren 20 candle {slope}; ATR(14) {atr:.5f}; '
                f'Zona demand indikatif {demand-atr*.3:.5f}–{demand+atr*.3:.5f}; '
                f'zona supply indikatif {supply-atr*.3:.5f}–{supply+atr*.3:.5f}. '
                'Zona perlu divalidasi terhadap timeframe, likuiditas, berita dan struktur pasar.')
    except Exception as e: return 'CSV tidak dapat diproses: '+type(e).__name__

def extract_text(filename: str, content: bytes):
    ext=Path(filename).suffix.lower()
    if ext=='.csv': return read_csv_zones(content)
    if ext in ['.txt','.md']: return content.decode('utf-8',errors='replace')[:12000]
    if ext=='.pdf':
        try:
            import fitz
            with fitz.open(stream=content,filetype='pdf') as pdf:
                return '\n'.join(p.get_text() for p in list(pdf)[:8])[:12000] or 'PDF berbasis gambar; tidak ada teks terbaca.'
        except Exception: return 'PDF tidak berhasil diekstrak.'
    return ''

def basic_answer(question: str, artifact: str, astro_data: dict | None, news: list):
    low=question.lower()
    lines=[]
    if any(w in low for w in ['zone','zona','supply','demand','support','resistance']) and not artifact.startswith('ANALISIS OHLC'):
        lines.append('Untuk mencari zona supply/demand yang bisa dihitung, unggah CSV OHLC dengan kolom High, Low, Close. Tanpa data harga saya tidak bisa menetapkan level yang valid.')
    if any(w in low for w in ['buy','sell','entry','sinyal']):
        lines.append('Keputusan transaksi: TUNGGU KONFIRMASI. Evaluasi struktur harga dan reaksi pada zona, batasi risiko, serta hindari entry menjelang berita berdampak tinggi. Astrologi tidak terbukti dapat memprediksi harga secara konsisten.')
    if 'astro' in low or 'planet' in low:
        if astro_data: lines.append(f"Chart yang dipilih: {astro_data['date_local']} {astro_data['time_local']} {astro_data['timezone']}. Bias saat ini {astro_data['astro_bias_details'].get('headline', astro_data['astro_bias'])}; tetap cocokkan dengan harga dan news.")
        else: lines.append('Buka Astro Matrix dan tekan HITUNG CHART untuk menampilkan posisi planet yang dihitung Swiss Ephemeris.')
    if any(w in low for w in ['news','kalender','nfp','cpi','fomc']):
        if news:
            high=[e for e in news if e['impact'].lower()=='high']
            lines.append(f'Ada {len(news)} event pada tanggal pilihan, {len(high)} high impact. '+('; '.join(f"{e['time_local']} {e['country']} {e['title']}" for e in high[:4]) if high else 'Tidak ada event high impact dalam data yang berhasil diambil.'))
        else: lines.append('Belum ada data ekonomi terverifikasi untuk tanggal tersebut. Pastikan feed terhubung atau buka kalender sumber.')
    if any(w in low for w in ['vip','join','member','admin']): lines.append('Untuk informasi paket VIP, gunakan tombol WhatsApp resmi ZERO SYNDICATE pada halaman ini.')
    if artifact: lines.append('HASIL BERKAS:\n'+artifact[:3300])
    if not lines: lines.append('Saya bisa membantu membandingkan event ekonomi, menjelaskan chart astrologi, atau menghitung zona dari CSV OHLC. Pilih tanggal/jam lalu ajukan pertanyaan yang spesifik.')
    return '\n\n'.join(lines)

@app.post('/api/analyst')
async def analyst(request: Request, question: str=Form(''), instrument: str=Form('XAUUSD'), date: str=Form(''), clock: str=Form('13:00'), tz: str=Form('Asia/Jakarta'), lat:float=Form(-6.2088), lon:float=Form(106.8456), houses:str=Form('P'), file: UploadFile|None=File(None)):
    client_ip=request.client.host if request.client else 'unknown'
    now=time.time(); old=[t for t in _rate_guard.get(client_ip,[]) if now-t<60]
    if len(old)>=12: raise HTTPException(429, 'Terlalu banyak permintaan, coba lagi dalam satu menit')
    old.append(now); _rate_guard[client_ip]=old
    if len(_rate_guard)>3000: _rate_guard.clear()
    if len(question)>3000: raise HTTPException(400,'Pesan terlalu panjang')
    artifact=''; mime=''; image_data=''; filename=''
    if file is not None and file.filename:
        filename=Path(file.filename).name[:120]
        ext=Path(filename).suffix.lower()
        if ext not in ['.csv','.png','.jpg','.jpeg','.webp','.txt','.md','.pdf']:
            raise HTTPException(400,'Format file harus CSV, PNG/JPG/WEBP, TXT, atau PDF')
        binary=await file.read(6*1024*1024+1)
        if len(binary)>6*1024*1024: raise HTTPException(413,'File melebihi 6 MB')
        if ext in ['.png','.jpg','.jpeg','.webp']:
            image_data=base64.b64encode(binary).decode('ascii')
            mime='image/jpeg' if ext in ['.jpg','.jpeg'] else 'image/png' if ext=='.png' else 'image/webp'
            artifact=f'Gambar {filename} diterima. Pembacaan visual membutuhkan layanan model yang dikonfigurasi pada server; jangan membuat zona hanya dari nama berkas.'
        else: artifact=extract_text(filename,binary)
    astro_data=None; news=[]
    if date:
        try:
            astro_data=astro(date,clock,tz,lat,lon,houses)
        except Exception:
            astro_data=None
        # Penting: jangan download 2 feed (bisa 16 detik) untuk setiap
        # pertanyaan biasa. Pakai cache yang sudah tersedia; feed live
        # dipakai hanya saat diminta eksplisit.
        need_news=any(k in question.lower() for k in ('news','nfp','cpi','fomc','kalender','rilis','fundamental'))
        try:
            if need_news:
                await asyncio.to_thread(calendar_raw)
            with _cache_lock:
                cached_events=list(_cache['events'])
            zone=ZoneInfo(tz)
            target_day=datetime.strptime(date,'%Y-%m-%d').date()
            news=[{**ev,'time_local':datetime.fromisoformat(ev['at']).astimezone(zone).strftime('%H:%M')}
                  for ev in cached_events
                  if datetime.fromisoformat(ev['at']).astimezone(zone).date()==target_day][:40]
        except Exception:
            news=[]
    baseline=basic_answer(question, artifact, astro_data,news)
    gemini_key=os.getenv('GEMINI_API_KEY')
    api_key=os.getenv('CHAT_API_KEY') or os.getenv('OPENAI_API_KEY')
    api_url=os.getenv('CHAT_API_URL','https://api.openai.com/v1/chat/completions')
    model=os.getenv('CHAT_MODEL','gpt-4.1-mini')
    if not api_key and not gemini_key:
        if image_data: baseline += '\n\nAnalisis foto belum aktif: atur GEMINI_API_KEY atau CHAT_API_KEY pada server.'
        return {'reply':baseline, 'mode':'jawaban dasar','file':filename or None,'news_count':len(news)}
    system=('Anda adalah NARA dari ZERO SYNDICATE. Gaya bicaramu rapi, ringkas, dan terdengar seperti desk analis manusia. Jangan memakai kata AI atau sistem dalam jawaban. Jangan mengaku sebagai manusia. '
            'Jawab dalam Bahasa Indonesia, berbasis data. Jangan mengarang harga, news, sumber, atau win rate. '
            'Jangan menjanjikan akurasi tinggi atau hasil pasti. Astrologi tidak tervalidasi memprediksi pasar; '
            'jika ada tafsir BUY/SELL, sebut sebagai eksplorasi bukan sinyal. '
            'Jika diminta zone dari foto, baca level terlihat dan jelaskan ketidakpastian; jangan mengarang jika blur. '
            'Jelaskan risiko dan periksa berita besar. Hindari instruksi transaksi sebagai kepastian.')
    context=f'Instrumen: {instrument}. Tanggal: {date} {clock} {tz}.\nASTRO: {json.dumps(astro_data,ensure_ascii=False)[:6000]}\nNEWS: {json.dumps(news,ensure_ascii=False)[:7000]}\nDATA BERKAS: {artifact[:9000]}'
    user_content=[{'type':'text','text':(question or 'Tolong analisis data ini')+'\n\n'+context}]
    if image_data: user_content.append({'type':'image_url','image_url':{'url':f'data:{mime};base64,{image_data}'}})
    try:
        if gemini_key:
            model_id=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')
            if not re.fullmatch(r'[a-zA-Z0-9_.\-]+',model_id): raise ValueError('GEMINI_MODEL tidak valid')
            prompt=context+'\n\nPERTANYAAN PENGGUNA: '+(question or 'Tolong analisis data yang dilampirkan')
            parts=[{'text':prompt}]
            if image_data: parts.append({'inline_data':{'mime_type':mime,'data':image_data}})
            gemini_res=await asyncio.to_thread(
                requests.post,
                'https://generativelanguage.googleapis.com/v1beta/models/'+model_id+':generateContent',
                headers={'x-goog-api-key':gemini_key,'Content-Type':'application/json'},
                json={'system_instruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':parts}],
                      'generationConfig':{'temperature':0.2,'maxOutputTokens':1300}},timeout=35)
            if not gemini_res.ok:
                # Jangan kirim pesan mentah dari Google karena bisa berisi
                # metadata sensitif. Klasifikasikan berdasarkan kode HTTP.
                code=gemini_res.status_code
                issue={400:'Permintaan atau nama model ditolak. Periksa GEMINI_MODEL di Render.',
                       401:'Kunci layanan analis ditolak. Buat kunci baru dan simpan di Render.',
                       402:'Kredit layanan model tidak tersedia.',
                       403:'Akses model atau API key ditolak. Periksa izin dan kunci di Google AI Studio.',
                       404:'Model tidak ditemukan. Periksa nama GEMINI_MODEL di Render.',
                       429:'Kuota layanan model sedang habis. Coba lagi setelah kuota tersedia.',
                       500:'Layanan model sedang bermasalah.',
                       503:'Layanan model sedang sibuk. Coba lagi nanti.'}.get(code,'Permintaan ke penyedia model gagal.')
                return {'reply':baseline+'\n\nNARA: '+issue,
                        'mode':'perlu pengecekan', 'error_code':'GEMINI_HTTP_'+str(code),
                        'file':filename or None,'news_count':len(news)}

            candidates=gemini_res.json().get('candidates') or []
            answer='\n'.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if p.get('text')) if candidates else ''
            if not answer: raise ValueError('Model tidak mengembalikan teks yang dapat ditampilkan')
            return {'reply':answer,'mode':'Gemini terhubung','file':filename or None,'news_count':len(news)}
        res=await asyncio.to_thread(requests.post,api_url,
                    headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json'},
                    json={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user_content}],
                          'temperature':0.2,'max_tokens':900},timeout=35)
        res.raise_for_status(); answer=res.json()['choices'][0]['message']['content']
        return {'reply':answer,'mode':'analis otomatis terhubung','file':filename or None,'news_count':len(news)}
    except requests.Timeout:
        return {'reply':baseline+'\n\nNARA: Koneksi penyedia model terlalu lama. Coba lagi beberapa saat.',
                'mode':'waktu habis', 'error_code':'MODEL_TIMEOUT', 'file':filename or None,'news_count':len(news)}
    except requests.RequestException:
        return {'reply':baseline+'\n\nNARA: Penyedia model belum bisa dijangkau. Periksa status jaringan Render.',
                'mode':'perlu pengecekan', 'error_code':'MODEL_CONNECTION', 'file':filename or None,'news_count':len(news)}
    except Exception:
        return {'reply':baseline+'\n\nNARA: Jawaban lanjutan belum berhasil diproses. Coba ulang atau periksa konfigurasi model.',
                'mode':'perlu pengecekan', 'error_code':'MODEL_RESPONSE', 'file':filename or None,'news_count':len(news)}


# ZERO QUANT v3: optional licensed OANDA candles or upload CSV. No broker order API.
from quant_engine import fetch_oanda, parse_csv, analyze

@app.get('/api/xauusd/analyze')
def xau_auto(timeframe: str='M15'):
    if timeframe not in ('M15','H1','H4'): raise HTTPException(400,'Timeframe harus M15, H1 atau H4')
    try:
        bars=fetch_oanda(timeframe)
        coverage=calendar_raw()
        events=(coverage['events'] if coverage['events'] else None) if not coverage['errors'] else None
        if events:
            # Verify current-day coverage rather than mistaking a next-week-only feed for complete data.
            dates=[datetime.fromisoformat(e['at']).date() for e in events]
            today=datetime.now(timezone.utc).date()
            if today < min(dates)-timedelta(days=1) or today > max(dates)+timedelta(days=1): events=None
        # Astronomical observations are research-only context; never influence price setups.
        utc=datetime.now(timezone.utc)
        astro_snapshot=astro(utc.date().isoformat(),utc.strftime('%H:%M'),tz='UTC',lat=0,lon=0)
        result=analyze(bars,timeframe,source='OANDA REST (mid candles)',news=events,astro=astro_snapshot,live=True)
        result['data_attribution']='OANDA API; verify broker symbol, spread, and data usage rights.'
        return result
    except ValueError as exc: raise HTTPException(400,str(exc)[:160])
    except RuntimeError as exc: raise HTTPException(503,str(exc)[:200])
    except requests.RequestException: raise HTTPException(502,'Sumber OANDA tidak dapat dijangkau saat ini')

@app.post('/api/xauusd/csv')
async def xau_csv(timeframe: str=Form('M15'),file:UploadFile=File(...)):
    if timeframe not in ('M15','H1','H4'): raise HTTPException(400,'Timeframe tidak tersedia')
    if not file.filename.lower().endswith('.csv'):raise HTTPException(400,'Unggah file CSV')
    data=await file.read(3_000_001)
    try:
        bars=parse_csv(data)
        return analyze(bars,timeframe,source='User-provided CSV OHLC',news=None,astro=None,live=False)
    except ValueError as exc: raise HTTPException(400,str(exc)[:200])
