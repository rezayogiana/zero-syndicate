"""ZERO QUANT ENGINE — price research; never place orders.
   Astro is contextual metadata ONLY and is never added to a trading score.
"""
from __future__ import annotations
import csv, io, math, os, threading, time
from datetime import datetime, timezone
from typing import Any
import requests

OANDA_ALLOWED={'https://api-fxpractice.oanda.com','https://api-fxtrade.oanda.com'}
GRANULARITY={'M15':900,'H1':3600,'H4':14400}
_price_cache={}
_price_lock=threading.RLock()


def _as_time(v: Any):
    if not v: return None
    try:
        dt=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (ValueError, TypeError): return None


def parse_csv(data: bytes):
    if len(data)>3_000_000: raise ValueError('CSV melebihi 3 MB')
    raw=data.decode('utf-8-sig',errors='replace')
    sample=raw[:1000]
    try: dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
    except csv.Error: dialect=csv.excel
    table=csv.DictReader(io.StringIO(raw),dialect=dialect)
    if not table.fieldnames: raise ValueError('CSV kosong')
    names={str(k).strip().lower():k for k in table.fieldnames if k}
    if any(n not in names for n in ('open','high','low','close')): raise ValueError('Harus ada kolom Open, High, Low, Close')
    tcol=next((names[n] for n in ['timestamp','time','date','datetime'] if n in names),None)
    candles=[]
    for r in table:
        try:
            c={n:float(r[names[n]]) for n in ('open','high','low','close')}
            if not all(math.isfinite(v) and 0 < v < 1_000_000 for v in c.values()): continue
            if not c['low']<=min(c['open'],c['close'])<=max(c['open'],c['close'])<=c['high']: continue
            c['time'] = (_as_time(r.get(tcol)).isoformat() if tcol and _as_time(r.get(tcol)) else None)
            candles.append(c)
        except (TypeError,ValueError,KeyError): continue
        if len(candles)>8000: raise ValueError('Maksimum 8.000 candle per berkas')
    if len(candles)<100: raise ValueError('Minimal 100 candle valid diperlukan')
    return candles


def fetch_oanda(granularity='M15',count=250):
    token=os.getenv('OANDA_API_TOKEN','').strip()
    if not token: raise RuntimeError('OANDA_API_TOKEN belum diisi. Harga live tidak tersedia.')
    base=os.getenv('OANDA_API_BASE','https://api-fxpractice.oanda.com').rstrip('/')
    if base not in OANDA_ALLOWED: raise RuntimeError('OANDA_API_BASE tidak diizinkan')
    if granularity not in GRANULARITY: raise ValueError('Timeframe tidak didukung')
    with _price_lock:
        cached=_price_cache.get((base,granularity))
        if cached and time.time()-cached[0]<75: return list(cached[1])
    response=requests.get(f'{base}/v3/instruments/XAU_USD/candles',headers={'Authorization':f'Bearer {token}'},params={'granularity':granularity,'count':min(500,max(110,count)),'price':'M'},timeout=13)
    if response.status_code in (401,403,404): raise RuntimeError('Token, akun, atau akses instrumen XAU_USD tidak tersedia pada OANDA.')
    response.raise_for_status()
    payload=response.json(); result=[]
    for bar in payload.get('candles',[]):
        if not bar.get('complete') or not isinstance(bar.get('mid'),dict):continue
        try:
            p=bar['mid']; c={k:float(p[k][0] if isinstance(p[k],list) else p[k]) for k in ('o','h','l','c')}
            candle={'open':c['o'],'high':c['h'],'low':c['l'],'close':c['c'],'time':_as_time(bar.get('time')).isoformat()}
            if 0 < candle['low']<=min(candle['open'],candle['close'])<=max(candle['open'],candle['close'])<=candle['high']:
                result.append(candle)
        except (ValueError,TypeError,KeyError,AttributeError):continue
    if len(result)<100: raise RuntimeError('Data candle lengkap XAUUSD tidak mencukupi')
    with _price_lock: _price_cache[(base,granularity)]=(time.time(),list(result))
    return result


def ema(values,period):
    out=values[0]; k=2/(period+1)
    for v in values[1:]: out=(v*k)+(out*(1-k))
    return out


def atr14(bars):
    tr=[]
    for i in range(1,len(bars)):
        bar=bars[i]; prev=bars[i-1]['close']
        tr.append(max(bar['high']-bar['low'],abs(bar['high']-prev),abs(bar['low']-prev)))
    return sum(tr[-14:])/14


def rsi14(closes):
    changes=[closes[i]-closes[i-1] for i in range(-14,0)]
    gain=sum(max(0,x) for x in changes)/14
    loss=sum(max(0,-x) for x in changes)/14
    return 100 if loss==0 else 100-100/(1+gain/loss)


def price_features(bars):
    if len(bars)<100: raise ValueError('Butuh minimal 100 candle')
    closes=[b['close'] for b in bars]
    last=closes[-1]; atr=atr14(bars)
    if not atr>0: raise ValueError('ATR nol; data harga tidak layak')
    e20=ema(closes[-70:],20);e50=ema(closes[-150:],50)
    rsi=rsi14(closes)
    prev_hi=max(b['high'] for b in bars[-21:-1]);prev_lo=min(b['low'] for b in bars[-21:-1])
    # Kinematic analogy: derivatives of *observed prices*, not physical forces.
    velocity=(closes[-1]-closes[-5])/4/atr
    prev_velocity=(closes[-5]-closes[-9])/4/atr
    acceleration=(velocity-prev_velocity)/4
    buy=last>e20>e50 and 53<=rsi<=72 and last>prev_hi+0.05*atr and velocity>0
    sell=last<e20<e50 and 28<=rsi<=47 and last<prev_lo-0.05*atr and velocity<0
    side='BUY_WATCH' if buy else 'SELL_WATCH' if sell else 'HOLD'
    return {'side':side,'close':last,'ema20':e20,'ema50':e50,'rsi14':rsi,'atr14':atr,
            'breakout_upper':prev_hi,'breakout_lower':prev_lo,'velocity_atr_per_candle':velocity,
            'acceleration_atr_per_candle2':acceleration,'trend':'UP' if e20>e50 else 'DOWN' if e20<e50 else 'FLAT'}


def news_check(events,now):
    if events is None: return {'state':'UNVERIFIED','reason':'Kalender ekonomi tidak tersedia; tidak ada izin konfirmasi entry.'}
    for event in events:
        if str(event.get('impact','')).lower()!='high':continue
        if str(event.get('country','')).upper() not in ('USD','US','UNITED STATES'):continue
        dt=_as_time(event.get('at'))
        if dt and abs((dt-now).total_seconds())<=45*60:
            return {'state':'BLOCKED','reason':f"Dekat event high impact USD: {str(event.get('title',''))[:90]}"}
    return {'state':'CLEAR','reason':'Tidak terdeteksi event high impact USD ±45 menit dalam cakupan feed.'}


def analyze(bars, timeframe='M15',source='CSV',news=None,astro=None, live=False):
    if timeframe not in GRANULARITY:raise ValueError('Timeframe tidak tersedia')
    feat=price_features(bars)
    lasttime=_as_time(bars[-1].get('time'))
    now=datetime.now(timezone.utc)
    age=round((now-lasttime).total_seconds()) if lasttime else None
    fresh=(age is not None and -60<=age<=2*GRANULARITY[timeframe]) if live else False
    gate=news_check(news,now) if live else {'state':'HISTORICAL','reason':'CSV/historical: bukan harga live.'}
    state='WAIT'
    reasons=[]
    if not live: reasons.append('Mode CSV/historis; tidak menghasilkan sinyal entry live.')
    elif not fresh: reasons.append('Harga tidak cukup segar atau timestamp tidak valid.')
    elif gate['state']!='CLEAR': reasons.append(gate['reason'])
    elif feat['side']!='HOLD': state=feat['side'].replace('_WATCH','_SETUP')
    if feat['side']=='HOLD': reasons.append('Belum ada konfluensi EMA + RSI + breakout.')
    else: reasons.append(f"Konfirmasi harga berbasis tren {feat['trend']}, RSI dan breakout; ini setup indikatif, bukan probabilitas kemenangan.")
    if gate['state']=='BLOCKED': reasons.append('Hindari entry dekat rilis data USD.')
    if gate['state']=='UNVERIFIED': reasons.append('Kalender tidak terverifikasi: tunggu verifikasi manual sebelum trading.')
    risk=None
    if feat['side']!='HOLD':
        direction=1 if feat['side']=='BUY_WATCH' else -1
        entry=feat['close'];stop=entry-direction*1.5*feat['atr14'];target=entry+direction*3.0*feat['atr14']
        risk={'entry_indicative':round(entry,3),'stop_loss_reference':round(stop,3),'take_profit_reference':round(target,3),'rr_reference':'1:2','note':'Harga referensi dari close candle, bukan harga bid/ask eksekusi; spread/slippage/komisi belum termasuk.'}
    astro_info=None
    if astro:
        astro_info={'date':astro.get('date_local'),'planets_count':len(astro.get('planets',[])),'aspects_count':len(astro.get('aspects',[])),
                    'bias_research_only':astro.get('astro_bias'),'predictive_weight':0,
                    'note':'Faktor astrologi diamati terpisah; tidak memengaruhi klasifikasi harga sebelum ada validasi out-of-sample.'}
    return {'symbol':'XAUUSD','timeframe':timeframe,'source':source,'is_live':live,'last_candle_utc':lasttime.isoformat() if lasttime else None,
            'age_seconds':age,'fresh':fresh,'news_filter':gate,'market_setup':feat['side'],'decision':state,
            'indicators':{k:round(v,5) if isinstance(v,float) else v for k,v in feat.items() if k!='side'},
            'risk_plan':risk,'astro_research':astro_info,'reasons':reasons,
            'chart_data':[{'time':b.get('time'),'close':round(b['close'],5)} for b in bars[-72:]],
            'disclaimer':'Analisis edukasi/paper-trading. Bukan instruksi broker, tidak ada eksekusi order otomatis, tanpa klaim win rate.'}
