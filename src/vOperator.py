import pandas as pd
import json
import copy
import os

from utils.dataType import get_data_type, get_df_column_type
from utils.helper import load_vSpec, vSpec_to_df, df_to_vSpec, get_encoding_field
import utils.data as udata
from IPython.display import display

def Vega(spec):
    bundle = {}
    bundle['application/vnd.vega.v5+json'] = spec
    display(bundle, raw=True)

def VegaLite(spec):
    bundle = {}
    bundle['application/vnd.vegalite.v4+json'] = spec
    display(bundle, raw=True)

class Chart:
    def __init__(self, fName = None, df_data = None, df_style = None, if_clean_data = True):
        if fName != None:
            self.fName = os.path.basename(fName).split('.')[0]
            self.vSpec = load_vSpec(os.path.abspath(fName))
            self.init_from_vSpec(self.vSpec)  
            self.if_clean_data = if_clean_data
        else:
            self.fName = None
            self.df_style = df_style
            self.vSpec = df_to_vSpec(df_style)
            self.if_clean_data = if_clean_data
            
            self.df_data = df_data
            self.vSpec['data'] = {'values': json.loads(df_data.to_json(orient="records"))}
            
        self.df_data_fields = get_df_column_type(self.df_data)
        
        ## Build relation table between data and style
        self.df_relation = self.df_data_fields.merge(self.df_style, left_on = 'data_field', right_on = 'value')

        ## Compute class keys
        self.class_keys = self._compute_class_keys()
        
        ## Post-processing
        self._postprocessing()
        
    def init_from_vSpec(self, vSpec):
        self.vSpec = vSpec
        
        ## Preprocessing to uniform "standard" formats
        self._preprocessing_vSpec(vSpec)
 
        ## Handle data
        self.df_data = pd.DataFrame.from_records(vSpec['data']['values'])
        
        ## Handle style
        vSpec = copy.deepcopy(vSpec)
        del vSpec['data']
        self.df_style = vSpec_to_df(vSpec)
        

    
    def _preprocessing_vSpec(self, vSpec: dict):
        ## Parse data str
        if isinstance(vSpec['data']['values'], str):
            vSpec['data']['values'] = json.loads(vSpec['data']['values'])
            
        ## Convery {'mark': m} to {'mark': {'type': m}} for convenience
        if 'mark' in vSpec and isinstance(vSpec['mark'], str):
            vMark = vSpec['mark']
            if vMark == 'circle':
                vMark = 'point'
            
            vSpec['mark'] = {
                'type': vMark
            }
            
    
    def _postprocessing(self):
        pass
        ## Remove data fields that are not encoded
        if self.if_clean_data:
            encoded_fields = list(set(self.df_relation['data_field'].values.tolist()))
        
            self.df_data_fields = self.df_data_fields[self.df_data_fields.data_field.apply(lambda x: x in encoded_fields)]
        
    def _compute_class_keys(self):
        """
            Compute the class keys. Class keys are columns that 1) are not encoded; and 2) have the same values
        """        
        try:
            candidates = [column for column in self.df_data if len(self.df_data[column].unique()) == 1]
            encoding_fields = list(set(self.df_relation['data_field'].values.tolist()))

            return [c for c in candidates if not c in encoding_fields]
        except: 
            return []
    
    def get_relation_keys(self):
        return self.df_relation['property'].values.tolist()
    
    def show(self):
        return VegaLite(self.vSpec)
    
def union_property_value_df(df1, df2, how = 'left_on_conflict'):
    if not how in ['left', 'right', 'left_on_conflict', 'right_on_conflict']:
        raise ValueError("how parameter must be one of ['left', 'right', 'left_on_conflict', 'right_on_conflict']")
    
    ## handle basic cases
    if how == 'left':
        return df1.copy()
    elif how == 'right':
        return df2.copy()
    elif how == 'left_on_conflict':
        return df1.set_index('property').combine_first(df2.set_index('property')).reset_index()
    elif how == 'right_on_conflict':
        return df2.set_index('property').combine_first(df1.set_index('property')).reset_index()   
    
def find_replicable_encoding(df, encoding_data_type):    
    ## try to find a match in the new df_data (with the same data_type)
    new_encoding_fields = df[df['data_type'] == encoding_data_type]
        
    if not new_encoding_fields.empty: ## if found, pick the first result
        new_encoding_field = new_encoding_fields.iloc[0]
    else: ## if cannot find data_columns with the same data type, assign one
        new_encoding_field = df.iloc[0] 
        
    return new_encoding_field['data_field'], new_encoding_field['data_type']    

def update_data_type(df_style, field, field_type):
    field_type_entry = field.split('_field')[0] + '_type'
    
    row = df_style['property'] == field_type_entry
    df_style.loc[row, 'value'] = field_type
    return df_style
        

def repair_relation(df_data, df_style, df_relations):
    field_mapping = {}
    df_data_columns = df_data.columns.values
    df_data_fields = get_df_column_type(df_data)
    
    for idx, row in df_relations.iterrows():
        prop = row['property']
        
        df_style_prop = df_style[df_style['property'] == prop]  

        if df_style_prop.empty:
            continue
        
        df_style_prop = df_style_prop.iloc[0]
        old_field = df_style_prop['value']
        if old_field in df_data_columns:
            new_field = old_field
            pass
        else:
            if old_field not in df_relations['data_field'].values.tolist():
                continue
            
            if old_field in field_mapping:
                new_field = field_mapping[old_field]
            else:
                new_field, new_type = find_replicable_encoding(df_data_fields, row['data_type'])
                df_style = update_data_type(df_style, new_field, new_type)
                
            df_style.loc[df_style['property'] == prop, 'value'] = new_field
            
            field_mapping[old_field] = new_field
        
        df_data_fields = df_data_fields[df_data_fields['data_field'] != new_field]
    

def auto_apply_encoding(df_data, df_style, new_keys_to_encode, auto_encoding_chanel):
    """Automatically apply encodings to new_keys_to_encode

    Args:
        df_data, df_style, df_mark (Pandas.DataFrame): input list
        new_keys_to_encode (List(str)): a list of keys (data columns) to encode
        
    Return:
        df_style
    """
    encoded_fields = [x.split('_')[0] for x in df_style['property'].tolist() if x.endswith('field')]
    candidate_fields = [auto_encoding_chanel, 'color', 'column', 'row', 'shape']
    
    vEncoding = df_to_vSpec(df_style)
    for k in new_keys_to_encode:    
        for f in candidate_fields:
            if not f in encoded_fields:
                vEncoding['encoding'][f] = {
                    'field': k,
                    'type': 'nominal'
                }
                encoded_fields.append(f)
                break
                
    return vSpec_to_df(vEncoding)

def union(left: Chart, right: Chart, how_data = "left_on_conflict",  how_style = "left_on_conflict", auto_encoding = False, force_merge_data = False):
    ## union basic df
    df_data = udata.union_data_df(left.df_data, right.df_data, how = how_data, force_merge_prefix = [left.fName, right.fName])
    df_style = union_property_value_df(left.df_style, right.df_style, how = how_style)
    
    if how_style == 'left':
        df_relations = left.df_relation
    elif how_style == 'right':
        df_relations = right.df_relation
    else:
        df_relations = pd.concat([left.df_relation, right.df_relation]) 
        
    repair_relation(df_data, df_style, df_relations)
    
    ## update encoding
    if auto_encoding != False:
        new_keys_to_encode = list(set(left.class_keys).intersection(right.class_keys))
        df_style = auto_apply_encoding(df_data, df_style, new_keys_to_encode, auto_encoding_chanel = auto_encoding)
    
#     df_style, df_transform = check_encoding(left, right, df_data, df_style, df_transform)
    
    result = Chart(df_style = df_style, df_data = df_data) 
    return result

def difference_property_value_df(df1, df2):
    df = df1.merge(df2, how='outer', on=['property'], indicator = True)
    
    df = df[df.apply(lambda x: x['value_x'] != x['value_y'], axis = 1)]
    return df

def intersection_property_value_df(df1, df2):
    df = df1.merge(df2, how='inner', on=['property'], indicator = True)    
    return df

def intersection(left: Chart, right: Chart, on_data = "all", on_style = "all"):
    ## union basic df
    df_data = udata.intersection_data_df(left.df_data, right.df_data, on_data = on_data)
    
    df_style = intersection_property_value_df(left.df_style, right.df_style)    

    return {"df_data": df_data, "df_style": df_style}


def difference(left: Chart, right: Chart, on_data = "all", on_style = "all"):
    ## union basic df
    df_data = udata.difference_data_df(left.df_data, right.df_data, on_data = on_data)
    
    df_style = difference_property_value_df(left.df_style, right.df_style)    

    return {"df_data": df_data, "df_style": df_style}