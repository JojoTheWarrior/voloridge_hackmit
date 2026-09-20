"""Strip refs from cached wikitext and print keyword-matching sentences with their section heading."""
import re, sys, pathlib
KW = re.compile(r"refiner|depot|oil terminal|tank farm|storage tank|fuel tank|LNG|gas plant|gas field|gas processing|petrochem|power plant|power station|desalinat|smelter|alumin|steel|tanker|oil field|oilfield|pipeline|Fujairah|Ras Laffan|Ras Tanura|Kharg|Asaluyeh|South Pars|Mahshahr|Abadan|Bandar Abbas|Lavan|Sirri|Habshan|Ruwais|Jebel Ali|Mina |Bapco|BAPCO|Sitra|Shuaiba|Al Zour|Ahmadi|Yanbu|Jubail|Abqaiq|Shaybah|Mesaieed|Haifa|Bazan|BAZAN|Shahran|airport|fuel|on fire|blaze|set ablaze", re.I)
def clean(t):
    t = re.sub(r"<ref[^>]*?/>", "", t)
    t = re.sub(r"<ref[^>]*?>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t); t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    return t
for f in sys.argv[1:]:
    txt = clean(pathlib.Path(f).read_text())
    print(f"\n######## {f}")
    heads = []
    for line in txt.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", line)
        if m:
            lvl = len(m.group(1)); heads = [h for h in heads if h[0] < lvl] + [(lvl, m.group(2))]; continue
        for s in re.split(r"(?<=[.!?])\s+", line):
            if KW.search(s): print("[" + " > ".join(h[1] for h in heads[-2:]) + "] " + s.strip()[:600])
