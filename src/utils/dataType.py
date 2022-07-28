from typing import List
import numpy as np
import pandas as pd
from dateutil.parser import parse

def get_df_column_type(df_data, fuzz = False):
    """Return the data type of the input data frame

    Args:
        df_data (Pandas.DataFrame): input data table
        fuzz (bool, optional): [description]. Defaults to False.
        
    Return:
        (str): data type. "quantitative", "temporal", "ordinal", "nominal"
    """
    df = pd.DataFrame(df_data.columns.values, columns=['data_field'])
    df['data_type'] = df.apply(lambda row: get_data_type(df_data[row['data_field']].values.tolist()), axis=1)   
    return df

def get_data_type(values: List, fuzz=False):
    """Return the data type of the input list

    Args:
        values (List): input list
        fuzz (bool, optional): [description]. Defaults to False.
        
    Return:
        (str): data type. "quantitative", "temporal", "ordinal", "nominal"
    """
    if all(map(lambda x: is_date(x), values)):
        dataType = "temporal" ## temporal
    elif is_nominal(values):
        dataType = "ordinal" ## ordinal
    elif is_number(values):
        dataType = "quantitative" 
    elif is_string(values):
        dataType = "nominal"

    return dataType

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.
        :param string: str, string to check for date
        :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        try:
            ## for int, only allows four-digit time (i.e. year)
            cast_int = int(string)
            if len(str(cast_int)) == 4 and cast_int < 2100:
                return True
            else:
                return False
        except:
            pass
        parse(str(string), fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    
def is_number(l: List):
    """
        Return whether an input list is a number list
        :param l: List, list to check 
    """
    try: 
        [float(x) for x in l]
        return True
    except:
        return False
    
def is_nominal(l: List):
    """Return whether an input list is nominal 

    Args:
        l (List): [description]
    """
    if not is_number(l):
        return False
    
    l_diff = [l[n]-l[n-1] for n in range(1,len(l))]
    if len(np.unique(l_diff)) == 1 and len(l) > 2:
        return True
    else:
        return False

def is_string(l):
    """
        Return whether an input list is a string list
        :param l: List, list to check 
    """
    try: 
        [str(x) for x in l]
        return True
    except:
        return False    