#!/usr/bin/env python3
import os, json, random, hashlib, shutil, requests
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
import sys
sys.path.insert(0,str(HERE))
import render_group as rg

BUILD=REPO/"build_audio"
OUTROOT=REPO/"approved_final_videos"
VISROOT=REPO/"approved_visual_cache"
MANIFEST=HERE/"approved_visuals.json"

def fetch_approved(deity):
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    urls=manifest.get(deity,[])
    if len(urls)<7:
        raise RuntimeError(f"{deity}: only {len(urls)} approved visuals")
    d=VISROOT/deity
    d.mkdir(parents=True,exist_ok=True)
    files=[]
    for i,url in enumerate(urls,1):
        p=d/f"{i:02d}.jpg"
        if not p.exists():
            r=requests.get(url,timeout=90,headers={"User-Agent":"ApprovedDevotionalRenderer/1.0"})
            r.raise_for_status()
            p.write_bytes(r.content)
            from PIL import Image
            im=Image.open(p).convert("RGB")
            im.thumbnail((2200,2200),Image.Resampling.LANCZOS)
            im.save(p,quality=92)
        files.append(p)
    return files

def render_entry(e,approved_files,outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/f"{e['id']}_{rg.safe(e['title'])}_11X_FINAL_APPROVED.mp4"
    work=outdir/f"work_{e['id']}"
    work.mkdir(exist_ok=True)
    try:
        voice=BUILD/"audio"/f"{e['id']}.wav"
        mixed=work/"mixed.wav"
        duration=rg.music_and_voice(e,voice,mixed)

        rnd=random.Random(int(hashlib.sha256(e["id"].encode()).hexdigest()[:8],16))
        imgs=list(approved_files)
        rnd.shuffle(imgs)
        imgs=imgs[:min(8,len(imgs))]

        # Shiva stays visually restrained: static compositions with crossfades only.
        if e["deity"]=="Shiva":
            old_make=rg.make_video
            # build static clips then use standard overlay/audio pipeline
            import subprocess
            fps=12; fade=.8
            per=(duration+(len(imgs)-1)*fade)/len(imgs)
            clips=[]
            for idx,p in enumerate(imgs):
                clip=work/f"clip_{idx:02d}.mp4"; clips.append(clip)
                vf="scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,scale=1280:720,format=yuv420p"
                subprocess.run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(p),"-vf",vf,"-t",f"{per:.3f}","-r",str(fps),"-an","-c:v","libx264","-preset","veryfast","-crf","27",str(clip)],check=True)
            cmd=["ffmpeg","-y","-loglevel","error"]
            for c in clips: cmd+=["-i",str(c)]
            fc=[]; last="[0:v]"; offset=per-fade
            for i in range(1,len(clips)):
                outv=f"[v{i}]"; fc.append(f"{last}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}{outv}"); last=outv; offset+=per-fade
            base=work/"base.mp4"
            cmd+=["-filter_complex",";".join(fc),"-map",last,"-c:v","libx264","-preset","veryfast","-crf","27","-pix_fmt","yuv420p",str(base)]
            subprocess.run(cmd,check=True)
            overlay=work/"overlay.png"; rg.make_overlay(e,overlay)
            subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(base),"-loop","1","-i",str(overlay),"-i",str(mixed),
              "-filter_complex","[0:v][1:v]overlay=0:0:shortest=1[v]","-map","[v]","-map","2:a","-c:v","libx264","-preset","veryfast","-crf","25","-c:a","aac","-b:a","160k","-pix_fmt","yuv420p","-shortest","-movflags","+faststart",str(out)],check=True)
        else:
            rg.make_video(e,imgs,mixed,duration,out,work)
        return {"id":e["id"],"title":e["title"],"deity":e["deity"],"status":"success","video":out.name}
    except Exception as ex:
        return {"id":e["id"],"title":e["title"],"deity":e["deity"],"status":"failed","error":repr(ex)}
    finally:
        shutil.rmtree(work,ignore_errors=True)

def main():
    group=int(os.environ.get("GROUP","0"))
    entries=json.loads((BUILD/"audio_manifest.json").read_text(encoding="utf-8"))
    selected=[e for e in entries if (int(e["id"].split("-")[1])-1)//10==group]
    outdir=OUTROOT/f"group_{group:02d}"
    pools={}
    status=[]
    for e in selected:
        if e["deity"] not in pools:
            pools[e["deity"]]=fetch_approved(e["deity"])
        print("FINAL APPROVED",e["id"],e["title"],flush=True)
        s=render_entry(e,pools[e["deity"]],outdir)
        status.append(s)
        print(s,flush=True)
    (outdir/"STATUS.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    failures=[x for x in status if x["status"]!="success"]
    if failures:
        raise SystemExit(f"{len(failures)} failures in group {group}")
    print("GROUP COMPLETE",group,len(status),flush=True)

if __name__=="__main__":
    main()
