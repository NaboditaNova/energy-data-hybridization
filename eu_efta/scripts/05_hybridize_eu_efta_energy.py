# -*- coding: utf-8 -*-
"""
Hybridize EU/EFTA energy data.

Inputs:
- data/intermediate/energy_balance_mapped_current_keys.h5
- data/intermediate/psut_energy_mapped.h5

Outputs:
- data/processed/energy_hybridization_eu_efta.h5
- data/diagnostic/energy_hybridization_eu_efta_output_check.h5
- data/diagnostic/energy_hybridization_eu_efta_psut_fallback_cases.h5
"""

import pandas as pd
from rme_tools import tools as to


'''Settings'''

mry = 2024
years = list(range(2010, mry + 1))


'''Read input data'''

eb = to.read('energy_balance_mapped_current_keys')
eb = eb[eb.lv('year').isin(years)]

ps = to.read('psut_energy_mapped')
ps = ps[ps.lv('year').isin(years)]

kp = to.read_key('psut_pro', full=True)
pr = kp.loc[kp['rmh'] != ':', 'rmh'].drop_duplicates().tolist()


'''Build Eurostat OUT target for PSUT scaling'''

ta = eb[(eb.lv('ind') == 'OUT') & (eb.lv('pro').isin(pr))].reset_index()
ta = ta.rename(columns={'value': 'target_output'})
ta = ta.loc[:, ['geo', 'year', 'pro', 'target_output']]
ta = to.set_index(ta).pipe(to.aggregate).pipe(to.sort)


'''Build PSUT OUT source for scaling factor'''

sc = ps[ps.lv('ind') == 'OUT'].reset_index()
sc = sc.rename(columns={'value': 'source_output'})
sc = sc.loc[:, ['geo', 'year', 'pro', 'source_output']]
sc = to.set_index(sc).pipe(to.aggregate).pipe(to.sort)


'''Select country-year-product cases where PSUT can be used'''

va = sc.reset_index().merge(ta.reset_index(), on=['geo', 'year', 'pro'], how='inner')
va['source_output'] = pd.to_numeric(va['source_output'], errors='coerce').fillna(0)
va['target_output'] = pd.to_numeric(va['target_output'], errors='coerce').fillna(0)

fb = va[va['source_output'] == 0].copy()
fb = to.set_index(fb).pipe(to.sort)
to.save(fb, 'energy_hybridization_eu_efta_psut_fallback_cases', 'diagnostic')

va = va[va['source_output'] != 0].copy()
va['scaling_factor'] = va['target_output'] / va['source_output']


'''Scale valid PSUT rows to Eurostat OUT'''

sf = va.set_index(['geo', 'year', 'pro'])[['scaling_factor']]

ps = ps[ps.lv('pro').isin(pr)]
ps = ps.join(sf, how='inner')

ps['value'] = pd.to_numeric(ps['value'], errors='coerce').fillna(0)
ps['value'] = ps['value'] * ps['scaling_factor']

ps = ps[['value']].pipe(to.aggregate).pipe(to.sort)


'''Keep EB rows where PSUT cannot replace the row'''

eb = eb.reset_index()
eb = eb.merge(va[['geo', 'year', 'pro']].assign(use_psut_case=1), on=['geo', 'year', 'pro'], how='left')
eb = eb[eb['use_psut_case'].isna()].drop(columns='use_psut_case')
eb = to.set_index(eb).pipe(to.aggregate).pipe(to.sort)


'''Combine EB fallback rows with scaled PSUT rows'''

hy = pd.concat([eb, ps]).pipe(to.aggregate).pipe(to.sort)


'''Save final hybridized result'''

to.save(hy, 'energy_hybridization_eu_efta', 'processed')


'''Check selected OUT rows against Eurostat target'''

ch = hy[(hy.lv('pro').isin(pr)) & (hy.lv('ind') == 'OUT')].reset_index()
ch = ch.rename(columns={'value': 'hybrid_output'})
ch = ch.merge(ta.reset_index(), on=['geo', 'year', 'pro'], how='left')
ch['diff_output'] = ch['hybrid_output'] - ch['target_output']
ch = to.set_index(ch).pipe(to.sort)

to.save(ch, 'energy_hybridization_eu_efta_output_check', 'diagnostic')


'''Clean memory'''

del eb, ps, hy, kp, pr, ta, sc, va, fb, sf, ch, mry, years