"""Behavior checks and end-to-end artifact validation, all offline."""
import hashlib
import json
import sys
import unittest

import numpy as np
import pandas as pd

from pmlib import ROOT, DATA
from prepare import station_from_url
from statistics import bh, paired
from weather_panel import asof, empirical_prob

class ResearchChecks(unittest.TestCase):
    def test_asof_never_reads_future(self):
        t=np.array([100.,200.,300.]);p=np.array([.1,.2,.9])
        self.assertEqual(asof(t,p,250,100),.2)
        self.assertTrue(np.isnan(asof(t,p,99,100)))
        self.assertTrue(np.isnan(asof(t,p,500,100)))

    def test_local_day_handles_dst(self):
        d=pd.Timestamp('2026-03-08',tz='America/New_York')
        self.assertEqual((d+pd.DateOffset(days=1)).timestamp()-d.timestamp(),23*3600)
        utc=pd.Timestamp('2026-06-01T01:00:00Z')
        self.assertEqual(utc.tz_convert('America/New_York').strftime('%Y-%m-%d'),'2026-05-31')

    def test_station_query_and_nonairport(self):
        self.assertEqual(station_from_url('https://www.weather.gov/wrh/timeseries?site=klga'),'KLGA')
        self.assertEqual(station_from_url('https://www.wunderground.com/history/daily/gb/london/EGLC'),'EGLC')
        self.assertIsNone(station_from_url('https://www.cwa.gov.tw/V8/C/W/OBS_Station.html?ID=46692'))

    def test_bucket_precision_and_full_family_bh(self):
        self.assertEqual(empirical_prob(np.repeat(20.49,30),20,20),1.)
        self.assertEqual(empirical_prob(np.repeat(20.51,30),20,20),0.)
        q=bh([.01]+[1.]*21)
        self.assertAlmostEqual(q[0],.22)

    def test_one_date_is_not_independent_buckets(self):
        f=pd.DataFrame({'date':['2026-06-01']*1000,'effect':[-.01]*1000})
        r=paired(f)
        self.assertEqual(r['n_dates'],1)
        self.assertEqual(r['status'],'insufficient')
        self.assertEqual(r['p'],1.)

    def test_real_station_dates_and_coverage(self):
        d=pd.read_parquet(DATA/'station_daily.parquet')
        self.assertTrue(d.date.str.startswith(('2024','2025','2026')).all())
        complete=d[d.complete]
        self.assertTrue((complete.hours>=18).all())
        self.assertGreater(len(complete),1000)

    def test_final_artifacts(self):
        if '--artifacts' not in sys.argv:self.skipTest('use --artifacts after report generation')
        prereg=json.loads((ROOT/'prereg.json').read_text())
        digest=hashlib.sha256((ROOT/'prereg.json').read_bytes()).hexdigest()
        self.assertEqual(digest,(ROOT/'prereg.sha256').read_text().split()[0])
        r=pd.read_csv(ROOT/'results.csv')
        self.assertEqual(set(r.test_id),{t['id'] for t in prereg['tests']})
        self.assertEqual(len(r),prereg['family_size'])
        self.assertTrue(np.allclose(r.q,bh(r.p)))
        self.assertTrue((r.loc[r.status!='tested','p']==1).all())
        f=json.loads((ROOT/'findings.json').read_text())
        required={'id','title','one_liner','datasets','mechanism','method','results','controls','verdict','known_or_novel','prior_art','figures','scripts','caveats'}
        self.assertGreaterEqual(len(f),len(r))
        for claim in f:
            self.assertTrue(required<=set(claim))
            self.assertIn(claim['verdict'],['supported','partial','rejected'])
            for p in claim['figures']+claim['scripts']:
                self.assertTrue((ROOT/p).exists(),p)
        self.assertGreaterEqual(len(list((ROOT/'figures').glob('*.png'))),6)
        self.assertTrue((ROOT/'REPORT.md').exists())

if __name__=='__main__':
    unittest.main(argv=[sys.argv[0]],verbosity=2)
