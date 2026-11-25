#!/usr/bin/env python3
import os, json, time, requests, random, hashlib, shutil, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
sys.path.insert(0,str(HERE))
import render_group as rg
BUILD=REPO/"build_audio"
OUTROOT=REPO/"rendered_deity"
VIS=REPO/"visual_assets"
DEITY=os.environ["DEITY"]
SKIP_IDS=set(x for x in os.getenv("SKIP_IDS","").split(",") if x)

QUERIES=rg.QUERIES
HEADERS={"User-Agent":"AnantaBhaktiDeityRenderer/1.0 (GitHub powargaurish-coder)"}

def license_ok(meta):
    lic=(meta.get("LicenseShortName",{}).get("value","") or "").lower()
    if any(x in lic for x in ["noncommercial","no derivatives"]): return False
    return any(x in lic for x in ["public domain","cc0","cc by","creative commons"])

def get_json(params):
    for attempt in range(10):
        r=requests.get("https://commons.wikimedia.org/w/api.php",params=params,headers=HEADERS,timeout=45)
        if r.status_code==429:
            time.sleep(min(75,6*(attempt+1))); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError("Wikimedia API remained rate limited")

def get_bytes(url):
    for attempt in range(10):
        r=requests.get(url,headers=HEADERS,timeout=60)
        if r.status_code==429:
            time.sleep(min(90,8*(attempt+1))); continue
        r.raise_for_status(); return r.content
    raise RuntimeError("Wikimedia image download remained rate limited")

def cache_deity(deity):
    d=VIS/deity; d.mkdir(parents=True,exist_ok=True)
    existing=sorted(d.glob("*.jpg"))
    meta=d/"ATTRIBUTION.json"
    if len(existing)>=9 and meta.exists():
        return
    seen=set(); candidates=[]
    for q in QUERIES[deity]:
        params={"action":"query","format":"json","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":35,
                "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1400}
        data=get_json(params)
        for page in (data.get("query",{}).get("pages",{}) or {}).values():
            ii=(page.get("imageinfo") or [{}])[0]; em=ii.get("extmetadata",{}) or {}
            url=ii.get("thumburl") or ii.get("url"); title=page.get("title","")
            if not url or url in seen or not license_ok(em): continue
            low=title.lower()
            if any(x in low for x in ["logo","map","diagram","text","icon","flag","chart"]): continue
            seen.add(url)
            candidates.append({"url":url,"title":title,
              "artist":(em.get("Artist",{}).get("value","") or "")[:300],
              "license":(em.get("LicenseShortName",{}).get("value","") or ""),
              "license_url":(em.get("LicenseUrl",{}).get("value","") or ""),
              "description_url":ii.get("descriptionurl","")})
        if len(candidates)>=16: break
        time.sleep(1.5)

    used=[]
    for item in candidates:
        if len(used)>=12: break
        p=d/f"{len(used)+1:02d}.jpg"
        try:
            p.write_bytes(get_bytes(item["url"]))
            from PIL import Image
            im=Image.open(p).convert("RGB")
            if im.width<500 or im.height<400:
                p.unlink(missing_ok=True); continue
            im.thumbnail((1800,1800),Image.Resampling.LANCZOS)
            im.save(p,quality=89)
            used.append(item)
            time.sleep(2)
        except Exception as e:
            print("skip",item["title"],repr(e),flush=True)
            p.unlink(missing_ok=True)
            time.sleep(3)
    if len(used)<9:
        raise RuntimeError(f"{deity}: only {len(used)} usable images")
    meta.write_text(json.dumps(used,ensure_ascii=False,indent=2),encoding="utf-8")
    print(deity,"cached",len(used),flush=True)

def main():
    cache_deity(DEITY)
    entries=json.loads((BUILD/"audio_manifest.json").read_text(encoding="utf-8"))
    selected=[e for e in entries if e["deity"]==DEITY and e["id"] not in SKIP_IDS]
    outdir=OUTROOT/DEITY; outdir.mkdir(parents=True,exist_ok=True)
    pool=json.loads((VIS/DEITY/"ATTRIBUTION.json").read_text(encoding="utf-8"))
    status=[]
    for e in selected:
        out=outdir/f"{e['id']}_{rg.safe(e['title'])}_11X.mp4"
        if out.exists():
            status.append({"id":e["id"],"status":"existing","video":out.name}); continue
        work=outdir/f"work_{e['id']}"; work.mkdir(exist_ok=True)
        try:
            voice=BUILD/"audio"/f"{e['id']}.wav"
            mixed=work/"mixed.wav"; duration=rg.music_and_voice(e,voice,mixed)
            imgs,used=rg.download_selected(e,pool,9)
            rg.make_video(e,imgs,mixed,duration,out,work)
            status.append({"id":e["id"],"status":"success","video":out.name,"images":used})
            print("DONE",e["id"],out.name,flush=True)
        except Exception as ex:
            status.append({"id":e["id"],"status":"failed","error":repr(ex)})
            print("FAILED",e["id"],repr(ex),flush=True)
        finally:
            shutil.rmtree(work,ignore_errors=True)
    (outdir/"STATUS.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    failed=[x for x in status if x["status"]=="failed"]
    if failed: raise SystemExit(f"{len(failed)} failures in {DEITY}")
    print("COMPLETE",DEITY,len(selected))

if __name__=="__main__": main()
