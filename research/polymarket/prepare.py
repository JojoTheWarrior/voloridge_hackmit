"""Immutable local input snapshot and contract/station mapping. No hypothesis tests."""
import hashlib
import json
import re
from urllib.parse import urlparse, parse_qs

import pandas as pd

from pmlib import DATA, ROOT, read_jsonl_gz

TZ_GROUPS = {
    'Europe/London':'london', 'America/New_York':'nyc miami atlanta',
    'America/Chicago':'chicago dallas austin houston', 'America/Los_Angeles':'los-angeles seattle san-francisco',
    'America/Phoenix':'phoenix', 'America/Denver':'denver', 'Asia/Dubai':'dubai',
    'Asia/Seoul':'seoul busan', 'America/Toronto':'toronto',
    'America/Argentina/Buenos_Aires':'buenos-aires', 'Europe/Istanbul':'ankara istanbul',
    'Pacific/Auckland':'wellington', 'America/Sao_Paulo':'sao-paulo',
    'Europe/Paris':'paris', 'Asia/Kolkata':'lucknow', 'Europe/Berlin':'munich',
    'Asia/Jerusalem':'tel-aviv', 'Asia/Tokyo':'tokyo', 'Asia/Hong_Kong':'hong-kong',
    'Asia/Shanghai':'shanghai chongqing beijing wuhan chengdu shenzhen guangzhou qingdao jinan zhengzhou',
    'Asia/Singapore':'singapore', 'Europe/Rome':'milan', 'Europe/Madrid':'madrid',
    'Europe/Warsaw':'warsaw', 'Asia/Taipei':'taipei', 'America/Mexico_City':'mexico-city',
    'Europe/Moscow':'moscow', 'Europe/Amsterdam':'amsterdam', 'Europe/Helsinki':'helsinki',
    'America/Panama':'panama-city', 'Asia/Kuala_Lumpur':'kuala-lumpur', 'Asia/Jakarta':'jakarta',
    'Asia/Riyadh':'jeddah', 'Africa/Lagos':'lagos', 'Africa/Johannesburg':'cape-town',
    'Asia/Karachi':'karachi', 'Asia/Manila':'manila',
}
TIMEZONES = {city: tz for tz, cities in TZ_GROUPS.items() for city in cities.split()}

def station_from_url(url):
    u = urlparse(str(url))
    s = parse_qs(u.query).get('site', [None])[0]
    if s and re.fullmatch('[a-zA-Z0-9]{4}', s):
        return s.upper()
    m = re.search(r'/([A-Z0-9]{4})/?$', u.path)
    return m.group(1) if m else None

def main():
    prereg = ROOT/'prereg.json'
    assert hashlib.sha256(prereg.read_bytes()).hexdigest() == (ROOT/'prereg.sha256').read_text().split()[0]
    cat = pd.read_parquet(DATA/'weather_catalog.parquet')
    cat['station_original'] = cat.station
    cat['station'] = cat.res_url.map(station_from_url)
    cat['timezone'] = cat.city.map(TIMEZONES)
    assert cat.timezone.notna().all()
    cat['source_domain'] = cat.res_url.map(lambda s: urlparse(str(s)).netloc)
    cat['source_family'] = cat.source_domain.map(lambda s: 'WU' if 'wunderground' in s else ('NOAA' if s == 'www.weather.gov' else 'other'))
    cat.to_parquet(DATA/'catalog_enriched.parquet',index=False)
    # Never modify the crawls. The vol10k writer was unexpectedly still active;
    # freeze parsed rows once instead of allowing a moving analysis universe.
    out = DATA/'gamma_snapshot.parquet'
    if not out.exists():
        rows = read_jsonl_gz(DATA/'gamma/vol10k.jsonl.gz')
        df = pd.DataFrame(rows).drop_duplicates('id',keep='last')
        df.to_parquet(out,index=False)
        (DATA/'gamma_snapshot_metadata.json').write_text(json.dumps(dict(
            rows=len(df), cursor=(DATA/'gamma/vol10k.cursor').read_text().strip(),
            note='Snapshot of existing local crawl; did not launch or modify crawler. Cursor was not DONE at inspection.'),indent=2))
    print('prepared',len(cat),'weather rows; stations',cat.station.nunique())

if __name__ == '__main__':
    main()
