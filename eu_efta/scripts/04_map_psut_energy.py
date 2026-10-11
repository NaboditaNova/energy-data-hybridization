# -*- coding: utf-8 -*-
"""
Map Eurostat PSUT energy data.

Inputs:
- data/intermediate/psut_energy.h5
- data/intermediate/energy_balance_mapped_current_keys.h5

Outputs:
- data/intermediate/psut_energy_mapped.h5
- data/diagnostic/psut_energy_mapped_check.h5
"""

import pandas as pd
from rme_tools import tools as to


'''Read input data'''

ps = to.read('psut_energy')
eb = to.read('energy_balance_mapped_current_keys')

kp = to.read_key('psut_pro', full=True)
ki = to.read_key('psut_ind_bridge', full=True)

kp = kp[kp['rmh'] != ':'].rename(columns={'rmh': 'pro'})
pr = kp['pro'].drop_duplicates().tolist()


'''Map PSUT products'''

# Script 03 uses pro and ind as standard level names.
# Rename them temporarily to distinguish the source PSUT classifications.
ps = to.rename(ps, {'pro': 'psutp', 'ind': 'psut_ind'})
ps = ps.reset_index()

ps = ps.merge(kp[['psutp', 'pro']], on='psutp', how='left')
ps = ps[ps['pro'].isin(pr)]


'''Map PSUT activities and supply labels'''

ps = ps.merge(ki[['flow', 'psut_ind', 'rmh', 'method']], on=['flow', 'psut_ind'], how='left')
ps = ps.rename(columns={'rmh': 'ind'})

mi = ps[ps['ind'].isna()][['flow', 'psut_ind']].drop_duplicates()

if mi.shape[0] > 0:
    print('Missing PSUT bridge mappings:')
    print(mi.to_string(index=False))
    raise ValueError('Missing entries in keys.xlsx sheet psut_ind_bridge.')

ps = ps[ps['ind'] != ':']
ps = ps[ps['method'] != 'drop']


'''Apply direct and static shares'''

ps['share'] = float('nan')
ps.loc[ps['method'] == 'direct', 'share'] = 1


'''Apply energy-balance shares'''

# Keep the energy-balance MultiIndex and avoid resetting its index.
eb = eb.rename(columns={'value': 'eb_value'})[['eb_value']]

ps = ps.set_index(['geo', 'year', 'pro', 'ind'])
ps = ps.join(eb, how='left')
ps = ps.reset_index()

ps['eb_value'] = ps['eb_value'].fillna(0)

ma = ps['method'] == 'eb_share'

ps.loc[ma, 'eb_sum'] = ps.loc[ma].groupby(
    ['geo', 'year', 'pro', 'flow', 'psut_ind']
)['eb_value'].transform('sum')

ps.loc[ma, 'n_targets'] = ps.loc[ma].groupby(
    ['geo', 'year', 'pro', 'flow', 'psut_ind']
)['ind'].transform('count')

ps.loc[ma & (ps['eb_sum'] > 0), 'share'] = (
    ps.loc[ma & (ps['eb_sum'] > 0), 'eb_value']
    / ps.loc[ma & (ps['eb_sum'] > 0), 'eb_sum']
)

ps.loc[ma & ((ps['eb_sum'] == 0) | ps['eb_sum'].isna()), 'share'] = (
    1 / ps.loc[ma & ((ps['eb_sum'] == 0) | ps['eb_sum'].isna()), 'n_targets']
)


'''Apply allocation shares'''

ps['value'] = pd.to_numeric(ps['value'], errors='coerce').fillna(0)
ps['value'] = ps['value'] * ps['share'].fillna(0)


'''Finalize mapped PSUT data'''

ps = ps.loc[:, ['geo', 'year', 'pro', 'ind', 'value']]
ps = to.set_index(ps).pipe(to.aggregate).pipe(to.sort)


'''Save outputs'''

to.save(ps, 'psut_energy_mapped', 'intermediate')

ch = ps.groupby(['geo', 'year', 'pro']).sum()
to.save(ch, 'psut_energy_mapped_check', 'diagnostic')


'''Clean memory'''

del ps, eb, kp, ki, pr, mi, ma, ch