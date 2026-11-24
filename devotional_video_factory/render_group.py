#!/usr/bin/env python3
import json, os, re, sys, math, random, hashlib, subprocess, textwrap
from pathlib import Path
import requests, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
REPO_ROOT=ROOT.parent
BUILD=REPO_ROOT/"build_audio"
OUTROOT=REPO_ROOT/"rendered_videos"
CACHE=REPO_ROOT/"visual_cache"
OUTROOT.mkdir(exist_ok=True); CACHE.mkdir(exist_ok=True)

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
ROOT_FREQ={"Ganesha":146.83,"Shiva":138.59,"Vishnu":146.83,"Krishna":164.81,"Rama":146.83,"Hanuman":155.56,"Durga":174.61,"Lakshmi":164.81}

def run(cmd):
    subprocess.run(cmd,check=True)

def safe(s):
    return re.sub(r"[^A-Za-z0-9_-]+","_",s).strip("_")[:90]

def license_ok(meta):
    lic=(meta.get("LicenseShortName",{}).get("value","") or "").lower()
    if any(x in lic for x in ["noncommercial","no derivatives","nc","nd"]): return False
    return any(x in lic for x in ["public domain","cc0","cc by","creative commons"])

def fetch_pool(deity,min_n=9):
    d=REPO_ROOT/"visual_assets"/safe(deity)
    meta_file=d/"ATTRIBUTION.json"
    if not meta_file.exists():
        raise RuntimeError(f"Missing cached visual attribution for {deity}")
    pool=json.loads(meta_file.read_text(encoding="utf-8"))
    if len(pool)<min_n:
        raise RuntimeError(f"Only {len(pool)} cached images for {deity}")
    return pool

def download_selected(entry,pool,n=9):
    d=REPO_ROOT/"visual_assets"/safe(entry["deity"])
    files=sorted(d.glob("*.jpg"))
    if len(files)<n:
        raise RuntimeError(f"{entry['deity']} has only {len(files)} cached images")
    rnd=random.Random(int(hashlib.sha256(entry["id"].encode()).hexdigest()[:8],16))
    order=list(range(len(files)))
    rnd.shuffle(order)
    selected_files=[files[i] for i in order[:n]]
    used=[pool[i] for i in order[:n]]
    return selected_files,used

def music_and_voice(entry,voice_path,out_path):
    voice,sr=sf.read(voice_path,always_2d=True); voice=voice.mean(axis=1).astype(np.float32)
    peak=max(float(np.max(np.abs(voice))),1e-8); voice=voice/peak*0.72
    # gentle room space
    v=voice.copy()
    for ms,g in [(90,.055),(180,.032),(285,.018)]:
        d=int(sr*ms/1000)
        if d<len(voice):v[d:]+=g*voice[:-d]
    gap=np.zeros(int(sr*.48),dtype=np.float32)
    reps=[]
    for i in range(11):
        reps.append(v)
        if i<10:reps.append(gap)
    chant=np.concatenate(reps)
    n=len(chant); t=np.arange(n,dtype=np.float32)/sr
    root=ROOT_FREQ.get(entry["deity"],146.83)
    drone=(.40*np.sin(2*np.pi*root*t)+.15*np.sin(2*np.pi*root*1.5*t+.3)+.08*np.sin(2*np.pi*root*2*t+1.0))
    pad=.11*np.sin(2*np.pi*root*1.25*t+.2)+.075*np.sin(2*np.pi*root*1.6667*t+1.2)
    music=(drone+pad)*(.80+.20*np.sin(2*np.pi*.032*t-.5)**2)
    # gentle flute phrases
    ratios=[1,5/4,4/3,3/2,4/3,5/4]
    if entry["deity"]=="Shiva":ratios=[1,6/5,4/3,3/2,4/3,6/5]
    melody=np.zeros(n,dtype=np.float32); pos=1.2; k=0
    while pos<n/sr-1:
        m=min(int(sr*2.5),n-int(pos*sr))
        if m<=0:break
        tt=np.arange(m,dtype=np.float32)/sr; freq=root*2*ratios[k%len(ratios)]
        phase=2*np.pi*freq*np.cumsum(1+.003*np.sin(2*np.pi*5*tt))/sr
        sig=.09*np.sin(phase)+.02*np.sin(2*phase)
        env=np.ones(m,dtype=np.float32); a=min(int(.25*sr),m//3); r=min(int(.45*sr),m//3)
        if a:env[:a]=np.linspace(0,1,a)
        if r:env[-r:]=np.linspace(1,0,r)
        i=int(pos*sr); melody[i:i+m]+=sig*env
        pos+=6.0;k+=1
    music+=melody; music/=max(float(np.max(np.abs(music))),1e-8)
    mix=chant+.27*music.astype(np.float32)
    pk=max(float(np.max(np.abs(mix))),1e-8)
    if pk>.96:mix=mix/pk*.96
    sf.write(out_path,mix,sr,subtype="PCM_16")
    return len(mix)/sr

def font(paths,size):
    for p in paths:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

DEVFONT=["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf","/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf"]
DEVBOLD=["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf","/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.ttf"]
LATIN=["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

def wrap_px(draw,text,fnt,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        cand=(cur+" "+w).strip()
        if draw.textbbox((0,0),cand,font=fnt)[2]<=maxw:cur=cand
        else:
            if cur:lines.append(cur)
            cur=w
    if cur:lines.append(cur)
    return lines[:4]

def make_overlay(entry,path):
    W,H=1280,720
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA")
    titlef=font(LATIN,28); devf=font(DEVBOLD,39); latf=font(LATIN,25); meanf=font(LATIN,20)
    box_y=H-265
    d.rounded_rectangle([34,box_y,1246,H-28],radius=24,fill=(0,0,0,148),outline=(255,255,255,35),width=1)
    d.text((58,box_y+18),f"{entry['title']}  •  11×",font=titlef,fill=(255,235,184,245))
    y=box_y+62
    for line in wrap_px(d,entry["devanagari"],devf,1160)[:2]:
        d.text((58,y),line,font=devf,fill=(255,255,255,248));y+=48
    for line in wrap_px(d,entry.get("transliteration",""),latf,1160)[:2]:
        d.text((58,y),line,font=latf,fill=(230,238,255,238));y+=34
    meaning="Meaning / theme: "+entry.get("english_meaning_theme","")
    for line in wrap_px(d,meaning,meanf,1160)[:2]:
        d.text((58,y),line,font=meanf,fill=(225,225,225,225));y+=27
    im.save(path)

def make_video(entry,images,audio_path,duration,out_path,work):
    fps=12; fade=.75
    per=(duration+(len(images)-1)*fade)/len(images)
    clips=[]
    for idx,p in enumerate(images):
        clip=work/f"clip_{idx:02d}.mp4"; clips.append(clip)
        frames=max(24,int(round(per*fps)))
        if idx%2==0:z="min(zoom+0.0007,1.10)"
        else:z="if(eq(on,1),1.10,max(zoom-0.0007,1.0))"
        x="iw/2-(iw/zoom/2)+sin(on/35)*5"
        y="ih/2-(ih/zoom/2)+cos(on/40)*4"
        vf=f"scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1280x720:fps={fps},format=yuv420p"
        run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(p),"-vf",vf,"-t",f"{per:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","27",str(clip)])
    cmd=["ffmpeg","-y","-loglevel","error"]
    for c in clips:cmd+=["-i",str(c)]
    fc=[]; last="[0:v]"; offset=per-fade
    for i in range(1,len(clips)):
        out=f"[v{i}]";fc.append(f"{last}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}{out}");last=out;offset+=per-fade
    base=work/"base.mp4"
    cmd+=["-filter_complex",";".join(fc),"-map",last,"-c:v","libx264","-preset","veryfast","-crf","27","-pix_fmt","yuv420p",str(base)]
    run(cmd)
    overlay=work/"overlay.png";make_overlay(entry,overlay)
    run(["ffmpeg","-y","-loglevel","error","-i",str(base),"-loop","1","-i",str(overlay),"-i",str(audio_path),
         "-filter_complex","[0:v][1:v]overlay=0:0:shortest=1[v]","-map","[v]","-map","2:a",
         "-c:v","libx264","-preset","veryfast","-crf","25","-c:a","aac","-b:a","160k","-pix_fmt","yuv420p",
         "-shortest","-movflags","+faststart",str(out_path)])

def main():
    group=int(os.getenv("GROUP","0"))
    all_entries=json.loads((BUILD/"audio_manifest.json").read_text(encoding="utf-8"))
    # ten groups by original P1 number, so output naming and progress remain predictable
    selected=[e for e in all_entries if (int(e["id"].split("-")[1])-1)//10==group]
    gout=OUTROOT/f"group_{group:02d}";gout.mkdir(parents=True,exist_ok=True)
    attributions=[]
    for e in selected:
        try:
            print("VIDEO",e["id"],e["title"],flush=True)
            voice=BUILD/"audio"/f"{e['id']}.wav"
            work=gout/f"work_{e['id']}";work.mkdir(exist_ok=True)
            mixed=work/"mixed.wav";duration=music_and_voice(e,voice,mixed)
            pool=fetch_pool(e["deity"])
            imgs,used=download_selected(e,pool,9)
            out=gout/f"{e['id']}_{safe(e['title'])}_11X.mp4"
            make_video(e,imgs,mixed,duration,out,work)
            attributions.append({"id":e["id"],"title":e["title"],"video":out.name,"images":used})
            # retain only final outputs, not clip intermediates
            import shutil;shutil.rmtree(work,ignore_errors=True)
        except Exception as ex:
            print("FAILED",e["id"],repr(ex),flush=True)
            attributions.append({"id":e["id"],"title":e["title"],"error":repr(ex)})
    (gout/"ATTRIBUTION_AND_STATUS.json").write_text(json.dumps(attributions,ensure_ascii=False,indent=2),encoding="utf-8")
    success=len(list(gout.glob("P1-*.mp4")))
    print("GROUP",group,"SUCCESS",success,"OF",len(selected))
    if success < max(1,len(selected)-2):raise SystemExit("Too many video failures in group")

if __name__=="__main__":main()
