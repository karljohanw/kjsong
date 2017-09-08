#!/usr/bin/python

import mysql.connector
from collections import OrderedDict
from countsyl import count_syllables
from operator import attrgetter

_vowels = "aeiouyåäöüóáéæø" #to be extended

_first_syl_stress=['hun','cze','fin','ice']
_penultima_stress=['epo','pol','wel','que']
_ultima_stress=['fre','tur','arm']

def db_maintain_connect():
    return mysql.connector.connect(host='localhost', user='updater', password='password',
                                   database='kjstats', charset='utf8', use_unicode = True)

def db_search_connect():
    return mysql.connector.connect(host='localhost', user='updater', password='password',
                                   database='kjstats', charset='utf8', use_unicode = True)

def get_lang_dict(cnx, lang):
    rdict={}
    cursor = cnx.cursor()
    query=("SELECT word,stress,distress,pattern,flag FROM Words WHERE lang=%s ORDER BY word,flag")
    cursor.execute(query, (lang,))
    for word,stress,distress,pattern,flag in cursor:
        tmp_dict = {"pattern":pattern if len(pattern)>1 else '!', "flag":flag, "stress": stress, "distress": distress}
        rdict.setdefault(word,[]).append(tmp_dict)
    cursor.close()
    return rdict

def detect_verse_feets_helper(wlist, syllable_info, metre):
    if not wlist and not metre:
        return [[]]
    if not wlist or not metre:
        raise IndexError("Metres or words left")
    (m,M) = syllable_info[wlist[0]]
    rval = []
    for i in range(m,M+1):
        if len(metre) < i:
            break
        new_item = (wlist[0],metre[0:i])
        try:
            tmp = detect_verse_feets_helper(wlist[1:], syllable_info, metre[i:])
            rval_help = [([new_item] + d) for d in tmp]
            rval+=rval_help
        except IndexError:
            pass
    return rval

def detect_verse_feets(sentence, metre, lang='eng', ldict={}, extra=0):
    wlist = sentence.lower().split()
    syllable_info = {w: get_word_syllables(ldict, w) or count_syllables(w, _vowels, lang) for w in wlist}
    if not extra:
        return detect_verse_feets_helper(wlist, syllable_info, metre)
    elif extra>0:
        mlen=len(metre)
        mkanda = (metre*(2 if extra>0 else 1))[:(mlen+extra)]
        mkandb = (metre*(2 if extra>0 else 1))[(mlen-extra):]
        a = detect_verse_feets_helper(wlist, syllable_info, mkanda)
        b = detect_verse_feets_helper(wlist, syllable_info, mkandb)
        #return a or b?
        return b

def get_word(ldict, w, lang='eng'):
    if w in ldict:
        rval = [l for l in ldict[w] if l['flag']==0]
        return rval if rval else ldict[w]
    elif (w[-2:]=="'s" or w[-2:]=="s'") and w[:-2] in ldict and lang=='eng':
        return ldict[w[:-2]]
    elif w[-1]=='s' and w[:-1] in ldict and lang=='eng':
        return ldict[w[:-1]]
    else:
        min_length, max_length = count_syllables(w, _vowels, lang)
        rval=[]
        fix_stress = None

        if lang in _ultima_stress or (lang=='epo' and w[-1]=="'"):
            fix_stress = -1
        elif lang in _penultima_stress:
            fix_stress = -2
        elif lang in _first_syl_stress:
            fix_stress = 0

        for i in range(min_length, max_length+1):
            pattern = ('?'*i) if ((fix_stress is None) or i==1) else ('U'*i)
            if lang=='fre' and i==max_length and (w[-1]=='e' or w[-2:]=='es'):
                fix_stress = -2
            if pattern and '?' not in pattern:
                pattern = (pattern[:fix_stress] + 'X' + (pattern[(fix_stress+1):] if fix_stress!=-1 else ''))
            rval.append({'pattern':  pattern})
        return rval

def get_word_syllables(ldict, w):
    rval = None
    if w in ldict:
        detect = [l['stress']+l['distress'] for l in ldict[w] if l['flag']==0]
        if detect:
            rval = (min(detect),max(detect))
    return rval
    
def get_ml_allocation(cnx, sentence, ldict, lang='eng'):
    wlist = sentence.lower().split()
    wdicts = [get_word(ldict, w, lang) for w in wlist]
    pattern = ['']
    for w in wdicts:
        orig_len = len(pattern)
        pattern = pattern*len(w)
        for i in range(0,len(pattern)):
            pattern[i] += w[(i//orig_len)]['pattern']
    return pattern
