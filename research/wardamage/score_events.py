"""Curated, located event list -> score_out/events.csv. Events were chosen from Wikipedia/news text (score_out/events_raw_*.csv)
BEFORE looking at satellite data for them, except rows marked round1_known=1 (already examined in round 1).
Coordinates: osm = OSM/Nominatim; cluster = centroid of pre-June-2025 persistent VIIRS cells (no event-period data); approx = from memory / text description."""
import pandas as pd, re
W = "https://en.wikipedia.org/wiki/"
# id, war, date, time_utc, place, lat, lon, r_km, coord_src, country, type, attacker, reported, raw-match regex, gdelt url regex, round1_known
E = [
("E01",2026,"2026-03-01","06:00","Port Shuaiba US tactical ops centre",29.035,48.160,3,"approx","Kuwait","port","Iran","Drone destroyed office trailer; fire and smoke plumes visible for hours; 6 US soldiers killed","Shuaiba","shuaiba",0),
("E02",2026,"2026-03-01","","Jebel Ali port",25.010,55.060,5,"approx","UAE","port","Iran","Fire at port from interception debris; dark plumes seen","Jebel Ali","jebel-?ali",0),
("E03",2026,"2026-03-01","","Duqm port",19.663,57.712,5,"osm","Oman","port","Iran","Two drones; worker housing hit, debris near fuel tanks","Duqm","duqm",0),
("E04",2026,"2026-03-01","","Tanker Hercules Star, 17 nmi NW of Mina Saqr",26.18,55.83,20,"approx_text","UAE","tanker","Iran","Projectile strike sparked fierce fire, extinguished","Hercules Star","hercules-?star|mina-?saqr",0),
("E05",2026,"2026-03-01","","Tanker Skylight, 5 nmi N of Khasab",26.29,56.25,15,"approx_text","Oman","tanker","Iran","Tanker attacked, 4 injured","Skylight","skylight|khasab",0),
("E06",2026,"2026-03-02","","Mina Salman port / tanker Stena Imperative",26.205,50.610,3,"approx","Bahrain","port","Iran","Port struck; tanker Stena Imperative set ablaze, fire extinguished","Mina Salman","mina-?salman|stena-?imperative",0),
("E07",2026,"2026-03-02","","Ras Laffan Industrial City (drone strike)",25.905,51.545,7,"cluster","Qatar","lng","Iran","Drone strike; QatarEnergy halted all LNG production; later imagery: main plant apparently undamaged","Ras Laffan","ras-?laffan|qatarenergy|qatar-?lng",0),
("E08",2026,"2026-03-02","","Mesaieed Industrial Area",24.970,51.570,5,"cluster","Qatar","petrochemical","Iran","Struck by Iranian drone; no damage detail","Mesaieed","mesaieed",0),
("E09",2026,"2026-03-02","","Ras Tanura refinery",26.693,50.102,4,"osm","Saudi Arabia","refinery","Iran","Limited/contained fire from intercepted-drone debris; refinery shut ~1 week","Ras Tanura","ras-?tanura",0),
("E10",2026,"2026-03-03","","Fujairah Oil Industry Zone tanks",25.190,56.350,4,"approx","UAE","tank_farm","Iran","Debris started fire; two storage tanks burning with dark plumes; under control same day","Fujairah","fujairah",1),
("E11",2026,"2026-03-03","","Duqm port fuel tank",19.663,57.712,5,"osm","Oman","tank_farm","Iran","Fuel tank hit by several drones; damage contained","Duqm","duqm",0),
("E12",2026,"2026-03-04","","Ras Tanura refinery (second hit)",26.693,50.102,4,"osm","Saudi Arabia","refinery","Iran","Hit by projectile a second time","Ras Tanura","ras-?tanura",0),
("E13",2026,"2026-03-05","","Bandar Abbas port (Shahid Bahonar / navy)",27.140,56.200,5,"approx","Iran","port","US/Israel","Port set ablaze by airstrikes","Bandar Abbas","bandar-?abbas",0),
("E14",2026,"2026-03-07","","Shahran oil depot, Tehran",35.797,51.288,3,"approx","Iran","depot","Israel","Depot struck; huge fire, smoke plume still visible 9 Mar (HRW)","Tehran fuel depots","shahran|tehran.*(oil|fuel|depot)|(oil|fuel|depot).*tehran",0),
("E15",2026,"2026-03-07","","Aghdasieh oil depot, Tehran",35.800,51.490,3,"approx","Iran","depot","Israel","Depot struck; smoke plume visible 9 Mar (HRW)","Tehran fuel depots","aghdasieh|tehran.*(oil|fuel|depot)|(oil|fuel|depot).*tehran",0),
("E16",2026,"2026-03-07","","Shahr-e Rey oil depot / Tehran refinery",35.540,51.440,4,"cluster","Iran","depot","Israel","Depot east of refinery struck; smoke still rising 11 Mar (HRW)","Tehran fuel depots","shahr-?e?-?rey|tehran.*(oil|fuel|depot|refinery)|(oil|fuel|depot).*tehran",1),
("E17",2026,"2026-03-07","","Fardis oil depot, Karaj",35.720,50.980,5,"approx","Iran","depot","Israel","Oil tanks destroyed (imagery 11 Mar, HRW)","Tehran fuel depots","fardis|karaj",0),
("E18",2026,"2026-03-09","","BAPCO Sitra refinery",26.112,50.608,3,"osm","Bahrain","refinery","Iran","Fire near refinery, 32 injured; force majeure; separate fire at Ma'ameer facility under control","BAPCO","bapco|sitra|bahrain.*refinery",0),
("E19",2026,"2026-03-09","","Subiya power station fuel tank",29.565,48.175,4,"cluster","Kuwait","power_plant","Iran","Fuel tank fire from drone debris","Subiya","subiya|sabiya",0),
("E20",2026,"2026-03-10","","Ruwais refinery (ADNOC)",24.120,52.725,5,"cluster","UAE","refinery","Iran","Fire after drone strike; 922 kb/d refinery shut","Ruwais","ruwais",0),
("E21",2026,"2026-03-10","","Kerman airport fuel depot",30.283,56.951,4,"osm","Iran","depot","US/Israel","HRANA: fuel depot struck","Kerman","kerman",0),
("E22",2026,"2026-03-11","","Port of Salalah fuel tanks",16.945,54.005,4,"approx","Oman","tank_farm","Iran","Two fuel tanks set ablaze; port suspended","Salalah","salalah",0),
("E23",2026,"2026-03-11","","Tankers Safesea Vishnu / Zefyros off Basra",29.78,48.80,25,"approx_text","Iraq","tanker","Iran","Both tankers set ablaze and abandoned; Iraqi terminals suspended","Safesea|Zefyros","safesea|zefyros|basra.*tanker|tanker.*(iraq|basra)",0),
("E24",2026,"2026-03-12","","Bahrain Intl Airport fuel depot, Muharraq",26.265,50.640,3.5,"approx","Bahrain","depot","Iran","Fuel tanks set on fire overnight 11-12 Mar; large fire","Bahrain International Airport|Fuel depot near Bahrain","muharraq|bahrain.*(fuel|airport)",0),
("E25",2026,"2026-03-13","","Kharg Island military sites",29.240,50.320,6,"cluster","Iran","terminal","US","90+ military sites bombed; oil infrastructure spared","Kharg","kharg",0),
("E26",2026,"2026-03-14","","Fujairah port / oil terminal",25.190,56.350,4,"approx","UAE","terminal","Iran","Drone attack caused fires; loading partly suspended","Fujairah","fujairah",1),
("E27",2026,"2026-03-15","","Jask port",25.640,57.770,4,"approx","Iran","port","US/Israel","Video showed extensive airstrike damage","Jask","jask",0),
("E28",2026,"2026-03-16","","Dubai Intl Airport fuel tank",25.253,55.365,4,"osm","UAE","tank_farm","Iran","Drone set fuel tank on fire early morning; extinguished later that day","Dubai International Airport fuel","dubai.*(airport|fuel)|dxb",0),
("E29",2026,"2026-03-16","","Fujairah Oil Industry Zone (16-17 Mar)",25.190,56.350,4,"approx","UAE","tank_farm","Iran","Drone hits caused fires on 16 and 17 Mar","Fujairah","fujairah",1),
("E30",2026,"2026-03-18","10:40","South Pars / Asaluyeh gas refineries",27.510,52.600,9,"cluster","Iran","gas_processing","Israel","Tanks, refineries, pipelines hit ~14:10 local; fire 'being put under control'; refinery 4 nearly destroyed (imagery)","South Pars","south-?pars|asaluyeh|assaluyeh",1),
("E31",2026,"2026-03-18","","Ras Laffan LNG (missile strike)",25.905,51.545,7,"cluster","Qatar","lng","Iran","Missiles caused fires and extensive damage; 17% LNG capacity lost; fire brought under control","Ras Laffan","ras-?laffan",1),
("E32",2026,"2026-03-18","","Bandar Abbas ports / oil terminal",27.120,56.100,8,"approx","Iran","port","US/Israel","Early-morning explosions around Shahid Bahonar/Rajaee ports and near an oil terminal","Bandar Abbas","bandar-?abbas",0),
("E33",2026,"2026-03-19","","SAMREF refinery, Yanbu",23.970,38.250,4,"cluster","Saudi Arabia","refinery","Iran","Drone fell at refinery; loadings briefly halted; minimal damage","SAMREF","samref|yanbu",0),
("E34",2026,"2026-03-19","","BAZAN refinery, Haifa",32.795,35.055,4,"approx","Israel","refinery","Iran","Refinery hit; 'essential infrastructure damaged'; minister: no significant damage","BAZAN","bazan|haifa.*refiner|refiner.*haifa",0),
("E35",2026,"2026-03-19","","Mina Al-Ahmadi refinery (19-20 Mar)",29.055,48.135,4,"osm","Kuwait","refinery","Iran","Drone hit caused small fire; hit again 20 Mar","Ahmadi","ahmadi|kuwait.*refiner",0),
("E36",2026,"2026-03-21","","Victory Base, Baghdad airport",33.246,44.216,5,"osm","Iraq","airbase","Iraqi militia","Base 'set ablaze' by drone","Victory Base","victory-?base|baghdad.*airport",0),
("E37",2026,"2026-03-24","","Kuwait Intl Airport fuel depot",29.220,47.955,5,"osm","Kuwait","depot","Iran","Drones set fuel tank/depot on fire (24-25 Mar); burned 3 days, extinguished 28 Mar","Kuwait International Airport fuel","kuwait.*(airport|fuel)",0),
("E38",2026,"2026-03-27","","Mobarakeh Steel",32.245,51.430,4,"cluster","Iran","steel","Israel","Storage and power infrastructure damaged; struck again 31 Mar","Mobarakeh","mobarakeh",0),
("E39",2026,"2026-03-27","","Khouzestan Steel, Ahvaz",31.290,48.760,3,"cluster","Iran","steel","Israel","All furnaces damaged; >=6 months repair","Kh(o)?uzestan Steel","kh(o)?uzestan.*steel|ahvaz",0),
("E40",2026,"2026-03-27","","Prince Sultan Air Base",24.066,47.582,5,"osm","Saudi Arabia","airbase","Iran","Several US tankers and an E-3 destroyed/damaged on the ground","Prince Sultan","prince-?sultan",0),
("E41",2026,"2026-03-27","","Aluminium Bahrain (Alba) smelter",26.080,50.605,2.5,"approx","Bahrain","smelter","Iran","Facilities attacked; 2 injured","Alba|Aluminium Bahrain","alba|alumin.*bahrain",0),
("E42",2026,"2026-03-28","","EGA Al Taweelah smelter",24.780,54.700,4,"approx","UAE","smelter","Iran","Severe damage, shutdown; up to a year to restore","Taweelah|Emirates Global","taweelah|emirates-?global|ega",0),
("E43",2026,"2026-03-31","","VLCC Al Salmi, Dubai anchorage",25.35,55.15,20,"approx_text","UAE","tanker","Iran","Fully laden VLCC hit and caught fire; later contained","Al Salmi","al-?salmi|dubai.*tanker|tanker.*dubai",0),
("E44",2026,"2026-04-01","","Kuwait Intl Airport fuel storage (2nd)",29.220,47.955,5,"osm","Kuwait","depot","Iran","Fuel storage hit; major fire","Kuwait International Airport fuel storage","kuwait.*(airport|fuel)",0),
("E45",2026,"2026-04-02","","Fuel tank near Mashhad airport",36.234,59.642,4,"osm","Iran","tank_farm","US/Israel","Fuel tank struck, fire","Mashhad","mashhad",0),
("E46",2026,"2026-04-03","","Mina Al-Ahmadi refinery (multiple fires)",29.055,48.135,4,"osm","Kuwait","refinery","Iran","Set on fire in multiple locations","Ahmadi","ahmadi|kuwait.*refiner",0),
("E47",2026,"2026-04-03","","Habshan gas complex",23.850,53.640,5,"cluster","UAE","gas_processing","Iran","Interception debris caused fire; significant damage; 1 killed","Habshan","habshan",0),
("E48",2026,"2026-04-04","","Mahshahr / Bandar Imam petrochemical zone",30.460,49.080,7,"cluster","Iran","petrochemical","US/Israel","Fajr, Rejal, Amir-Kabir plants hit; 5 killed, 170 injured","Mahshahr","mahshahr|bandar-?imam",1),
("E49",2026,"2026-04-05","","BAPCO storage tanks, Sitra",26.130,50.625,5,"approx","Bahrain","tank_farm","Iran","Fires at operational units and storage tanks; extinguished","Bapco|BAPCO","bapco|sitra",0),
("E50",2026,"2026-04-05","","Borouge petrochemical, Ruwais",24.127,52.750,4,"osm","UAE","petrochemical","Iran","Multiple fires from interception debris","Borouge","borouge|ruwais",0),
("E51",2026,"2026-04-05","","KPC/KNPC facilities (Ahmadi/Abdullah area)",29.030,48.150,7,"approx","Kuwait","refinery","Iran","Fires at several facilities, severe damage","Kuwait Petroleum","kuwait.*(petroleum|refiner|oil)|knpc",0),
("E52",2026,"2026-04-06","","South Pars petrochemical, Asaluyeh",27.540,52.570,8,"cluster","Iran","petrochemical","Israel","'Largest petrochemical site' struck; major damage","Asaluyeh|South Pars Petro","asaluyeh|assaluyeh|south-?pars",0),
("E53",2026,"2026-04-07","","SABIC petrochemical complex, Jubail",27.030,49.580,9,"cluster","Saudi Arabia","petrochemical","Iran","Drones hit SABIC complex causing fire","SABIC","sabic|jubail",0),
("E54",2026,"2026-04-07","","Kharg Island military sites (2nd)",29.240,50.320,6,"cluster","Iran","terminal","US","Several large explosions","Kharg","kharg",0),
("E55",2026,"2026-04-08","06:30","Lavan Island refinery",26.797,53.346,3,"osm","Iran","refinery","UAE (reported)","Airstrike sparked large fire; heavy damage, output crippled for months","Lavan","lavan",0),
("E56",2026,"2026-04-08","","Sirri Island export facilities",25.900,54.530,5,"cluster","Iran","terminal","unknown","Early-morning explosions; crude export facilities struck","Sirri","sirri",0),
("E57",2026,"2026-04-08","","Fujairah oil terminal (post-ceasefire)",25.190,56.350,4,"approx","UAE","terminal","Iran","Drones/missiles caused damage and fires","Fujairah","fujairah",0),
("E58",2026,"2026-05-04","","Fujairah Oil Industry Zone tanks (May)",25.190,56.350,4,"approx","UAE","tank_farm","Iran","Several storage tanks set on fire; workers injured","Fujairah","fujairah",0),
("E59",2026,"2026-05-17","","Barakah NPP perimeter",23.965,52.235,4,"osm","UAE","nuclear","Iran","Drone strike caused fire at edge of plant","Barakah","barakah",0),
("E60",2026,"2026-06-03","","Kuwait Intl Airport Terminal 1",29.220,47.955,5,"osm","Kuwait","airport","Iran (denied)","Heavy damage to Terminal 1; 1 dead, 63 injured","Kuwait International Airport Terminal","kuwait.*airport",0),
("E61",2026,"2026-06-08","","Karun petrochemical, Mahshahr",30.460,49.080,7,"cluster","Iran","petrochemical","Israel","Partially damaged","Karun","karun|mahshahr",0),
("E62",2026,"2026-07-14","","NSA Bahrain fuel tanks (Iranian claim)",26.210,50.610,3,"approx","Bahrain","depot","Iran","Iran CLAIMED it set Fifth Fleet fuel tanks on fire; unconfirmed","NSA Bahrain","fifth-?fleet|nsa-?bahrain|juffair",0),
("E63",2026,"2026-07-24","","Isa Air Base fuel tanks (Iranian claim)",25.914,50.593,4,"osm","Bahrain","airbase","Iran","Iran CLAIMED drones hit fuel tanks/depots; unconfirmed","Isa Air Base","isa-?air",0),
("E64",2026,"2026-08-30","11:18","Larak Island IRGC launchers",26.860,56.360,5,"approx","Iran","other","US","Two launchers struck; explosion; 3 killed","Larak","larak",0),
("E65",2026,"2026-09-01","","Lavan Island (US strike)",26.797,53.346,4,"osm","Iran","other","US","US attack killed 3 Basij; target unspecified","Lavan","lavan",0),
("E66",2026,"2026-03-18","","Tanker Parimal, east of Khor Fakkan",25.35,56.55,20,"approx_text","UAE","tanker","Iran","Struck, fire, abandoned","Parimal","parimal|khor-?fakkan",0),
# June 2025 Twelve-Day War
("T01",2025,"2025-06-14","","Shahran oil depot, Tehran (2025)",35.797,51.288,3,"approx","Iran","depot","Israel","Evening strikes hit oil and gasoline depots; large fire","Shahran","shahran|tehran.*(oil|fuel|depot)",0),
("T02",2025,"2025-06-14","","Shahr-e Rey refinery fuel tank (2025)",35.540,51.440,4,"cluster","Iran","refinery","Israel","Fuel tank at Shahr Rey refinery struck (Iranian oil ministry; not in the Wikipedia text)","Shahr","shahr-?e?-?rey|tehran.*refiner",0),
("T03",2025,"2025-06-14","","South Pars Phase 14 refinery (2025)",27.700,52.220,6,"cluster","Iran","gas_processing","Israel","Fire halted 12 mcm/d of gas production at Phase 14","South Pars","south-?pars",0),
("T04",2025,"2025-06-14","","Fajr Jam gas plant (2025)",27.930,52.200,4,"cluster","Iran","gas_processing","Israel","Fire at Fajr Jam gas refinery (Iranian media; not in the Wikipedia text)","Fajr","fajr-?e?-?jam|jam-?gas",0),
("T05",2025,"2025-06-15","","BAZAN refinery, Haifa (2025)",32.795,35.055,4,"approx","Israel","refinery","Iran","Night 15-16 Jun: significant damage, 3 killed, full shutdown (earlier fire nearby night of 14-15 Jun)","BAZAN","bazan|haifa",0),
("T06",2025,"2025-06-14","","Mehrabad airport, Tehran (2025)",35.690,51.313,4,"osm","Iran","airport","Israel","Explosion and fire reported early morning","Mehrabad","mehrabad",0),
]
cols = ["event_id","war","event_date","time_utc","place","lat","lon","radius_km","coord_source","country","asset_type","attacker","reported","raw_rx","gdelt_rx","round1_known"]
ev = pd.DataFrame(E, columns=cols)
raw = pd.concat([pd.read_csv(f"score_out/events_raw_{k}.csv").assign(src=k) for k in ("timeline","countries","war")], ignore_index=True)
def src(r):
    m = raw[(raw.event_date.astype(str).between(str(pd.Timestamp(r.event_date) - pd.Timedelta(days=1))[:10], str(pd.Timestamp(r.event_date) + pd.Timedelta(days=1))[:10])) & raw.place.astype(str).str.contains(r.raw_rx, case=False, regex=True)]
    m = m[m.ref_url.notna()]
    if len(m): return m.iloc[0].ref_url, W + str(m.iloc[0].wiki_page).replace(" ", "_").replace(".txt", "")
    return "", ""
s = ev.apply(src, axis=1, result_type="expand"); ev["source_url"], ev["wiki_page"] = s[0], s[1]
hrw = "https://www.hrw.org/news/2026/04/14/iran-israels-oil-depot-strikes-endanger-environment-health"
ev.loc[ev.event_id.isin(["E14","E15","E16","E17"]), "source_url"] = hrw
ev.loc[ev.wiki_page == "", "wiki_page"] = ev.war.map({2026: W + "Timeline_of_the_2026_Iran_war", 2025: W + "Twelve-Day_War"})
ev["discovery"] = "news_first"
ev.drop(columns=["raw_rx"]).to_csv("score_out/events.csv", index=False)
print(len(ev), "events;", (ev.source_url == "").sum(), "without cite url"); print(ev[ev.source_url == ""][["event_id","place"]])
