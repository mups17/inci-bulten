# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   İNCİ HOLDİNG — HAFTALIK İNTERAKTİF HTML RAPOR + OTOMATİK MAİL    ║
║   Colab'da çalıştır → HTML üret → Gmail ile yöneticilere gönder     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════
#  0. PAKET KURULUMU
# ══════════════════════════════════════════════════
import subprocess, sys
def pip(*a): subprocess.check_call([sys.executable,"-m","pip","install","-q",*a])
print("📦 Paketler yükleniyor...")
pip("numpy<2")
pip("huggingface_hub==0.20.3")
pip("feedparser","beautifulsoup4","requests","python-dateutil","deep-translator")
pip("torch==2.3.0+cpu","--index-url","https://download.pytorch.org/whl/cpu")
pip("sentence-transformers==2.6.1")
print("✅ Hazır.\n")

# ══════════════════════════════════════════════════
#  1. MAİL AYARLARI  ← BURAYA GİR
# ══════════════════════════════════════════════════
CONFIG = {
    "smtp_user":     "bulten@inceholding.com",
    "smtp_password": "xxxx xxxx xxxx xxxx",
    "recipients": [
        "yonetici1@inceholding.com",
        "yonetici2@inceholding.com",
    ],
    "save_html": True,
    "output_dir": "/content/exports",
}

# ══════════════════════════════════════════════════
#  2. SABİTLER
# ══════════════════════════════════════════════════
import os, re, time, json
from pathlib import Path
from datetime import datetime
from collections import Counter
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
import torch
from sentence_transformers import SentenceTransformer, util

Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)

SOURCES = {
    "techcrunch":    {"name":"TechCrunch",      "rss":"https://techcrunch.com/feed/"},
    "wired":         {"name":"Wired",           "rss":"https://www.wired.com/feed/rss"},
    "arstechnica":   {"name":"Ars Technica",    "rss":"https://feeds.arstechnica.com/arstechnica/index"},
    "venturebeat":   {"name":"VentureBeat",     "rss":"https://venturebeat.com/feed/"},
    "mittech":       {"name":"MIT Tech Review", "rss":"https://www.technologyreview.com/feed/"},
    "electrek":      {"name":"Electrek",        "rss":"https://electrek.co/feed/"},
    "ainews":        {"name":"AI News",         "rss":"https://www.artificialintelligence-news.com/feed/"},
    "thehackernews": {"name":"The Hacker News", "rss":"https://feeds.feedburner.com/TheHackersNews"},
    "bleepingcomp":  {"name":"BleepingComputer","rss":"https://www.bleepingcomputer.com/feed/"},
    "securityweek":  {"name":"SecurityWeek",    "rss":"https://www.securityweek.com/feed/"},
    "greenbiz":      {"name":"GreenBiz",        "rss":"https://www.greenbiz.com/rss.xml"},
    "cleantechnica": {"name":"CleanTechnica",   "rss":"https://cleantechnica.com/feed/"},
    "autonews":      {"name":"Automotive News", "rss":"https://www.autonews.com/rss.xml"},
    "logmgmt":       {"name":"Logistics Mgmt",  "rss":"https://www.logisticsmgmt.com/rss"},
    "mfg_tomorrow":  {"name":"Mfg Tomorrow",    "rss":"https://www.manufacturingtomorrow.com/rss.xml"},
    "webrazzi":      {"name":"Webrazzi",        "rss":"https://webrazzi.com/feed/"},
    "egirisim":      {"name":"eGirişim",        "rss":"https://egirisim.com/feed/"},
    "bthaber":       {"name":"BT Haber",        "rss":"https://www.bthaber.com/feed/"},
    "supplychain247":{"name":"Supply Chain 247","rss":"https://www.supplychain247.com/rss"},
    "cisa_alerts":   {"name":"CISA Alerts",     "rss":"https://www.cisa.gov/cybersecurity-advisories/all.xml"},
    "startupwatch":  {"name":"Startups Watch",  "rss":"https://startups.watch/feed"},
}
TR_SRC  = {"webrazzi","egirisim","bthaber"}
SEC_SRC = {"thehackernews","bleepingcomp","cisa_alerts","securityweek"}
CVE_RE  = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
SEC_KW  = ["cve","vulnerability","exploit","ransomware","data breach","malware",
           "siber saldırı","siber güvenlik","veri ihlali","zafiyet"]

COMPANIES = {
    "Maxion İnci":          {"s":"Otomotiv","c":"#C0392B","i":"🚗",
        "kw":["alüminyum jant","sac jant","wheel","rim","automotive manufacturing",
              "oem supplier","lightweight materials","auto parts","smart manufacturing"]},
    "Maxion Jantaş":        {"s":"Otomotiv","c":"#E74C3C","i":"🏗️",
        "kw":["ağır vasıta","ticari araç","kamyon jantı","steel wheel","commercial vehicle",
              "stamping","heavy duty trucks","fleet vehicles"]},
    "İnci GS Yuasa":        {"s":"Enerji","c":"#27AE60","i":"🔋",
        "kw":["akü","battery","enerji depolama","energy storage","lithium-ion",
              "bms","electric vehicle battery","ev charging","şarj istasyonu"]},
    "Vflow Tech":           {"s":"Enerji","c":"#2ECC71","i":"⚡",
        "kw":["vanadyum redoks","flow battery","şebeke dengeleme","redox flow",
              "microgrid","renewable grid","endüstriyel batarya"]},
    "İncitaş":              {"s":"Enerji","c":"#F39C12","i":"☀️",
        "kw":["güneş enerjisi","solar","mikroinverter","off-grid","fotovoltaik"]},
    "Yusen İnci Lojistik":  {"s":"Lojistik","c":"#8E44AD","i":"📦",
        "kw":["lojistik","logistics","tedarik zinciri","supply chain",
              "warehouse management","freight","last mile"]},
    "ISM Minibar":          {"s":"Soğutma","c":"#2980B9","i":"🏨",
        "kw":["minibar","absorbe soğutma","otel ekipmanları","hospitality tech",
              "hotel appliance","hotel room fridge","absorption fridge","silent cooling"]},
    "Starcool":             {"s":"Soğutma","c":"#3498DB","i":"❄️",
        "kw":["araç buzdolabı","karavan soğutma","portable fridge",
              "cold chain logistics","refrigerated transport","soğuk zincir",
              "reefer","refrigerated container","temperature controlled"]},
    "Vinci B.V.":           {"s":"Girişim","c":"#9B59B6","i":"🚀",
        "kw":["deep tech","b2b saas","corporate venture","endüstriyel iot",
              "startup investment","teknoloji yatırımı","sanayi girişimi",
              "endüstriyel startup","holding inovasyon"]},
    "İnci Holding (Genel)": {"s":"Girişim","c":"#8B1A1A","i":"🏢",
        "kw":["açık inovasyon","esg raporu","sürdürülebilirlik raporu",
              "stratejik ortaklık anlaşması","holding bünyesi","kurumsal girişim",
              "ar-ge yatırımı","inovasyon merkezi","teknoloji transfer"]},
}
SECTORS = {
    "Otomotiv": {"icon":"🚗","color":"#C0392B","companies":["Maxion İnci","Maxion Jantaş"]},
    "Enerji":   {"icon":"🔋","color":"#27AE60","companies":["İnci GS Yuasa","Vflow Tech","İncitaş"]},
    "Lojistik": {"icon":"📦","color":"#8E44AD","companies":["Yusen İnci Lojistik"]},
    "Soğutma":  {"icon":"❄️","color":"#2980B9","companies":["ISM Minibar","Starcool"]},
    "Girişim":  {"icon":"🚀","color":"#9B59B6","companies":["Vinci B.V.","İnci Holding (Genel)"]},
}

def norm(t): return re.sub(r"\s+", " ", (t or "").strip())
def pdate(s):
    try: return dtparser.parse(s)
    except: return datetime.now()
def get_sector(n):
    for s,d in SECTORS.items():
        if n in d["companies"]: return s
    return "Genel"

# ══════════════════════════════════════════════════
#  3. RSS ÇEKME
# ══════════════════════════════════════════════════
def fetch_rss(max_per=18):
    items, seen = [], set()
    print("📡 RSS kaynakları okunuyor...")
    for i,(key,info) in enumerate(SOURCES.items()):
        print(f"\r   {i+1}/{len(SOURCES)} — {info['name']:<25}", end="", flush=True)
        try:
            feed = feedparser.parse(info["rss"])
            for e in feed.entries[:max_per]:
                t = norm(e.get("title",""))
                u = (e.get("link","") or "").strip()
                if not t or not u or u in seen or len(t)<15: continue
                d = getattr(e,"summary","") or getattr(e,"description","") or ""
                if d: d = BeautifulSoup(d,"html.parser").get_text(" ",strip=True); d = norm(d)[:800]
                if len(d)<30 and "CVE" not in t: continue
                seen.add(u)
                full = f"{t} {d}"
                cves = list(set(CVE_RE.findall(full)))
                sec  = any(k in full.lower() for k in SEC_KW) or key in SEC_SRC
                items.append({"title":t,"description":d,"url":u,"source":info["name"],
                               "date":pdate(getattr(e,"published","") or "").strftime("%Y-%m-%d"),
                               "country":"Türkiye" if key in TR_SRC else "Global",
                               "cve_ids":",".join(cves),"is_security":bool(sec)})
            time.sleep(0.3)
        except: pass
    print(f"\r   ✅ {len(items)} kayıt çekildi.{' '*30}")
    return items

# ══════════════════════════════════════════════════
#  4. NLP ANALİZİ
# ══════════════════════════════════════════════════
def run_nlp(items, threshold=57.0):
    print("🧠 NLP modeli yükleniyor...")
    dev   = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=dev)
    names = list(COMPANIES.keys())
    ekw   = model.encode([" ".join(COMPANIES[c]["kw"]) for c in names], convert_to_tensor=True)
    esec  = model.encode([COMPANIES[c]["s"] for c in names],            convert_to_tensor=True)
    eneg  = model.encode([
        "telefon aksesuar oyun bitcoin kripto magazin siyaset reality show "
        "indirim kampanya kasko taksi tüketici moda güzellik yemek tarif "
        "best cars top 10 ranking review consumer guide listicle "
        "maga trump siyasi parti seçim celebrity gossip"
    ], convert_to_tensor=True)

    # Listicle / tüketici başlığı pre-filter
    LISTICLE_RE = re.compile(
        r"^(en iyi|top \d|best \d|\d+ .*(araç|car|ev|phone|ürün|product)|"
        r"inceleme|review:|test:|vs\.|karşılaştırma)",
        re.IGNORECASE
    )

    texts = [f"{i['title']} {i['description']}" for i in items]
    print("🔍 Haberler analiz ediliyor...")
    ne    = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
    skw   = util.cos_sim(ne, ekw); ssec = util.cos_sim(ne, esec); sneg = util.cos_sim(ne, eneg)
    mx,_  = torch.max(torch.stack([skw,ssec]), dim=0)
    MULTI_THRESH = 50.0   # ikincil sektör eşiği
    out   = []
    for idx, item in enumerate(items):
        it  = dict(item)
        # Birincil eşleşme — en iyi şirket
        bi  = torch.argmax(mx[idx]).item()
        raw = mx[idx][bi].item()
        ng  = sneg[idx][0].item()
        sem = ((raw+1)/2)*100
        bn  = names[bi]; cd = COMPANIES[bn]

        if ng >= raw*0.70 or LISTICLE_RE.match(item.get("title","")):
            it.update({"status":"trash","score":0,"sector":"","color":"#444","kw":"",
                       "sectors":[],"sector_colors":{}})
        elif sem < 56:
            it.update({"status":"unmatched","score":round(sem,1),"sector":"","color":"#444","kw":"",
                       "sectors":[],"sector_colors":{}})
        else:
            tl   = texts[idx].lower()
            hits = [k for k in cd["kw"] if (k in tl if " " in k else bool(re.search(rf"\b{re.escape(k)}\b",tl)))]
            kws  = min(100.0, len(hits)*25.0)
            hyb  = round(sem*0.75+kws*0.25, 1)

            if hyb < threshold:
                it.update({"status":"unmatched","score":hyb,"sector":"","color":"#444","kw":"",
                           "sectors":[],"sector_colors":{}})
            else:
                # Çoklu sektör: sem≥MULTI_THRESH VE en az 1 keyword hit zorunlu
                seen_sectors = {}
                for ci, cn in enumerate(names):
                    c_raw  = mx[idx][ci].item()
                    c_sem  = ((c_raw+1)/2)*100
                    if c_sem < MULTI_THRESH: continue
                    c_data = COMPANIES[cn]
                    c_hits = [k for k in c_data["kw"] if (k in tl if " " in k else bool(re.search(rf"\b{re.escape(k)}\b",tl)))]
                    if not c_hits: continue   # ← keyword zorunlu, salt semantik eşleşme kabul yok
                    c_kws  = min(100.0, len(c_hits)*25.0)
                    c_hyb  = c_sem*0.75 + c_kws*0.25
                    sn = c_data["s"]
                    if sn not in seen_sectors or c_hyb > seen_sectors[sn][0]:
                        seen_sectors[sn] = (c_hyb, c_data["c"])

                extra = sorted(seen_sectors.items(), key=lambda x: -x[1][0])
                all_sectors    = [s for s, _ in extra]
                sector_colors  = {s: v[1] for s, v in extra}
                primary_sector = cd["s"]
                primary_color  = cd["c"]
                # Birincil sektör keyword hit yoksa da listeye ekle (ana eşleşme korunur)
                if primary_sector not in all_sectors:
                    all_sectors    = [primary_sector] + all_sectors
                    sector_colors[primary_sector] = primary_color

                it.update({
                    "status":        "matched",
                    "score":         hyb,
                    "sector":        primary_sector,
                    "color":         primary_color,
                    "sectors":       all_sectors,
                    "sector_colors": sector_colors,
                    "kw":            ", ".join(hits[:5]) if hits else "Semantik Uyum"
                })

        out.append(it)

    matched = sum(1 for i in out if i["status"]=="matched")
    multi   = sum(1 for i in out if len(i.get("sectors",[])) > 1)
    print(f"   ✅ {matched} haber bültene girdi / {len(out)} toplam  ({multi} çoklu sektör)")
    return out

# ══════════════════════════════════════════════════
#  4b. ÇEVİRİ (Global haberler → Türkçe)
# ══════════════════════════════════════════════════
def translate_items(items):
    """NLP'den geçen yabancı dil haberlerini Türkçe'ye çevirir.
    - matched: başlık + açıklama
    - unmatched: sadece başlık (bülten dışı listesi için)
    """
    from deep_translator import GoogleTranslator
    to_translate = [i for i in items if i.get("country") != "Türkiye"
                    and i["status"] in ("matched", "unmatched")]
    if not to_translate:
        return items

    matched_cnt   = sum(1 for i in to_translate if i["status"]=="matched")
    unmatched_cnt = sum(1 for i in to_translate if i["status"]=="unmatched")
    print(f"🌐 Çevriliyor: {matched_cnt} bülten + {unmatched_cnt} bülten dışı...")
    translator = GoogleTranslator(source="auto", target="tr")

    ok = err = 0
    for item in to_translate:
        try:
            orig_title = item["title"]
            tr_title   = translator.translate(orig_title[:450])
            if not tr_title:
                raise ValueError("boş yanıt")

            item["title_orig"] = orig_title
            item["title"]      = tr_title
            item["translated"] = True

            if item["status"] == "matched":
                orig_desc = item.get("description", "") or ""
                tr_desc   = translator.translate(orig_desc[:450]) if orig_desc else ""
                item["description_orig"] = orig_desc
                item["description"]      = tr_desc

            ok += 1
            time.sleep(0.15)
        except Exception:
            item["translated"] = False
            err += 1

    print(f"   ✅ {ok} çevrildi{f', {err} hata' if err else ''}")
    return items



def build_report(items):
    matched   = [i for i in items if i["status"]=="matched"]
    unmatched = [i for i in items if i["status"]=="unmatched"]
    sec_items = [i for i in items if i.get("is_security") or i.get("cve_ids")]
    trash_cnt = sum(1 for i in items if i["status"]=="trash")
    week      = datetime.now().isocalendar()[1]
    date_str  = datetime.now().strftime("%d %B %Y")
    avg_sc    = round(sum(i["score"] for i in matched)/max(len(matched),1), 1)

    # Sektör sayımı — bir haber birden fazla sektörde sayılabilir
    sec_counts = {}
    for sn in SECTORS:
        sec_counts[sn] = sum(1 for i in matched if sn in i.get("sectors", [i.get("sector","")]))
    sec_max    = max(sec_counts.values()) if sec_counts else 1

    kw_all = []
    for i in matched:
        kw_all.extend([k.strip() for k in (i.get("kw","") or "").split(",") if k.strip() and k.strip()!="Semantik Uyum"])
    top_kw = Counter(kw_all).most_common(10)

    data_js = json.dumps(items, ensure_ascii=False)

    def _safe_id(name):
        out = ""
        for c in name:
            out += "_" if c in " .()\u0130" else c
        return out

    def _sc_color(sc):
        if sc >= 70: return "#27AE60"
        if sc >= 60: return "#F39C12"
        return "#E74C3C"

    # -- Sector pills (sidebar) --
    sector_pills_html = ""
    for sn, sdata in SECTORS.items():
        cnt = sec_counts.get(sn, 0)
        if cnt == 0:
            continue
        comp_names = ", ".join(sdata["companies"])
        sector_pills_html += (
            '<div class="filt-pill" onclick="toggleSector(\'' + sn + '\')" id="spill-' + sn + '">' +
            '<div><span class="pill-sector-name">' + sdata["icon"] + " " + sn + '</span>' +
            '<span class="pill-companies">(' + comp_names + ')</span></div>' +
            '<span class="filt-cnt">' + str(cnt) + '</span></div>'
        )

    # -- Sectors pane --
    sectors_pane_html = ""
    for sn, sdata in SECTORS.items():
        if sec_counts.get(sn, 0) == 0:
            continue
        # Haberi birincil veya ikincil sektöründe göster
        sn_items = [i for i in matched if sn in i.get("sectors", [i.get("sector","")])][:12]
        rows = ""
        for idx, it in enumerate(sn_items):
            cc = _sc_color(it["score"])
            t  = it["title"][:65] + ("..." if len(it["title"]) > 65 else "")
            rows += (
                "<tr>" +
                '<td style="color:var(--t4)">' + str(idx+1) + "</td>" +
                '<td><a href="' + it["url"] + '" target="_blank">' + t + "</a></td>" +
                "<td>" + it["source"] + "</td>" +
                '<td style="color:' + cc + ';font-weight:700">' + str(int(it["score"])) + "</td>" +
                '<td style="color:var(--t4)">' + it["date"] + "</td>" +
                "</tr>"
            )
        sectors_pane_html += (
            '<div class="sector-block">' +
            '<div class="sector-hdr" style="border-left:3px solid ' + sdata["color"] + '">' +
            '<span style="font-size:18px">' + sdata["icon"] + "</span>" +
            '<span class="sector-hdr-name">' + sn + "</span>" +
            '<span class="sector-badge" style="background:' + sdata["color"] + '">' + str(sec_counts.get(sn,0)) + "</span></div>" +
            '<table class="stbl"><tr><th>#</th><th>Başlık</th><th>Kaynak</th><th>Skor</th><th>Tarih</th></tr>' +
            rows + "</table></div>"
        )

    # -- Kartlar --
    cards_html = ""
    for item in matched:
        col = item["color"]; sc = item["score"]
        cc  = "#27AE60" if sc>=70 else ("#F39C12" if sc>=60 else "#E74C3C")
        cl  = "Çok Yüksek" if sc>=70 else ("Yüksek" if sc>=60 else "Orta")
        desc = (item.get("description","") or "")[:280]
        if len(item.get("description","") or "")>280: desc+="..."
        kwtags = "".join(f'<span class="kwtag">{k.strip()}</span>' for k in (item.get("kw","") or "").split(",")[:4] if k.strip())
        sec_tag  = '<span class="sectag">🔒 Güvenlik</span>' if item.get("is_security") else ""
        trl_tag  = '<span class="trltag">🌐 Çeviri</span>' if item.get("translated") else ""
        orig_ttl = item.get("title_orig","")
        title_attr = f' title="🌐 Orijinal: {orig_ttl}"' if orig_ttl else ""

        # Çoklu sektör etiketleri
        all_secs = item.get("sectors") or ([item.get("sector")] if item.get("sector") else [])
        sc_colors = item.get("sector_colors") or {item.get("sector",""):item.get("color","#444")}
        sector_tags = "".join(
            f'<span class="comptag" style="border-color:{sc_colors.get(s, col)};color:{sc_colors.get(s, col)}">{s}</span>'
            for s in all_secs if s
        )
        data_sectors = ",".join(all_secs)

        cards_html += f"""
        <div class="card" data-sector="{item.get('sector','')}" data-sectors="{data_sectors}" data-score="{sc}" data-date="{item.get('date','')}" data-src="{item.get('source','')}">
          <div class="card-inner">
            <div class="card-accent" style="background:{col}"></div>
            <div class="card-body">
              <a class="card-title" href="{item['url']}" target="_blank"{title_attr}>{item['title']}</a>
              <p class="card-desc">{desc}</p>
              <div class="card-tags">
                {sector_tags}
                {kwtags}{sec_tag}{trl_tag}
              </div>
            </div>
            <div class="card-score">
              <div class="score-num" style="color:{cc}">{int(sc)}</div>
              <div class="score-lbl">SKOR</div>
              <div class="score-bar"><div class="score-fill" style="width:{sc}%;background:{cc}"></div></div>
              <div class="conf-lbl" style="color:{cc}">{cl}</div>
            </div>
          </div>
          <div class="card-foot">
            <span>{item.get('source','')} · {item.get('country','')}</span>
            <span>{item.get('date','')}</span>
          </div>
        </div>"""

    # -- Güvenlik kartları --
    sec_html = ""
    for item in sec_items[:10]:
        bc = "#E74C3C" if item.get("cve_ids") else "#8E44AD"
        sec_html += f"""
        <div class="sec-card" style="border-left-color:{bc}">
          {'<span class="cve-tag">'+item["cve_ids"][:40]+'</span>' if item.get("cve_ids") else ''}
          <a class="sec-title" href="{item['url']}" target="_blank">{item['title']}</a>
          <div class="sec-meta">{item['source']} · {item.get('date','')}</div>
        </div>"""

    # -- Bülten dışı --
    um_rows = []
    for i in sorted(unmatched, key=lambda x: x.get("score",0), reverse=True)[:25]:
        ttl   = i["title"][:88] + ("..." if len(i["title"])>88 else "")
        orig  = i.get("title_orig","")
        tip   = (' title="🌐 Orijinal: ' + orig + '"') if orig else ""
        badge = '<span class="trltag" style="font-size:9px;padding:1px 5px">🌐</span>' if i.get("translated") else ""
        um_rows.append('<div class="um-row"><a href="' + i["url"] + '" target="_blank" class="um-title"' + tip + '>' + ttl + '</a>' + badge + '<span class="um-src">' + i["source"] + '</span></div>')
    um_html = "\n".join(um_rows)

    security_pane_html = sec_html if sec_html else '<div class="empty"><div class="empty-icon">🔒</div><p>Bu taramada güvenlik haberi bulunamadı.</p></div>'
    outside_pane_html  = ('<div style="background:var(--s1);border:1px solid var(--b1);border-radius:3px;overflow:hidden">' + um_html + "</div>") if um_html else '<div class="empty"><div class="empty-icon">🌍</div><p>Bülten dışı temiz haber bulunamadı.</p></div>'

    # -- Donut chart --
    import math
    donut_r = 52; donut_cx = 70; donut_cy = 70; donut_stroke = 16
    donut_circ = 2 * math.pi * donut_r
    total_matched = max(len(matched), 1)
    donut_svg = ""
    offset = 0.0
    sector_list = [(sn, SECTORS[sn], sec_counts.get(sn,0)) for sn in SECTORS if sec_counts.get(sn,0)>0]
    for sn, sdata, cnt in sector_list:
        frac = cnt / total_matched
        dash = round(frac * donut_circ, 2)
        gap  = round(donut_circ - dash, 2)
        rotate = round(offset * 360 / total_matched - 90, 2)
        donut_svg += (
            '<circle cx="' + str(donut_cx) + '" cy="' + str(donut_cy) + '" r="' + str(donut_r) + '" fill="none"' +
            ' stroke="' + sdata["color"] + '" stroke-width="' + str(donut_stroke) + '"' +
            ' stroke-dasharray="' + str(dash) + ' ' + str(gap) + '"' +
            ' transform="rotate(' + str(rotate) + ' ' + str(donut_cx) + ' ' + str(donut_cy) + ')"' +
            ' opacity="0.9"/>'
        )
        offset += cnt
    donut_legend = ""
    for sn, sdata, cnt in sector_list:
        pct = round(cnt/total_matched*100)
        donut_legend += (
            '<div class="donut-leg-row">' +
            '<span class="donut-leg-dot" style="background:' + sdata["color"] + '"></span>' +
            '<span class="donut-leg-name">' + sdata["icon"] + " " + sn + '</span>' +
            '<span class="donut-leg-pct">' + str(pct) + '%</span>' +
            '</div>'
        )

    # -- Bar chart --
    bar_svg = ""
    bar_w, bar_h = 340, 160
    bar_pad_l, bar_pad_b = 80, 28
    bar_inner_w = bar_w - bar_pad_l - 20
    bar_inner_h = bar_h - bar_pad_b - 10
    for si, (sname, sdata) in enumerate(SECTORS.items()):
        cnt = sec_counts.get(sname, 0)
        bw  = int((cnt / sec_max) * bar_inner_w) if sec_max > 0 else 0
        y   = 10 + si * (bar_inner_h // len(SECTORS))
        bh  = max(12, bar_inner_h // len(SECTORS) - 5)
        bar_svg += f"""
        <text x="{bar_pad_l-8}" y="{y+bh//2+4}" text-anchor="end" fill="#666" font-size="11" font-family="Outfit,sans-serif">{sdata['icon']} {sname}</text>
        <rect x="{bar_pad_l}" y="{y}" width="{bw}" height="{bh}" rx="2" fill="{sdata['color']}" opacity="0.85"/>
        <text x="{bar_pad_l+bw+6}" y="{y+bh//2+4}" fill="{sdata['color']}" font-size="11" font-family="Outfit,sans-serif" font-weight="600">{cnt}</text>"""

    # -- Keyword bars --
    kw_bars = ""
    if top_kw:
        kw_max = top_kw[0][1]
        for ki, (kword, kcnt) in enumerate(top_kw[:8]):
            pw = int((kcnt/kw_max)*100)
            kw_bars += f"""
            <div class="kw-row">
              <span class="kw-label">{kword}</span>
              <div class="kw-track"><div class="kw-fill" style="width:{pw}%"></div></div>
              <span class="kw-cnt">{kcnt}</span>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>İnci Holding — Hafta {week} Teknoloji Bülteni</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,700;0,800;1,700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  /* Palette — sıcak koyu, kırmızı aksan */
  --bg:#0D0B0A;--s1:#131110;--s2:#1A1816;--s3:#222;
  --b1:#242120;--b2:#2E2B29;--b3:#3D3A37;
  --red:#922020;--red2:#C0392B;--red-dim:rgba(146,32,32,.12);
  --text:#EDE5DA;--t2:#9C9189;--t3:#5C534C;--t4:#302C2A;
  --green:#2E9E68;--amber:#D4841A;--blue:#3A7FBF;
  --num-font:400 13px/1 'Outfit',sans-serif;
}}
html,body{{min-height:100%;background:var(--bg);color:var(--text);
  font-family:'Outfit',sans-serif;font-size:14px;line-height:1.55;
  font-weight:400;-webkit-font-smoothing:antialiased}}
a{{color:inherit;text-decoration:none}}
::-webkit-scrollbar{{width:3px}}
::-webkit-scrollbar-thumb{{background:var(--red);border-radius:2px}}

/* ── HERO ── */
.hero{{
  position:relative;overflow:hidden;
  background:radial-gradient(ellipse 80% 60% at 20% 50%,#1A0A0A 0%,var(--bg) 70%);
  border-bottom:1px solid var(--b1);padding:52px 64px 44px;
}}
.hero::after{{
  content:'';position:absolute;inset:0;
  background:
    radial-gradient(circle at 75% 30%, rgba(146,32,32,.07) 0%, transparent 55%),
    repeating-linear-gradient(0deg,transparent,transparent 59px,rgba(146,32,32,.04) 59px,rgba(146,32,32,.04) 60px),
    repeating-linear-gradient(90deg,transparent,transparent 59px,rgba(146,32,32,.04) 59px,rgba(146,32,32,.04) 60px);
  pointer-events:none;
}}
.hero-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap;position:relative;z-index:1}}
.logo-group{{display:flex;align-items:center;gap:16px}}
.logo-mark{{width:4px;height:52px;background:linear-gradient(180deg,var(--red2),var(--red));border-radius:2px;flex-shrink:0}}
.logo-text{{font-family:'Playfair Display',serif;font-size:30px;font-weight:800;letter-spacing:3px;color:#FFF;line-height:1.1}}
.logo-sub{{font-size:10px;color:var(--t3);letter-spacing:4px;text-transform:uppercase;margin-top:5px;font-weight:500}}
.hero-meta{{text-align:right;position:relative;z-index:1}}
.hero-week{{font-family:'Playfair Display',serif;font-size:48px;font-weight:800;font-style:italic;
  color:rgba(146,32,32,.25);line-height:1;letter-spacing:-1px}}
.hero-date{{font-size:11px;color:var(--t3);letter-spacing:2px;text-transform:uppercase;margin-top:4px}}

/* ── KPI STRIP ── */
.kpi-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--b1);border-bottom:1px solid var(--b1)}}
.kpi{{background:var(--s1);padding:20px 22px}}
.kpi-lbl{{font-size:9px;color:var(--t3);letter-spacing:2.5px;text-transform:uppercase;font-weight:600;margin-bottom:8px}}
.kpi-val{{font-size:28px;font-weight:300;line-height:1;letter-spacing:-1px}}
.kpi-sub{{font-size:10px;color:var(--t3);margin-top:4px;font-weight:400}}

/* ── LAYOUT ── */
.wrap{{max-width:1320px;margin:0 auto;padding:0 36px}}
.main-grid{{display:grid;grid-template-columns:1fr 300px;gap:40px;padding:36px 0}}

/* ── TABS ── */
.tab-bar{{display:flex;gap:0;border-bottom:1px solid var(--b1);margin-bottom:28px}}
.tbtn{{background:none;border:none;color:var(--t3);padding:11px 22px;cursor:pointer;
  font-family:'Outfit',sans-serif;font-size:12px;font-weight:500;letter-spacing:1px;
  text-transform:uppercase;border-bottom:2px solid transparent;transition:all .2s}}
.tbtn:hover{{color:var(--t2)}}
.tbtn.on{{color:var(--text);border-bottom-color:var(--red2)}}

/* ── CONTROLS ── */
.controls{{display:flex;gap:10px;align-items:center;margin-bottom:24px;flex-wrap:wrap}}
.ctrl-input{{background:var(--s2);border:1px solid var(--b2);color:var(--text);
  padding:9px 16px;border-radius:4px;font-family:'Outfit',sans-serif;
  font-size:13px;width:220px;outline:none;transition:border-color .2s;font-weight:400}}
.ctrl-input:focus{{border-color:var(--red2)}}
.ctrl-input::placeholder{{color:var(--t3)}}
.ctrl-sel{{background:var(--s2);border:1px solid var(--b2);color:var(--t2);
  padding:9px 14px;border-radius:4px;font-family:'Outfit',sans-serif;
  font-size:13px;outline:none;cursor:pointer}}
.ctrl-sel:focus{{border-color:var(--red2)}}
.count-pill{{font-size:11px;color:var(--t3);letter-spacing:1px;text-transform:uppercase;font-weight:600;
  padding:6px 14px;background:var(--s2);border-radius:4px;border:1px solid var(--b1)}}

/* ── CARDS ── */
.card{{background:var(--s1);border:1px solid var(--b1);border-radius:6px;
  margin-bottom:10px;overflow:hidden;transition:border-color .25s,box-shadow .25s;
  animation:fu .4s ease both}}
.card:hover{{border-color:var(--b3);box-shadow:0 4px 24px rgba(0,0,0,.35)}}
@keyframes fu{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.card-inner{{display:flex;align-items:stretch}}
.card-accent{{width:3px;flex-shrink:0;border-radius:6px 0 0 0}}
.card-body{{flex:1;padding:16px 20px;min-width:0}}
.card-title{{font-size:14px;font-weight:600;line-height:1.5;margin-bottom:7px;
  display:block;color:var(--text);transition:color .2s}}
.card-title:hover{{color:#FFF}}
.card-desc{{font-size:12px;color:var(--t2);line-height:1.7;margin-bottom:12px;font-weight:400}}
.card-tags{{display:flex;flex-wrap:wrap;gap:5px}}
.comptag{{border:1px solid;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;
  background:rgba(255,255,255,.03);letter-spacing:.3px;text-transform:uppercase}}
.kwtag{{background:var(--s2);color:var(--t3);border:1px solid var(--b2);
  border-radius:20px;padding:2px 9px;font-size:10px;font-weight:400}}
.sectag{{background:#1C0808;color:#E05252;border:1px solid #3A1010;
  border-radius:20px;padding:3px 10px;font-size:10px;font-weight:500}}
.trltag{{background:#0C1620;color:#5B9FD4;border:1px solid #1A3050;
  border-radius:20px;padding:3px 10px;font-size:10px;font-weight:500;cursor:help}}
.card-score{{flex-shrink:0;padding:16px 20px;text-align:right;border-left:1px solid var(--b1);
  display:flex;flex-direction:column;align-items:flex-end;justify-content:center;min-width:84px;gap:5px}}
.score-num{{font-size:30px;font-weight:300;line-height:1;letter-spacing:-1.5px}}
.score-lbl{{font-size:9px;color:var(--t3);letter-spacing:2px;text-transform:uppercase;font-weight:600}}
.score-bar{{width:56px;height:2px;background:var(--b2);border-radius:2px;overflow:hidden}}
.score-fill{{height:100%;border-radius:2px;transition:width .6s cubic-bezier(.4,0,.2,1)}}
.conf-lbl{{font-size:10px;font-weight:500;color:var(--t3)}}
.card-foot{{display:flex;justify-content:space-between;padding:8px 20px;
  background:var(--s2);font-size:11px;color:var(--t3);border-top:1px solid var(--b1);font-weight:400}}

.hidden{{display:none!important}}

/* ── SIDEBAR ── */
.sidebar{{position:sticky;top:20px;align-self:start;display:flex;flex-direction:column;gap:16px}}
.side-box{{background:var(--s1);border:1px solid var(--b1);border-radius:6px;overflow:hidden}}
.side-head{{padding:13px 18px;border-bottom:1px solid var(--b1);font-size:9px;color:var(--t3);
  letter-spacing:2.5px;text-transform:uppercase;font-weight:700;
  display:flex;justify-content:space-between;align-items:center}}
.clear-btn{{color:var(--red2);cursor:pointer;font-size:10px;font-weight:500;letter-spacing:.5px;transition:color .2s}}
.clear-btn:hover{{color:#E05252}}
.side-body{{padding:10px 0}}
.pill-sector-name{{font-size:12px;font-weight:500;display:block}}
.pill-companies{{font-size:10px;color:var(--t4);display:block;margin-top:2px;font-style:italic}}
.filt-pill{{display:flex;align-items:center;justify-content:space-between;
  padding:8px 16px;cursor:pointer;transition:all .15s;
  font-size:12px;color:var(--t3);border-left:2px solid transparent}}
.filt-pill:hover{{background:var(--s2);color:var(--t2)}}
.filt-pill.on{{border-left-color:var(--red2);background:var(--red-dim);color:var(--text);font-weight:500}}
.filt-cnt{{font-size:11px;color:var(--t4);font-weight:600}}
.filt-pill.on .filt-cnt{{color:var(--t2)}}

/* ── CHART BOXES ── */
.chart-box{{padding:16px}}
.kw-row{{display:flex;align-items:center;gap:10px;margin-bottom:9px}}
.kw-label{{font-size:11px;color:var(--t2);width:108px;flex-shrink:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:400}}
.kw-track{{flex:1;height:3px;background:var(--b2);border-radius:2px;overflow:hidden}}
.kw-fill{{height:100%;background:var(--red2);border-radius:2px;transition:width .4s}}
.kw-cnt{{font-size:11px;color:var(--t3);font-weight:600;width:20px;text-align:right}}
.donut-wrap{{display:flex;align-items:center;gap:16px}}
.donut-svg{{width:96px;height:96px;flex-shrink:0}}
.donut-legend{{flex:1}}
.donut-leg-row{{display:flex;align-items:center;gap:7px;margin-bottom:7px}}
.donut-leg-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.donut-leg-name{{font-size:11px;color:var(--t2);flex:1;font-weight:400}}
.donut-leg-pct{{font-size:11px;color:var(--t3);font-weight:600}}

/* ── SEKTÖR TABLOSU ── */
.sector-block{{margin-bottom:28px}}
.sector-hdr{{display:flex;align-items:center;gap:10px;padding:11px 16px;
  border-radius:6px 6px 0 0;background:var(--s2);border:1px solid var(--b1);border-bottom:none}}
.sector-hdr-name{{font-size:13px;font-weight:600;flex:1;letter-spacing:.2px}}
.sector-badge{{border-radius:20px;padding:2px 11px;font-size:11px;font-weight:700;color:#FFF}}
.stbl{{width:100%;border-collapse:collapse;font-size:12px;border:1px solid var(--b1);border-top:none;border-radius:0 0 6px 6px;overflow:hidden}}
.stbl th{{background:var(--s2);color:var(--t3);padding:8px 12px;text-align:left;font-weight:600;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--b1)}}
.stbl td{{padding:9px 12px;border-bottom:1px solid var(--b1);color:var(--t2)}}
.stbl tr:last-child td{{border-bottom:none}}
.stbl tr:hover td{{background:var(--s2);color:var(--text)}}
.stbl td a:hover{{color:#FFF}}

/* ── GÜVENLİK ── */
.sec-card{{background:var(--s1);border:1px solid var(--b2);border-left:3px solid #C0392B;
  border-radius:6px;padding:14px 18px;margin-bottom:9px}}
.cve-tag{{background:#1C0808;color:#E05252;border:1px solid #3A1010;
  border-radius:20px;padding:2px 10px;font-size:10px;font-weight:600;
  display:inline-block;margin-bottom:6px;letter-spacing:.5px}}
.sec-title{{font-size:13px;font-weight:600;color:var(--text);display:block;margin-bottom:4px}}
.sec-title:hover{{color:#FFF}}
.sec-meta{{font-size:11px;color:var(--t3);font-weight:400}}

/* ── BÜLTEN DIŞI ── */
.um-row{{display:flex;align-items:center;gap:10px;padding:10px 18px;border-bottom:1px solid var(--b1)}}
.um-row:last-child{{border-bottom:none}}
.um-title{{flex:1;font-size:12px;color:var(--t2);font-weight:400}}
.um-title:hover{{color:var(--text)}}
.um-src{{font-size:10px;color:var(--t4);white-space:nowrap;font-weight:600;letter-spacing:.5px;text-transform:uppercase}}
.empty{{text-align:center;padding:80px 20px;color:var(--t4)}}
.empty-icon{{font-size:36px;opacity:.25;margin-bottom:14px}}

/* ── FOOTER ── */
.footer{{border-top:1px solid var(--b1);padding:22px 36px;display:flex;justify-content:space-between;
  align-items:center;background:var(--s1);margin-top:48px}}
.footer-l{{font-size:11px;color:var(--t4);font-weight:500;letter-spacing:.3px}}
.footer-r{{font-size:11px;color:var(--t4)}}

@media(max-width:900px){{
  .main-grid{{grid-template-columns:1fr}}
  .sidebar{{position:static}}
  .kpi-grid{{grid-template-columns:repeat(3,1fr)}}
  .wrap{{padding:0 18px}}
  .hero{{padding:36px 22px 32px}}
}}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-top">
    <div class="logo-group">
      <div class="logo-mark"></div>
      <div>
        <div class="logo-text">İNCİ HOLDİNG</div>
        <div class="logo-sub">STRATEJİK TEKNOLOJİ &amp; İNOVASYON BÜLTENİ</div>
      </div>
    </div>
    <div class="hero-meta">
      <div class="hero-week">W{week}</div>
      <div class="hero-date">{date_str}</div>
    </div>
  </div>
</div>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-lbl">TARANAN KAYNAK</div><div class="kpi-val" style="color:var(--text)">{len(SOURCES)}</div><div class="kpi-sub">RSS beslemesi</div></div>
  <div class="kpi"><div class="kpi-lbl">İNCELENEN KAYIT</div><div class="kpi-val" style="color:var(--text)">{len(items)}</div><div class="kpi-sub">pre-filter geçen</div></div>
  <div class="kpi"><div class="kpi-lbl">BÜLTENE GİREN</div><div class="kpi-val" style="color:var(--green)">{len(matched)}</div><div class="kpi-sub">NLP onaylı</div></div>
  <div class="kpi"><div class="kpi-lbl">BÜLTEN DIŞI</div><div class="kpi-val" style="color:var(--amber)">{len(unmatched)}</div><div class="kpi-sub">temiz ama eşleşmez</div></div>
  <div class="kpi"><div class="kpi-lbl">ÇÖPE ATILAN</div><div class="kpi-val" style="color:var(--red)">{trash_cnt}</div><div class="kpi-sub">B2C / magazin</div></div>
  <div class="kpi"><div class="kpi-lbl">ORT. UYUM SKORU</div><div class="kpi-val" style="color:var(--text)">{avg_sc}</div><div class="kpi-sub">0–100 arası</div></div>
</div>
<div class="wrap">
  <div class="main-grid">
    <div>
      <div class="tab-bar">
        <button class="tbtn on" onclick="switchTab('bulletin',this)">📋 BÜLTEN</button>
        <button class="tbtn" onclick="switchTab('sectors',this)">🗂 SEKTÖRLER</button>
        <button class="tbtn" onclick="switchTab('security',this)">🔒 SİBER GÜVENLİK</button>
        <button class="tbtn" onclick="switchTab('outside',this)">🌍 BÜLTEN DIŞI</button>
      </div>
      <div class="controls" id="mainControls">
        <input class="ctrl-input" type="text" id="searchBox" placeholder="🔍  Ara..." oninput="applyFilters()">
        <select class="ctrl-sel" id="sortSel" onchange="applyFilters()">
          <option value="score">Skora Göre</option>
          <option value="date">Tarihe Göre</option>
          <option value="source">Kaynağa Göre</option>
        </select>
        <span class="count-pill" id="countPill">{len(matched)} haber</span>
      </div>
      <div id="pane-bulletin"><div id="cards-container">{cards_html}</div></div>
      <div id="pane-sectors" class="hidden">{sectors_pane_html}</div>
      <div id="pane-security" class="hidden">{security_pane_html}</div>
      <div id="pane-outside" class="hidden">{outside_pane_html}</div>
    </div>
    <div class="sidebar">
      <div class="side-box">
        <div class="side-head">SEKTÖR FİLTRESİ <span class="clear-btn" onclick="clearSectors()">temizle</span></div>
        <div class="side-body">{sector_pills_html}</div>
      </div>
      <div class="side-box">
        <div class="side-head">SEKTÖR DAĞILIMI</div>
        <div class="chart-box donut-wrap">
          <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg" class="donut-svg">
            <circle cx="70" cy="70" r="52" fill="none" stroke="#1E1E1E" stroke-width="16"/>
            {donut_svg}
            <text x="70" y="66" text-anchor="middle" fill="#EDE5DA" font-family="Outfit,sans-serif" font-size="18" font-weight="300">{len(matched)}</text>
            <text x="70" y="80" text-anchor="middle" fill="#5C534C" font-family="Outfit,sans-serif" font-size="9">haber</text>
          </svg>
          <div class="donut-legend">{donut_legend}</div>
        </div>
      </div>
      <div class="side-box">
        <div class="side-head">ÖNCÜ TERİMLER</div>
        <div class="chart-box">{kw_bars if kw_bars else '<p style="color:var(--t4);font-size:11px">Veri yok.</p>'}</div>
      </div>
    </div>
  </div>
</div>
<div class="footer">
  <div class="footer-l">İnci Holding © {datetime.now().year} · AI Destekli Stratejik Bülten · Hafta {week}</div>
  <div class="footer-r" style="color:var(--t4);font-size:10px">Otomatik üretildi · {datetime.now().strftime('%d.%m.%Y %H:%M')} · {len(SOURCES)} kaynak</div>
</div>
<script>
let activeSectors = new Set();
let currentTab    = 'bulletin';
function eid(id){{ return document.getElementById(id); }}
function qsa(sel){{ return document.querySelectorAll(sel); }}
function switchTab(tab, btn) {{
  currentTab = tab;
  qsa('.tbtn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  ['bulletin','sectors','security','outside'].forEach(p => {{
    eid('pane-'+p).classList.toggle('hidden', p !== tab);
  }});
  eid('mainControls').style.display = tab === 'bulletin' ? 'flex' : 'none';
  if (tab === 'bulletin') applyFilters();
}}
function applyFilters() {{
  const q    = (eid('searchBox').value || '').toLowerCase();
  const sort = eid('sortSel').value;
  let cards  = Array.from(qsa('.card'));
  let visible = 0;
  cards.forEach(card => {{
    const cardSectors = (card.dataset.sectors || card.dataset.sector || '').split(',').filter(Boolean);
    const sectorOk = activeSectors.size === 0 || cardSectors.some(s => activeSectors.has(s));
    const ok = sectorOk && (!q || card.textContent.toLowerCase().includes(q));
    card.classList.toggle('hidden', !ok);
    if (ok) visible++;
  }});
  eid('countPill').textContent = visible + ' haber';
  const container = eid('cards-container');
  const visCards  = cards.filter(c => !c.classList.contains('hidden'));
  visCards.sort((a, b) => {{
    if (sort === 'score')  return parseFloat(b.dataset.score)  - parseFloat(a.dataset.score);
    if (sort === 'date')   return (b.dataset.date  || '').localeCompare(a.dataset.date  || '');
    if (sort === 'source') return (a.dataset.src   || '').localeCompare(b.dataset.src   || '');
    return 0;
  }});
  visCards.forEach(c => container.appendChild(c));
}}
function toggleSector(s) {{
  const el = eid('spill-' + s);
  if (activeSectors.has(s)) {{ activeSectors.delete(s); el.classList.remove('on'); }}
  else {{ activeSectors.add(s); el.classList.add('on'); }}
  applyFilters();
}}
function clearSectors() {{
  activeSectors.clear();
  qsa('.filt-pill').forEach(p => p.classList.remove('on'));
  applyFilters();
}}
applyFilters();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════
#  6. MAİL GÖNDERİMİ
# ══════════════════════════════════════════════════
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders

def send_email(html_report: str, html_filename: str):
    cfg = CONFIG
    week = datetime.now().isocalendar()[1]
    date_str = datetime.now().strftime("%d %B %Y")
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"İnci Holding | Hafta {week} Teknoloji & İnovasyon Bülteni | {date_str}"
    msg["From"]    = cfg["smtp_user"]
    msg["To"]      = ", ".join(cfg["recipients"])
    body_html = f"""<html><head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F4F0EB;font-family:Georgia,serif">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F0EB;padding:32px 0">
    <tr><td align="center">
    <table width="620" cellpadding="0" cellspacing="0" style="background:#FFF;border-radius:2px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.08)">
      <tr><td style="background:#0A0A0A;padding:32px 40px">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td><div style="width:5px;height:36px;background:#8B1A1A;border-radius:1px;display:inline-block;vertical-align:middle;margin-right:14px"></div>
            <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#FFF;letter-spacing:2px;vertical-align:middle">İNCİ HOLDİNG</span>
            <div style="font-size:10px;color:#444;letter-spacing:3px;margin-top:4px;margin-left:19px">STRATEJİK TEKNOLOJİ BÜLTENİ</div>
          </td>
          <td align="right">
            <div style="font-size:36px;font-weight:700;color:rgba(139,26,26,.35);font-family:Georgia,serif;line-height:1">W{week}</div>
            <div style="font-size:11px;color:#444;margin-top:2px">{date_str}</div>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="background:#8B1A1A;padding:18px 40px;text-align:center">
        <p style="color:rgba(255,255,255,.7);font-size:12px;margin:0 0 10px">Tam interaktif rapor ekte — tarayıcıda açın</p>
        <p style="color:#FFF;font-size:13px;margin:0;font-weight:600">Filtreleme · Arama · Sektör Görünümleri · Siber Güvenlik · Trend Analizi</p>
      </td></tr>
      <tr><td style="padding:32px 40px">
        <p style="font-size:15px;color:#1A1A1A;line-height:1.7;margin:0 0 20px">Sayın yöneticimiz,</p>
        <p style="font-size:14px;color:#444;line-height:1.8;margin:0 0 24px">
          Bu hafta <strong>{len(SOURCES)}</strong> kaynak tarandı.
          NLP motoru onaylı haberler ekli interaktif raporda sektör bazlı ayrıştırılmış olarak sunulmaktadır.
        </p>
        <div style="background:#F9F5F0;border-left:4px solid #8B1A1A;padding:16px 20px;margin-bottom:24px;border-radius:0 2px 2px 0">
          <p style="font-size:12px;color:#666;margin:0 0 8px;letter-spacing:1.5px;font-family:monospace">RAPORUN İÇERİĞİ</p>
          <ul style="color:#1A1A1A;font-size:13px;line-height:2;margin:0;padding-left:18px">
            <li>Şirket &amp; sektör bazlı filtreli haber akışı</li>
            <li>NLP uyum skoru ve güven seviyesi</li>
            <li>Sektör trend barları ve öncü terim analizi</li>
            <li>Siber güvenlik ve CVE bildirimleri</li>
            <li>Bülten dışı genel teknoloji gündemi</li>
          </ul>
        </div>
        <p style="font-size:12px;color:#999;line-height:1.7;margin:0">
          Ekteki <strong>.html</strong> dosyasını herhangi bir tarayıcıda açın.<br>
          İnternet bağlantısı gerekmez, tüm veriler dosya içindedir.
        </p>
      </td></tr>
      <tr><td style="background:#F4F0EB;padding:20px 40px;border-top:1px solid #EEE">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:10px;color:#AAA;font-family:monospace">İnci Holding © {datetime.now().year}</td>
          <td align="right" style="font-size:10px;color:#AAA">Otomatik üretildi · {datetime.now().strftime('%d.%m.%Y %H:%M')}</td>
        </tr></table>
      </td></tr>
    </table></td></tr></table>
    </body></html>"""
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    part = MIMEBase("application", "octet-stream")
    part.set_payload(html_report.encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{html_filename}"')
    msg.attach(part)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(cfg["smtp_user"], cfg["smtp_password"])
            srv.sendmail(cfg["smtp_user"], cfg["recipients"], msg.as_string())
        print(f"  ✅ Mail gönderildi → {', '.join(cfg['recipients'])}")
        return True
    except Exception as e:
        print(f"  ⚠️  Mail gönderilemedi: {e}")
        print("  💡 Gmail → Ayarlar → Güvenlik → 'Uygulama Şifreleri' → 16 haneli şifre gir")
        return False

# ══════════════════════════════════════════════════
#  7. ÇALIŞTIR
# ══════════════════════════════════════════════════
import base64, os

# Ortam tespiti
IN_COLAB   = "COLAB_RELEASE_TAG" in os.environ or "google.colab" in str(globals().get("__spec__",""))
IN_ACTIONS = "GITHUB_ACTIONS" in os.environ

print("═"*55)
print("  🚀 İNCİ BÜLTEN — HAFTALIK RAPOR BAŞLIYOR")
if IN_ACTIONS: print("  📦 Ortam: GitHub Actions")
elif IN_COLAB: print("  📦 Ortam: Google Colab")
print("═"*55+"\n")

raw   = fetch_rss(max_per=18)
print()
items = run_nlp(raw)
print()
items = translate_items(items)

print("\n📄 İnteraktif HTML rapor oluşturuluyor...")
report_html = build_report(items)
tag   = datetime.now().strftime("%Y%m%d_%H%M")
week  = datetime.now().isocalendar()[1]
fname = f"inci_bulten_hafta{week}_{tag}.html"

# GitHub Actions: docs/index.html olarak kaydet (GitHub Pages bunu serve eder)
if IN_ACTIONS:
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(report_html, encoding="utf-8")
    (out_dir / fname).write_text(report_html, encoding="utf-8")
    print(f"  💾 docs/index.html güncellendi")
    print(f"  💾 docs/{fname} arşivlendi")
else:
    # Colab / lokal
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
    fpath = Path(CONFIG["output_dir"]) / fname
    if CONFIG["save_html"]:
        fpath.write_text(report_html, encoding="utf-8")
        print(f"  💾 HTML kaydedildi: {fpath}")

print("\n📧 Mail gönderiliyor...")
smtp_pw = os.environ.get("SMTP_PASSWORD", CONFIG["smtp_password"])
smtp_us = os.environ.get("SMTP_USER",     CONFIG["smtp_user"])
if smtp_pw and "xxxx" not in smtp_pw:
    CONFIG["smtp_password"] = smtp_pw
    CONFIG["smtp_user"]     = smtp_us
    send_email(report_html, fname)
else:
    print("  ⚠️  Mail ayarları girilmemiş")

matched_count   = sum(1 for i in items if i["status"]=="matched")
unmatched_count = sum(1 for i in items if i["status"]=="unmatched")
trash_count     = sum(1 for i in items if i["status"]=="trash")
print(f"\n✅ TAMAMLANDI")
print(f"   Bültene giren : {matched_count}")
print(f"   Bülten dışı   : {unmatched_count}")
print(f"   Çöpe atılan   : {trash_count}")
print(f"   Toplam kayıt  : {len(items)}")

# Colab'da önizleme
if IN_COLAB:
    try:
        from IPython.display import display, HTML as ipHTML
        b64      = base64.b64encode(report_html.encode("utf-8")).decode("ascii")
        data_url = f"data:text/html;base64,{b64}"
        dl_link  = f'<a href="{data_url}" download="{fname}" style="color:#922020;font-weight:600">⬇ {fname} indir</a>'
        print(f"\n🖥️  Önizleme açılıyor...\n")
        display(ipHTML(f"""
<div style="background:#141414;border:1px solid #242424;border-radius:6px;
            padding:12px 18px;margin:6px 0;font-family:'Outfit',sans-serif;
            font-size:11px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
  <span style="color:#666">⚡ <strong style="color:#EDE5DA">{fname}</strong>
    &nbsp;·&nbsp; {len(report_html)//1024} KB
    &nbsp;·&nbsp; <span style="color:#2E9E68">{matched_count} haber</span></span>
  <span>{dl_link}</span>
</div>
<div style="width:100%;height:88vh;border-radius:4px;overflow:hidden;border:1px solid #2A2A2A">
  <iframe src="{data_url}" style="width:100%;height:100%;border:none;background:#0D0B0A" allowfullscreen></iframe>
</div>"""))
    except ImportError:
        pass
