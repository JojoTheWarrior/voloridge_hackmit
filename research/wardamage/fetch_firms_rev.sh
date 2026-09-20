#!/bin/bash
cd "$(dirname "$0")/data/firms_archive"
for c in $@; do for y in $(seq 2012 2024); do f="viirs-snpp_${y}_${c}.csv"; [ -s "$f" ] || curl -s -m 900 -o "$f" "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/$y/$f"; done; echo "done $c"; done
