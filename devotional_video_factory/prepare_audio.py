#!/usr/bin/env python3
import json, os, re, sys, difflib, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
MANIFEST = ROOT / "manifest_100.json"
SRC_ROOT = REPO_ROOT / "source_texts"
OUT = REPO_ROOT / "build_audio"
AUDIO = OUT / "audio"
META = OUT / "meta"
AUDIO.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)

DIRECT = {
"P1-001":"वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ। निर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा॥",
"P1-002":"ॐ एकदन्ताय विद्महे वक्रतुण्डाय धीमहि। तन्नो दन्तिः प्रचोदयात्॥",
"P1-006":"सुमुखश्चैकदन्तश्च कपिलो गजकर्णकः। लम्बोदरश्च विकटो विघ्ननाशो विनायकः। धूम्रकेतुर्गणाध्यक्षो भालचन्द्रो गजाननः॥",
"P1-012":"ॐ सुमुखाय नमः। ॐ एकदन्ताय नमः। ॐ कपिलाय नमः। ॐ गजकर्णकाय नमः। ॐ लम्बोदराय नमः। ॐ विकटाय नमः। ॐ विघ्ननाशाय नमः। ॐ विनायकाय नमः॥",
"P1-013":"ओम् नमः शिवाय॥",
"P1-014":"ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम्। उर्वारुकमिव बन्धनान्मृत्योर्मुक्षीय मामृतात्॥",
"P1-031":"ओम् नमो नारायणाय॥",
"P1-032":"ओम् नमो भगवते वासुदेवाय॥",
"P1-039":"ॐ नारायणाय विद्महे वासुदेवाय धीमहि। तन्नो विष्णुः प्रचोदयात्॥",
"P1-046":"हरे कृष्ण हरे कृष्ण कृष्ण कृष्ण हरे हरे। हरे राम हरे राम राम राम हरे हरे॥",
"P1-047":"ॐ देवकीनन्दनाय विद्महे वासुदेवाय धीमहि। तन्नः कृष्णः प्रचोदयात्॥",
"P1-058":"श्री राम जय राम जय जय राम॥",
"P1-059":"श्री राम राम रामेति रमे रामे मनोरमे। सहस्रनाम तत्तुल्यं रामनाम वरानने॥",
"P1-060":"ॐ दाशरथाय विद्महे सीतावल्लभाय धीमहि। तन्नो रामः प्रचोदयात्॥",
"P1-066":"सीता राम सीता राम सीता राम जय सीता राम॥",
"P1-068":"ओम् हनुमते नमः॥",
"P1-069":"ॐ आञ्जनेयाय विद्महे वायुपुत्राय धीमहि। तन्नो हनुमान् प्रचोदयात्॥",
"P1-078":"ओम् दुं दुर्गायै नमः॥",
"P1-079":"ॐ कात्यायनाय विद्महे कन्याकुमारि धीमहि। तन्नो दुर्गिः प्रचोदयात्॥",
"P1-080":"या देवी सर्वभूतेषु शक्तिरूपेण संस्थिता। नमस्तस्यै नमस्तस्यै नमस्तस्यै नमो नमः॥",
"P1-081":"सर्वमङ्गलमाङ्गल्ये शिवे सर्वार्थसाधिके। शरण्ये त्र्यम्बके गौरि नारायणि नमोऽस्तु ते॥",
"P1-093":"ओम् श्रीं महालक्ष्म्यै नमः॥",
"P1-094":"ॐ महालक्ष्म्यै च विद्महे विष्णुपत्न्यै च धीमहि। तन्नो लक्ष्मीः प्रचोदयात्॥",
"P1-097":"नमस्तेऽस्तु महामाये श्रीपीठे सुरपूजिते। शङ्खचक्रगदाहस्ते महालक्ष्मि नमोऽस्तु ते॥"
}

OVERRIDE = {
"P1-003":("vedamantra-book","mantras/Ganapatyatharvashirsham.tex"),
"P1-004":("sangrah","docs/stotras-shlok/ganesha_ganesha-pancharatnam.md"),
"P1-005":("sangrah","docs/stotras-shlok/ganesha_sri-ganesha-ashtakam.md"),
"P1-007":("sangrah","docs/stotras-shlok/ganesha_sankata-nasana-ganesha-stotram.md"),
"P1-008":("sangrah","docs/stotras-shlok/ganesha_sri-ganesha-bhujanga-stuti.md"),
"P1-009":("sangrah","docs/kavacham/ganesha_sri-ganesha-kavacham.md"),
"P1-010":("sangrah","docs/stotras-shlok/ganesha_sri-ganapathi-mangalashtakam.md"),
"P1-011":("sangrah","docs/stotras-shlok/ganesha_ganesha-pratah-smarana-stotram.md"),
"P1-015":("sangrah","docs/stotras-shlok/shiva_shiva-panchakshara-stotram-in-hindi.md"),
"P1-016":("sangrah","docs/stotras-shlok/shiva_shiva-shadakshara-stotram-in-hindi.md"),
"P1-017":("stotra-sangrahah","stotras/shiva/Lingashtakam.tex"),
"P1-018":("stotra-sangrahah","stotras/shiva/Bilvashtakam.tex"),
"P1-019":("sangrah","docs/stotras-shlok/shiva_rudrashtakam-in-hindi.md"),
"P1-020":("sangrah","docs/stotras-shlok/shiva_shiva-manasa-puja-stotram-in-hindi.md"),
"P1-022":("sangrah","docs/stotras-shlok/shiva_chandrasekhara-ashtakam-in-hindi.md"),
"P1-023":("sangrah","docs/stotras-shlok/bhairava_kalabhairavashtakam.md"),
"P1-024":("stotra-sangrahah","stotras/shiva/DakshinamurtiStotram.tex"),
"P1-026":("sangrah","docs/stotras-shlok/shiva_shiva-mahimna-stotram-in-hindi.md"),
"P1-027":("sangrah","docs/stotras-shlok/shiva_vishwanatha-ashtakam-in-hindi.md"),
"P1-029":("sangrah","docs/stotras-shlok/shiva_shiva-aparadha-kshamapana-stotram-in-hindi.md"),
"P1-030":("vedamantra-book","mantras/RudraPrashnah.tex"),
"P1-037":("vedamantra-book","mantras/NarayanaSuktam.tex"),
"P1-038":("vedamantra-book","mantras/PurushaSuktam.tex"),
"P1-040":("stotra-sangrahah","stotras/krishna/Achyutashtakam.tex"),
"P1-049":("stotra-sangrahah","stotras/krishna/Madhurashtakam.tex"),
"P1-050":("stotra-sangrahah","stotras/krishna/Krishnashtakam1.tex"),
"P1-052":("stotra-sangrahah","stotras/krishna/Damodarashtakam.tex"),
"P1-053":("stotra-sangrahah","stotras/krishna/Govindashtakam.tex"),
"P1-070":("sangrah","docs/chalisa/aa-hanuman-chalisa.md"),
"P1-082":("sangrah","docs/stotras-shlok/saptashloki-durga-stotra.md"),
"P1-083":("sangrah","docs/stotras-shlok/durga_argala-stotram.md"),
"P1-084":("sangrah","docs/stotras-shlok/kilak-stotra.md"),
"P1-087":("sangrah","docs/stotras-shlok/devi_devi-aparadha-kshamapana-stotram.md"),
"P1-089":("vedamantra-book","mantras/DurgaSuktam.tex"),
"P1-090":("sangrah","docs/stotras-shlok/devi_bhavani-ashtakam.md"),
"P1-095":("vedamantra-book","mantras/ShriSuktam.tex"),
"P1-096":("sangrah","docs/stotras-shlok/lakshmi_kanakadhara-stotram-in-hindi.md"),
"P1-098":("sangrah","docs/namavali/108_sri-lakshmi-ashtottara-shatanamavali-3.md")
}

ALIASES = {
"P1-021":["shiva tandava","shiv tandav"],"P1-025":["ardhanarishvara","ardhanareeshwara"],
"P1-028":["shiva pratah smarana"],"P1-033":["vishnu sahasranama","vishnu namavali"],
"P1-034":["vishnu shatpadi"],"P1-035":["vishnu panchayudha"],"P1-036":["narayana kavacha"],
"P1-041":["mukunda mala"],"P1-042":["vishnu pratah smarana"],"P1-043":["vishnu mangalashtakam"],
"P1-044":["vishnu bhujanga"],"P1-045":["vishnu panjara"],"P1-048":["govinda damodara madhaveti"],
"P1-051":["gopala sahasranama"],"P1-054":["krishna anusmriti"],"P1-055":["mukunda ashtakam"],
"P1-057":["vasudeva dvadasha nama"],"P1-061":["rama raksha","ramraksha"],"P1-062":["rama ashtakam"],
"P1-063":["rama bhujanga"],"P1-064":["rama dvadasha nama"],"P1-065":["rama pratah smarana"],
"P1-067":["rama mangalashtakam"],"P1-071":["bajrang baan"],"P1-072":["hanuman ashtakam"],
"P1-073":["hanuman bahuk"],"P1-074":["anjaneya dvadasha nama"],"P1-075":["hanuman kavacha"],
"P1-076":["hanuman mangalashtakam"],"P1-077":["sundarakanda hanuman","sundarakand"],
"P1-085":["devi kavacha","durga kavacha"],"P1-086":["durga ashtottara shatanama"],
"P1-088":["mahishasura mardini","aigiri nandini"],"P1-091":["durga pratah smarana"],
"P1-092":["durga mangalashtakam"],"P1-099":["lakshmi pratah smarana"],"P1-100":["gajalakshmi stotra"]
}

SKIP_WORDS={"stotra","stotram","stuti","ashtakam","ashtaka","selected","verses","verse","names","name","sri","shri","lord","mantra","hymn","prayer","morning","pratah","the","and","nama","japa","traditional","suktam","sukta"}

def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(x for x in s.split() if x not in SKIP_WORDS)

def score(q,f):
    q,b=norm(q),norm(Path(f).stem)
    if not q or not b:return 0.0
    qs,bs=set(q.split()),set(b.split())
    inter=len(qs&bs); union=max(1,len(qs|bs))
    return (inter/union)*0.65+difflib.SequenceMatcher(None,q,b).ratio()*0.35+min(inter,4)*0.06

def source_files():
    roots={"stotra-sangrahah":SRC_ROOT/"stotra-sangrahah","vedamantra-book":SRC_ROOT/"vedamantra-book","namavali-manjari":SRC_ROOT/"namavali-manjari","sangrah":SRC_ROOT/"sangrah"}
    files=[]
    for repo,root in roots.items():
        if not root.exists():continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".tex",".md",".txt"}:
                files.append((repo,p,p.relative_to(root).as_posix()))
    return roots,files

def clean_tex(s):
    s=re.sub(r"(?m)%.*$","",s)
    s=s.replace("\\\\","\n")
    s=re.sub(r"\\(?:begin|end)\{[^{}]+\}"," ",s)
    s=re.sub(r"\\[A-Za-z@]+(?:\[[^\]]*\])?"," ",s)
    return s.replace("{"," ").replace("}"," ")

BAD=re.compile(r"(ध्यान|विनियोग|ऋषि|छन्द|देवता|कीलक|न्यास|समाप्त|इति\s)",re.I)

def extract(path):
    raw=path.read_text(encoding="utf-8",errors="ignore")
    if path.suffix.lower()==".tex":raw=clean_tex(raw)
    lines=[]
    for ln in raw.splitlines():
        ln=re.sub(r"^[#>*\-\d\.\)\s]+","",ln).strip()
        ln=re.sub(r"[*_~|]"," ",ln).strip()
        if not re.search(r"[\u0900-\u097F]",ln):continue
        if BAD.search(ln) and len(ln)<90:continue
        dev="".join(ch for ch in ln if ("\u0900"<=ch<="\u097F") or ch.isspace() or ch in "।॥ऽॐ-")
        dev=re.sub(r"\s+"," ",dev).strip()
        if len(re.findall(r"[\u0900-\u097F]",dev))<12:continue
        lines.append(dev)
        joined=" ".join(lines)
        if "॥" in dev and len(joined)>=35:break
        if len(joined)>=220:break
    if not lines:return None
    text=" ".join(lines)
    m=re.search(r"^(.{20,320}?॥)",text)
    if m:text=m.group(1)
    return text[:340].strip()

def find_source(e,roots,files):
    eid=e["id"]
    if eid in OVERRIDE:
        repo,rel=OVERRIDE[eid]; p=roots[repo]/rel
        if p.exists():return p,f"{repo}/{rel}",1.0
    queries=[e["title"]]+ALIASES.get(eid,[])
    best=None
    for repo,p,rel in files:
        s=max(score(q,rel) for q in queries)
        if norm(e["deity"]) in norm(rel):s+=0.08
        if best is None or s>best[0]:best=(s,p,f"{repo}/{rel}")
    return (best[1],best[2],best[0]) if best else (None,None,0)

def translit(text):
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        import unidecode
        return unidecode.unidecode(transliterate(text,sanscript.DEVANAGARI,sanscript.IAST))
    except Exception:return ""

MEAN={
"P1-001":"O Lord Ganesha, remover of obstacles, bless all my endeavours and keep them free from difficulties.",
"P1-013":"I bow to Lord Shiva, the auspicious inner Self.",
"P1-014":"A prayer for healing, strength, freedom from fear, and liberation from mortality.",
"P1-031":"I bow to Lord Narayana, the all-pervading divine presence.",
"P1-032":"I bow to Lord Vasudeva, the Supreme Divine.",
"P1-046":"A joyful invocation of Krishna and Rama through the divine names.",
"P1-058":"Victory and reverence to Lord Rama; may the divine name bring peace and strength.",
"P1-068":"I bow to Lord Hanuman, embodiment of courage, devotion and service.",
"P1-078":"I bow to Goddess Durga, invoking her protective divine power.",
"P1-081":"Salutations to the auspicious Divine Mother who grants refuge and fulfils righteous purposes.",
"P1-093":"I bow to Mahalakshmi, invoking abundance, grace and well-being."
}
def meaning(e):
    if e["id"] in MEAN:return MEAN[e["id"]]
    d,t=e["deity"],e["type"]
    if "kavacha" in t:return f"A protective hymn invoking {d} for courage, safeguarding and divine grace."
    if "vedic" in t:return f"A sacred Vedic passage invoking the divine presence associated with {d}; presented here as a selected listening passage."
    if "namavali" in t:return f"A devotional recitation of sacred names of {d}, contemplating different divine qualities."
    if "morning" in t:return f"A morning remembrance of {d}, seeking clarity, devotion and an auspicious start to the day."
    if "ashtakam" in t:return f"An eight-verse devotional hymn praising {d} and seeking divine grace."
    if t=="mantra":return f"A devotional invocation of {d}, repeated for focus, peace and remembrance."
    return f"A devotional verse praising {d} and contemplating divine qualities, grace and protection."

def main():
    entries=json.loads(MANIFEST.read_text(encoding="utf-8"))
    roots,files=source_files(); report=[]
    for e in entries:
        text=DIRECT.get(e["id"]); source="direct canonical text"; sc=1.0
        if not text:
            p,source,sc=find_source(e,roots,files)
            if p:text=extract(p)
        if not text or (source!="direct canonical text" and sc<0.22):
            report.append({**e,"status":"UNRESOLVED","source":source,"source_score":round(sc,3)})
            print("UNRESOLVED",e["id"],e["title"],sc);continue
        item={**e,"status":"SOURCE_SELECTED","source":source,"source_score":round(sc,3),"devanagari":text,"transliteration":translit(text),"english_meaning_theme":meaning(e)}
        (META/f"{e['id']}.json").write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding="utf-8")
        report.append(item)
        print("TEXT",e["id"],text[:80],source)
    (OUT/"source_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    resolved=[x for x in report if x["status"]!="UNRESOLVED"]
    if len(resolved)<90:raise SystemExit(f"Only {len(resolved)}/100 passages resolved; refusing recording.")

    sys.path.insert(0,str(REPO_ROOT/"vexyl-tts"))
    os.environ["VEXYL_TTS_DEVICE"]="cpu"; os.environ["VEXYL_TTS_DISK_CACHE"]="0"
    import vexyl_tts_server as vt
    vt.load_model()
    desc=("Vasudha speaks in a very soft, serene Indian devotional tone, warm and peaceful, slightly slow-paced, "
          "with careful Sanskrit pronunciation and a gentle chant-like cadence. The voice is soothing for daily meditation "
          "and repeat listening. The recording is clean with no background noise.")
    for item in resolved:
        print("AUDIO",item["id"],item["title"],flush=True)
        wav_bytes,sr=vt._synthesize_sync(item["devanagari"],"sa-IN","warm",desc)
        (AUDIO/f"{item['id']}.wav").write_bytes(wav_bytes)
    (OUT/"audio_manifest.json").write_text(json.dumps(resolved,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Completed",len(resolved),"audio masters")

if __name__=="__main__":main()
