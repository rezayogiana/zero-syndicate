/** ZERO SYNDICATE V4.0 — Signal Desk
 * Research dashboard only. Never places orders and never fabricates market data.
 * Astro BUY/SELL: transparent symbolic heuristic based on verified ephemerides.
 */
(()=>{'use strict';
const el=id=>document.getElementById(id);
const MAX_SNAPSHOTS=25;
let astro=window.ZERO_LATEST_ASTRO||null;
let quant=window.ZERO_LATEST_QUANT||null;
let news=null;
let modelHealth=null;
let liveTimer=null;
let nextLiveMinute='';
const now=()=>new Date().toISOString();
const humanInput=d=>d?`${d.date_local} ${d.time_local} ${d.timezone}`:'—';
const symDir=d=>d?.astro_bias_details?.direction||d?.astro_bias||null;
function text(id,value){const e=el(id);if(e)e.textContent=value}
function setMsg(m){text('cmdMessage',m)}
function readHistory(){try{const t=JSON.parse(localStorage.getItem('ZERO_V40_SIGNAL_HISTORY')||'[]');return Array.isArray(t)?t.slice(0,MAX_SNAPSHOTS):[]}catch{return []}}
function writeHistory(items){try{localStorage.setItem('ZERO_V40_SIGNAL_HISTORY',JSON.stringify(items.slice(0,MAX_SNAPSHOTS)));return true}catch{setMsg('Penyimpanan browser tidak tersedia. Ekspor/copy masih bisa dicoba.');return false}}
function makeSnapshot(){const d=astro?.data;if(!d)return null;
return {saved_at:now(),date:d.date_local,time:d.time_local,tz:d.timezone,astro_direction:symDir(d),symbolic_score:d.astro_bias_details?.score??null,aspect_drivers:(d.astro_bias_details?.drivers||[]).slice(0,6),astro_sample:!!astro.demo,market_decision:quant?.decision||'WAIT',market_source:quant?.source||'NO VERIFIED PRICE',market_live:!!quant?.is_live,news_status:news?.live?'FEED_AVAILABLE':'UNVERIFIED',disclaimer:'NOT FINANCIAL ADVICE; symbolic astro research, not a market prediction or order.'}}
function renderHistory(){const list=readHistory(),root=el('cmdHistory');root.replaceChildren();text('cmdCount',`${list.length} snapshot disimpan lokal di browser`);
if(!list.length){const s=document.createElement('span');s.className='cmd-muted';s.textContent='Belum ada snapshot.';root.append(s);return}
list.slice(0,6).forEach(s=>{const row=document.createElement('div');row.className='cmd-history-row';const b=document.createElement('b');b.textContent=s.astro_direction||'—';b.className=s.astro_direction==='SELL'?'negative':'positive';const t=document.createElement('span');t.textContent=`${s.date} ${s.time} • ${s.tz}`;const sub=document.createElement('small');sub.textContent=(s.astro_sample?'SNAPSHOT CONTOH':'EPHEMERIS')+' · PRICE '+(s.market_live?s.market_decision:'UNVERIFIED');row.append(b,t,sub);root.append(row)})}
function paintAstro(){const d=astro?.data;const direction=symDir(d);const heading=el('cmdAstroDirection');const head=(d?.astro_bias_details?.headline)|| (direction?`HIGH PROBABILITY ${direction}`:'WAIT'); heading.textContent=head;heading.classList.toggle('negative',direction==='SELL');heading.classList.toggle('positive',direction==='BUY');text('cmdAstroStrength', d?`${d.astro_bias_details?.confidence_label||'WATCH'} • skor ${Number(d.astro_bias_details?.score||0)>=0?'+':''}${d.astro_bias_details?.score??'—'}`:'MENUNGGU PERHITUNGAN CHART');text('cmdInput',humanInput(d));
const reasons=el('cmdAstroReasons');reasons.replaceChildren();const drivers=d?.astro_bias_details?.drivers||[];
(drivers.length?drivers:['Tidak ada aspek terverifikasi untuk konfigurasi yang dipilih.']).slice(0,5).forEach(reason=>{const li=document.createElement('li');li.textContent=reason;reasons.append(li)});
text('cmdUpdated',d?`${astro.demo?'PREVIEW SNAPSHOT':'LIVE CHART'} • ${humanInput(d)}`:'MENUNGGU DATA ASTRO');}
function paintMarket(){let val='WAIT / NO PRICE DATA',detail='Belum ada sumber candle XAUUSD yang telah diverifikasi.';
if(quant){if(quant.is_live&&quant.fresh){val=quant.decision||'WAIT';detail=`${quant.source||'PRICE API'} • candle ${quant.last_candle_utc||'—'} • gate ${quant.news_filter?.state||'UNVERIFIED'}`}else{val='WAIT / HISTORICAL OR STALE';detail='Data candle yang tersedia bukan harga live segar. Tidak digunakan untuk keputusan transaksi.'}}
text('cmdMarket',val);text('cmdMarketDesc',detail);
const elm=el('cmdMarket');elm.classList.toggle('positive',val==='BUY_SETUP');elm.classList.toggle('negative',val==='SELL_SETUP');}
function paintNews(){let val='WAIT / FEED NOT VERIFIED',detail='Berita ekonomi belum berhasil diverifikasi dari penyedia.';
if(news?.live){const hi=(news.events||[]).filter(e=>String(e.impact).toLowerCase()==='high');val=`FEED AVAILABLE / ${hi.length} HIGH IMPACT`;detail=hi.length?'Event yang diterima: '+hi.slice(0,3).map(e=>`${e.time_local||'—'} ${e.title||'Event'}`).join(' • '):'Dalam cakupan feed yang diterima, tidak ada high-impact pada tanggal pilihan.'}
text('cmdNews',val);text('cmdNewsDesc',detail)}
function paintSystem(){text('cmdDesk',modelHealth?.ok?'DESK ONLINE':'DESK OFFLINE')}
function repaint(){paintAstro();paintMarket();paintNews();paintSystem()}
function syncClock(){if(!el('cmdLiveClock')?.checked)return;const fmt=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});const parts=Object.fromEntries(fmt.formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));const key=`${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;if(key===nextLiveMinute)return;nextLiveMinute=key;
el('astroDate').value=`${parts.year}-${parts.month}-${parts.day}`;el('astroTime').value=`${parts.hour}:${parts.minute}`;el('astroTZ').value='Asia/Jakarta';el('astroTime').dispatchEvent(new Event('change',{bubbles:true}));text('cmdMode','AUTO SYNC WIB / SETIAP MENIT');}
function reportText(){const s=makeSnapshot();if(!s)return 'Astro belum terhitung. Hitung chart terlebih dahulu.';return `ZERO SYNDICATE V4.0 — XAUUSD ASTRO NOTE\n${s.date} ${s.time} ${s.tz}\nASTRO: ${s.astro_direction}\nKonfluensi: ${s.symbolic_score}\nAlasan:\n${s.aspect_drivers.map((a,i)=>`${i+1}. ${a}`).join('\n')}\nMarket: ${s.market_live?s.market_decision:'TIDAK ADA DATA HARGA LIVE'}\nNews: ${s.news_status}\n${s.disclaimer}`}
function toCSV(rows){const keys=['saved_at','date','time','tz','astro_direction','symbolic_score','astro_sample','market_decision','market_source','market_live','news_status','aspect_drivers','disclaimer'];const esc=v=>'"'+String(v??'').replace(/"/g,'""').replace(/\r?\n/g,' | ')+'"';return '\uFEFF'+keys.join(',')+'\r\n'+rows.map(r=>keys.map(k=>esc(Array.isArray(r[k])?r[k].join(' | '):r[k])).join(',')).join('\r\n')}
window.addEventListener('zero:astro',e=>{astro=e.detail?.data?e.detail:null;repaint()});
window.addEventListener('zero:quant',e=>{quant=e.detail||null;paintMarket()});
window.addEventListener('zero:news',e=>{news=e.detail||null;paintNews()});
window.addEventListener('zero:health',e=>{modelHealth=e.detail||null;paintSystem()});
el('cmdRefresh')?.addEventListener('click',()=>{el('calcAstro')?.click();el('reloadNews')?.click();if(el('quantTF'))el('quantScan')?.click();setMsg('Pemindaian diminta. Hasil menunggu API terkait.');});
el('cmdLiveClock')?.addEventListener('change',()=>{const active=el('cmdLiveClock').checked;nextLiveMinute='';if(active){syncClock();liveTimer=window.setInterval(syncClock,10000);setMsg('SYNC WIB aktif hanya selama halaman dibuka.')}else{clearInterval(liveTimer);liveTimer=null;text('cmdMode','UPDATE ON INPUT');setMsg('SYNC WIB dimatikan. Tanggal/jam dapat dipilih manual.')}});
el('cmdCopy')?.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(reportText());setMsg('Laporan Astro disalin.')}catch{setMsg('Browser membatasi clipboard. Gunakan HTTPS atau ekspor CSV.')}});
el('cmdSave')?.addEventListener('click',()=>{const s=makeSnapshot();if(!s){setMsg('Hitung chart Astro dulu sebelum menyimpan.');return}const rows=readHistory();rows.unshift(s);if(writeHistory(rows)){renderHistory();setMsg('Snapshot disimpan di perangkat ini.')}});
el('cmdExport')?.addEventListener('click',()=>{const rows=readHistory();if(!rows.length){setMsg('Belum ada riwayat. Klik SIMPAN KE RIWAYAT dahulu.');return}const blob=new Blob([toCSV(rows)],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ZERO_SYNDICATE_V40_signal_history.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);setMsg('CSV riwayat dibuat. Semua entri adalah riset simbolik.')});
repaint();renderHistory();
})();
