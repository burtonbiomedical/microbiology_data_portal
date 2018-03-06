import os
import errno
import json
import sys
import pandas as pd

def mkdir_p(path):
    try:
        os.makedirs(path, mode=0o777)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def read_in():
    lines = sys.stdin.readlines()
    return json.loads(lines[0])

def shred_string(x):
    if type(x) == dict:
        new_dict = {}
        if 'error' in x.keys():
            return x
        for key, value in x.items():
            try:
                new_dict[key] = value.split('user_data')[1]
            except:
                new_dict[key] = value.split('public')[1]
        return new_dict
    else:
        return x.split('user_data')[1]

def remove_drugs(df):
    new_df = df.copy()
    for col in df:
        if pd.isnull(df[col]).sum() > (df.shape[0]*0.95):
            new_df.drop(col, axis=1, inplace=True)
    return new_df
