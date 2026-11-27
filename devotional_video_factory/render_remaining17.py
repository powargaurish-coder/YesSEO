#!/usr/bin/env python3
import json, os, shutil, requests
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
import sys
sys.path.insert(0,str(HERE))
import render_group as rg

BUILD=REPO/"build_audio"
OUT=REPO/"final_remaining17"
VIS=REPO/"remaining17_visuals"
APPROVED=HERE/"approved_visuals.json"

TARGET_IDS=[
"P1-046","P1-047","P1-048","P1-049","P1-050","P1-051","P1-052","P1-053",
"P1-054","P1-055","P1-056","P1-057","P1-062","P1-064","P1-065","P1-067","P1-074"
]

def dl(url,path):
    r=requests.get(url,timeout=120,headers={"User-Agent":"FinalRemaining17Renderer/1.0"})
    r.raise_for_status(); path.write_bytes(r.content)

def make_krishna_variants(url):
    d=VIS/"Krishna"; d.mkdir(parents=True,exist_ok=True)
    src=d/"master.png"
    if not src.exists(): dl(url,src)
    im=Image.open(src).convert("RGB")
    # Preserve anatomy: variants only change framing/background treatment, never synthesize limbs.
    variants=[]
    W,H=1280,720
    for i in range(8):
        out=d/f"{i+1:02d}.jpg"
        if out.exists():
            variants.append(out); continue
        base=im.copy()
        # background fill from same image only
        bg=base.copy()
        bg.thumbnail((W,H),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(W,H),(0,0,0))
        # blurred background
        cover=base.copy()
        scale=max(W/cover.width,H/cover.height)
        cover=cover.resize((int(cover.width*scale),int(cover.height*scale)),Image.Resampling.LANCZOS)
        x=(cover.width-W)//2; y=(cover.height-H)//2
        cover=cover.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(18))
        cover=ImageEnhance.Brightness(cover).enhance(0.68+0.04*(i%3))
        canvas.paste(cover,(0,0))
        # foreground: only crop/scale the same correct two-hand master
        fg=base.copy()
        target_h=int(H*(0.88-0.025*(i%4)))
        scale=target_h/fg.height
        fg=fg.resize((int(fg.width*scale),target_h),Image.Resampling.LANCZOS)
        xpos=int((W-fg.width)/2 + [0,-45,45,-25,25,-60,60,0][i])
        ypos=H-fg.height-10
        canvas.paste(fg,(xpos,ypos))
        if i in (2,5): canvas=ImageEnhance.Contrast(canvas).enhance(1.05)
        if i in (3,6): canvas=ImageEnhance.Brightness(canvas).enhance(1.04)
        canvas.save(out,quality=92)
        variants.append(out)
    return variants

def approved_files(deity,manifest):
    urls=manifest.get(deity,[])
    if deity=="Krishna":
        if len(urls)!=1: raise RuntimeError("Krishna must use exactly one corrected two-hand master")
        return make_krishna_variants(urls[0])
    if len(urls)<7: raise RuntimeError(f"{deity}: insufficient approved visuals")
    d=VIS/deity; d.mkdir(parents=True,exist_ok=True)
    files=[]
    for i,u in enumerate(urls[:8],1):
        p=d/f"{i:02d}.jpg"
        if not p.exists():
            dl(u,p)
            im=Image.open(p).convert("RGB")
            im.thumbnail((2200,2200),Image.Resampling.LANCZOS)
            im.save(p,quality=92)
        files.append(p)
    return files

def main():
    manifest=json.loads(APPROVED.read_text(encoding="utf-8"))
    entries=json.loads((BUILD/"audio_manifest.json").read_text(encoding="utf-8"))
    emap={e["id"]:e for e in entries}
    missing=[x for x in TARGET_IDS if x not in emap]
    if missing: raise SystemExit("Missing audio manifest entries: "+",".join(missing))
    OUT.mkdir(parents=True,exist_ok=True)
    pools={}
    status=[]
    for eid in TARGET_IDS:
        e=emap[eid]
        deity=e["deity"]
        if deity not in pools: pools[deity]=approved_files(deity,manifest)
        voice=BUILD/"audio"/f"{eid}.wav"
        if not voice.exists(): raise RuntimeError(f"Missing wav {eid}")
        work=OUT/f"work_{eid}"; work.mkdir(exist_ok=True)
        out=OUT/f"{eid}_{rg.safe(e['title'])}_11X_FINAL_APPROVED.mp4"
        try:
            mixed=work/"mixed.wav"; duration=rg.music_and_voice(e,voice,mixed)
            imgs=pools[deity]
            # use 8 approved visuals/variants
            rg.make_video(e,imgs,mixed,duration,out,work)
            status.append({"id":eid,"deity":deity,"status":"success","video":out.name})
            print("DONE",eid,out.name,flush=True)
        except Exception as ex:
            status.append({"id":eid,"deity":deity,"status":"failed","error":repr(ex)})
            print("FAILED",eid,repr(ex),flush=True)
        finally:
            shutil.rmtree(work,ignore_errors=True)
    (OUT/"STATUS.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    ok=[x for x in status if x["status"]=="success"]
    if len(ok)!=17: raise SystemExit(f"Expected 17 successes, got {len(ok)}")
    print("REMAINING17 COMPLETE",len(ok),flush=True)

if __name__=="__main__":
    main()
