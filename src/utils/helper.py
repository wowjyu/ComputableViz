import pandas as pd
import json

def load_vSpec(file_path: str):
    return json.load(open(file_path, 'r'))

def flatten_json(y:dict) -> dict:
    """A helper function that flattens a json"""
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

def unflatten_json(y: dict) -> dict:
    """A helper function that unflattens a json"""
    out = {}
    
    def unflatten(x, keys, value):
        if len(keys) == 1:
            key = keys.pop()
            if key == '0':
                key = 0
                if isinstance(x, dict):
                    x = [{}]
            elif key.isnumeric():
                key = int(key)   
                if len(x) >= key:
                    x.append(value)
            x[key] = value
#             print(x, value)
        else:
            key = keys.pop()
            if key == '0':
                key = 0
                if isinstance(x, dict):
                    x = [{}]
            elif key.isnumeric():
                key = int(key)
                if len(x) >= key:
                    x.extend([{} for x in range(key+1-len(x))])
            else:
                if not key in x:
                    x[key] = {}
            
            x[key] = unflatten(x[key], keys, value)
#         print(x)
        return x

    for key, value in y.items():
        out = unflatten(out, key.split('_')[::-1], value)
        
    return out

# def unflatten_json(y: dict) -> dict:
#     """A helper function that unflattens a json"""
#     out = {}
    
#     def unflatten(x, keys, value):
#         if len(keys) == 1:
#             key = keys.pop()
#             if key == '0':
#                 key = 0
#                 if isinstance(x, dict):
#                     x = [{}]            
#             x[key] = value
#         else:
#             key = keys.pop()
#             if key == '0':
#                 key = 0
#                 if isinstance(x, dict):
#                     x = [{}]
#             else:
#                 if not key in x:
#                     print(x, key)
#                     x[key] = {}
            
#             x[key] = unflatten(x[key], keys, value)
#         return x

#     for key, value in y.items():
#         out = unflatten(out, key.split('_')[::-1], value)
        
#     return out
    
# assert unflatten_json(flatten_json(line1.vSpec['encoding'])) == line1.vSpec['encoding']

def vSpec_to_df(vSpec: dict):
    """
        Convert a part of vega-lite specificaiton (dict) into a data table.
        Nested keys will be concatenated by "_".

        Example:
        {'x':{'y': 1}} => ['x-y', 1]
    """
    df = pd.DataFrame.from_dict(flatten_json(vSpec), orient='index', columns=['value'])
    df.index.name = 'property'
    return df.reset_index()

def df_to_vSpec(df):
    """
        Reverse process of vSpec_to_df.

        Example:
        ['x-y', 1] => {'x':{'y': 1}}
    """
    out = {}
    for index, row in df.iterrows():
        out[row['property']] = row['value']
    return unflatten_json(out)

def get_encoding_field(df_encoding = None, df_transform = None):
    """
        Return a list of data fields as in "data" and "transform"
    """
    records = []
    
    if df_encoding is not None:
        for _, row in df_encoding.iterrows():
            r = row['value']
            if row['property'].endswith('field'):
                records.append({'field': r, 'type': 'encoding'})
        
    if df_transform is not None:
        for _, row in df_transform.iterrows():
            r = row['value']
            if row['property'].endswith('field'):
                records.append({'field': r, 'type': 'transform'})        
#             elif row['property'].endswith('as'):
#                 records.append({'field': r, 'type': 'transform_as'})             
            elif 'groupby' in row['property']:
                records.append({'field': r, 'type': 'transform'})
            
    return pd.DataFrame(records, columns = ['field', 'type'])    
    
    
    