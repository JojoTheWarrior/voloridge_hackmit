import gww, json
for n,(x,y,d) in {"Xiaowan":(100.0,24.85,0.3),"Jinghong":(100.7,22.2,0.25),"SerraDaMesa":(-48.6,-14.0,0.4),"TresMarias":(-45.3,-18.6,0.35),"Emborcacao":(-47.8,-18.4,0.3),"Itumbiara":(-48.9,-18.35,0.3),"NovaPonte":(-47.4,-19.2,0.3),"SaoSimao":(-50.3,-18.9,0.3),"AguaVermelha":(-50.0,-19.9,0.3)}.items():
    fs=gww.find(x,y,d); print(n,len(fs))
    big=[]
    for f in fs:
        p=f["props"]; big.append((f["id"],f["name"],{k:p[k] for k in p if k in("area","Area","source_name","grand_id","name_en")}))
    print("  ",big[:12])
