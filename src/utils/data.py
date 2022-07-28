from utils.dataType import get_data_type
import pandas as pd
from itertools import combinations

def union_data_df(df1, df2, how = 'left_on_conflict', force_merge = False, force_merge_prefix = ('chart1', 'chart2')):
    """
        Return the union of two data-frames
        
        Args:
            df1, df2 (pandas.DataFrame): a data frame
            how (str): how to handle the union operation
            - left: keep the left df
            - right: keep the right df
            - left_on_conflict: keep the left df if conflict
            - right_on_conflict: keep the right df if conflict
            force_merge (bool): if true. force merge with prefix 
        Return:
            (pandas.DataFrame | None): result. None if failed
    """    
    if not how in ['left', 'right', 'left_on_conflict', 'right_on_conflict', 'concat']:
        raise ValueError("how parameter must be one of ['left', 'right', 'left_on_conflict', 'right_on_conflict']")
    
    ## default return
    if how == 'left':
        return df1
    elif how == 'right':
        return df2
    
    if how == 'concat':
        if not '_filename' in df1:
            df1['_filename'] = force_merge_prefix[0]
        if not '_filename' in df2:
            df2['_filename'] = force_merge_prefix[1]
        return df1.merge(df2, how='outer')     
        
    column_relation = compare_data_df_columns(set(df1.columns), set(df2.columns))
    common_primary_keys = find_common_primary_keys(df1, df2)

    result_df = None
    on_conflict = False

    if column_relation in ["==", '<', '>']:   
        result_df = df1.merge(df2, how='outer')
        if not is_unique_key(result_df, common_primary_keys): ## if the primary keys are no longer unique, data conflicts occur
            on_conflict = True
            
            if force_merge:
                df1['_filename'] = force_merge_prefix[0]
                df2['_filename'] = force_merge_prefix[1]
                return df1.merge(df2, how='outer')
            else:
#                 df1['_indicator'] = 'left'
#                 df2['_indicator'] = 'right'
#                 df1.head()
                return df1.merge(df2, how='outer')
            
    elif column_relation == '||':     
        ## two data-frames have distinct columns
        if how == 'left_on_conflict':
            result_df = df1
        elif how == 'right_on_conflict':
            result_df = df2
        else:
            on_conflict = True
    elif column_relation == '∩':
        common_columns = list(set(df1.columns).intersection(set(df2.columns)))
        
        result_df = df1.merge(df2, how='outer', on=common_columns)

        if not is_unique_key(result_df, common_primary_keys): ## if the primary keys are no longer unique, data conflicts occur
            on_conflict = True

    ## return None if data conflicts            
    if on_conflict:
        return None
            
    return result_df

def difference_data_df(df1, df2, on_data = "all"):
    """
        Return the difference of two data-frames
        
        Args:
            df1, df2 (pandas.DataFrame): a data frame
            on_data (str): how to handle the operation
            - none: ignore 
            - key: on the common key
            - all: on all columns
        Return:
            (pandas.DataFrame | None): result. None if failed
    """   
    if not on_data in ['none', 'key', 'all']:
        raise ValueError("on_data parameter must be one of ['none', 'key', 'all'")
        
    if on_data == "none":
        return None

    on_keys = []
    resultdf = df1
    if on_data == "key":
        on_keys = find_common_primary_keys(df1, df2)
        resultdf = df1.merge(df2, on=on_keys, how = 'outer', indicator = True)
        resultdf['_merge'] = resultdf['_merge'].astype(str)
        
        for idx, r in resultdf.iterrows():
            if r['_merge'] == 'both':
                on_keys_values = r[on_keys]
                row1 = df1[df1[on_keys] == on_keys_values].to_dict('records')
                row2 = df2[df2[on_keys] == on_keys_values].to_dict('records')
                
                if row1 == row2:
                    resultdf.at[idx,'_merge'] = '=='
                else:
                    resultdf.at[idx,'_merge'] = 'conflict'
        resultdf = resultdf[resultdf['_merge'] != '==']
        
    elif on_data == 'all':
        on_keys = list(set(df1.columns).intersection(set(df2.columns)))
        resultdf = df1.merge(df2,on=on_keys, how = 'outer', indicator = True)
        resultdf = resultdf[resultdf['_merge'] != 'both'] ## 'both' means the same value in this case

    return resultdf  
    

def intersection_data_df(df1, df2, on_data = "all"):
    """
        Return the intersection of two data-frames
        
        Args:
            df1, df2 (pandas.DataFrame): a data frame
            on_data (str): how to handle the operation
            - none: ignore 
            - key: on the common key
            - all: on all columns
        Return:
            (pandas.DataFrame | None): result. None if failed
    """      
    if not on_data in ['none', 'key', 'all']:
        raise ValueError("on_data parameter must be one of ['none', 'key', 'all'")
        
    if on_data == "none":
        return None

    on_keys = []
    if on_data == "key":
        on_keys = find_common_primary_keys(df1, df2)
        df = df1.merge(df2, on = on_keys, how='inner', suffixes = ("_left", "_right"))
        return df
    elif on_data == 'all':
        on_keys = list(set(df1.columns).intersection(set(df2.columns)))
        return df1.merge(df2, how='inner', on = on_keys)
        
def is_unique_key(df, keys):
    """
        Check if the input keys are unique keys if df. 
        
        Args:
            df (pandas.DataFrame): a data frame
            keys (str[]): keys 
        Return:
            (Boolean): result
    """    
    if keys == None:
        return False
    return df.shape[0] == df[keys].drop_duplicates().shape[0]

def is_primary_key(df, keys):
    """
        Check if the input keys are primary keys if df. 
        
        Args:
            df (pandas.DataFrame): a data frame
            keys (str[]): keys 
        Return:
            (Boolean): result
    """
    if not is_unique_key(df, keys): ## primary keys must be unique keys
        return False

    ## assumption: we only consider "temporal", "ordinal", "nominal" data to be primary keys 
    for k in keys:
        datatype = get_data_type(df[k])
        if not datatype in ["temporal", "ordinal", "nominal"]:
            return False

    return True

def find_primary_key(df):
    """
        Find the primary key of a dataframe (ref: https://en.wikipedia.org/wiki/Primary_key)
        
        Args:
            df (pandas.DataFrame): a data frame
        Return:
            (str[] | None): the primary keys. None if not found.
    """
    ## enumerate all possible combinations of keys
    keys = df.columns.values
    keys = [k for k in keys if get_data_type(df[k]) in ["temporal", "ordinal", "nominal"] ] ## we only consider "temporal", "ordinal", "nominal" data to be primary keys 

    key_combinations = []
    for n_key in range(1, len(keys) + 1):
        key_combinations.extend([list(x) for x in combinations(keys, n_key)])  ## combinations return () which needs to be casted into []
    
    ## brute force solution: assuming an unique key is a primary key, which might be incorrect
    for candidate in key_combinations[::-1]:
        if is_primary_key(df, candidate):
            return candidate

    return None

def find_common_primary_keys(df1, df2):
    """
        Find the common primary key of two dataframes.
        
        Args:
            df1, df2 (pandas.DataFrame): a data frame
        Return:
            (str[] | None): the primary keys. None if not found.
    """
    common_keys = list(set(df1.columns).intersection(set(df2.columns)))
    common_keys = [k for k in common_keys if (get_data_type(df1[k]) in ["temporal", "ordinal", "nominal"]) and (get_data_type(df2[k]) in ["temporal", "ordinal", "nominal"])] ## we only consider "temporal", "ordinal", "nominal" data to be primary keys 

    key_combinations = []
    for n_key in range(1, len(common_keys) + 1):
        key_combinations.extend([list(x) for x in combinations(common_keys, n_key)])  ## combinations return () which needs to be casted into []
    
    for candidate in key_combinations[::-1]:
        if is_primary_key(df1, candidate) and is_primary_key(df2, candidate):
            return candidate
            
    return None
    
def is_dfs_equal(df1, df2):
    """
        Check if two df are equal, ignoring the column order

        Args:
            df1, df2 (pandas.DataFrame): the data frame
        Return:
            (Boolean)
    """
    try:
        pd.util.testing.assert_frame_equal(df1.sort_index(axis=1), df2.sort_index(axis=1), check_names=True)
        return True
    except:
        return False

def compare_data_df_rows(df1, df2):
    """
        Check the relationships the data rows
        
        Args:
            df1, df2 (pandas.DataFrame): the data frame
        Return:
            (str): '==' for identical, '<' for subset, '>' for superset, '∩' for intersection, '||' for distinct sets
    """

    ## Data columns must be the same to compare the rows
    column_relationship = compare_data_df_columns(set(df1.columns.values), set(df2.columns.values))
    if column_relationship != '==':
        raise ValueError()
        
    df = pd.merge(df1, df2, how='outer', indicator='Exist')
    merge_results = set(df['Exist'].unique())

    if merge_results == set(['both']):
        return '=='
    elif merge_results == set(['both', 'right_only']):
        return '<'
    elif merge_results == set(['both', 'left_only']):
        return '>'
    elif merge_results == set(['right_only', 'left_only']):
        return '||'
    elif merge_results == set(['both', 'right_only', 'left_only']):
        return '∩'
    return ValueError()

def compare_data_df_columns(cols_1, cols_2):
    """
        Check the relationships the data columns
        
        Args:
            cols_1, cols_2 (set): the data columns 
        Return:
            (str): '==' for identical, '<' for subset, '>' for superset, '∩' for intersection, '||' for distinct sets
    """
    if cols_1 == cols_2:
        return '=='
    elif cols_1.issubset(cols_2):
        return '<'
    elif cols_1.issuperset(cols_2):
        return '>'
    elif len(cols_1.intersection(cols_2)):
        return '∩'
    else:
        return '||'
