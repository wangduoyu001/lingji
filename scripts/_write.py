# python script
import sys, os
base = os.getcwd()
f = open(os.path.join(base, 'src', 'indexer', 'index.py'), 'w', encoding='utf-8')
f.write('import json')
