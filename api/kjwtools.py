#!/usr/bin/python

import datetime
import mysql.connector
import re
import kjwgraph
import difflib
import glob

from collections import OrderedDict
from datetime import date

local_tune_links_pwd = '../tuneLinks'

def to_footnote_object(txt):
    return [OrderedDict([('text',v[0])]) if len(v)==1 else OrderedDict([('id',v[0]),('text',v[1])]) for v in [a.split('=',1) for a in txt.split(';')]]

def from_footnote_object(obj):
    return ';'.join([o['id']+'='+o['text'] if 'id' in o else o['text'] for o in obj])

def line_object(lnr, line, cmnt=None, tabs=0, redundant=False, cmpr=False, syll=0):
    obj=OrderedDict([('no',lnr)])
    if tabs!=0: obj['tabs'] = tabs
    if cmpr: obj['compressable'] = True
    if redundant: obj['text'] = "*"+line+"*"
    else: obj['text'] = line
    if cmnt: obj['footnote'] = to_footnote_object(cmnt)
    if syll: obj['syllable-diff'] = syll
    return obj

def key_to_id(cnx, key, name, table):
    cursor = cnx.cursor()
    query = ("SELECT "+name+" FROM "+table+" WHERE "+name+"_key=%s")
    cursor.execute(query, (key,))
    r_id = cursor.fetchone()
    if r_id is None:
        raise KeyError("No such "+table+" key as %s!" % key)
    return r_id[0]

def lyric_key_to_id(cnx, key):
    return key_to_id(cnx, key, "lyric", "Lyric")

def songbook_key_to_id(cnx, key):
    return key_to_id(cnx, key, "sb", "Songbook")

def tune_key_to_id(cnx, key):
    return key_to_id(cnx, key, "tune", "Tune")

def person_key_to_id(cnx, key):
    return key_to_id(cnx, key, "person", "Person")

def metre_key_to_id(cnx, key):
    return key_to_id(cnx, key, "metre", "Metre")

def id_to_key(cnx, id, name, table):
    cursor = cnx.cursor()
    query = ("SELECT "+name+"_key FROM "+table+" WHERE "+name+"=%s")
    cursor.execute(query, (int(id),))
    r_key = cursor.fetchone()
    cursor.close()
    if r_key is None:
        raise KeyError("No such "+table+" id as %s!" % id)
    return r_key[0]

def lyric_id_to_key(cnx, key):
    return id_to_key(cnx, key, "lyric", "Lyric")

def songbook_id_to_key(cnx, key):
    return id_to_key(cnx, key, "sb", "Songbook")

def tune_id_to_key(cnx, key):
    return id_to_key(cnx, key, "tune", "Tune")

def person_id_to_key(cnx, key):
    return id_to_key(cnx, key, "person", "Person")

def metre_id_to_key(cnx, key):
    if key==0: return None
    return id_to_key(cnx, key, "metre", "Metre")

def bit_is_set(bitmap, bit):
    return bitmap & (1 << bit)

def set_bit(bitmap, bit):
    return bitmap | (1 << bit)

def unset_bit(bitmap, bit):
    return bitmap & (0xFF ^ (1 << bit))

def tweak_bit(bitmap, bit):
    return bitmap ^ (1 << bit)

def person_base_dict(cnx, person_key, pid, by, dy, cmnt):
    person = OrderedDict([('key', person_key)])
    cursor = cnx.cursor()
    query = ("SELECT nm FROM PersonName WHERE person=%s ORDER BY main DESC")
    cursor.execute(query, (pid,))
    vec = [nm for (nm,) in cursor]
    cursor.close()
    person['name'] = vec
    if by: person['birth'] = by
    if dy: person['death'] = dy
    if cmnt: person['comment'] = cmnt
    return person

def get_song_author(cnx, lyric_id, search_dict={}):
    cursor = cnx.cursor(buffered=True)
    to_merge = ["lyric=%(lyric)s"]
    search_dict['lyric']=lyric_id
    if 'var' in search_dict:
        to_merge.append("var=%(var)s")
    if 'lang' is search_dict:
        to_merge.append("lang=%(lang)s")
    query = ("SELECT lang,var,person_key,Person.person,birthYear,deathYear,yr,what,comment FROM "
             "Author JOIN Person ON Person.person=Author.person "
             "WHERE "+(' AND '.join(to_merge))+" ORDER BY var, yr, birthYear, person_key")
    cursor.execute(query, search_dict)
    authors = OrderedDict()
    for (lang, var, key, pid, by, dy, y, what, cmnt) in cursor:
        person= person_base_dict(cnx, key, pid, by, dy, cmnt)
        person['composed'] = y
        if what: person['what'] = what
        authors.setdefault((lang, var), []).append(person)
    cursor.close()
    return authors

def get_tune_composer(cnx, tune_id):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT person_key,Person.person,birthYear,deathYear,yr,comment,what FROM Composer JOIN "
             "Person ON Person.person=Composer.person WHERE tune=%s ORDER BY yr,birthYear,person_key")
    cursor.execute(query, (tune_id,))
    authors = []
    for (person_key, pid, by, dy, y, cmnt, what) in cursor:
        person= person_base_dict(cnx, person_key, pid, by, dy, cmnt)
        person['composed'] = y
        if what: person['what'] = what
        authors.append(person)
    cursor.close()
    return authors

def get_person_from_row_tuple(cnx, person_tuple, search = {}):
    (pid, pkey, by, dy, cmnt) = person_tuple
    person = person_base_dict(cnx, pkey, pid, by, dy, cmnt)
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Tune.tune,tune_key,ttl,yr,what FROM Composer JOIN Tune ON Tune.tune=Composer.tune WHERE person=%s")
    cursor.execute(query, (pid,))
    comps = []
    for (i,k,t,y,w) in cursor:
        comps.append(OrderedDict([('key',k), ('title',t), ('year',y), ('codes',get_tune_code(cnx, i)), ('links',get_tune_links(cnx, i, k))]))
        if w: comps[-1]['what'] = w
    cursor.close()
    to_merge, search_dict = get_song_search_tools(search)
    search_dict['person'] = pid
    query = ("SELECT DISTINCT(Lyric.lyric), Lyric.lyric_key, Lyric.orig_lang, Lyric.metre, "
             "Lyric.loops, Author.lang, Author.var FROM Lyric JOIN Author ON "
             "Lyric.lyric=Author.lyric "+(' '.join(to_merge))+" WHERE Author.person=%(person)s "
             "ORDER BY Lyric.orig_lang=Author.lang, Author.yr, Lyric.lyric_key")
    cursor = cnx.cursor(buffered=True)
    cursor.execute("SET SESSION group_concat_max_len = 100000")
    cursor.execute(query, search_dict)
    songs = OrderedDict()
    songs_sdir = OrderedDict()
    for (l,k,o,m,t,lang,var) in cursor:
        songs_sdir.setdefault((l,k,o,m,t),[]).append((lang,var))
    cursor.close()
    songs = [get_song_from_row_tuple(cnx, (l,k,o,m,t), {'langvars':langvars}) for ((l,k,o,m,t),langvars) in songs_sdir.items()]
    if songs: person['songs'] = songs
    if comps: person['tunes'] = comps
    return person

def replace_if(mystr, old, new, stmt):
    return mystr.replace(old,new) if stmt else mystr

def search_stmnt(dict, key):
    return ("%%%s%%" % replace_if(dict[key]['text'],' ','%', not 'exact' in dict[key] or not dict[key]['exact']))

def get_person_search_tools(search = {}):
    to_merge = []
    search_dict = {}
    join_by = ' OR ' if 'match' in search and search['match']=='any' else ' AND '
    if 'name' in search:
        to_merge.append("LOWER(nm) LIKE LOWER(%(name)s)")
        search_dict['nick'] = search_stmnt(search, 'name')
    if 'birth' in search:
        to_merge.append("birthYear BETWEEN %(birthMin)s AND %(birthMax)s")
        if 'exact' in search['birth']:
            search_dict['birthMin'] = search['birth']['min']
            search_dict['birthMax'] = search['birth']['min']
        else:
            search_dict['birthMin'] = search['birth'].get('min',-2147483648)
            search_dict['birthMax'] = search['birth'].get('max',2147483647)
    if 'death' in search:
        to_merge.append("deathYear BETWEEN %(deathMin)s AND %(deathMax)s")
        if 'exact' in search['death']:
            search_dict['deathMin'] = search['death']['min']
            search_dict['deathMax'] = search['death']['min']
        else:
            search_dict['deathMin'] = search['death'].get('min', -2147483648)
            search_dict['deathMax'] = search['death'].get('max', 2147483647)
    return (to_merge, search_dict, join_by)

def set_person(cnx, person):
    key = person['key']
    by =  person.get('birth', None)
    dy =  person.get('death', None)
    cmnt = person.get('comment', None)
    return (by, dy, cmnt, key)

def update_or_insert_names(cnx, publ_data):
    update_publ_query = ("UPDATE PersonName SET main=%s WHERE person=%s AND nm=%s")
    insert_publ_query = ("INSERT INTO PersonName(main,person,nm) VALUES (%s,%s,%s)")
    for publ in publ_data:
        cursor = cnx.cursor()
        try:
            cursor.execute(insert_publ_query, publ)
        except mysql.connector.errors.IntegrityError:
            cursor.execute(update_publ_query, publ)
        cursor.close()

def get_song_publications(cnx, lyric_id, search_dict={}):
    cursor = cnx.cursor()
    to_merge = ["lyric=%(lyric)s"]
    search_dict['lyric'] = lyric_id
    if 'var' in search_dict:
        to_merge.append("var=%(var)s")
    if 'lang' in search_dict:
        to_merge.append("lang=%(lang)s")
    query = ("SELECT lang, var, sb_key, Songbook.ttl, yr, entry, tune_key, Tune.ttl, Publ.comment "
             "FROM Songbook JOIN Publ ON Publ.sb=Songbook.sb JOIN Tune ON Tune.tune=Publ.tune "
             "WHERE "+(' AND '.join(to_merge))+" ORDER BY yr, Songbook.ttl, entry")
    cursor.execute(query, search_dict)
    publs = OrderedDict()
    for (lang, var, sb_key, sb_ttl, yr, entry, tune_key, tune_ttl, cmnt) in cursor:
        publ = OrderedDict([('book', OrderedDict([('key', sb_key), ('title', sb_ttl), ('year', yr)])),
                            ('entry', entry),
                            ('tune', OrderedDict([('key', tune_key), ('title', tune_ttl)]))])
        if cmnt: publ['comment'] = cmnt
        publs.setdefault((lang,var), []).append(publ)
    cursor.close()
    return publs

def get_songbook_publications(cnx, songbook_id):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Publ.lyric, lyric_key, lang, var, entry, tune_key, ttl, Publ.comment, "
             "orig_lang, Lyric.metre, Lyric.loops FROM Publ JOIN Lyric ON Lyric.lyric=Publ.lyric "
             "JOIN Tune ON Tune.tune=Publ.tune WHERE sb=%s ORDER BY entry")
    cursor.execute(query, (songbook_id,))
    publs = []
    for (lyric_id, key, lang, var, entry, tune_key,tune_ttl, cmnt, orig, metre,loops) in cursor:
        song_dict = get_song_from_row_tuple(cnx, (lyric_id,key, orig, metre,loops), {'lang':lang, 'var':var,'nopubl':True})
        publ = OrderedDict([('entry', entry), ('song', song_dict),
                            ('tune', OrderedDict([('key', tune_key), ('title', tune_ttl)]))])
        if cmnt: publ['comment'] = cmnt
        publs.append(publ)
    cursor.close()
    return publs

def get_tune_publications(cnx, tune_id):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Publ.lyric, lyric_key, lang, var, sb_key,Songbook.ttl, yr, entry, Publ.comment, "
             "orig_lang, Lyric.metre, Lyric.loops FROM Publ JOIN Lyric ON Lyric.lyric=Publ.lyric "
             "JOIN Songbook ON Publ.sb=Songbook.sb WHERE tune=%s ORDER BY entry")
    cursor.execute(query, (tune_id,))
    song_dicts = {}
    publs = []
    for (lyric_id, key, lang, var, sb_key,sb_ttl, yr, entry, cmnt, orig, metre,loops) in cursor:
        if not lyric_id in song_dicts:
            song_dicts[lyric_id] = get_song_from_row_tuple(cnx, (lyric_id, key, orig, metre,loops), {'lang':lang, 'var':var,'nopubl':True})
        to_append = OrderedDict([('book', OrderedDict([('key', sb_key), ('title', sb_ttl), ('year', yr)])), ('entry', entry)])
        if cmnt: to_append['comment'] = cmnt
        song_dicts[lyric_id].setdefault('books',[]).append(to_append)
    cursor.close()
    return [val for val in song_dicts.values()]

def get_tune_links(cnx, tune_id, tune_key):
    local_stuff = [(o.split('/')[-1],o) for o in glob.glob(local_tune_links_pwd+"/"+tune_key+"/*")]
    local_links = [OrderedDict([('format',f.split('.')[1].upper()), ('description', f.split('.')[0]), ('url', p), ('local', True)]) for (f,p) in local_stuff]
    cursor = cnx.cursor()
    query = ("SELECT format, descr, url FROM TuneLinks WHERE tune=%s ORDER BY format, descr, url")
    cursor.execute(query, (tune_id,))
    links = [OrderedDict([('format',f), ('description',d), ('url',url)]) for (f, d, url) in cursor]
    cursor.close()
    return local_links + links

def get_tune_code(cnx, tune_id):
    cursor = cnx.cursor()
    query = ("SELECT stem,var,nwns FROM TuneHarmony WHERE tune=%s ORDER BY stem,var")
    cursor.execute(query, (tune_id,))
    harm_dict = {}
    for s,v,harm in cursor:
        harm_dict.setdefault(s,[]).append(OrderedDict([('variant', None if not v else v),('code',harm)]))
    cursor.close()

    cursor = cnx.cursor()
    query = ("SELECT stem,var,k,len FROM TuneRythm WHERE tune=%s ORDER BY stem,var")
    cursor.execute(query, (tune_id,))
    len_dict = {}
    for s,l,k,rythm in cursor:
        len_dict.setdefault(s,[]).append(OrderedDict([('variant', None if not l else l),('time',k),('code',rythm)]))
    cursor.close()

    cursor = cnx.cursor()
    query = ("SELECT stem, code FROM TuneCode WHERE tune=%s ORDER BY stem")
    cursor.execute(query, (tune_id,))
    vector = []
    for s,c in cursor:
        tmp = OrderedDict([('name', None if not s else s),('code',c)])
        if s in harm_dict:
            tmp['harmony'] = harm_dict[s]
        if s in len_dict:
            tmp['rythm'] = len_dict[s]
        vector.append(tmp)
    cursor.close()
    return vector

def set_tune_code(cnx, tune_id, code_dicts):
    tcs, harms, rythms = [],[],[]
    for code_dict in code_dicts:
        nm = '' if not code_dict['name'] else code_dict['name']
        tcs.append((tune_id, nm, code_dict['code']))
        if 'harmony' in code_dict:
            for harm in code_dict['harmony']:
                if harm['code']:
                    harms.append((tune_id, nm, harm['variant'] if harm['variant'] else '', harm['code']))
        if 'rythm' in code_dict:
            for rythm in code_dict['rythm']:
                if rythm['code']:
                    rythms.append((tune_id, nm, (rythm['variant'] if rythm['variant'] else ''), rythm['time'], rythm['code']))
    cursor = cnx.cursor()
    query = ("DELETE FROM TuneHarmony WHERE tune=%s")
    cursor.execute(query, (tune_id,))
    cursor.close()
    cursor = cnx.cursor()
    query = ("DELETE FROM TuneRythm WHERE tune=%s")
    cursor.execute(query, (tune_id,))
    cursor.close()
    cursor = cnx.cursor()
    query = ("DELETE FROM TuneCode WHERE tune=%s")
    cursor.execute(query, (tune_id,))
    cursor.close()

    cursor = cnx.cursor()
    query = ("INSERT INTO TuneCode(tune,stem,code) VALUES(%s,%s,%s)")
    cursor.executemany(query, tcs)
    cursor.close()
    if harms:
        cursor = cnx.cursor()
        query = ("INSERT INTO TuneHarmony(tune,stem,var,nwns) VALUES(%s,%s,%s,%s)")
        cursor.executemany(query, harms)
        cursor.close()
    if rythms:
        cursor = cnx.cursor()
        query = ("INSERT INTO TuneRythm(tune,stem,var,k,len) VALUES(%s,%s,%s,%s,%s)")
        cursor.executemany(query, rythms)
        cursor.close()
    
def get_song_title(cnx, lyric_id, orig_lang, search_dict = {}):
    cursor = cnx.cursor()
    to_merge = ["lyric=%(lyric)s"]
    search_dict['lyric'] = lyric_id
    search_dict['origlang'] = orig_lang
    if 'var' in search_dict:
        to_merge.append("var=%(var)s")
    if 'lang' in search_dict:
        to_merge.append("lang=%(lang)s")
    query = ("SELECT lang,var,ttl FROM Title WHERE "+(' AND '.join(to_merge))+" ORDER BY "
             "(lang=%(origlang)s) DESC,lang,var,main DESC,ttl")
    cursor.execute(query, search_dict)
    titles = OrderedDict()
    for (lang, var, ttl) in cursor:
        titles.setdefault((lang,var), []).append(ttl)
    cursor.close()
    cursor = cnx.cursor()
    query = ("SELECT lang,var,GROUP_CONCAT(line SEPARATOR ' - ') FROM Line "
             "WHERE "+(' AND '.join(to_merge))+" AND type IN ('i','v','c') AND vnr IN (0,1) "
             "AND (lnr=1 OR (lnr=2 AND stat&(1<<4))) AND alt='' GROUP BY lang,var,vnr,type ORDER BY "
             "(lang=%(origlang)s) DESC, lang, var, vnr, "
             "CASE type WHEN 'i' THEN 1 WHEN 'v' THEN 2 ELSE 3 END")
    cursor.execute(query, search_dict)
    for (lang, var, first_line) in cursor:
        titles.setdefault((lang,var), []).append("*"+first_line.replace('*','')+"..*")
    cursor.close()
    return titles

def get_comments(cnx, trans, lyric_id, search_dict = {}):
    cursor = cnx.cursor()
    to_merge = ["lyric=%(lyric)s","trans=%(trans)s"]
    search_dict['lyric'] = lyric_id
    search_dict['trans'] = trans
    if 'var' in search_dict:
        to_merge.append("var=%(var)s")
    if 'lang' in search_dict:
        to_merge.append("lang=%(lang)s")
    query=("SELECT lang,var,cmnt FROM Comments WHERE "+(' AND '.join(to_merge))+" ORDER BY var")
    cursor.execute(query, search_dict)
    comments = {}
    for (lang, var, comment) in cursor: comments.setdefault((lang,var),[]).append(comment)
    cursor.close()
    return comments    

def get_song_id(cnx, id, orig_lang, search_dict={}):
    cursor = cnx.cursor()
    to_merge = ["lyric=%(lyric)s"]
    search_dict['lyric'] = id
    search_dict['origlang'] = orig_lang
    if 'var' in search_dict:
        to_merge.append("var=%(var)s")
    if 'lang' in search_dict:
        to_merge.append("lang=%(lang)s")
    if 'langvars' in search_dict:
        to_merge_tmp, idx = [], 0
        for (lang,var) in search_dict['langvars']:
            to_merge_tmp.append("(lang=%(lang"+str(idx)+")s AND var=%(var"+str(idx)+")s)")
            search_dict['lang'+str(idx)] = lang
            search_dict['var'+str(idx)] = var
            idx+=1
        to_merge.append('('+' OR '.join(to_merge_tmp)+')')
        del search_dict['langvars']
    query = ("SELECT lang, var, alt, type, vnr, vch, lnr, stat, line, cmnt FROM Line "
             "WHERE "+(' AND '.join(to_merge))+" ORDER BY (lang=%(origlang)s) DESC, lang, var, "
             "vnr, vch, CASE type WHEN 'i' THEN 1 WHEN 'v' THEN 2 WHEN 'b' THEN 3 "
             "WHEN 'c' THEN 4 WHEN 'o' THEN 5 ELSE 6 END, lnr, alt")
    cursor.execute(query, search_dict)
    lyrics = []
    base_verse = OrderedDict()
    lvl_one = OrderedDict()
    for (lang, var, alt, type, vnr, vch, lnr, status, line, cmnt) in cursor:
        if (lang,var) not in lvl_one:
            lvl_one[lang,var] = OrderedDict([((type,vnr,vch), [(lnr,alt,status,line,cmnt)])])
        else:
            if(type,vnr,vch) not in lvl_one[lang,var]:
                lvl_one[lang,var][type,vnr,vch] = [(lnr,alt,status,line,cmnt)]
            else:
                lvl_one[lang,var][type,vnr,vch].append((lnr,alt,status,line,cmnt))
    cursor.close()
    title_dict = get_song_title(cnx, id, orig_lang, search_dict)
    author_dict = get_song_author(cnx, id, search_dict)
    publ_dict = get_song_publications(cnx, id, search_dict) if not 'nopubl' in search_dict else {}
    trans_cmnt_dict = get_comments(cnx, True, id, search_dict)
    for (lang,var), lvl_two in lvl_one.items():
        lyric = OrderedDict()
        lyric['language']=lang
        if var: lyric['variant'] = var
        lyric['titles'] = (title_dict[lang,var] if (lang,var) in title_dict else [])
        lyric['authors'] = (author_dict[lang,var] if (lang,var) in author_dict else [])
        lyric['verses'] = []
        redundancy_dictionary = OrderedDict()
        base_refrain_dict = OrderedDict()
        my_alts = OrderedDict()
        for (typ,vnr,vch), lvl_three in lvl_two.items():
            verse = OrderedDict([('type',typ), ('no',str(vnr)+vch), ('lines', [])])
            for (lnr, alt, status, line, cmnt) in lvl_three:
                redundant = bit_is_set(status, 2)
                argument = bit_is_set(status, 3)
                compress = bit_is_set(status, 4)
                tabz = status & 0x03
                if bit_is_set(status,5): verse['supplement'] = True
                if bit_is_set(status,6) and bit_is_set(status,7):
                    verse['copyright'] = 'block'
                elif bit_is_set(status,6):
                    verse['copyright'] = 'permission'
                elif bit_is_set(status,7):
                    verse['copyright'] = 'royalty'
                syll = ((status >> 12) & 0x7) * (-1 if bit_is_set(status,15) else 1)
                if typ=='v':
                    #redundancy is only used in verses
                    pnr = 1 if not verse['lines'] else verse['lines'][-1]['no'] + 1
                    for rnr in range(pnr, lnr):
                        if rnr in redundancy_dictionary:
                            verse['lines'].append(redundancy_dictionary[rnr])
                if alt:
                    orig_words, all_new_words = verse['lines'][-1]['text'].strip('*').split(), line.split()
                    new_words,diff_words,tf = [w for w in all_new_words if w not in orig_words],[],0
                    if all_new_words!=new_words:
                        for word in new_words:
                            sf = line.find(word,tf)
                            tf = sf + len(word)
                            if diff_words and diff_words[-1]['to']+1==sf:
                                diff_words[-1]['to']=tf
                            else:
                                diff_words.append(OrderedDict([('from',sf),('to',tf)]))
                    alt_obj = OrderedDict([("alt",alt),("text",line)])
                    if diff_words and diff_words != orig_words: alt_obj['new_words_idx'] = diff_words
                    verse['lines'][-1].setdefault('alts',[]).append(alt_obj)
                    if syll: alt_obj['syllable-diff'] = syll
                    if redundant:
                        redundancy_dictionary[lnr].setdefault('alts',[]).append(alt_obj.copy())
                    if cmnt: alt_obj['footnote'] = to_footnote_object(cmnt)
                else:
                    if argument:
                        #this line has arguments
                        try:
                            cmp_line = base_refrain_dict[lnr] if typ=='c' else redundancy_dictionary[lnr]
                            argvec = re.findall(r'_([^_]*)_', line)
                            compvec = re.findall(r'_([^_]*)_', cmp_line['text'])
                            for i in range(0, len(argvec)):
                                if compvec[i]!=argvec[i]:
                                    tmp=OrderedDict([('from',compvec[i]),('to',argvec[i])])
                                    if 'args' not in verse or tmp not in verse['args']:
                                        verse.setdefault('args',[]).append(tmp)
                        except KeyError:
                            #missing "base" arguments, do noting
                            pass
                    this_line = line_object(lnr, line, cmnt, tabz, redundant, compress, syll)
                    verse['lines'].append(this_line)
                    if redundant:
                        redundancy_dictionary[lnr] = this_line.copy()
                        if 'footnote' in redundancy_dictionary[lnr]:
                            redundancy_dictionary[lnr].pop('footnote', None)
                        redundancy_dictionary[lnr]['redundant'] = True
                    elif argument and lnr in redundancy_dictionary:
                        this_line['redundant'] = True
            if typ=='v' and redundancy_dictionary:
                rnr = verse['lines'][-1]['no']+1
                while rnr in redundancy_dictionary:
                    #fill up with redundant lines
                    verse['lines'].append(redundancy_dictionary[rnr])
                    rnr=rnr+1
            elif typ=='c':
                if not base_refrain_dict:
                    for line in verse['lines']:
                        base_refrain_dict[line['no']] = line.copy()
                        base_refrain_dict[line['no']]['redundant'] = True
                else:
                    added_lines = [line['no'] for line in verse['lines']]
                    for line in base_refrain_dict.values():
                        if line['no'] not in added_lines:
                            verse['lines'].append(line)
                    verse['lines'] = sorted(verse['lines'], key=lambda line: line['no'])
            lyric['verses'].append(verse)
            for line in verse['lines']:
                if 'alts' in line:
                    tmp_list = [a['alt'] for a in line['alts']]
                    for a in tmp_list:
                        if a not in my_alts: my_alts[a] = []
                        my_alts[a] += [b for b in tmp_list if b not in my_alts[a] and a!=b]
        if not 'nopubl' in search_dict:
            lyric['publications'] = (publ_dict[lang,var] if (lang,var) in publ_dict else [])
        if my_alts:
            my_alt_jsonable_dict = OrderedDict([(k,list(v)) for k,v in my_alts.items() if v])
            if my_alt_jsonable_dict:
                lyric['conflicts'] = my_alt_jsonable_dict
        if (lang,var) in trans_cmnt_dict: lyric['comments'] = trans_cmnt_dict[lang,var]
        lyrics.append(lyric)
    return lyrics

def get_tune_dict_base(cnx, t_id, t_key, ttl, metre=None, loop=None):
    return OrderedDict([('key',t_key),('title',ttl),('composers',get_tune_composer(cnx, t_id)),('codes',get_tune_code(cnx, t_id)),('links',get_tune_links(cnx, t_id, t_key))])

def get_partial_metre_ids(cnx, metre):
    cursor = cnx.cursor()
    query = ("SELECT ord,part,loops FROM Part WHERE comp=%s ORDER BY ord")
    cursor.execute(query, (metre,))
    rval = {part:(order,loop) for (order,part,loop) in cursor}
    cursor.close()
    return rval

def get_song_metre_match(cnx, lyric_id, metre, loop):
    t_ids, publ_tunes = ['0'],[]
    
    #unnessecary below?
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT COUNT(*),Tune.tune, tune_key, ttl FROM Tune JOIN Publ ON Tune.tune=Publ.tune "
             "WHERE Publ.lyric=%s GROUP BY Tune.tune ORDER BY COUNT(*) DESC")
    cursor.execute(query, (lyric_id,))
    for (count, t_id, t_key, title) in cursor:
        t_ids.append(str(t_id))
        to_append = get_tune_dict_base(cnx, t_id, t_key, title)
        to_append['count'] = count
        to_append['published'] = True
        publ_tunes.append(to_append)
    cursor.close()

    edges,_ = kjwgraph.read_graph(cnx)
    result = kjwgraph.graph_search(edges, metre, 16)
    partial_metres = get_partial_metre_ids(cnx, metre)
    resultsplus = kjwgraph.graph_search_multi(edges, [m for m,_ in partial_metres.items()], 16)
    for m,(a,b,u,x) in result.items():
        get_song_metre_match_help(cnx, publ_tunes, t_ids, m, loop, u+x)
    for m,(n,a,b,u,x) in resultsplus.items():
        get_song_metre_match_help(cnx, publ_tunes, t_ids, m, partial_metres[n][1], u+x, partial_metres[n][0]+1)
    return sorted(publ_tunes, key=lambda k: (1 if 'partial' in k else 0, 0 if k.get('published', False) else 1, -k.get('count', 0), k.get('penalty', 0)))
    
def get_song_metre_match_help(cnx, publ_tunes, t_ids, metre, loop, ux, order=0):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT COUNT(*),Tune.tune,tune_key,ttl,(Lyric.loops=%s) FROM Lyric JOIN Publ "
             "ON Lyric.lyric=Publ.lyric JOIN Tune ON Publ.tune=Tune.tune WHERE Lyric.metre=%s AND "
             "Tune.tune NOT IN ("+','.join(t_ids)+") GROUP BY Tune.tune "
             "ORDER BY (Lyric.loops=%s) DESC, COUNT(*) DESC")
    cursor.execute(query, (loop, metre, loop))
    for (count, t_id, t_key, title, matches) in cursor:
        t_ids.append(str(t_id))
        to_append = get_tune_dict_base(cnx, t_id, t_key, title)
        if ux:
            to_append['penalty'] = ux
        else:
            to_append['count'] = count
        if order!=0:
            to_append['partial'] = {'song':order}
        publ_tunes.append(to_append)
    cursor.close()

    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Tune.tune,tune_key,ttl,Tune.loops FROM Tune WHERE metre=%s AND tune "
             "NOT IN ("+ ','.join(t_ids) +") ORDER BY (Tune.loops=%s) DESC")
    cursor.execute(query, (metre, loop))
    for (t_id, t_key, title, t_loop) in cursor:
        t_ids.append(str(t_id))
        to_append = get_tune_dict_base(cnx, t_id, t_key, title)
        to_append['penalty'] = ux*min(t_loop,loop)
        if order!=0:
            to_append['partial'] = {'song':order}
        publ_tunes.append(to_append)
    cursor.close()

    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Tune.tune,tune_key,ttl,Part.loops,Tune.loops,ord FROM Tune "
             "JOIN Part ON metre=comp "
             "WHERE part=%s AND Tune.tune NOT IN ("+ ','.join(t_ids) +") "
             "ORDER BY (Part.loops=%s) DESC")
    cursor.execute(query, (metre, loop))
    for (t_id, t_key, title, p_loop, t_loop, ood) in cursor:
        if str(t_id) not in t_ids:
            t_ids.append(str(t_id))
            to_append = get_tune_dict_base(cnx, t_id, t_key, title)
            to_append['penalty'] = ux*min(t_loop,p_loop) #*((loop*b)//(p_loop*a))
            to_append['partial'] = {'tune': ood + 1}
            if order!=0:
                to_append['partial']['song'] = order
            publ_tunes.append(to_append)
    cursor.close()

def delete_song_tags(cnx, lyric, tags):
    delete_query = ("DELETE FROM Keyword WHERE lyric=%s AND keyword=%s")
    if tags:
        cursor = cnx.cursor()
        cursor.executemany(delete_query, [(lyric,tag) for tag in tags])
        cursor.close()

def append_song_tags(cnx, lyric, tags):
    insert_query = ("INSERT IGNORE INTO Keyword(lyric,keyword) VALUES(%s,%s)")
    if tags:
        cursor = cnx.cursor()
        cursor.executemany(insert_query, [(lyric,tag) for tag in tags])
        cursor.close()
        
def renew_song_tags(cnx, lyric, tags):
    delete_query = ("DELETE FROM Keyword WHERE lyric=%s")
    if tags:
        cursor = cnx.cursor()
        cursor.execute(delete_query, (lyric,))
        cursor.close()
        append_song_tags(cnx, lyric, tags)

def get_song_tags(cnx, lyric):
    cursor = cnx.cursor()
    query = ("SELECT keyword FROM Keyword WHERE lyric=%s")
    cursor.execute(query, (lyric,))
    rvec = [keyword for (keyword,) in cursor]
    cursor.close()
    return rvec

def get_song_dict_tune_metre_match(cnx, l_id, l_key, orig_lang, metre=None, loop=None):
    title_dict = get_song_title(cnx, l_id, orig_lang, {})
    titles = []
    for (l,v),ttls in title_dict.items():
        to_append = OrderedDict()
        to_append['language']=l
        if v: to_append['variant']=v
        to_append['title'] = ttls
        titles.append(to_append)
    tags = get_song_tags(cnx, l_id)
    return OrderedDict([('key',l_key),('titles',titles),('tags',tags)])    

def get_tune_metre_match(cnx, tune_id, metre, loop):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT COUNT(*),Lyric.lyric,lyric_key,orig_lang FROM Lyric JOIN Publ ON "
             "Lyric.lyric=Publ.lyric WHERE Publ.tune=%s GROUP BY Lyric.lyric ORDER BY COUNT(*) DESC")
    cursor.execute(query, (tune_id,))
    l_ids, publ_songs = ['0'],[]
    for (count, l_id, l_key, orig_lang) in cursor:
        l_ids.append(str(l_id))
        to_append = get_song_dict_tune_metre_match(cnx, l_id, l_key, orig_lang)
        to_append['count'] = count
        to_append['published'] = True
        publ_songs.append(to_append)
    cursor.close()

    # improve time complexity by not read graph from db everytime?
    _,edges = kjwgraph.read_graph(cnx)
    result = kjwgraph.graph_search(edges, metre, 16)
    partial_metres = get_partial_metre_ids(cnx, metre)
    resultsplus = kjwgraph.graph_search_multi(edges, [m for m,_ in partial_metres.items()], 16)
    for m,(a,b,u,x) in result.items():
        get_tune_metre_match_full(cnx, publ_songs, l_ids, m, loop, u+x)
    for m,(n,a,b,u,x) in resultsplus.items():
        get_tune_metre_match_full(cnx, publ_songs, l_ids, m, partial_metres[n][1], u+x, partial_metres[n][0]+1)
    return sorted(publ_songs, key=lambda k: (1 if 'partial' in k else 0, 0 if 'published' in k and k['published'] else 1, -k['count'] if 'count' in k else 0, k['penalty'] if 'penalty' in k else 0))

def get_tune_metre_match_full(cnx, publ_songs, l_ids, metre, loop, ux, order=0):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT COUNT(*),Lyric.lyric,lyric_key,orig_lang,(Tune.loops=%s) FROM Lyric JOIN Publ "
             "ON Lyric.lyric=Publ.lyric JOIN Tune ON Publ.lyric=Tune.tune WHERE Tune.metre=%s AND "
             "Lyric.lyric NOT IN ("+ ','.join(l_ids) +") GROUP BY Lyric.lyric "
             "ORDER BY (Tune.loops=%s) DESC, COUNT(*) DESC")
    cursor.execute(query, (loop, metre, loop))
    for (count, l_id, l_key, orig_lang, matches) in cursor:
        l_ids.append(str(l_id))
        to_append = get_song_dict_tune_metre_match(cnx, l_id, l_key, orig_lang)
        if ux:
            to_append['penalty'] = ux
        else:
            to_append['count'] = count
        if order!=0:
            to_append['partial'] = {'tune':order}
        publ_songs.append(to_append)
    cursor.close()

    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Lyric.lyric,lyric_key,orig_lang,Lyric.loops FROM Lyric WHERE metre=%s "
             "AND Lyric.lyric NOT IN ("+ ','.join(l_ids) +") ORDER BY (Lyric.loops=%s) DESC")
    cursor.execute(query, (metre, loop))
    for (l_id, l_key, orig_lang, l_loop) in cursor:
        l_ids.append(str(l_id))
        to_append = get_song_dict_tune_metre_match(cnx, l_id, l_key, orig_lang)
        to_append['penalty'] = ux*min(l_loop,loop)
        if order!=0:
            to_append['partial'] = {'tune':order}
        publ_songs.append(to_append)
    cursor.close()

    cursor = cnx.cursor(buffered=True)
    query = ("SELECT Lyric.lyric,lyric_key,orig_lang,Part.loops,Lyric.loops,ord FROM Lyric "
             "JOIN Part ON metre=comp "
             "WHERE part=%s AND Lyric.lyric NOT IN ("+ ','.join(l_ids) +") "
             "ORDER BY (Part.loops=%s) DESC")
    cursor.execute(query, (metre, loop))
    for (l_id, l_key, orig_lang, p_loop, l_loop, ood) in cursor:
        if str(l_id) not in l_ids:
            l_ids.append(str(l_id))
            to_append = get_song_dict_tune_metre_match(cnx, l_id, l_key, orig_lang)
            to_append['penalty'] = ux*min(l_loop,loop) #*(loop*b)//(p_loop*a)
            to_append['partial'] = {'song':ood+1}
            if order!=0:
                to_append['partial']['tune'] = order
            publ_songs.append(to_append)
    cursor.close()

def get_metre_vector(cnx,metre,loops):
    metre_vec = find_metre_ids(cnx,metre)
    if not metre_vec:
        _,metre_key,metre_string = find_metre_id(cnx, metre)
        metre_vec = [OrderedDict([('name',OrderedDict([('key',metre_key),('string',metre_string)])),('times', loops)])]
    return metre_vec

def get_song_from_row_tuple(cnx, row_tuple, search_dict = {}):
    (id, key, orig_lang, metre, loops) = row_tuple
    song = OrderedDict([('key',key), ('lyrics', get_song_id(cnx, id, orig_lang, search_dict))])
    if 'var' not in search_dict and 'lang' not in search_dict and 'lang0' not in search_dict:
        song['metre'] = get_metre_vector(cnx, metre, loops)
        if 'exclude-matches' not in search_dict:
            song['tunes'] = get_song_metre_match(cnx, id, metre, loops)
        cmnt_dict = get_comments(cnx, False, id, search_dict)
        if cmnt_dict:
            song['comments'] = [OrderedDict([('language',l), ('comment',c[0])]) for (l,_),c in cmnt_dict.items()]
    
    tag_list = get_song_tags(cnx, id)
    if tag_list: song['tags'] = tag_list
    return song

def get_song_most_matching_key(cnx, key):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT lyric,lyric_key,orig_lang,metre,loops FROM Lyric WHERE lyric_key LIKE %s")
    cursor.execute(query, (key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching lyrics to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if row:
        return row
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT lyric,lyric_key,orig_lang,metre,loops FROM Lyric WHERE lyric_key LIKE %s")
    cursor.execute(query, ('%'+key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching lyrics to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise KeyError("No such lyric key as %s!" % key)
    return row

def get_tune_most_matching_key(cnx, key):
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT tune, tune_key, ttl, metre, loops FROM Tune WHERE tune_key LIKE %s")
    cursor.execute(query, (key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching lyrics to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if row:
        return row
    cursor = cnx.cursor(buffered=True)
    query = ("SELECT tune, tune_key, ttl, metre, loops FROM Tune WHERE tune_key LIKE %s")
    cursor.execute(query, ('%'+key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching tunes to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise KeyError("No such tune key as %s!" % key)
    return row

def get_person_most_matching_key(cnx, key):
    cursor = cnx.cursor(buffered=True)
    query=("SELECT person,person_key,birthYear,deathYear,comment FROM Person WHERE person_key LIKE %s")
    cursor.execute(query, (key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching person to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if row:
        return row
    cursor = cnx.cursor(buffered=True)
    query=("SELECT person,person_key,birthYear,deathYear,comment FROM Person WHERE person_key LIKE %s")
    cursor.execute(query, ('%'+key+'%',))
    if cursor.rowcount>1:
        cursor.close()
        raise KeyError("To many matching person to %s!" % key)
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise KeyError("No such person key as %s!" % key)
    return row

def get_tune_search_tools(search = {}):
    to_merge = []
    search_dict = {}
    if 'code' in search:
        to_merge.append("JOIN (SELECT tune FROM TuneCode WHERE code LIKE %(code)s) ON Tune.tune=TuneCode.tune")
        search_dict['code'] = search_stmnt(search, 'code')
    return (to_merge, search_dict)

def get_song_search_tools(search = {}):
    to_merge = []
    search_dict = {}
    if 'line' in search:
        to_merge.append("JOIN (SELECT lyric,GROUP_CONCAT(line ORDER BY vch,vnr,lnr SEPARATOR ' ') "
                        "AS texten FROM Line WHERE alt='' GROUP BY lyric,lang HAVING texten "
                        "LIKE %(line)s) AS Search ON Lyric.lyric=Search.lyric")
        search_dict['line'] = search_stmnt(search, 'line')
    if 'title' in search:
        to_merge.append("JOIN (SELECT lyric,ttl FROM Title WHERE ttl LIKE %(title)s) AS TSearch "
                        "ON Lyric.lyric=TSearch.lyric")
        search_dict['title'] = search_stmnt(search, 'title')
    if 'keywords' in search:
        to_merge.append("JOIN (SELECT lyric, GROUP_CONCAT(keyword ORDER BY keyword SEPARATOR ',') "
                        "AS words FROM Keyword GROUP BY lyric HAVING words LIKE LOWER(%(keywords)s)) "
                        "AS KSearch ON Lyric.lyric=KSearch.lyric")
        search_dict['keywords'] = '%'+('%'.join(sorted(search_dict['keywords'])))+'%'
    return (to_merge, search_dict)

def renew_titles(cnx, title_data):
    delete_title_query = ("DELETE FROM Title WHERE lyric=%s AND lang=%s AND var=%s")
    insert_title_query = ("INSERT INTO Title(lyric,lang,var,ttl,main) VALUES (%s,%s,%s,%s,%s)")
    for ((id, lang, var)), titles in title_data.items():
        update_titles = [title for title in titles if title[0]!='*' and title[-1]!='*']
        if update_titles:
            cursor = cnx.cursor()
            cursor.execute(delete_title_query, (id, lang, var))
            cursor.close()
            cursor = cnx.cursor()
            first = update_titles[0]
            cursor.executemany(insert_title_query,
                               [(id, lang, var, title, (first==title)) for title in update_titles])
            cursor.close()

def renew_comments(cnx, cmnt_data, trans=False):
    delete_cmnt_query = ("DELETE FROM Comments WHERE lyric=%s AND lang=%s AND var=%s AND trans=%s")
    insert_cmnt_query = ("INSERT INTO Comments(lyric,lang,var,cmnt,trans) VALUES (%s,%s,%s,%s,%s)")
    for (id, lang, var), lvl_two in cmnt_data.items():
        cursor = cnx.cursor()
        cursor.execute(delete_cmnt_query, (id, lang, var, trans))
        cursor.close()
        cursor = cnx.cursor()
        myvec = [(id, lang, var, cmnt, trans) for cmnt in lvl_two]
        cursor.executemany(insert_cmnt_query, myvec)
        cursor.close()

def update_or_insert_author(cnx, author_data):
    update_author_query = ("UPDATE Author SET what=%s WHERE lyric=%s AND person=%s AND "
                           "lang=%s AND var=%s AND yr=%s")
    insert_author_query = ("INSERT INTO Author(what,lyric,person,lang,var,yr) "
                           "VALUES (%s,%s,%s,%s,%s,%s)")
    for author in author_data:
        cursor = cnx.cursor()
        try:
            cursor.execute(insert_author_query, author)
        except mysql.connector.errors.IntegrityError:
            cursor.execute(update_author_query, author)
        cursor.close()

def renew_composers(cnx, tune_id, composer_data):
    delete_composer_query = ("DELETE FROM Composer WHERE tune=%s")
    insert_composer_query = ("INSERT INTO Composer(tune,person,yr,what) VALUES(%s,%s,%s,%s)")
    cursor = cnx.cursor()
    cursor.execute(delete_composer_query, (tune_id,))
    cursor.close()
    cursor = cnx.cursor()
    cursor.executemany(insert_composer_query, [(tune_id, pid, yr, what) for (pid, yr, what) in composer_data])
    cursor.close()

def create_publication_lyric_data(cnx, publications, id, lang, var):
    publ_data = []
    for publ in publications:
        if 'tune' in publ and 'book' in publ and 'entry' in publ:
            publ_data.append((publ.get('comment', None), id, lang, var,
                              tune_key_to_id(cnx, publ['tune']['key']),
                              songbook_key_to_id(cnx, publ['book']['key']), publ['entry']))
    return publ_data

def create_publication_songbook_data(cnx, publications, songbook_id):
    publ_data = []
    for publ in publications:
        if 'song' in publ and 'key' in publ['song'] and 'language' in publ['song']['lyrics'][0] and 'tune' in publ and 'entry' in publ:
            publ_data.append((publ.get('comment', None), lyric_key_to_id(cnx, publ['song']['key']),
                              publ['song']['lyrics'][0]['language'],
                              publ['song']['lyrics'][0].get('variant', ''),
                              tune_key_to_id(cnx, publ['tune']['key']), songbook_id, publ['entry']))
    return publ_data

def update_or_insert_publications(cnx, publ_data):
    update_publ_query = ("UPDATE Publ SET comment=%s WHERE lyric=%s AND "
                         "lang=%s AND var=%s AND tune=%s AND sb=%s AND entry=%s")
    insert_publ_query = ("INSERT INTO Publ(comment,lyric,lang,var,tune,sb,entry) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s)")
    for publ in publ_data:
        cursor = cnx.cursor()
        try:
            cursor.execute(insert_publ_query, publ)
        except mysql.connector.errors.IntegrityError:
            cursor.execute(update_publ_query, publ)
        cursor.close()

def syll_diff_no(line):
    no = 0
    if 'syllable-diff' in line:
        no = ((abs(line['syllable-diff']) & 0x7) << 12)
        if line['syllable-diff'] < 0: no = set_bit(no, 15)
    return no
        
def create_line_data(lines, id, lang, var, vnr, vch, args, typ, supl, cright, rty):
    line_data = []
    for line in lines:
        text = line['text']
        any_args = re.findall(r'_([^_]*)_', text)
        if 'redundant' in line and line['redundant']:
            if not(args and not any_args):
                continue
        if 'text' in line and 'no' in line:
            status = line.get('tabs', 0)
            if text[0]=='*' and text[1]!='*' and text[-2]!='*' and text[-1]=='*' and typ not in "bc":
                text = text[1:-1]
                status = set_bit(status, 2)
            while args and any_args:
                args.pop(0)
                any_args.pop(0)
                status = set_bit(status, 3)
            if 'compressable' in line: status = set_bit(status, 4)
            if supl: status = set_bit(status, 5)
            if cright: status = set_bit(status, 6)
            if rty: status = set_bit(status, 7)
            cmnt = from_footnote_object(line['footnote']) if 'footnote' in line else None
            line_data.append((status|syll_diff_no(line),text,cmnt,id,lang,var,'',typ,vnr,vch,line['no']))
        if 'alts' in line:
            for alt in line['alts']:
                if 'text' in alt and 'alt' in alt:
                    cmnt = from_footnote_object(alt['footnote']) if 'footnote' in alt else None
                    data = (status|syll_diff_no(alt),alt['text'],cmnt,id,lang,var,alt['alt'],typ,vnr,vch,line['no'])
                    line_data.append(data)
    return line_data

def create_verse_data(verses, id, lang, var):
    line_data = []
    for verse in verses:
        if 'lines' in verse and 'type' in verse and 'no' in verse:
            try:
                vnr = int(verse['no'])
                vch = ''
            except ValueError:
                # Last sign in verse no is a char!
                vnr = int(verse['no'][0:-1])
                vch = verse['no'][-1]
            args = [arg['to'] for arg in verse.get('args', [])]
            s = verse.get('supplement', False)
            c = (verse['copyright']!='royalty') if 'copyright' in verse else False
            r = (verse['copyright']!='permission') if 'copyright' in verse else False
            line_data+= create_line_data(verse['lines'],id,lang,var,vnr,vch,args,verse['type'],s,c,r)
    return line_data

def update_or_insert_lines(cnx, line_data):
    update_line_query = ("UPDATE Line SET stat=%s, line=%s, cmnt=%s WHERE lyric=%s AND lang=%s AND "
                         "var=%s AND alt=%s AND type=%s AND vnr=%s AND vch=%s AND lnr=%s")
    insert_line_query = ("INSERT INTO Line(stat,line,cmnt,lyric,lang,var,alt,type,vnr,vch,lnr) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    for line in line_data:
        cursor = cnx.cursor()
        try:
            cursor.execute(insert_line_query, line)
        except mysql.connector.errors.IntegrityError:
            cursor.execute(update_line_query, line)
        cursor.close()

def add_new_person(cnx, person):
    try:
        person_key_to_id(cnx, person['key'])
        raise NameError("Person with key '%s' does already exist!" % song['key'])
    except KeyError:
        # key doesn't exists already, go to work
        pass
    first = person['name'][0] #raise exception if no name is given
    person_tpl = set_person(cnx, person)
    cursor = cnx.cursor()
    query = ("INSERT INTO Person(birthYear,deathYear,comment,person_key) VALUES (%s,%s,%s,%s)")
    cursor.execute(query, person_tpl)
    person_id = cursor.lastrowid
    cursor.close()
    cursor = cnx.cursor()
    query = ("INSERT INTO PersonName(person,nm,main) VALUES (%s,%s,%s)")
    cursor.executemany(query, [(person_id, nm, (nm==first)) for nm in person['name']])
    cursor.close()
    return person_id

        
def get_person_id_or_add_if_not_exists(cnx, person):
    try:
        return person_key_to_id(cnx, person['key'])
    except KeyError:
        if 'name' in person:
            return add_new_person(cnx, person)
        else:
            raise NameError("Not enough information to add person '%s' to database" % person['key'])

def clean_lyrics(cnx, key):
    id = lyric_key_to_id(cnx, key)
    line_query = ("DELETE FROM Line WHERE lyric=%s")
    publ_query = ("DELETE FROM Publ WHERE lyric=%s")
    auth_query = ("DELETE FROM Author WHERE lyric=%s")
    tags_query = ("DELETE FROM Keyword WHERE lyric=%s")
    cursor = cnx.cursor()
    cursor.execute(line_query, (id,))
    cursor.execute(publ_query, (id,))
    cursor.execute(auth_query, (id,))
    cursor.execute(tags_query, (id,))
    cursor.close()

def set_song_lyrics(cnx, id, lyrics, orig_lang=None):
    title_data = {}
    author_data = []
    publ_data = []
    line_data = []
    cmnt_data = {}
    for lyric in lyrics:
        if 'language' not in lyric: continue
        lang = lyric['language']
        var = lyric.get('variant', '')
        if not orig_lang: orig_lang = lang
        if 'titles' in lyric:
            title_data[(id, lang, var)] = [title for title in lyric['titles']]
        if 'authors' in lyric:
            author_data+=[(a.get('what', None), id, get_person_id_or_add_if_not_exists(cnx, a), lang, var,
                           a['composed']) for a in lyric['authors'] if 'key' in a and 'composed' in a]
        if 'publications' in lyric and lyric['publications']:
            publ_data += create_publication_lyric_data(cnx, lyric['publications'], id, lang, var)
        if 'verses' in lyric:
            line_data += create_verse_data(lyric['verses'], id, lang, var)
        if 'comments' in lyric:
            cmnt_data[(id, lang, var)] = [cmnt for cmnt in lyric['comments']]
    renew_titles(cnx, title_data)
    update_or_insert_author(cnx, author_data)
    update_or_insert_publications(cnx, publ_data)
    update_or_insert_lines(cnx, line_data)
    renew_comments(cnx, cmnt_data, True)
    return orig_lang

verse_feets = {'I': "UX", 'T': "XU", 'D':"XUU", 'B':"UXU", 'P':"UUX"}

def key_to_string(lines):
    return ';'.join([''.join([verse_feets[m[-1]][i%len(verse_feets[m[-1]])] for i in range( 0, int(m[0:-1])) ]) for m in lines.split('.')])

def generate_metres(metres):
    if metres.strip('.;-1234567890'+''.join(verse_feets.keys())): 
        raise ValueError("Unpermitted value in given metre format!")
    try:
        return ';'.join([((key_to_string(m[0])+";")*(1 if 1>=len(m) else int(m[1])))[:-1] for m in [x.split('-') for x in metres.split(';')]])+";"
    except:
        pass
    raise ValueError("Could not generate metre from '%s'!" % metres)

def find_metre(cnx, metre_key, using_key=True):
    if using_key:
        metre_string = generate_metres(metre_key)
    else:
        metre_string = metre_key
    cursor = cnx.cursor()
    query = ("SELECT metre, metre_key, metre_string FROM Metre WHERE metre_string=%s")
    cursor.execute(query, (metre_string,))
    id_key = cursor.fetchone()
    cursor.close()
    return id_key

def find_metre_ids(cnx, metre_id):
    cursor = cnx.cursor()
    query = ("SELECT metre_key,metre_string,loops FROM Part JOIN Metre ON part=metre WHERE comp=%s ORDER BY ord")
    cursor.execute(query, (metre_id,))
    rvec = [OrderedDict([('name',OrderedDict([('key',k),('string',s)])),('times',l)]) for (k,s,l) in cursor]
    cursor.close()
    return rvec

def find_metre_id(cnx, metre_id):
    cursor = cnx.cursor()
    query = ("SELECT metre, metre_key, metre_string FROM Metre WHERE metre=%s")
    cursor.execute(query, (metre_id,))
    key_str = cursor.fetchone()
    cursor.close()
    return key_str

def find_metre_key(cnx, metre_key):
    cursor = cnx.cursor()
    query = ("SELECT metre, metre_key, metre_string FROM Metre WHERE metre_key=%s")
    cursor.execute(query, (metre_key,))
    key_str = cursor.fetchone()
    cursor.close()
    return key_str

def update_or_insert_partial_metres(cnx, line_data):
    delete_pm_query = ("DELETE FROM Part WHERE comp=%s")
    update_pm_query = ("UPDATE Part SET loops=%s, ord=%s WHERE comp=%s AND part=%s")
    insert_pm_query = ("INSERT IGNORE INTO Part(loops,ord,comp,part) VALUES (%s,%s,%s,%s)")
    cursor = cnx.cursor()
    _,_,comp,_ = line_data[0]
    cursor.execute(delete_pm_query, (comp,))
    cursor.close()
    for line in line_data:
        cursor = cnx.cursor()
        cursor.execute(insert_pm_query, line)
        cursor.close()

def author_dead_less_than(person, yr):
    try:
        return person['death']+yr > date.today().year
    except ValueError:
        return True

def longest_common_substring(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]

#TODO: make possible to handle chars
def composed(whatstr, vno, vch):
    d = {a[0]:[i for r in (x.split("-") for x in a[1].split(",")) for i in range(int(r[0]), int(r[-1]) + 1)] for a in [w.split('.') for w in whatstr.split(';')]}
    return int(vno) in d[vch]

def royalty_requireable_author(authors, vno, vch):
    if len(authors) == 1 and authors[0]['composed'] > 1923:
        return 'death' not in authors[0] or author_dead_less_than(authors[0], 70)
    for author in authors:
        if 'what' in author and author['composed'] > 1923 and composed(author['what'],vno,vch) and author_dead_less_than(author, 70):
                return True
    return False

def omit_royalty_requirement_verses(song):
    for lyric in song['lyrics']:
        for verse in lyric['verses']:
            if 'copyright' in verse and verse['copyright']=='royalty':
                if royalty_requireable_author(lyric['authors'], verse['no'], verse['type']):
                    verse['lines'] = []
                else:
                    del(verse['copyright'])
