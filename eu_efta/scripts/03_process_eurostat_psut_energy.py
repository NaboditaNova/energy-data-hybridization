# -*- coding: utf-8 -*-
"""
Process Eurostat PSUT energy data.

Input:
- Eurostat env_ac_pefasu

Output:
- data/intermediate/psut_energy.h5
"""

from rme_tools import tools as to


'''Settings'''

mry = 2024
years = list(range(2010, mry + 1))
TJ_TO_KTOE = 0.0238846


'''Read PSUT energy data'''

ps = to.read_estat(
    'env_ac_pefasu',
    filter_on={'unit': 'TJ'}
)

ps = ps[ps.lv('year').isin(years)]
ps = ps[ps.lv('stk_flow').isin(['USE', 'SUP'])]


'''Convert TJ to KTOE'''

ps['value'] = ps['value'] * TJ_TO_KTOE


'''Rename dimensions'''

ps = to.rename(
    ps,
    {
        'prod_nrg': 'pro',
        'stk_flow': 'flow',
        'nace_r2': 'ind',
    }
)

ps = to.replace(ps, {'SUP': 'SUPPLY'})
ps = ps.pipe(to.aggregate).pipe(to.sort)


'''Save preprocessed PSUT data'''
to.save(ps, 'psut_energy', 'intermediate')


'''Clean memory'''

del ps, mry, years, TJ_TO_KTOE