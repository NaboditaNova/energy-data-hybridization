# -*- coding: utf-8 -*-
"""
Created on Tue Dec 22 10:34:27 2020

@author: Birte Ewers
"""

from pathlib import Path
import pandas as pd

mode = 'full_structure'
#mode = 'deployed'

def add_labels(df: pd.DataFrame, lang='EN'):
    """
    Replace codes with labels e.g. for Excel output. The labels are taken from the file 'labels.xlsx'.

    Many of the labels also contain the codes. Items for which the labels are not existing
    do not cause an error.

    Parameters
    ----------
    df : DataFrame
        DataFrame to which labels are to be added
    lang : str 
        For determining the language of the labels ('EN' or 'DE')
    
    Returns
    -------
    DataFrame
        With codes replaced by labels.
    """
    # read file with labels, select column in English
    label = read('labels', 'rme_tools', 'xlsx').set_index('item').iloc[:,1].dropna().to_dict()

    # if language is German, reload file and select German column
    if lang=='DE':
        label = read('labels', 'rme_tools', 'xlsx').set_index('item').iloc[:,2].dropna().to_dict()

    # replace index values/column names with the respective labels
    df = df.rename(label, axis=1)
    df = df.rename(label, axis=0)

    # replace row and column index names with the respective labels
    df = df.rename_axis(index=label, columns=label)

    # for columns with datatype object (string/text) replace values with the respective labels
    df.loc[:, df.dtypes == object] = df.loc[:, df.dtypes == object].replace(label)
            
    return df

def add_level(df, level_name, func):
    """
    Add index level to DataFrame with values according to a given function.

    Parameters
    ----------
    df : DataFrame
        DataFrame to which level is to be added
    level_name : str 
        Name of the level to be added.
    func : str or callable or Series/array
        For assignment of values.
    
    Returns
    -------
    DataFrame
        A new DataFrame With added level.
    """
    # add column called level_name and assign values to it
    df = (df.assign(level_name=func)
          .rename({'level_name':level_name}, axis=1)
          .set_index(level_name, append=True)) # add column to index

    # sort the resulting DataFrame
    df = sort(df)
    return df

def add_subtotals(df, levels=['pro', 'ind']):
    """
    Add subtotals and totals (CPA64) to input-output table with RME182 classification.

    Required format for input-output table: level names: 'pro' or 'pro_cpa' for
    sectors and 'ind' or ind_cpa' for sectors and final use.

    Parameters
    ----------
    df : DataFrame
        Input-output table
    levels : str or list
        Name of the levels to which subtotals are to be added
    
    Returns
    -------
    DataFrame
        With added subtotals
    """
    # if levels is str convert to list
    if isinstance(levels, str):
        levels = [levels]

    if 'pro' in levels:
        # add column with CPA codes if not available
        if 'pro_cpa' not in df.index.names:
            ck = read_key('rme')
            df = df.assign(pro_cpa=df.level('pro').map(ck))
            df = df.set_index(['pro_cpa'], append=True)
        ls = list(df.index.names)
        ls.remove('pro')
        # groupby all index levels except for 'pro'
        pro_cpa = (df.loc[df.index.droplevel('pro').duplicated(keep=False)==True]
                   .groupby(by=ls).sum())
        pro_cpa.index = pro_cpa.index.set_names('pro', level='pro_cpa')
        df = df.droplevel('pro_cpa')
        pro_cpa = sort(pro_cpa)
        df = pd.concat([df, pro_cpa])
    
    if 'ind' in levels:
        # add column with CPA codes if not available
        if 'ind_cpa' not in df.index.names:
            ck = read_key('rme')
            df = df.assign(ind_cpa=df.level('ind').map(ck))
            df = df.set_index(['ind_cpa'], append=True)
        ls = list(df.index.names)
        ls.remove('ind')
        ind_cpa = (df.loc[df.index.droplevel('ind').duplicated(keep=False)==True]
                   .groupby(by=ls).sum())
        ind_cpa.index = ind_cpa.index.set_names('ind', level='ind_cpa')
        df = df.droplevel('ind_cpa')
        ind_cpa = sort(ind_cpa)
        df = pd.concat([df, ind_cpa])
        
    df = sort(df)
    
    return df

def aggregate(df):
    '''Aggregate data using groupby, useful after conversions to a different classification.'''
    # REMARK: min_count is for getting NaNs instead of 0, if all values are NaN; doesn't work if strings are aggregated
    # https://github.com/pandas-dev/pandas/issues/20824   
    
    df = df.sort_index()    
    df = df.groupby(by=df.index.names, dropna=False, sort=False).sum(min_count=1)

    return df

def check(df, check_for=['nans', 'nans_index', 'negatives', 'duplicates']):
    '''Function to check whether a dataframe contains NaN values, NaN values 
    in index columns or negative values.'''
    
    import numpy as np

    try:
        if 'nans' in check_for:
            assert ~np.any(df.isna())
    except AssertionError:
        print('Warning: The dataframe contains ' + str(df.isnull().sum().sum()) + ' NaN value(s).')

    
    try: 
        if 'negatives' in check_for:
            assert ~np.any(df<0)
    except AssertionError:
        print('Warning: The dataframe contains ' + str(np.sum((df < 0).values.ravel())) + ' negative value(s).')

        
    try:
        if 'nans_index' in check_for:    
            for x in df.index.names:
                assert ~np.any(df.lv(x).isna())
    except AssertionError:
        print('Warning: The dataframe index contains NaNs.')
        
    try: 
        if 'duplicates' in check_for:
            assert ~np.any(df.index.duplicated())
    except AssertionError:
        print('Warning: The dataframe contains ' + str(np.sum(df.index.duplicated().values.ravel())) + ' duplicates')


def convert(df, level_to_convert, key=None, target=None, original=None, new_level=None, ignore_na=False):
    '''Convert level to different classification and save in existing level or new level.'''

    df = df.copy(deep=True)
     
    if key is None :
        key = level_to_convert        
    if target: 
        if original:
            ck = read_key(key, target, original)
        else: ck = read_key(key, target)
    else: ck = read_key(key)    
                  
             
    if df.level(level_to_convert).isin(ck.index).all() or ignore_na==True:
        
        df = df.assign(temp = df.level(level_to_convert).map(ck))
        df = df.set_index('temp', append=True)
        if new_level is None :
            df = df.droplevel(level_to_convert)
            df = df.rename_axis(index={'temp': level_to_convert})
        else: df = df.rename_axis(index={'temp': new_level})
            
                   
    else : 
       missing_elements = df[~df.level(level_to_convert).isin(ck.index)].level(level_to_convert).unique()
              
       print ('''Error: Conversion not possible as the column
                 contains elements not present in the conversion key:''', 
                 missing_elements, ".")             
    return df

def convert_array(np, levels, names):
    '''Convert arrray to Pandas dataframe.'''
    ix = create_index(levels, names)
    df = pd.DataFrame(np.ravel(), ix, columns=['value'])
    
    return df

def calibrate_trade(df, on=['year', 'pro', 'ind'], level='ind'):
    '''Calibrate trade data, so that intra-EU imports and exports coincide.
    Method: Adjust to the mean between intra-EU imports and exports.
    Apply or do not apply adjustments to extra-EU imports and exports, so that 
    total imports and exports stay idential.'''
    ag = df.groupby(on).sum()

    ag = unstack(ag, level=level)

    ag = ag.assign(i=lambda x:(x.EXP_i+x.IMP_i)/2,
    #               EXP_e=lambda x:(x.EXP_e+(x.EXP_i-x.i)),
    #               IMP_e=lambda x:(x.IMP_e+(x.IMP_i-x.i)),
                    EXP_i=lambda x:x.i,
                    IMP_i=lambda x:x.i)
    
    ag = ag.drop(columns='i').pipe(stack)
    
    ag[ag.value<0] = 0
    
    df = scale(df, ag, on=ag.index.names)

    return df, ag

def create_index(levels, names=None):
    """
    Create a MultiIndex from a mix of strings (read via to.read_index)
    and iterables (used as-is).

    Parameters
    ----------
    levels : list
        Each element is either:
          - str       -> passed to to.read_index(str)
          - iterable  -> used directly as the level values
    names : list or None, optional
        Level names for the resulting MultiIndex. If None, use the
        provided string names; otherwise fallback to 'lvl{i}'.

    Returns
    -------
    pandas.MultiIndex
    """
    n = len(levels)
    ix = [None] * n          # preallocate container for level values
    auto_names = [None] * n    # preallocate container for inferred names

    for i, level in enumerate(levels):
        if isinstance(level, str):
            ix[i] = read_index(level)          # e.g. 'geo', 'year', 'rm', ...
            auto_names[i] = level
        else:
            ix[i] = pd.Index(level)
            auto_names[i] = f'lvl{i}'

    if names is None:
        names = auto_names
    else:
        if len(names) != n:
            raise ValueError("Len(names) must match number of levels")

    return pd.MultiIndex.from_product(ix, names=names)
    

def create_iterable(srs1, srs2):
    """Get series with unique and sorted values from two series. Useful for creating multindex 
    from product."""
    
    s1 = pd.Series(srs1.unique())
    s2 = pd.Series(srs2.unique())
    srs = (s1.append(s2)
             .drop_duplicates()
             .pipe(sort)
             .reset_index(drop=True))                     
    return srs

def edit_level(df, level_name, func):
    """
    Replace the values of an existing index level.

    Parameters
    ----------
    df : DataFrame
        DataFrame with a MultiIndex.
    level_name : str
        Name of the index level to be replaced.
    func : str or callable or Series/array
        Values used to create the new level.

    Returns
    -------
    DataFrame
        DataFrame with the updated index level."""
        
    df = (df.assign(level_name=func)
          .droplevel(level_name)
          .rename({'level_name':level_name}, axis=1)
          .set_index(level_name, append=True))
    
    df = sort(df)
    return df


# def empty_index(levels=['geo', 'year', 'pro']):
#     """Create an empty MultiIndex for the RME classification.

#     Parameters
#     ----------
#     levels : list, default ['geo', 'year', 'pro']
#         Names of the index levels to include.

#     Returns
#     -------
#     MultiIndex
#     MultiIndex containing combinations of countries, years and
#     RME product codes."""
    
#     ix = read_index('rme')
#     ix = ix[ix.str.len()==6]
#     geo = read_index('geo')
#     years = [x for x in range (2010, 2023)]

#     if 'geo' in levels:
#         if 'year' in levels:
#             ix = pd.MultiIndex.from_product([geo, years, ix], names = levels)
#         else:
#             ix = pd.MultiIndex.from_product([geo, ix], names = levels)
#     else:
#         ix = pd.MultiIndex.from_product([years, ix], names = levels)
#     return ix
   

def excel(dfs: list,  file: str, sheet_names=None, titles=None, lang='EN', flat=False):
    '''Export dataframes to Excel.'''
       
    import xlsxwriter as xl
    import pandas.io.formats.excel
    
    pandas.io.formats.excel.ExcelFormatter.header_style = None
    
    writer = pd.ExcelWriter('reports/'+file+'.xlsx', engine='xlsxwriter')

    if flat==True:
        index=False
    else: index=True

    if not isinstance(dfs, list):
        dfs = [dfs]
        if sheet_names:            
            sheet_names = [sheet_names]
        if titles:
            titles = [titles]
    
    nsheets = len(dfs)
    
    if sheet_names is None:
        sheet_names = [f'Data{i}' for i in (range(nsheets))]
        sheet_names[0] = 'Data'        
    
    for i in range(nsheets):      
        if flat==False:
            if lang:
                dfs[i] = add_labels(dfs[i], lang=lang)
        else: dfs[i] = dfs[i].reset_index()

        dfs[i].to_excel(excel_writer=writer, sheet_name=sheet_names[i], startrow=3, na_rep=':', index=index)
    
    workbook = writer.book
    worksheets = [writer.sheets[sheet_names[i]] for i in range(nsheets)]
    
    empty_format = workbook.add_format({'num_format': '#,##0',
                                        'bg_color': '#FFFFFF',
                                        'border': 0})

    flat_format = workbook.add_format({'num_format': '0.0'})
    
    num_format = workbook.add_format({'num_format': '#,##0'})

    header_format = workbook.add_format({'align': 'center',                                   
                                         'valign': 'top',
                                         'bg_color': '#cddc8b',
                                         'border': 1,
                                         'text_wrap':True, 
                                         'bold': False,
                                         'border_color':'gray'})
    
    index_format = workbook.add_format({'align': 'left',                                   
                                         'valign': 'top',
                                         'bg_color': '#cddc8b',
                                         'border': 1,
                                         'bold': False,
                                         'border_color':'gray'})

    red_format = workbook.add_format({'font_color':'#9C0006',
                                      'bg_color':'#FFC7CE',
                                      'num_format': '#,##0'})
        
    yellow_format = workbook.add_format({'font_color':'#9C6500',
                                         'bg_color':'#FFEB9C',
                                         'num_format': '#,##0.0#'})
    
    small_num = workbook.add_format({'num_format': '0.0#'})


    title_format = workbook.add_format({'bold': True})
    
     
    for i in range(nsheets):
        
        num_levels = dfs[i].index.nlevels
        num_col_levels = dfs[i].columns.nlevels
        (num_rows, num_cols) = dfs[i].shape

        header_start = 3      
        
        if num_col_levels > 1:
            header_end = header_start + num_col_levels
        else: header_end = header_start + num_col_levels - 1
        
        rows_start = header_end + 1
        rows_end = rows_start + num_rows - 1
        
        cols_start = num_levels
        cols_end = cols_start + num_cols - 1
        
        if num_levels > 1:
            for k in range(0, num_levels):
                col_len = max(dfs[i].index.levels[k].to_series().astype(str).str.len().max()-2, 8)
                worksheets[i].set_column(k, k, col_len, index_format)
        else: 
            col_len = max(dfs[i].index.to_series().astype(str).str.len().max()-2, 8)
            if flat==False:
                worksheets[i].set_column(0, 0, col_len, index_format)
            else: worksheets[i].set_column(0, 0, col_len)

        if flat==False:
            worksheets[i].set_column(cols_start, cols_end, 10, num_format)
        else:
            worksheets[i].set_column(cols_start, cols_end-2, 10)
            worksheets[i].set_column(cols_end-1, cols_end-1, 10, flat_format)



        worksheets[i].set_zoom(90)
        
        for r in range(header_start, rows_start):
            worksheets[i].set_row(r, None, header_format)

        if flat==False:
            worksheets[i].conditional_format(rows_start, cols_start, rows_end, cols_end,
                                              {'type':    'cell',
                                              'criteria': 'between',
                                              'minimum':   0.01,
                                              'maximum':    2,
                                              'format':    small_num})
    
            worksheets[i].conditional_format(rows_start, cols_start, rows_end, cols_end,
                                              {'type':    'cell',
                                              'criteria': 'between',
                                              'minimum':   2,
                                              'maximum':   50,
                                              'format':    small_num})
            
            worksheets[i].conditional_format(rows_start, cols_start, rows_end, cols_end,
                                             {'type':     'cell',
                                              'criteria': '==',
                                              'value':     0,
                                              'format':    red_format})
            
            worksheets[i].conditional_format(rows_start, cols_start, rows_end, cols_end,
                                            {'type':     'cell',
                                             'criteria': '<',
                                             'value':     0,
                                             'format':    yellow_format})

        worksheets[i].freeze_panes(rows_start, cols_start)
        
        if titles:
            worksheets[i].write(0, 0, titles[i], title_format)        
      
        for r in range(0, header_start):
            worksheets[i].set_row(r, None, empty_format)
    
    while True:
        try:
            writer.close()
        except xl.exceptions.FileCreateError as e:
            decision = input("Exception caught in workbook.close(): %s\n"
                             "Please close the file if it is open in Excel.\n"
                             "Try to write file again? [Y/n]: " % e)
            if decision != 'n':
                continue
    
        break

# def filter(df, constraints):
#     """Filter MultiIndex by sublevels."""
#     indexer = [constraints[name] if name in constraints else slice(None)
#                for name in df.index.names]
#     return df.loc[tuple(indexer)] if len(df.shape) == 1 else df.loc[tuple(indexer),]

def extract_7z(path, name):
    """Extract data from compressed 7z file. Requires path and name of uncompressed file."""

    import py7zr
    
    # extract synthetic data
    with py7zr.SevenZipFile(path, mode='r') as z:
        z.extractall()
        
    return name

def filter(df, constraints):
    """Filter MultiIndex by sublevels (list-like or strings as constraints)."""
    
    for key in constraints:
        if type(constraints[key]) is list:
            df = df[df.lv(key).isin(constraints[key])]
        else:  
            df = df[df.lv(key)==constraints[key]]
        
    return df


def finish_scale(df, droplevel=None, value_col='value'):
    """Clean the output of ``scale()`` and restore the original value column name.

    Parameters
    ----------
    df : DataFrame
        DataFrame returned by ``scale()`` containing scaling helper columns.
    droplevel : str or int, optional
        Index level to be dropped after scaling.
    value_col : str, default 'value'
        Name of the original value column.

    Returns
    -------
    DataFrame
        DataFrame with helper columns removed and ``scaled_value``
        renamed to ``value_col``."""
    

    df = df.drop([value_col,'scaling_factor', 'target_sum', 'initial_sum', 'final_sum'], axis=1)
    if droplevel:
        df = df.droplevel(droplevel)
    df = df.rename({'scaled_value': value_col}, axis=1)
    
    return df

def format_iot(df: pd.DataFrame):
    ''' Adjust iot format for Excel output. Unstack, adjust labels, add totals.'''
    
   
    if 'ind' in df.index.names:
        df = unstack(df, 'ind')
        
    if 'ind_cpa' in df.index.names:
        df = unstack(df, 'ind_cpa')

    df = sort(df)    

    df['TIU'] = df.loc(axis=1)[(df.columns.str.contains('RME')) 
                               | (df.columns.str.contains('CPA'))].sum(axis=1)

    df['TFU'] = df.loc[:,'HFCE':'EXP_e'].sum(axis=1)
    df['TU'] = df['TIU'] + df['TFU']
    
    df['EXP'] = df['EXP_i'] + df['EXP_e']
    df['TDU'] = df['TU'] - df['EXP']
    df['IMP'] = df['IMP_i'] + df['IMP_e']

    df = sort(df)

    return df

def gapfill(df: pd.DataFrame, lv_unstack='year', axis=1):    
    """
    Fill missing values by backward and forward filling.

    Parameters
    ----------
    df : DataFrame
        DataFrame with missing values to be filled.
    lv_unstack : str or None, default 'year'
        Index level to unstack before gap-filling. If None, filling is
        applied directly to the current layout.
    axis : int, default 1
        Axis along which missing values are filled.

    Returns
    -------
    DataFrame
        DataFrame with gaps filled.

    Notes
    -----
    The function applies repeated backward and forward filling. If
    ``lv_unstack`` is given, the data are unstacked before filling and
    stacked again afterwards.
    """
    
    if lv_unstack is not None and df.columns.name != lv_unstack:
        df = unstack(df, level=lv_unstack)
        
    df = (df.bfill(axis=axis, limit=1)
          .ffill(axis=axis, limit=1)
          .bfill(axis=axis, limit=1)
          .ffill(axis=axis, limit=1)
          .bfill(axis=axis)
          .ffill(axis=axis))
    
    if lv_unstack is not None:
        df = stack(df, level=lv_unstack)

    return df

def get_parent():
    """
    Get parent of current working directory.
    """
    from pathlib import Path
    
    parent = Path().resolve().parent
    return parent


def get_path(name, folder='intermediate', file_format='h5'):
    """Build a file path for reading or writing project data.

    Parameters
    ----------
    name : str
        File name without extension.
    folder : str, default 'intermediate'
        Folder where the file is stored.
    file_format : str, default 'h5'
        File extension.

    Returns
    -------
    Path
        Path object pointing to the requested file."""   
 
    if mode=='full_structure':

        if folder=='shared':
            path = Path().resolve().parent.joinpath(folder+'/'+name+'.'+file_format)
    
        else:
            if folder=='rme_tools':
                path = Path().resolve().parent.joinpath('rme_tools/'+name+'.'+file_format)
                
            else:
                if folder.startswith('data'):
                    path = Path().resolve().parent.joinpath(folder+'/'+name+'.'+file_format)
               
                else:
                    if folder=='root':
                        path = Path().joinpath(name+'.'+file_format)
                        
                    else:
                        if folder=='parent':
                            path = Path().resolve().parent.joinpath(name+'.'+file_format)      
                            
                        else:
                            path = Path().joinpath('data/'+folder+'/'+name+'.'+file_format)
            
    if mode=='deployed':
        
        if folder=='shared':
            path = Path().joinpath('data/raw/'+name+'.'+file_format)
            
        else:
            if folder=='rme_tools':
                path = Path().joinpath(name+'.'+file_format)
                
            else:
                if folder.startswith('data'):
                    path = Path().joinpath('data/raw/'+name+'.'+file_format)
                    
                else:
                    if folder=='root':
                        path = Path().joinpath(name+'.'+file_format)
                    else:
                        path = Path().joinpath('data/'+folder+'/'+name+'.'+file_format)
                    
    return path

def level(df, level, axis=0):
    """Return the values of one index level from rows or columns.

    Parameters
    ----------
    df : DataFrame or Series
        Object with an index or column MultiIndex.
    level : str or int
        Name or position of the level to extract.
    axis : int, default 0
        Axis from which the level is taken. Use 0 for row index
        and 1 for columns.

    Returns
    -------
    Index: Values of the selected level."""
        
    if axis==1:
        index = df.columns.get_level_values(level)
    else:
        index = df.index.get_level_values(level)
    return index

pd.Series.lv = level
pd.DataFrame.lv = level

pd.Series.level = level
pd.DataFrame.level = level


_UNSET = object()

def read(name, folder='intermediate', file_format='h5', archived_file=None, skiprows=0,
    sheet_name=0, na_values=None, na_filter=True, sep=',', encoding=None, decimal='.',
    dtype=None, usecols=None, index_col=None, nrows=None, header=_UNSET, names=None,
    keep_default_na=True):
    """
    Read files (*.h5, *.xlsx, *.csv, *.7z, *.zip) from selected folder.
    If zip/7z files contain multiple files, file to be extracted can be selected by 
    indicating it with the name variable. Example: /name.zip/file.dat''

    Parameters
    ----------
    name : str
        File name (without extension or with full name if file_format is None).
    folder : str, default 'intermediate'
        Folder where the file is located.
    file_format : str, default 'h5'
        File type override. If file_format is None, it will be inferred from the actual path extension.
    skiprows : int, default 0
        Number of lines to skip at the beginning (used in CSV/XLSX).
    sheet_name : int or str, default 0
        Sheet name or index for Excel files.
    na_values : scalar, str, list-like, or dict, optional
        Additional strings to recognize as NA/NaN.
    na_filter : bool, default True
        Detect missing values (faster if False).
    sep : str, default ','
        Field delimiter for the CSV file.
    encoding : str, optional
        Encoding to use for UTF when reading CSV files.
    decimal : str, default '.'
        Character to recognize as decimal point.
    dtype : Type name or dict of column -> type, optional
        Data type for data or columns.
    usecols : list-like or callable, optional
        Return a subset of the columns.
    index_col : int, str, or sequence, optional
        Column(s) to set as index (MultiIndex).
    nrows : int, optional
        Number of rows to read from the file.
    header: int, list of int, or None, default 'infer'
        Row(s) to use as the column names. Pass None if there is no header row.
    names: list-like, optional
        List of column names to use. Useful when header=None.

    Returns
    -------
    DataFrame
        Loaded pandas DataFrame.
    """

    import os
    import zipfile    
    import tempfile
    import py7zr
    from pathlib import Path
    
    
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)        
     
    path = str(get_path(name, folder, file_format))

    # Infer file format from path if extension is present
    _, ext = os.path.splitext((path))
    if ext:
        file_format = ext.lower().lstrip(".")        
    
    def get_archived_file(archived_files, archived_file=None):
        m = archived_file
        if m is None:
            for m in archived_files:
                if m.lower().endswith((".csv", ".dat")):
                    break
                else: raise FileNotFoundError(f"No *.csv or *.dat file found in archive: {archived_files}")
        return m

    read_csv_kwargs = {
        "skiprows": skiprows,
        "na_values": na_values,
        "na_filter": na_filter,
        "sep": sep,
        "encoding": encoding,
        "decimal": decimal,
        "dtype": dtype,
        "usecols": usecols,
        "index_col": index_col,
        "nrows": nrows,
        "header": 'infer' if header is _UNSET else header,
        "names": names, 
        "keep_default_na": keep_default_na}

    if file_format == 'xlsx':
        df = pd.read_excel(path, skiprows=skiprows, usecols=usecols, names=names, 
                           sheet_name=sheet_name, na_values=na_values, 
                           header=0 if header is _UNSET else header,
                           index_col=index_col, nrows=nrows, dtype=dtype)

    elif file_format == 'csv':
        df = pd.read_csv(path, **read_csv_kwargs)
    
    elif file_format == 'zip':
        with zipfile.ZipFile(path, mode='r') as archive:
            member = get_archived_file(archive.namelist(), archived_file=archived_file)
            with archive.open(member) as f:
                df = pd.read_csv(f, **read_csv_kwargs)
 
    elif file_format == '7z':
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            with py7zr.SevenZipFile(path, mode='r') as archive:
                member = get_archived_file(archive.getnames(), archived_file=archived_file)
                archive.extract(path=td, targets=[member])
            df = pd.read_csv(td / member, **read_csv_kwargs)

    elif file_format == 'h5':
        df = pd.read_hdf(path)

    else:
        raise ValueError(f"Unsupported file format: {file_format}")

    return df


def read_comext(path=None, nrows=None, filter_on=None):
    """
    Read and lightly clean a COMEXT trade file.

    Parameters
    ----------
    path : str or path-like, optional
        Path to the CSV file.
    nrows : int, optional
        Number of rows to read from the file.
    filter_on : dict, optional
        Dictionary with column-value pairs used to filter the result.

    Returns
    -------
    DataFrame
        COMEXT data with selected columns and standardized column names.
    """
    #TRADE_TYPE: intra- or extra-EU trade
    #STAT_REGIME: distinguishes normal imports/exports and inward/outward processing
    #values are 1, 2, 3, 9; no double counting if aggregated; useful to distinguish re-exports
    
   
   
    df = pd.read_csv(path, nrows=1)

    if len(df.columns)==19:
        df = (pd.read_csv(path,
                          nrows=nrows,
                          index_col=None,
                          na_filter=False, # else Namibia (iso2: NA) is detected as nan
                          header=0,
                          usecols=[1,  3, 5, 9, 12, 13, 15, 16, 17], 
                          names=['reporter', 'partner', 'pro', 'cpa_21', 'ind', 
                                  'regime', 'year', 'value', 'weight'],
                          dtype={'reporter':'str', 'partner':'str', 
                                  'pro':'str', 'cpa_21':'str', 'ind':'str',
                                  'regime':'int', 'year':'int', 
                                  'weight': 'float64', 'value': 'float64'}))

    else:
        df = (pd.read_csv(path,
                          nrows=nrows,
                          index_col=None,
                          header=0,
                          na_filter=False, # else Namibia (iso2: NA) is detected as nan
                          usecols=[1,  3, 5, 9, 13, 14, 16, 17, 18],
                          names=['reporter', 'partner', 'pro', 'cpa_21', 'ind', 
                                  'regime', 'year', 'value', 'weight'],
                          dtype={'reporter':'str', 'partner':'str', 
                                  'pro':'str', 'cpa_21':'str', 'ind':'str',
                                  'regime':'int', 'year':'int', 
                                  'weight': 'float64', 'value': 'float64'}))

        df = df.pipe(lambda x: x[(x['pro'] != 'TOTAL') | (x['cpa_21'] != 'TOTAL')])
        df = df.reset_index(drop=True)
           
        df.loc[df['ind']=='1', 'ind'] = 'IMP'
        df.loc[df['ind']=='2', 'ind'] = 'EXP'
        df['year'] = df['year'].astype(str).str[:4].astype(int)
        
        if filter_on:
            df = df.loc[(df[list(filter_on)] == pd.Series(filter_on)).all(axis=1)]     
    
    
    return df

def read_dict(key, target=None):
    ''' Load conversion key from file and convert it to a dictionary
    for replacing the original values with target values
    

    Parameters
    ----------
    original : string
        Specifies the original starting classification. Possible values:
            For product/sector classifications: hs, cn, cpa, prodcom, sbs, rme
    target : string
        Specifies the target classification. Possible values:
            For product/sector classifications: rme, hs_label, cn_label, rme_label, cpa
        
    Returns
    -------
    ck : dictionary
        Returns a dictionary containing a mapping between the
        original and the target classification.

    '''
    path = get_path('keys', 'parent', 'xlsx')
    ck = (pd.read_excel(path, dtype=str, sheet_name=key, na_values=None))
    
    if target:
        columns = [key, target]
        ck = ck.loc[:, columns]
  
    
    ck = (ck.set_index(key)
    .iloc[:, 0]
    .to_dict())
        
    return ck

def read_estat(code, filter_on=None, flags=False):
    """
    Function for reading Eurostat data using the Python eurostat package with optional filtering.
    Years are moved from columns headers to row values.

    Parameters
    ----------
    code : string
        Code of a Eurostat dataset. Get list of available codes from eurostat package eurostat.get_toc_df() 
    filter_on : dictionary, optional
        Dictionary with key-value pairs with column to be filtered on and the value to keep. The default is None.
    flags : boolean, optional
        Read flags.

    Returns
    -------
    df : Pandas dataframe
        DESCRIPTION.

    """
          
    import eurostat
    
    df = eurostat.get_data_df(code, flags=flags)
    
    df = df.rename({r'geo\TIME_PERIOD':'geo'}, axis=1)
    df = df.rename({r'indicators\TIME_PERIOD':'inc'}, axis=1)
    
    df = set_index(df)
    df.columns = df.columns.astype(int)
    
    if 'freq' in df.index.names:
        df = df.xs('A', 0, 'freq')
        
    df = stack(df, 'year')
    
    if filter_on:
        for key in filter_on:
            df = df.xs(filter_on[key], 0, key)
        
    df = sort(df)           
       
    return df

def read_index(name):
    ''' Read index.

    '''
    path = get_path('index', 'root', 'xlsx')

    ix = (pd.read_excel(path, dtype=str, sheet_name=name)).iloc[:,0]
   
          
    return ix

def read_key(key, target=None, original=None, full=False):
    ''' Load conversion key from file and convert it to a series suitable 
    for mapping the data from the original to the target classification.
    

    Parameters
    ----------
    key : string
        Specifies the name of the conversion key/original starting classification. 
    target : string
        Specifies the target classification. 
        
    Returns
    -------
    ck : Pandas series 
        Returns a Pandas series containing a mapping between the
        original and the target classification.

    '''
    path = get_path('keys', 'root', 'xlsx')

    ck = pd.read_excel(path, dtype=str, sheet_name=key, keep_default_na=False, skiprows=1)
    
    if original:
        key = original

    if target:
        columns = [key, target]
        ck = ck.loc[:, columns]
        
    if full is False:
        ck = (ck.set_index(key)
        .iloc[:, 0])
        
    if original:
        ck = ck[ck.index.duplicated(keep='first')==False]
    
    # country conversion key contains missing values for ISO2 codes (:)
    # which need to be removed (values not required for conversion from ISO2 to other classifications)
        
    if key=='iso2':
        ck = ck[ck.index.duplicated(keep='first')==False]
           
    return ck

def reindex(df, level, new_index=None, keep_old=False, axis=0):
    """
    Reindex single level of Pandas dataframe (Pandas reindex function does not 
    insert new values if single level is reindexed)

    Parameters
    ----------
    df : Pandas Dataframe with MultiIndex
        
    new_index : Pandas series, list or string.
        New index for the level to be reindexed. If string, serves as input to function 
        read index. If none, defaults to RME182.
    keep_old : Boolean
        Determines whether values from the old index not present in 
        the new index are deleted or kept.
    level : Integer
        Index level to be reindexed.

    Returns
    -------
    df : Pandas dataframe
        
    """
        
    if new_index is None:
        new_index = read_index('rme')
        new_index = new_index[new_index.str.len()==6]
    else:
        if isinstance(new_index, str):
            new_index = read_index(new_index)
                    
    if keep_old :
        l = pd.Index(set([*df.level(level, axis=axis).unique(), *new_index]))    
    else: 
        l = pd.Index(new_index)
    
    l = sorted(l, key=lambda x: order[x] if x in order else 999)
    
    if axis==0:        
       
        t = [df.level(i).unique() for i in range(df.index.nlevels)]
        
        t[df.index.names.index(level)] = l
            
        s = pd.MultiIndex.from_product(t, names=df.index.names)
        df = df.reindex(s)
        
    if axis==1:
        
        t = [df.level(i, axis=1).unique() for i in range(df.columns.nlevels)]
        
        t[df.columns.names.index(level)] = l
            
        s = pd.MultiIndex.from_product(t, names=df.columns.names)
        df = df.reindex(s, axis=1)
        
    df = sort(df)

    return df

def rename(df, dic, axis=0):
    """Rename index or column level names.

    Parameters
    ----------
    df : DataFrame or Series
        Object whose axis names are to be renamed.
    dic : dict
        Dictionary mapping old axis names to new axis names.
    axis : int, default 0
        Axis whose names are changed. Use 0 for index names and 1
        for column names.

    Returns
    -------
    DataFrame or Series
        Object with renamed axis names. """

    if axis==0:
        df = df.rename_axis(index=dic)

    if axis==1:
        df = df.rename_axis(columns=dic)

    return df

# =============================================================================
# def replace(df, dic=None):
#     """Replace values in row or column index and in column and index names e.g. to harmonize CPA codes or countries.
#     """      
#   
#     if dic==None:
#         dic = (pd.read_excel(get_path('replacements', 'rme_tools', 'xlsx'), index_col='original').iloc[:,0].to_dict())
#     
#    # Replace row/column labels
# 
#     # Helper: map single Index or MultiIndex (level-wise)
#     def map_idx(idx):
#         if isinstance(idx, pd.MultiIndex):
#             return idx.set_levels([lvl.map(lambda x: dic.get(x, x)) for lvl in idx.levels])
#         return idx.map(lambda x: dic.get(x, x))
# 
#     df.index = map_idx(df.index)
#     df.columns = map_idx(df.columns)
# 
#     # Replace axis names
#     if isinstance(df.index, pd.MultiIndex):
#         df.index.names = [dic.get(n, n) for n in df.index.names]
#     else:
#         if df.index.name is not None:
#             df.index.name = dic.get(df.index.name, df.index.name)
# 
#     if isinstance(df.columns, pd.MultiIndex):
#         df.columns.names = [dic.get(n, n) for n in df.columns.names]
#     else:
#         if df.columns.name is not None:
#             df.columns.name = dic.get(df.columns.name, df.columns.name)
# 
# 
#     return df
# =============================================================================

# OLD VERSION:

def replace(df, dic=None):
    """Replace values in row or column index and in column and index names e.g. to harmonize CPA codes or countries.
    """      
  
    if dic==None:
        dic = (pd.read_excel(get_path('replacements', 'rme_tools', 'xlsx'), index_col='original').iloc[:,0].to_dict())
    
    df = df.rename(dic, axis=1)
    df = df.rename(dic, axis=0)        
    df = df.rename_axis(index=dic, columns=dic)
       
    # df.loc[:, df.dtypes == object] = df.loc[:, df.dtypes == object].replace(dic)
    
    return df

def save(df, name, folder='intermediate', format='fixed'):
    """
    Save a DataFrame to an HDF file.

    Parameters
    ----------
    df : DataFrame
        DataFrame to save.
    name : str
        File name and HDF key.
    folder : str, default 'intermediate'
        Folder where the file is stored.
    format : str, default 'fixed'
        Storage format passed to ``DataFrame.to_hdf()``.

    Returns
    -------
    None"""
    
    path = get_path(name, folder)

    df.to_hdf(path, key=name, format=format)
    
def save_compressed(df, name, folder='intermediate', complib='blosc:zstd', 
                    complevel=5, format='fixed'):
    """
    Save a DataFrame to an HDF file.

    Parameters
    ----------
    df : DataFrame
        DataFrame to save.
    name : str
        File name and HDF key.
    folder : str, default 'intermediate'
        Folder where the file is stored.
    complib: blosc:zstd
        Fast and compresses well
    complevel : int in [0..9], default 0
        Compression level
    format : str, 'table'
        Storage format passed to ``DataFrame.to_hdf()``.

    Returns
    -------
    None"""
    
    path = get_path(name, folder)

    with pd.HDFStore(path, mode='w', complevel=complevel, complib=complib) as store:
        store.put(name, df, format=format)

    
def scale (df, right, on, value_col='value'):
    """Scale values."""
    
    df = df.assign(initial_sum=df.groupby(on)[value_col].transform('sum'))
    df = df.assign(target_sum=lambda x: x.join(right, on=on, rsuffix='_y')[value_col + '_y'],
                   scaling_factor=lambda x: x['target_sum']/x['initial_sum'])
    df.loc[(df['initial_sum']==0) | (df['target_sum']==0), 'scaling_factor'] = 0
    df = df.assign(scaled_value=lambda x: x[value_col]*x['scaling_factor'])
    df = df.assign(final_sum=df.groupby(on)['scaled_value'].transform('sum'))
    
    check = df[['target_sum', 'final_sum']].groupby(on).sum()
    check = check[~(check['target_sum'].round(0)==check['final_sum'].round(0))]
        
    if check.shape[0]>0:
       print ('Scaling error: There are deviations between the target sum and the final sum.', check)
    
    return df

def set_index(df: pd.DataFrame):
    """
    Set likely identifier columns as index and sort the result.

    Parameters
    ----------
    df : DataFrame
        DataFrame containing identifier columns and value columns.

    Returns
    -------
    DataFrame
        DataFrame with selected index columns set as index and sorted.
    """
    
    ls = df.select_dtypes(include=['int64', 'int32', object]).columns.to_list()
    value_cols = ['source', 'value', 'weight', 'num_negatives', 'num_nan']
    index_cols = [x for x in ls if x not in value_cols]
    
    path = get_path(name='labels', folder='rme_tools', file_format='xlsx')
    
    order = pd.read_excel(path, index_col='item').iloc[:,0].to_dict()

    index_cols = sorted(index_cols, key=lambda x: order[x] if x in order else 999)
    if ls:
        df = df.set_index(index_cols)
    
    df = sort(df)
    
    return df

def split_row(df, row_to_split, split, level=0):
    """
    Split level value into two or more values in a MultiIndex datafrae,
    can be used to disaggregate rows if shares are known.

    Parameters
    ----------
    df : Pandas dataframe
        dataframe with 2-4 column levels
    row_to_split : String
        indentifier of the level value to split
    split : Dict
        Dictionary containing the new codes as well as the corresponding shares
        e.g {'RME001' : 0.4}
    level : integer
        Level of the level value for splitting

    Returns
    -------
    Pandas dataframe.

    """
    if level != 0:
       df = df.swaplevel(0, level)
    
    if df.index.nlevels==2:
        a, b = df.index.levels
        df = df.reindex(pd.MultiIndex.from_product([[*a, *split.keys()], b], names=df.index.names))
    
    if df.index.nlevels==3: 
        a, b, c = df.index.levels
        df = df.reindex(pd.MultiIndex.from_product([[*a, *split.keys()], b, c], names=df.index.names))
        
    if df.index.nlevels==4: 
        a, b, c, d = df.index.levels
        df = df.reindex(pd.MultiIndex.from_product([[*a, *split.keys()], b, c, d], names=df.index.names))
        
    df = df.unstack(level=0)    
        
    df.columns = df.columns.droplevel(level=0)
    keys, values = zip(*split.items()) 
    
    for i in range(len(keys)):
        df[keys[i]] = values[i] * df[row_to_split]  
    
    df = df.drop(columns=row_to_split)
    df = pd.DataFrame(df.stack()).rename(columns={0:'value'})
    
    return df


def sort(df, sort_levels=True):
    """
    Sort dataframe or series levels by custom sort order defined in the file 'labels.xlsx'.

    Only values in index levels and the order of columns and levels (if sort_levels=True) 
    are sorted. The order of values in columns is not affected. Items that are not defined 
    in the file 'labels.xlsx' are moved to the end.

    Parameters
    ----------
    df : DataFrame        
        DataFrame with levels to sort. 
    sort_levels : bool, default True
        If True, sort order of levels.
        
    Returns
    -------
    DataFrame
        Sorted.    
    """
    
    oth = int(1e6)
    
    if sort_levels==True:
        # check if index is MultiIndex
        if len(df.index.names)>1:
            # reorder levels of MultiIndex according to a sorted list of index names
            df = df.reorder_levels(sorted(list(df.index.names),
                                          key=lambda x: order[x] if x in order else oth))
            
    # sort values in row index by sort order
    df = df.sort_index(axis=0, key=lambda idx: pd.Index([order.get(i, oth) for i in idx]))
        
    # check if data is in DataFrame
    if isinstance(df, pd.DataFrame):
        # sort columns/column index by sort order
        df = df.sort_index(axis=1, key=lambda idx: pd.Index([order.get(i, oth) for i in idx]))


    return df

def stack(df: pd.DataFrame, name=None, level=-1,  col_name='value'):
    """
    Stack a column level into the row index.

    Parameters
    ----------
    df : DataFrame
        DataFrame to be stacked.
    name : str, optional
        New name for the stacked level if the resulting level name is
        ``None``.
    level : str or int, default -1
        Column level to stack.
    col_name : str, default 'value'
        Column name to use if stacking returns a Series.

    Returns
    -------
    DataFrame
        Stacked and sorted DataFrame.
    """
    df = df.stack(level=level, future_stack=True)

    if name:
        df = rename(df, {None: name})

    if isinstance(df, pd.Series):
        df = df.to_frame(col_name)      
        
    df = sort(df)
  
    return df

def unstack(df: pd.DataFrame, level='year'):
    """
    Unstack one index level into columns.

    Parameters
    ----------
    df : DataFrame
        DataFrame with a MultiIndex.
    level : str or int, default 'year'
        Index level to move to the columns.

    Returns
    -------
    DataFrame
        Unstacked and sorted DataFrame.

    Notes
    -----
    If the unstacked result creates an unnecessary top column level,
    that level is removed."""
    
    if level in df.index.names:
        try:
            df = pd.DataFrame(df.unstack(level=level))            
            if df.columns.nlevels > 1:
                if len(df.columns.levels[0])==1:
                    df = df.droplevel(axis=1, level=0)
        except: 
            print('Remark: Error during unstack occured.')
                
        
    else:         
        print('Column for unstacking not found in index nor in list of columns.')
        print (df.info())
    
    df = sort(df)
        
    return df

def update(df: pd.DataFrame, source: pd.DataFrame, **update_kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns an updated copy of df using values from source,
    along with a DataFrame showing all changed cells.

    Parameters:
    ----------    
        df (pd.DataFrame): The original DataFrame to be copied and updated.
        source (pd.DataFrame): The DataFrame providing new values.
        **update_kwargs: Optional keyword arguments passed to DataFrame.update().

    Returns:
    ----------
        updated (pd.DataFrame): A new DataFrame with the applied updates.
        diff (pd.DataFrame): A DataFrame with MultiIndex (row index, column name)
                             and columns 'original' and 'updated' showing all changes.
    """
    # Work on a deep copy to avoid mutating the input
    updated = df.copy(deep=True)
    original = df.copy(deep=True)

    # Apply the update
    updated.update(source, **update_kwargs)

    # Identify changed cells (handling NaNs correctly)
    mask_diff = ~updated.eq(original) & ~(updated.isna() & original.isna())

    # Construct the diff DataFrame for changed cells only
    diff = (
        original[mask_diff]
        .stack()
        .rename("original")
        .to_frame()
        .join(updated[mask_diff].stack().rename("updated"))
    )

    return updated, diff

# load file with labels and sort order
order = read('labels', 'rme_tools', 'xlsx').set_index('item').iloc[:,0].to_dict()