# -*- coding: utf-8 -*-

import os
import sys
import json

#read json file
#single is True,devide words one by one
def read_json(file_name,single=True,verbose=True):
    json={}
    with open(file_name, 'r') as f:
        json = json.load(f)
    print(json)




if __name__ == '__main__':
    json_file='../../20170707.filtered.json.gz'
    json=read_json(json_file)

