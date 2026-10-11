# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 10:07:44 2026

@author: Nabodita Anam
"""

"""
Map Eurostat energy balance data.

Input:
- data/intermediate/nrg_bal_c.h5

Output:
- data/intermediate/energy_balance_mapped_current_keys.h5
"""

import pandas as pd
from rme_tools import tools as to


'''Read Eurostat energy balance'''

eb = to.read('nrg_bal_c')


'''Map Eurostat products and flows using keys.xlsx'''

eb = to.rename(eb, {'nrgp': 'pro', 'nrg': 'ind'})

# Map Eurostat energy products to RM product codes.
eb = to.convert(
    eb,
    'pro',
    key='nrgp',
    target='rm',
    ignore_na=False
)
eb = eb[eb.lv('pro') != ':']

# Map Eurostat energy-balance flows to final industry/use codes.
eb = to.convert(
    eb,
    'ind',
    key='nrg',
    target='rmh',
    ignore_na=False
)
eb = eb[eb.lv('ind') != ':']

eb = eb.pipe(to.aggregate).pipe(to.sort)


'''Split temporary hybrid codes'''

# Allocate the combined code between electricity and heat supply.
ma = eb.lv('ind') == 'xRM124.1_RM126.1'

ne = eb[ma].copy()
ne['value'] = ne['value'] * 0.67
ne = ne.rename(index={'xRM124.1_RM126.1': 'RM124.1'})

eb.loc[ma, 'value'] = eb.loc[ma, 'value'] * 0.33
eb = eb.rename(index={'xRM124.1_RM126.1': 'RM126.1'})




##newly add:
    
mb = eb.lv('ind') == 'xRM067.1-067.6_RM124.1'

np = eb[mb].copy()
np['value'] = np['value'] * 0.50
np = np.rename(
    index={'xRM067.1-067.6_RM124.1': 'RM067.1-067.6'}
)

eb.loc[mb, 'value'] = eb.loc[mb, 'value'] * 0.50
eb = eb.rename(
    index={'xRM067.1-067.6_RM124.1': 'RM124.1'}
)


eb = pd.concat([eb, ne, np]).pipe(to.aggregate).pipe(to.sort)
#eb = pd.concat([eb, ne]).pipe(to.aggregate).pipe(to.sort)


'''Save mapped energy balance'''

to.save(
    eb,
    'energy_balance_mapped_current_keys',
    'intermediate'
)


'''Clean memory'''

del eb, ma, mb, ne, np