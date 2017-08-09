#!/usr/bin/python

try:
    import Queue as queue
except:
    import queue
from fractions import gcd
from collections import OrderedDict

def quad_formula(ar,br,ur,xr, at,bt,ut,xt):
    a,b,u,x = ar*at, br*bt, at*ur + ut, at*xr + xt
    q = gcd(gcd(a,b),gcd(u,x))
    a,b,u,x = a//q, b//q, u//q, x//q
    if a==b:
        a,b=1,1
    return a,b,u,x

def graph_search(edges, start, max_penalty):
    visited = OrderedDict([(start,(1,1,0,0))])
    q = queue.Queue()
    q.put((start,(1,1,0,0)))
    while not q.empty():
        v,(ra,rb,ru,rx) = q.get()
        if v in edges:
            for w,(ta,tb,tu,tx) in edges[v].items():
                if w not in visited:
                    a,b,u,x = quad_formula(ra, rb, ru, rx, ta, tb, tu, tx)
                    if (u+x)/a <= max_penalty:
                        visited[w] = (a,b,u,x)
                        q.put((w,(a,b,u,x)))
    return visited

def graph_search_multi(edges, multi_start, max_penalty):
    visited = OrderedDict([(start,(start,1,1,0,0)) for start in multi_start])
    q = queue.Queue()
    for start in multi_start:
        q.put((start,(start,1,1,0,0)))
    while not q.empty():
        v,(nil,ra,rb,ru,rx) = q.get()
        if v in edges:
            for w,(ta,tb,tu,tx) in edges[v].items():
                if w not in visited:
                    a,b,u,x = quad_formula(ra, rb, ru, rx, ta, tb, tu, tx)
                    if (u+x)/a <= max_penalty:
                        visited[w] = (nil,a,b,u,x)
                        q.put((w,(nil,a,b,u,x)))
    return visited

def matching_semicolon(a,b):
    for i in range(0,len(a)):
        if a[i]==';' and b[i]!=';' or a[i]!=';' and b[i]==';':
            return False
    return True

def matching_letters(a,b):
    for i in range(0,len(a)):
        if not ((a[i] in 'UX' and b[i] in 'UX' and a[i]==b[i]) or (a[i] in ';-' and b[i] in ';-')):
            return False
    return True

def read_metres(cnx):
    cursor = cnx.cursor()
    query = ("SELECT metre,metre_key,metre_string FROM Metre")
    cursor.execute(query)
    rval = {i:(key,string) for (i,key,string) in cursor}
    cursor.close()
    return rval

def read_graph(cnx):
    cursor = cnx.cursor()
    query = ("SELECT A,i,B,j,U,X FROM Edge")
    cursor.execute(query)
    rval,sval = {},{}
    for (a,i,b,j,u,x) in cursor:
        rval.setdefault(a,{})[b] = (i,j,u,x)
        if a!=0:
            sval.setdefault(b,{})[a] = (j,i,u,x)
    cursor.close()
    return rval,sval

def replace_graph(cnx, edges, equal={}):
    cursor = cnx.cursor()
    query = ("DELETE FROM Edge")
    cursor.execute(query)
    vec = [(a,i,b,j,u,x) for a,rest_a in edges.items() for b,(i,j,u,x) in rest_a.items()]
    cursor = cnx.cursor()
    query = ("INSERT INTO Edge(A,i,B,j,U,X) VALUES(%s,%s,%s,%s,%s,%s)")
    cursor.executemany(query,vec)
    cursor.close()

def print_dict(dic):
    for k,value in dic.items():
        print(k,value)

#delete elements in dict a if its key exists in b
def keys_setminus(a,b):
    for key in b.keys():
        if key in a.keys(): del a[key]

def setminus_edges(edges):
    for a in edges.keys():
        for b in edges[a].keys():
            if b in edges: keys_setminus(edges[a], edges[b])
