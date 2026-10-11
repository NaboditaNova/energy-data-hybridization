"""
Created on Fri Jul 24 10:06:50 2026

@author: Nabodita Anam
"""
"""
Process Eurostat energy balance data.

Output:
- data/intermediate/nrg_bal_c.h5
"""

from rme_tools import tools as to

'''Eurostat energy balance data'''

mry = 2024
years = list(range(2010, mry + 1))

# Read Eurostat energy balance in KTOE and keep modelling years.
eb = to.read_estat('nrg_bal_c', filter_on={'unit': 'KTOE'})
eb = eb[eb.lv('year').isin(years)]
eb = to.replace(eb)
eb = to.sort(eb)

# Save raw/clean Eurostat energy balance for later scripts.
to.save(eb, 'nrg_bal_c')

del eb, mry, years
