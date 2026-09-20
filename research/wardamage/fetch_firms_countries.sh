#!/bin/bash
# keyless FIRMS country-year archives (SNPP, 2012-2024)
cd "$(dirname "$0")/data/firms_archive"
for c in Iraq Libya Algeria Nigeria Venezuela Kazakhstan Iran Saudi_Arabia Qatar Kuwait United_Arab_Emirates Oman Egypt Angola Turkmenistan Syria Yemen; do
 for y in $(seq 2012 2024); do f="viirs-snpp_${y}_${c}.csv"; [ -s "$f" ] || curl -s -m 600 -o "$f" "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/$y/$f"; done; echo "done $c"; done
