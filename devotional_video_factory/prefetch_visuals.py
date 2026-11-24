#!/usr/bin/env python3
import json, time, re, requests, os
from pathlib import Path
from PIL import Image

OUT=Path("visual_assets")
OUT.mkdir(exist_ok=True)
QUERIES={
"Ganesha":["Ganesha painting","Ganesha sculpture","Ganesha Bali","Ganesha Thailand"],
"Shiva":["Shiva painting","Shiva sculpture","Shiva lingam temple","Shiva Bali"],
"Vishnu":["Vishnu painting","Narayana painting","Vishnu sculpture","Venkateswara"],
"Krishna":["Krishna painting","Radha Krishna painting","Krishna sculpture","Krishna temple"],
"Rama":["Rama Sita painting","Rama painting","Ram Darbar","Rama temple"],
"Hanuman":["Hanuman painting","Hanuman sculpture","Anjaneya","Hanuman temple"],
"Durga":["Durga painting","Mahishasura Mardini","Durga sculpture","Durga temple"],
"Lakshmi":["Lakshmi painting","Gajalakshmi","Lakshmi sculpture","Lakshmi temple"]
}
HEADERS={"User-Agent":"AnantaBhaktiVideoFactory/1.0 (devotional video production; contact via GitHub powargaurish-coder)"}

def license_ok(meta):
    lic=(meta.get("LicenseShortName",{}).get("value","") or "").lower()
    if any(x in lic for x in ["noncommercial","no derivatives"," nc"," nd"]): return False
    return any(x in lic for x in ["public domain","cc0","cc by","creative commons"])

def get_json(params):
    for attempt in range(8):
        r=requests.get("https://commons.wikimedia.org/w/api.php",params=params,headers=HEADERS,timeout=45)
        if r.status_code==429:
            time.sleep(min(60,5*(attempt+1))); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError("Wikimedia API remained rate-limited")

def get_bytes(url):
    for attempt in range(10):
        r=requests.get(url,headers=HEADERS,timeout=60)
        if r.status_code==429:
            time.sleep(min(90,8*(attempt+1))); continue
        r.raise_for_status(); return r.content
    raise RuntimeError("Wikimedia image download remained rate-limited")

only=os.getenv("DEITY_ONLY","").strip()
items=[(k,v) for k,v in QUERIES.items() if not only or k.lower()==only.lower()]
for deity,queries in items:
    d=OUT/deity; d.mkdir(parents=True,exist_ok=True)
    seen=set(); candidates=[]
    for q in queries:
        params={
          "action":"query","format":"json","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":35,
          "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1400
        }
        data=get_json(params)
        for page in (data.get("query",{}).get("pages",{}) or {}).values():
            ii=(page.get("imageinfo") or [{}])[0]; meta=ii.get("extmetadata",{}) or {}
            url=ii.get("thumburl") or ii.get("url")
            title=page.get("title","")
            if not url or url in seen or not license_ok(meta): continue
            lower=title.lower()
            if any(x in lower for x in ["logo","map","diagram","text","icon","flag","chart"]): continue
            seen.add(url)
            candidates.append({
              "url":url,"title":title,
              "artist":(meta.get("Artist",{}).get("value","") or "")[:300],
              "license":(meta.get("LicenseShortName",{}).get("value","") or ""),
              "license_url":(meta.get("LicenseUrl",{}).get("value","") or ""),
              "description_url":ii.get("descriptionurl","")
            })
        if len(candidates)>=18: break
        time.sleep(2)

    used=[]
    for item in candidates:
        if len(used)>=14: break
        idx=len(used)+1
        p=d/f"{idx:02d}.jpg"
        try:
            p.write_bytes(get_bytes(item["url"]))
            im=Image.open(p).convert("RGB")
            if im.width<600 or im.height<450:
                p.unlink(missing_ok=True); continue
            im.thumbnail((2000,2000),Image.Resampling.LANCZOS)
            im.save(p,quality=90)
            used.append(item)
            time.sleep(2.5)
        except Exception as e:
            p.unlink(missing_ok=True)
            print("skip",deity,item["title"],repr(e),flush=True)
            time.sleep(5)

    if len(used)<9:
        raise RuntimeError(f"{deity}: only {len(used)} usable images")
    (d/"ATTRIBUTION.json").write_text(json.dumps(used,ensure_ascii=False,indent=2),encoding="utf-8")
    print(deity,"cached",len(used),flush=True)
    time.sleep(5)
