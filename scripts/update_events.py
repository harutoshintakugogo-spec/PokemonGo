#!/usr/bin/env python3
"""Pokémon GO公式ニュースからイベント関連記事を取得してdata/events.jsonへ統合する。"""
from __future__ import annotations
import hashlib, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dateparser.search import search_dates

ROOT=Path(__file__).resolve().parents[1]
EVENTS_PATH=ROOT/'data/events.json'; STATUS_PATH=ROOT/'data/status.json'
NEWS_URL=os.getenv('POGO_NEWS_URL','https://pokemongo.com/news')
MAX_ARTICLES=int(os.getenv('MAX_ARTICLES','40'))
HEADERS={'User-Agent':'GO-EVENT-LOG/1.0 (+non-commercial fan site; GitHub Actions)','Accept-Language':'ja,en-US;q=0.8,en;q=0.7'}
KEYWORDS=('event','community day','raid day','research day','spotlight','go fest','tour','celebration','party','festival','week','weekend','ultra unlock','max battle','raid','イベント','コミュニティ・デイ','レイド','フェス','セレブレーション','パーティー','リサーチ')
EXCLUDE=('terms of service','privacy policy','support','code redemption')

def get(url:str)->requests.Response:
    r=requests.get(url,headers=HEADERS,timeout=35); r.raise_for_status(); return r

def clean(text:str)->str: return re.sub(r'\s+',' ',text or '').strip()
def slug_id(url:str)->str:
    slug=urlparse(url).path.rstrip('/').split('/')[-1] or hashlib.sha1(url.encode()).hexdigest()[:14]
    return re.sub(r'[^a-zA-Z0-9_-]+','-',slug).strip('-').lower()
def meta(soup:BeautifulSoup,*names:str)->str|None:
    for name in names:
        tag=soup.find('meta',attrs={'property':name}) or soup.find('meta',attrs={'name':name})
        if tag and tag.get('content'): return clean(tag['content'])
    return None

def discover()->list[tuple[str,str]]:
    soup=BeautifulSoup(get(NEWS_URL).text,'html.parser'); found={}
    for a in soup.find_all('a',href=True):
        href=urljoin(NEWS_URL,a['href']).split('#')[0]
        path=urlparse(href).path.rstrip('/')
        if '/news/' not in path or path.endswith('/news'): continue
        title=clean(a.get_text(' ',strip=True))
        if len(title)>=8: found[href]=max(found.get(href,''),title,key=len)
    return list(found.items())[:MAX_ARTICLES]

def is_event(title:str,desc:str,body:str)->bool:
    text=f'{title} {desc} {body[:1400]}'.lower()
    return any(k in text for k in KEYWORDS) and not any(k in text for k in EXCLUDE)

def published_at(soup:BeautifulSoup)->str:
    raw=meta(soup,'article:published_time','date','datePublished')
    if not raw:
        time=soup.find('time'); raw=time.get('datetime') if time else None
    if raw:
        try:
            dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if not dt.tzinfo: dt=dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError: pass
    return datetime.now(timezone.utc).isoformat()

def infer_period(text:str,announced:str):
    # 自動抽出は誤判定を避けるため、記事冒頭に現れる未来日を最大2件だけ利用する。
    base=datetime.fromisoformat(announced.replace('Z','+00:00'))
    matches=search_dates(text[:5000],languages=['en','ja'],settings={'RELATIVE_BASE':base.replace(tzinfo=None),'PREFER_DATES_FROM':'future','RETURN_AS_TIMEZONE_AWARE':False}) or []
    dates=[]
    for phrase,dt in matches:
        if dt.year < base.year-1 or dt.year > base.year+2: continue
        if any(abs((dt-x).total_seconds())<3600 for x in dates): continue
        dates.append(dt)
        if len(dates)==2: break
    if not dates: return None,None
    start=dates[0].replace(tzinfo=timezone.utc).isoformat()
    end=(dates[1] if len(dates)>1 else dates[0]).replace(tzinfo=timezone.utc).isoformat()
    return start,end

def category_icon(title:str):
    t=title.lower()
    pairs=[(('community day','コミュニティ'),('コミュニティ・デイ','🗓️')),(('raid','レイド'),('レイド','⚔️')),(('go fest','fest'),('GO Fest','🌐')),(('research','リサーチ'),('リサーチ','🔎')),(('celebration','anniversary','周年'),('記念イベント','🎉'))]
    for keys,result in pairs:
        if any(k in t for k in keys): return result
    return '公式イベント','📣'

def parse_article(url:str,fallback_title:str)->dict|None:
    soup=BeautifulSoup(get(url).text,'html.parser')
    title=meta(soup,'og:title','twitter:title') or clean(soup.find('h1').get_text(' ',strip=True) if soup.find('h1') else fallback_title)
    desc=meta(soup,'og:description','description') or ''
    main=soup.find('main') or soup.find('article') or soup.body
    body=clean(main.get_text(' ',strip=True) if main else '')
    if not is_event(title,desc,body): return None
    announced=published_at(soup); start,end=infer_period(body,announced); category,icon=category_icon(title)
    summary=desc[:320] or body[:320]
    return {'id':slug_id(url),'announcedAt':announced,'title':title,'category':category,'icon':icon,'start':start,'end':end,'summary':summary,'highlights':['公式ニュースから自動取得'],'url':url,'source':'official','autoImported':True}

def main():
    existing=json.loads(EVENTS_PATH.read_text(encoding='utf-8')) if EVENTS_PATH.exists() else []
    by_url={x.get('url'):x for x in existing}; fetched=added=0; errors=[]
    for url,title in discover():
        try:
            item=parse_article(url,title); fetched+=1
            if not item: continue
            if url in by_url:
                old=by_url[url]
                # 手動修正済みの開催日時や日本語要約は上書きしない。
                for key in ('title','announcedAt'):
                    if item.get(key): old[key]=item[key]
                old['lastSeenAt']=datetime.now(timezone.utc).isoformat()
            else:
                item['lastSeenAt']=datetime.now(timezone.utc).isoformat(); existing.append(item); by_url[url]=item; added+=1
        except Exception as exc: errors.append(f'{url}: {exc}')
    existing.sort(key=lambda x:x.get('announcedAt') or '',reverse=True)
    if fetched==0: raise RuntimeError('公式ニュースの記事を1件も取得できなかったため、既存データを変更しません。')
    EVENTS_PATH.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    now=datetime.now(timezone.utc).isoformat()
    STATUS_PATH.write_text(json.dumps({'lastUpdated':now,'lastRun':now,'fetched':fetched,'added':added,'total':len(existing),'errors':errors[:5],'message':f'{fetched}件確認し、{added}件追加'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'checked={fetched} added={added} total={len(existing)} errors={len(errors)}')
if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr); sys.exit(1)
