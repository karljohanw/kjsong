#!/usr/bin/python

import datetime
import mysql.connector
import re
import kjwtools
import os

from collections import OrderedDict
from datetime import date

CONF_PATH = os.environ.get('KJW_GLOBAL_CONF','global.conf')

def read_conf(conf_path=CONF_PATH):
    return {v[0] : v[1].strip().strip('"') for v in [l.split('=',1) for l in [line.strip() for line in open(conf_path, 'r')] if l and l[0]!='#']}

def db_search_connect():
    return mysql.connector.connect(host='localhost', user='searcher', password='password',
                                   database='kjsong', charset='utf8', use_unicode = True)

def db_maintain_connect():
    return mysql.connector.connect(host='localhost', user='updater', password='password',
                                   database='kjsong', charset='utf8', use_unicode = True)

def get_person(cnx, person_key):
    cursor = cnx.cursor()
    try:
        int(person_key)
        query=("SELECT person,person_key,birthYear,deathYear,comment FROM Person WHERE person=%s")
    except ValueError:
        query=("SELECT person,person_key,birthYear,deathYear,comment FROM Person WHERE person_key=%s")
    cursor.execute(query, (person_key,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        row = kjwtools.get_person_most_matching_key(cnx, person_key)
    rval = kjwtools.get_person_from_row_tuple(cnx, row)
    if 'songs' in rval:
        for song in rval['songs']: kjwtools.omit_royalty_requirement_verses(song)
    return rval

def get_persons(cnx, search = {}):
    to_merge, search_dict, join_by = kjwtools.get_person_search_tools(search)
    query = ("SELECT UNIQUE(Person.person), person_key, birthYear, deathYear, comment "
             "FROM Person "+("JOIN PersonName ON Person.person=PersonName.person " if 'name' in search else "")+(" WHERE "+join_by.join(to_merge) if to_merge else ""))
    cursor = cnx.cursor(buffered=True)
    cursor.execute(query, search_dict)
    odict = OrderedDict()
    rval = [kjwtools.get_person_from_row_tuple(p_key, pid, by, dy, cmnt, search) for (pid, p_key, by, dy, cmnt) in cursor]
    cursor.close()
    for pers in rval:
        if 'songs' in pers:
            for song in pers['songs']: kjwtools.omit_royalty_requirement_verses(song)
    return rval

def post_person(cnx, person):
    return kjwtools.add_new_person(cnx, person)

def put_person(cnx, person):
    old_person = get_person(cnx, person['key'])
    # line above raises exeption if person key doesn't exists
    old_person.update(person)
    person_tpl = kjwtools.set_person(cnx, old_person)
    cursor = cnx.cursor()
    query = ("UPDATE Person SET birthYear=%s, deathYear=%s, comment=%s WHERE person_key=%s")
    cursor.execute(query, person_tpl)
    person_id = cursor.lastrowid
    cursor.close()
    kjwtools.update_or_insert_names(cnx, [((person['namn'][0]==nm), person_id, nm) for nm in person['namn']])
    return person_id

def patch_person_name(cnx, person, names):
    try:
        person_id = int(person)
    except ValueError:
        person_id = kjwtools.person_key_to_id(cnx, person)
    kjwtools.update_or_insert_names(cnx, [(False, person_id, name) for name in names])
    
def get_song(cnx, key, search_dict = {}):
    cursor = cnx.cursor()
    try:
        int(key)
        query = ("SELECT lyric,lyric_key,orig_lang,metre,loops FROM Lyric WHERE lyric=%s")
    except ValueError:
        query = ("SELECT lyric,lyric_key,orig_lang,metre,loops FROM Lyric WHERE lyric_key=%s")
    cursor.execute(query, (key,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        row=kjwtools.get_song_most_matching_key(cnx, key)
    return kjwtools.get_song_from_row_tuple(cnx, row, search_dict)

def get_songs(cnx, search = {}):
    to_merge, search_dict = kjwtools.get_song_search_tools(search)
    query = ("SELECT DISTINCT(Lyric.lyric),Lyric.lyric_key, Lyric.orig_lang, Lyric.metre, "
             "Lyric.loops FROM Lyric "+(' '.join(to_merge))+" ORDER BY lyric_key")
    cursor = cnx.cursor(buffered=True)
    cursor.execute("SET SESSION group_concat_max_len = 100000")
    cursor.execute(query, search_dict)
    songs = [kjwtools.get_song_from_row_tuple(cnx, row_tuple, search) for row_tuple in cursor]
    cursor.close()
    return songs

def delete_tags(cnx, lyric_key, tags):
    lyric_id = kjwtools.lyric_key_to_id(cnx, lyric_key)
    kjwtools.delete_song_tags(cnx, lyric_id, tags)    

def append_tags(cnx, lyric_key, tags, delete_old=False):
    lyric_id = kjwtools.lyric_key_to_id(cnx, lyric_key)
    if delete_old:
        kjwtools.renew_song_tags(cnx, lyric_id, tags)
    else:
        kjwtools.append_song_tags(cnx, lyric_id, tags)

def put_song(cnx, song):
    cursor = cnx.cursor()
    query = ("SELECT lyric, orig_lang, metre, loops FROM Lyric WHERE lyric_key=%s")
    cursor.execute(query, (song['key'],))
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        raise KeyError("Song with key '%s' does not exist!" % song['key'])
    (id, orig_lang, metre, loops) = row
    if 'lyrics' in song and song['lyrics']: kjwtools.set_song_lyrics(cnx, id, song['lyrics'], orig_lang)
    if 'comments' in song:
        kjwtools.renew_comments(cnx, {(id, c['language'], ''): [c['comment']] for c in song['comments'] if 'comment' in c and 'language' in c}, False)
    if 'tags' in song:
        kjwtools.append_song_tags(cnx, id, song['tags'])
    if 'metre' in song:
        metre_id,_,_ = find_or_create_metres(cnx, song['metre'])
        if metre_id!=metre or (len(song['metre'])==1 and song['metre'][0]['times']!=loops):
            cursor = cnx.cursor()
            query = ("UPDATE Lyric SET metre=%s, loops=%s WHERE lyric=%s")
            cursor.execute(query, (metre_id, (1 if len(song['metre'])>1 else song['metre'][0]['times']), id))
            cursor.close()


def post_song(cnx, song):
    if 'lyrics' not in song or not ('metre' in song and song['metre'] and 'name' in song['metre'][0] and 'times' in song['metre'][0]):
        raise KeyError("Required information missing in order to add song!")
    try:
        kjwtools.lyric_key_to_id(cnx, song['key'])
        raise NameError("Song with key '%s' does already exist!" % song['key'])
    except KeyError:
        # key doesn't exists already, go to work
        pass
    metre_id,_,_ = find_or_create_metres(cnx, song['metre'])
    cursor = cnx.cursor()
    query = ("INSERT INTO Lyric(lyric_key, metre, loops) VALUES(%s,%s,%s)")
    cursor.execute(query, (song['key'], metre_id, (1 if len(song['metre'])>1 else song['metre'][0]['times'])))
    song_id = cursor.lastrowid
    cursor.close()
    orig_lang = kjwtools.set_song_lyrics(cnx, song_id, song['lyrics'])
    cursor = cnx.cursor()
    query = ("UPDATE Lyric SET orig_lang=%s WHERE lyric=%s")
    cursor.execute(query, (orig_lang, song_id))
    cursor.close()
    if 'comments' in song:
        kjwtools.renew_comments(cnx, {(song_id, c['language'], ''): [c['comment']] for c in song['comments'] if 'comment' in c and 'language' in c}, False)
    if 'tags' in song:
        kjwtools.renew_song_tags(cnx, song_id, song['tags'])

def get_songbook(cnx, book):
    cursor = cnx.cursor()
    try:
        int(book)
        query = ("SELECT sb, sb_key, ttl, yr, comment FROM Songbook WHERE sb=%s")
    except ValueError:
        query = ("SELECT sb, sb_key, ttl, yr, comment FROM Songbook WHERE sb_key=%s")
    cursor.execute(query, (book,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise KeyError("No such Songbook key as %s!" % id)
    (sb_id, sb_key, title, year, comment) = row
    book = OrderedDict([('key', sb_key), ('title', title), ('year', year), ('comment', comment),
                        ('contents', kjwtools.get_songbook_publications(cnx, sb_id))])
    for song in book['contents']: kjwtools.omit_royalty_requirement_verses(song['song'])
    return book

def put_songbook(cnx, book):
    cursor = cnx.cursor()
    query = ("SELECT sb, ttl, yr, comment FROM Songbook WHERE sb_key=%s")
    cursor.execute(query, (book['key'],))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise KeyError("No such Songbook key as %s!" % book['key'])
    (sb_id, title, year, comment) = row
    if 'title' in book: title = book['title']
    if 'year' in book: year = book['year']
    if 'comment' in book: comment = book['comment']
    if 'title' in book or 'year' in book or 'comment' in book:
        cursor = cnx.cursor()
        query = ("UPDATE Songbook SET ttl=%s, yr=%s, comment=%s WHERE sb=%s")
        cursor.execute(query, (title, year, comment, sb_id))
        cursor.close()
    if 'contents' in book:
        publ_data = kjwtools.create_publication_songbook_data(cnx, book['contents'], sb_id)
        print(book['contents'])
        print(publ_data)
        kjwtools.update_or_insert_publications(cnx, publ_data)

def post_songbook(cnx, book):
    try:
        kjwtools.songbook_key_to_id(cnx, book['key'])
        raise NameError("Songbook key %s already exists!" % book['key'])
    except KeyError:
        # No such songbook, go to work
        pass
    comment = book.get('comment', None)
    if 'title' in book and 'year' in book and 'key' in book:
        cursor = cnx.cursor()
        query = ("INSERT INTO Songbook (sb_key, ttl, yr, comment) VALUES(%s, %s, %s, %s)")
        cursor.execute(query, (book['key'], book['title'], book['year'], comment))
        sb_id = cursor.lastrowid
        cursor.close()
    if 'contents' in book:
        publ_data = kjwtools.create_publication_songbook_data(cnx, book['contents'], sb_id)
        kjwtools.update_or_insert_publications(cnx, publ_data)

def get_tune(cnx, tune, stripped=False):
    cursor = cnx.cursor()
    try:
        int(tune)
        query = ("SELECT tune, tune_key, ttl, metre, loops FROM Tune WHERE tune=%s")
    except ValueError:
        query = ("SELECT tune, tune_key, ttl, metre, loops FROM Tune WHERE tune_key=%s")
    cursor.execute(query, (tune,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        row = kjwtools.get_tune_most_matching_key(cnx, tune)
    (tune_id, tune_key, title, metre_id, loop) = row
    tune_dict = kjwtools.get_tune_dict_base(cnx, tune_id, tune_key, title)
    tune_dict['metre'] = kjwtools.get_metre_vector(cnx, metre_id, loop)
    tune_dict['publications'] = kjwtools.get_tune_publications(cnx, tune_id)
    if not stripped:
        tune_dict['songs'] = kjwtools.get_tune_metre_match(cnx, tune_id, metre_id, loop)
        #no lyrics listed in this case, include below if it will come again
        #for song in tune_dict['publications']: kjwtools.omit_royalty_requirement_verses(song)
    return tune_dict

def get_tunes(cnx, search = {}):
    to_merge, search_dict = kjwtools.get_tune_search_tools(search)
    query = ("SELECT DISTINCT(Tune.tune),Tune.tune_key, Tune.ttl, Tune.metre, "
             "Tune.loops FROM Tune "+(' '.join(to_merge))+" ORDER BY tune_key")
    tunes = []
    cursor = cnx.cursor(buffered=True)
    cursor.execute(query, search_dict)
    for (tune_id, tune_key, title, metre_id, loop) in cursor:
        tune_dict = kjwtools.get_tune_dict_base(cnx, tune_id, tune_key, title)
        tune_dict['metre'] = kjwtools.get_metre_vector(cnx, metre_id, loop)
        tune_dict['publications'] = kjwtools.get_tune_publications(cnx, tune_id)
        if 'include_matches' in search:
            tune_dict['songs'] = kjwtools.get_tune_metre_match(cnx, tune_id, metre_id, loop)
        tunes.append(tune_dict)
    cursor.close()
    return tunes

def post_tune(cnx, tune):
    try:
        kjwtools.tune_key_to_id(cnx, tune['key'])
        raise NameError("Tune key %s already exists!" % tune['key'])
    except KeyError:
        # No such tune, go to work
        pass
    if 'title' not in tune or 'metre' not in tune:
        raise KeyError("Required information missing in order to add tune!")
    metre_id, _, _ = find_or_create_metres(cnx, tune['metre'])
    cursor = cnx.cursor()
    query = ("INSERT INTO Tune(tune_key, ttl, metre, loops) VALUES(%s,%s,%s,%s)")
    tup = (tune['key'], tune['title'], metre_id, (tune['metre'][0]['times'] if len( tune['metre'])==1 else 1))
    cursor.execute(query, tup)
    tune_id = cursor.lastrowid
    cursor.close()

    if 'codes' in tune and tune['codes']:
        kjwtools.set_tune_code(cnx, tune_id, tune['codes'])
    if 'links' in tune:
        link_vec = [(tune_id, link['format'], link['description'], link['url']) for link in tune['links'] if 'local' not in link or not link['local']]
        cursor = cnx.cursor()
        query = ("INSERT INTO TuneLinks(tune,format,descr,url) VALUES(%s,%s,%s,%s)")
        cursor.executemany(query, link_vec)
        cursor.close()
    if 'composers' in tune:
        comp_vec = [(tune_id, kjwtools.get_person_id_or_add_if_not_exists(cnx,c), c['composed'], c['what'] if 'what' in c else None) for c in tune['composers']]
        cursor = cnx.cursor()
        query = ("INSERT INTO Composer(tune,person,yr,what) VALUES(%s,%s,%s,%s)")
        cursor.executemany(query, comp_vec)
        cursor.close()

def put_tune(cnx, tune):
    tune_id = kjwtools.tune_key_to_id(cnx, tune['key'])
    cursor = cnx.cursor()
    metre_id, _, _ = find_or_create_metres(cnx, tune['metre'])
    query = ("UPDATE Tune SET ttl=%s,metre=%s,loops=%s WHERE tune=%s")
    cursor.execute(query, (tune['title'], metre_id, (tune['metre'][0]['times'] if len( tune['metre'])==1 else 1), tune_id))
    cursor.close()
    if 'codes' in tune and tune['codes']:
        kjwtools.set_tune_code(cnx, tune_id, tune['codes'])
    if 'links' in tune:
        link_vec = [(link['url'], tune_id, link['format'], link['description']) for link in tune['links'] if 'local' not in link or not link['local']]
        cursor = cnx.cursor()
        ins_query = ("INSERT INTO TuneLinks(url,tune,format,descr) VALUES(%s,%s,%s,%s)")
        upd_query = ("UPDATE TuneLinks SET url=%s WHERE tune=%s AND format=%s AND descr=%s")
        for link in link_vec:
            try:
                cursor.execute(ins_query, link)
            except mysql.connector.errors.IntegrityError:
                cursor.execute(upd_query, link)
        cursor.close()
    if 'composers' in tune:
        comp_vec = [(kjwtools.get_person_id_or_add_if_not_exists(cnx,c), c['composed'], c['what'] if 'what' in c else None) for c in tune['composers']]
        kjwtools.renew_composers(cnx, tune_id, comp_vec)
        
def find_or_create_metres(cnx, metre_vec):
    if len(metre_vec)==1:
        metre_id,metre_key,metre_string = find_or_create_metre(cnx,metre_vec[0]['name'])
        return metre_id,metre_key,[OrderedDict([('name',OrderedDict([('key',metre_key),('string',metre_string)])),('times',metre_vec[0]['times'])])]
    vec = [(find_or_create_metre(cnx, metre_dict['name']),metre_dict['times']) for metre_dict in metre_vec]
    new_metre_string = ''.join([metre_str*int(times) for ((_,_,metre_str),times) in vec])
    new_metre_id,new_metre_key,_ = find_or_create_metre(cnx,{'key':None,'string':new_metre_string})
    try:
        kjwtools.update_or_insert_partial_metres(cnx, [(vec[i][1],i,new_metre_id,vec[i][0][0]) for i in range(0,len(vec))])
    except Exception as e:
        print(vec,e)
        raise
    return new_metre_id,new_metre_key,[OrderedDict([('name',OrderedDict([('key',key),('string',string)])),('times',times)]) for ((_,key,string),times) in vec]
    
def find_or_create_metre(cnx, metre_dict):
    if 'string' in metre_dict:
        found_metre = kjwtools.find_metre(cnx, metre_dict['string'], False)
    elif 'key' in metre_dict and metre_dict['key']:
        found_metre = kjwtools.find_metre_key(cnx, metre_dict['key'])
        if not found_metre:
            found_metre = kjwtools.find_metre(cnx, metre_dict['key'])
    if found_metre:
        return found_metre
    else:
        cursor = cnx.cursor()
        query = ("INSERT INTO Metre(metre_key,metre_string) VALUES(%s,%s)")
        if 'string' not in metre_dict:
            metre_str = kjwtools.generate_metres(metre_dict['key'])
        else:
            metre_str = metre_dict['string']
        cursor.execute(query, (metre_dict.get('key', None), metre_str))
        metre_id = cursor.lastrowid
        cursor.close()
        return (metre_id, metre_dict.get('key', None), metre_str)

def merge_persons(cnx, to_person_key, from_person_key):
    author_query = ("UPDATE Author SET person=%s WHERE person=%s")
    composer_query = ("UPDATE Composer SET person=%s WHERE person=%s")
    name_query = ("UPDATE PersonName SET person=%s WHERE person=%s")
    person_query = ("DELETE FROM Person WHERE person=%s")
    try:
        to_person_id = kjwtools.person_key_to_id(cnx, to_person_key)
        from_person_id = kjwtools.person_key_to_id(cnx, from_person_key)
        cursor = cnx.cursor()
        cursor.execute(author_query, (to_person_id, from_person_id))
        cursor.execute(composer_query, (to_person_id, from_person_id))
        cursor.execute(name_query, (to_person_id, from_person_id))
        cursor.execute(person_query, (from_person_id,))
        cursor.close()
    except KeyError:
        raise NameError("Could not merge!")

def var_to_alt(cnx,lyric,lang,to_var,from_var):
    try:
        update_query = ("UPDATE Line SET alt=%(from_var)s,var=%(to_var)s WHERE lyric=%(lyric_id)s "
                        "AND lang=%(lang)s AND var=%(from_var)s")
        del_query = ("DELETE A FROM Line AS A JOIN Line AS B ON A.lyric=B.lyric AND A.lang=B.lang "
                     "AND A.vch=B.vch AND A.vnr=B.vnr AND A.type=B.type AND A.lnr=B.lnr AND "
                     "A.line=B.line AND A.var=B.var AND A.alt!=B.alt AND B.lyric=%(lyric_id)s "
                     "AND B.alt=%(to_var)s AND A.alt=%(from_var)s")
        try:
            lyric_id = int(lyric)
        except ValueError:
            lyric_id = kjwtools.lyric_key_to_id(cnx, lyric)
        my_dict = {'lyric_id':lyric_id, 'lang': lang, 'from_var': from_var, 'to_var': to_var}
        cursor = cnx.cursor()
        cursor.execute(update_query, my_dict)
        cursor.execute(del_query, my_dict)
        cursor.close()
    except KeyError:
        raise NameError("Could not merge!")
