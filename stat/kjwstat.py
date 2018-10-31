#!/usr/bin/python

import mysql.connector
from collections import OrderedDict,defaultdict
from countsyl import count_syllables
from operator import attrgetter

_vowels = "aeiouyåäöüóáéæø" #to be extended

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
    elif w[-1]=='s' and w[:-1] in ldict and lang=='eng':
        return ldict[w[:-1]]
    else:
        return [{'pattern': '?'*count_syllables(w, _vowels, lang)[0]}]

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

def _store_harmony(cnx, a, b, nr=1, table="Observations"):
    query = ("INSERT INTO Harmony"+table+" VALUES (%(a)s,%(b)s,%(nr)s) "
             "ON DUPLICATE KEY UPDATE nr=nr+%(nr)s")
    cursor = cnx.cursor()
    cursor.execute(query, {'a':a,'b':b,'nr':nr})
    cursor.close()

def _store_melody(cnx, a, b, stem='', nr=1, table="Observations"):
    query = ("INSERT INTO Melody"+table+" VALUES (%(a)s,%(b)s,%(stem)s,%(nr)s) "
             "ON DUPLICATE KEY UPDATE nr=nr+%(nr)s")
    cursor = cnx.cursor()
    cursor.execute(query, {'a':a,'b':b,'nr':nr,'stem':stem})
    cursor.close()

def store_harmony_observation(cnx, st, obs, nr=1):
    _store_harmony(cnx, st, obs, nr, "Observations")

def store_harmony_transition(cnx, a, b, nr=1):
    _store_harmony(cnx, a, b, nr, "Transitions")

def store_melody_observation(cnx, st, obs, nr=1, stem=''):
    _store_melody(cnx, st, obs, stem, nr, "Observations")

def store_melody_transition(cnx, a, b, nr=1, stem=''):
    _store_melody(cnx, a, b, stem, nr, "Transitions")

def get_harmony_emisson_probabilities(cnx, states=None):
    query_total = ("SELECT st,SUM(nr) FROM HarmonyObservations "+(" WHERE st IN %s" if states else '')+" GROUP BY st")
    cursor = cnx.cursor()
    if states:
        states = tuple(states)
        cursor.execute(query_total % (states,))
    else:
        cursor.execute(query_total)
    total_observations={stat: nr for (stat,nr) in cursor}
    cursor.close()
    query = ("SELECT st,obs,nr FROM HarmonyObservations"+(" WHERE st IN %s" if states else ''))
    cursor = cnx.cursor()
    if states:
        cursor.execute(query % (states,))
    else:
        cursor.execute(query)
    rval = {}
    for (state,obs,nr) in cursor:
        rval.setdefault(state,{})[obs] = (float)(nr / total_observations[state])
    cursor.close()
    return rval

def get_harmony_transition_probabilities(cnx, states=None, threshold=0.0):
    query_total = ("SELECT a,SUM(nr) FROM HarmonyTransitions "+(" WHERE a IN %s AND b IN %s" if states else '')+" GROUP BY a")
    cursor = cnx.cursor()
    if states:
        states = tuple(states)
        cursor.execute(query_total % (states,states))
    else:
        cursor.execute(query_total)
    total_transitions={a: nr for (a,nr) in cursor}
    cursor.close()
    query = ("SELECT a,b,nr FROM HarmonyTransitions"+(" WHERE a IN %s AND b IN %s" if states else '')+" ORDER BY a,a!=b,b")
    cursor = cnx.cursor()
    if states:
        cursor.execute(query % (tuple(states),tuple(states)))
    else:
        cursor.execute(query)
    rval, diff = {}, 0
    for (a,b,nr) in cursor:
        if threshold:
            if a==b and (nr > (float(total_transitions[a])*threshold)):
                diff = (nr - (float(total_transitions[a])*threshold))/(len(total_transitions)-1)
                nr = float(total_transitions[a]) * threshold
            elif diff:
                nr += diff
        rval.setdefault(a,{})[b] = (float)(nr / float(total_transitions[a]))
    cursor.close()
    return rval

def get_melody_emisson_probabilities(cnx, stem=''):
    query_total = ("SELECT st,SUM(nr) FROM MelodyObservations WHERE stem=%s GROUP BY st")
    cursor = cnx.cursor()
    cursor.execute(query_total, (stem,))
    total_observations={stat: nr for (stat,nr) in cursor}
    cursor.close()
    query = ("SELECT st,obs,nr FROM MelodyObservations WHERE stem=%s")
    cursor = cnx.cursor()
    cursor.execute(query, (stem,))
    rval = {}
    for (state,obs,nr) in cursor:
        rval.setdefault(state,{})[obs] = (nr / total_observations[state])
    cursor.close()
    return rval

def get_melody_transition_probabilities(cnx, stem='', threshold=0.0):
    query_total = ("SELECT a,SUM(nr) FROM MelodyTransitions WHERE stem=%s GROUP BY a")
    cursor = cnx.cursor()
    cursor.execute(query_total, (stem,))
    total_transitions={stat: nr for (stat,nr) in cursor}
    cursor.close()
    query = ("SELECT a,b,nr FROM MelodyTransitions WHERE stem=%s")
    cursor = cnx.cursor()
    cursor.execute(query, (stem,))
    rval, diff = {}, 0
    for (a,b,nr) in cursor:
        if threshold:
            if a==b and (nr > (float(total_transitions[a])*threshold)):
                diff = (nr - (float(total_transitions[a])*threshold))/(len(total_transitions)-1)
                nr = float(total_transitions[a]) * threshold
            elif diff:
                nr += diff
        rval.setdefault(a,{})[b] = (float)(nr / float(total_transitions[a]))
    cursor.close()
    return rval

def store_harmony(cnx, harm):
    prev = None
    observations = defaultdict(int)
    transitions = defaultdict(int)
    for (state, observation) in harm:
        observations[state, observation]+=1
        if prev:
            transitions[prev, state]+=1
        prev = state
    for (state,observation),nr in observations.items():
        store_harmony_observation(cnx, state, observation, nr)
    for (a,b),nr in transitions.items():
        store_harmony_transition(cnx, a, b, nr)

def store_melody(cnx, harm, stem):
    prev = None
    observations = defaultdict(int)
    transitions = defaultdict(int)
    for (state, observation) in harm:
        observations[state, observation]+=1
        if prev:
            transitions[prev, state]+=1
        prev = state
    for (state,observation),nr in observations.items():
        store_melody_observation(cnx, state, observation, nr, stem)
    for (a,b),nr in transitions.items():
        store_melody_transition(cnx, a, b, nr, stem)
