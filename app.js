let announcements = [];
const state = { filter: 'all', query: '', sort: 'announced-desc', favorites: new Set(JSON.parse(localStorage.getItem('goEventFavorites') || '[]')) };
const timeline = document.getElementById('timeline');
const emptyState = document.getElementById('emptyState');

function statusOf(item) {
  if (!item.start || !item.end) return 'announced';
  const now = new Date();
  if (now < new Date(item.start)) return 'upcoming';
  if (now > new Date(item.end)) return 'past';
  return 'active';
}
function statusLabel(status) { return { active:'開催中', upcoming:'開催予定', past:'終了', announced:'日程は公式で確認' }[status]; }
function formatDateTime(value) { return value ? new Intl.DateTimeFormat('ja-JP',{month:'numeric',day:'numeric',weekday:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '公式ページで確認'; }
function formatAnnounced(value) { return value ? new Intl.DateTimeFormat('ja-JP',{year:'numeric',month:'long',day:'numeric'}).format(new Date(value)) : '発表日不明'; }
function monthKey(value) { return value ? new Intl.DateTimeFormat('ja-JP',{year:'numeric',month:'long'}).format(new Date(value)) : '発表日不明'; }
function countdown(item,status) {
  if (status === 'announced') return '開催日時は公式発表を確認';
  if (status === 'past') return '終了済み';
  const target = new Date(status === 'active' ? item.end : item.start).getTime();
  const diff = Math.max(0,target-Date.now());
  const days = Math.floor(diff/86400000), hours = Math.floor((diff%86400000)/3600000);
  return `${status === 'active' ? '終了' : '開始'}まで ${days}日 ${hours}時間`;
}
function saveFavorites(){ localStorage.setItem('goEventFavorites',JSON.stringify([...state.favorites])); }
function escapeHtml(value=''){ return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function filteredItems(){
  const q=state.query.trim().toLowerCase();
  return announcements.filter(item=>{
    const status=statusOf(item);
    const matches=state.filter==='all'||status===state.filter||(state.filter==='favorite'&&state.favorites.has(item.id));
    const text=[item.title,item.category,item.summary,...(item.highlights||[])].join(' ').toLowerCase();
    return matches&&(!q||text.includes(q));
  }).sort((a,b)=>{
    if(state.sort==='event-asc') return new Date(a.start||'9999-12-31')-new Date(b.start||'9999-12-31');
    if(state.sort==='event-desc') return new Date(b.start||0)-new Date(a.start||0);
    return new Date(b.announcedAt||0)-new Date(a.announcedAt||0);
  });
}
function render(){
  const items=filteredItems(); let previousMonth='';
  timeline.innerHTML=items.map(item=>{
    const status=statusOf(item), basis=state.sort==='announced-desc'?item.announcedAt:item.start;
    const month=monthKey(basis), heading=month!==previousMonth?`<h3 class="month-heading">${escapeHtml(month)}</h3>`:''; previousMonth=month;
    const saved=state.favorites.has(item.id), period=item.start&&item.end?`${formatDateTime(item.start)} 〜 ${formatDateTime(item.end)}`:'開催日時は公式ページで確認してください';
    return `${heading}<article class="timeline-item"><div class="timeline-marker"><span>${escapeHtml(item.icon||'📣')}</span></div><div class="timeline-card">
      <div class="meta-row"><span class="announcement-date">公式発表｜${escapeHtml(formatAnnounced(item.announcedAt))}${item.autoImported?'・自動取得':''}</span><span class="status status-${status}">${statusLabel(status)}</span></div>
      <div class="title-row"><div><p class="category">${escapeHtml(item.category||'公式ニュース')}</p><h3>${escapeHtml(item.title)}</h3></div><button class="favorite ${saved?'saved':''}" data-id="${escapeHtml(item.id)}" aria-label="保存">★</button></div>
      <div class="event-period"><span>開催期間</span><strong>${escapeHtml(period)}</strong></div>
      <p class="summary">${escapeHtml(item.summary||'公式発表の詳細をご確認ください。')}</p>
      <ul class="highlight-list">${(item.highlights||[]).map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>
      <div class="card-footer"><span class="countdown">${escapeHtml(countdown(item,status))}</span><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">公式発表を見る ↗</a></div>
    </div></article>`;
  }).join('');
  emptyState.hidden=items.length>0;
  document.getElementById('resultCount').textContent=`${items.length}件の公式発表を表示`;
  const statuses=announcements.map(statusOf);
  document.getElementById('announcementCount').textContent=announcements.length;
  document.getElementById('activeCount').textContent=statuses.filter(x=>x==='active').length;
  document.getElementById('upcomingCount').textContent=statuses.filter(x=>x==='upcoming').length;
  document.getElementById('favoriteCount').textContent=state.favorites.size;
  document.querySelectorAll('.favorite').forEach(btn=>btn.addEventListener('click',()=>{state.favorites.has(btn.dataset.id)?state.favorites.delete(btn.dataset.id):state.favorites.add(btn.dataset.id);saveFavorites();render();}));
}
async function loadData(){
  try{
    const [eventsResponse,statusResponse]=await Promise.all([fetch(`data/events.json?v=${Date.now()}`),fetch(`data/status.json?v=${Date.now()}`)]);
    if(!eventsResponse.ok) throw new Error(`events.json: ${eventsResponse.status}`);
    announcements=await eventsResponse.json();
    if(statusResponse.ok){ const s=await statusResponse.json(); document.getElementById('syncLabel').textContent=s.lastUpdated?`最終自動更新：${new Intl.DateTimeFormat('ja-JP',{dateStyle:'medium',timeStyle:'short'}).format(new Date(s.lastUpdated))}`:'自動取得はまだ実行されていません'; }
  }catch(error){
    console.error(error); document.getElementById('syncLabel').textContent='データの読込に失敗しました。Webサーバー経由で開いてください。';
  }
  render();
}
document.getElementById('todayLabel').textContent=`${new Intl.DateTimeFormat('ja-JP',{year:'numeric',month:'long',day:'numeric'}).format(new Date())}現在。`;
document.getElementById('searchInput').addEventListener('input',e=>{state.query=e.target.value;render();});
document.getElementById('sortSelect').addEventListener('change',e=>{state.sort=e.target.value;render();});
document.getElementById('filters').addEventListener('click',e=>{const btn=e.target.closest('[data-filter]');if(!btn)return;state.filter=btn.dataset.filter;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===btn));render();});
loadData(); setInterval(render,60000);
