#!/usr/bin/python

import etcs2ly, sys

txt = sys.stdin.read().splitlines()
dic = {}

for t in [t for t in txt if t and not t[0]=='#']:
    n, i, t, v = (t.replace(' ', '')).split(':',3)
    name = None if not n else n
    iden = None if not i else i
    time = None if not t else t
    #print(v, file=sys.stderr)
    if iden=='c':
        dic.setdefault(name, {'name': name})['code'] = v
    elif iden=='t':
        dic.setdefault(name, {'name': name})['rythm'] = [{'variant':None, 'time':time, 'code':v}]
    elif iden=='h':
        dic.setdefault(name, {'name': name})['harmony'] = [{'variant':None, 'code':v}]

sp = {s[0]:s[1] for s in [s.split(':') for s in ":';soprano:';alto:';tenor:;bass:".split(';')]}
rval = etcs2ly.etcs2ly(list(dic.values()), startpos=sp, tempo=100)
f = open('/tmp/edit.ly', 'w')
f.write(rval)  # python will convert \n to os.linesep
f.close()  # you can omit in most cases as the destructor will call it
