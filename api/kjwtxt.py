#!/usr/bin/python

import sys
import re
from kjwtools import to_footnote_object,from_footnote_object

from collections import OrderedDict

copy_dict = {'\u00a9':'permission','\u2117':'blocked','\u00ae':'royalty'}
supl_dict = {'v':'w','i':'j','c':'d','o':'p'}

ALT_DELIMNETER='\u005c'
FOOT_DELIMNETER='#'

def val_to_key(d, val):
    for k,v in d.items():
        if v==val:
            return k
    return None

def get_supl_letter(orig):
    try:
        return supl_dict[orig]
    except KeyError:
        return orig

def from_supl_letter(orig):
    res = val_to_key(supl_dict, orig)
    return res if res else orig
    
def split_list_at(mylist, func, la=False):
    rval = []
    tmp = []
    for l in mylist:
        if func(l):
            if tmp: rval.append(tmp)
            tmp = []
        if l or la: tmp.append(l)
    if tmp: rval.append(tmp)
    return rval

def line_to_author_dict(info):
    author_stuff = info[1:].split(' ')
    author_dict = {'key': author_stuff[0], 'composed': int(author_stuff[1])}
    if len(author_stuff) > 2:
        if author_stuff[2]!='n/a':
            author_dict['what']=author_stuff[2]
    if len(author_stuff) > 3:
        years = author_stuff[3].split('-')
        if years[0]: author_dict['birth']=int(years[0])
        if years[1]: author_dict['death']=int(years[1])
        author_dict['name']=' '.join(author_stuff[4:]).split(';')
        if not author_dict['name'][0]:
            raise ValueError("Author name of %s is missing!" % author_dict['key'])
    return author_dict

def metre_name_or_string(m):
    if set(m)-set("UX."):
        return {'key':m}
    return {'string':m.replace('.',';')+';'}

def line_to_metres(ln):
    return [{'name':metre_name_or_string(metre[0]), 'times': metre[1]} for metre in [m.split('-') for m in ln.split(';')]]

def line_to_publ_dict(info):
    publ_stuff = info[1:].split(' ')
    rval = {'book':{'key':publ_stuff[0]}, 'entry':int(publ_stuff[1]), 'tune':{'key':publ_stuff[2]}}
    if len(publ_stuff) > 3:
        rval['comment'] = ' '.join(publ_stuff[3:])
    return rval

def txt_vec_to_kjsongs(txt):
    return {'songs':[txt_vec_to_kjsong(t[1:] if t[0]=='===' else t) for t in split_list_at(txt,(lambda x: x=='==='), True)]}

def txt_footnoteify(tmp_line):
    if '#' in tmp_line['text']:
        tmp_vec = tmp_line['text'].split('#')
        tmp_line['text'] = tmp_vec[0]
        tmp_line['footnote'] = to_footnote_object(tmp_vec[1])
    if '~' in tmp_line['text']:
        tmp_vec = tmp_line['text'].split('~')
        tmp_line['text'] = tmp_vec[0]
        tmp_line['syllable-diff'] = int(tmp_vec[1])
    return tmp_line

def txt_vec_to_kjsong(txt):
    keywords = (txt[2][1:].split(',') if txt[2][0] == "%" else None)
    song = {'key':txt[0], 'metre':line_to_metres(txt[1]), 'lyrics':[]}
    if keywords: song['tags'] = keywords
    start = 2 + (1 if keywords else 0)
    while txt[start] and txt[start][0]=='#':
        song.setdefault('comments',[]).append({'language': txt[start][1:4], 'comment': txt[start][5:]})
        start+=1
    
    new_lang=False
    lst = [split_list_at(l,(lambda x: x[0] in '1234567890')) for l in split_list_at(txt[start:],(lambda x: x==''))]
    for lang_var in lst:
        tmp = {}
        base = lang_var[0]
        lv = base[0].split(' ')
        tmp = {'language': lv[0], 'verses': []}
        if len(lv)>1: tmp['variant'] = lv[1]
        for info in base[1:]:
            if info[0] == '@':
                tmp.setdefault('authors', []).append(line_to_author_dict(info))
            elif info[0] == '#':
                tmp.setdefault('comments', []).append(info[1:])
            elif info[0] == '$':
                tmp.setdefault('publications', []).append(line_to_publ_dict(info))
            else:
                tmp.setdefault('titles', []).append(info)
        for verse in lang_var[1:]:
            verse[0] = verse[0].strip()
            try:
                int(verse[0])
                vno,cright = verse[0],None
                vtype = 'v'
            except ValueError:
                vno,cright = (verse[0][:-2], verse[0][-2]) if len(verse[0])>=2 and verse[0][-2] in copy_dict.keys() else (verse[0][:-1], None)
                vtype = verse[0][-1]
            supplement = True if vtype in supl_dict.values() else False
            vtype = from_supl_letter(vtype)
            v_tmp = {'type':vtype, 'no':vno, 'lines':[]}
            if supplement: v_tmp['supplement'] = True
            if cright: v_tmp['copyright'] = copy_dict[cright]
            comp_and_indent_even=0
            i=0
            for line in verse[1:]:
                i=i+1
                if line[0]==';': continue
                tmp_line = {'no':i, 'text':line}
                tmp_line['tabs'] = len(tmp_line['text']) - len(tmp_line['text'].lstrip(' '))
                tmp_line['text'] = tmp_line['text'].strip(' ')
                if tmp_line['text'][0] == '-':
                    tmp_line['compressable'] = True
                    tmp_line['text'] = tmp_line['text'][1:]                    
                if ALT_DELIMNETER in tmp_line['text']:
                    tmp_vec = tmp_line['text'].split(ALT_DELIMNETER)
                    tmp_line['text'] = tmp_vec[0]
                    tmp_line['alts'] = [txt_footnoteify({"alt":str[0],"text":str[1]}) for str in [str.split('%') for str in tmp_vec[1:]]] #if len(str) >= 2
                tmp_line = txt_footnoteify(tmp_line)
                if tmp_line['text'][0] == ':':
                    tmp_line['text']='*'+tmp_line['text'][1:]+'*'
                else:
                    argvec = re.findall(r'_([^_]*)_', line)
                    if argvec:
                        tmp_vec = [{'to':a} for a in argvec]
                        if 'args' in v_tmp: v_tmp['args'] += tmp_vec
                        else: v_tmp['args'] = tmp_vec
                v_tmp['lines'].append(tmp_line)
            tmp['verses'].append(v_tmp)
        song['lyrics'].append(tmp)
    return song

def txt_vec_to_kjtunes(txt):
    return {'tunes':[txt_vec_to_kjtune(t[1:] if t[0]=='===' else t) for t in split_list_at(txt,(lambda x: x=='==='), True) if t[0]!='===' or len(t)>1]}

def split_name_and_stuff(txt, mark=':'):
    vec = txt.split(mark, 1)
    if len(vec) <= 1:
        return (None, vec[0])
    else:
        return (vec[0], vec[1])

def txt_vec_to_kjtune(txt):
    if not txt: return {}
    tune = {'key':txt[0],'title':txt[1], 'metre':line_to_metres(txt[2])}
    for info in txt[3:]:
        if info[0] == '@':
            tune.setdefault('composers', []).append(line_to_author_dict(info))
        elif info[0] == '$':
            l = info[1:].split('$')
            tune.setdefault('links',[]).append({'format':l[0], 'description':l[1], 'url':l[2]})
        elif info[0] == '%':
            l = info[1:].split('%',2)
            name, stuff = split_name_and_stuff(l[0])
            tmp_dict = {'name': name if name else None, 'code': stuff}
            if len(l)>1 and l[1]:
                tmp_dict['rythm'] = [{'variant':None if not i[0] else i[0], 'time':i[1], 'code':i[2]} for i in [this_l.split(':',2) for this_l in l[1].split(';')]]
            if len(l)>2 and l[2]:
                tmp_dict['harmony'] = [{'variant':i if i else None, 'code':j} for i,j in [split_name_and_stuff(a) for a in l[2].split(';')]]
            tune.setdefault('codes',[]).append(tmp_dict)
    return tune

def txt_defootnoteify(line):
    return (('~'+str(line['syllable-diff'])) if 'syllable-diff' in line else '')+(('#'+from_footnote_object(line['footnote'])) if 'footnote' in line else '')

def kjtune_to_txt_vec(kjtune):
    return [kjtune['key'], kjtune['title'], ';'.join([((m['name']['key'] if m['name']['key'] else m['name']['string'].replace(';','.')[0:-1])+'-'+str(m['times'])) for m in kjtune['metre']])] + [('@'+auth['key']+' '+str(auth['composed'])+(' '+auth['what'] if 'what' in auth else '')) for auth in kjtune['composers']] + [('%'+'%'.join([':'.join([c['name'] if c['name'] else '',c['code']]), ';'.join([':'.join([d['variant'] if d['variant'] else '', d['time'], d['code']]) for d in c.get('rythm',[])]), ';'.join([':'.join([d['variant'] if d['variant'] else '', d['code']]) for d in c.get('harmony',[])])])) for c in kjtune['codes']] + [('$'+'$'.join([l['format'],l['description'],l['url']])) for l in kjtune['links'] if l['url'][0:13]!='../tuneLinks/']

def kjtunes_to_txt_vec(kjtunes):
    rvec = []
    for kjtune in kjtunes['tunes']:
        if rvec: rvec.append('===')
        rvec+=kjtune_to_txt_vec(kjtune)
    return rvec

def kjsong_to_txt_vec(kjsong):
    rvec = [kjsong['key'], ';'.join([((m['name']['key'] if m['name']['key'] else m['name']['string'].replace(';','.')[0:-1])+'-'+str(m['times'])) for m in kjsong['metre']]), '%'+','.join(kjsong['tags'])]
    if 'comments' in kjsong:
        for cmnt_dict in kjsong['comments']:
            rvec.append(('#'+cmnt_dict['language']+' '+cmnt_dict['comment']))
    for lyric in kjsong['lyrics']:
        rvec.append('')
        rvec.append(lyric['language']+((' '+lyric['variant']) if 'variant' in lyric else ''))
        for title in lyric['titles']:
            if not (title[0]=='*' and title[-1]=='*'):
                rvec.append(title)
        for auth in lyric['authors']:
            rvec.append('@'+auth['key']+' '+str(auth['composed'])+(' '+auth['what'] if 'what' in auth else ''))
        if 'publications' in lyric:
            for publ in lyric['publications']:
                rvec.append(('$'+publ['book']['key']+' '+str(publ['entry'])+' '+publ['tune']['key']+(' '+publ['comment'] if 'comment' in publ else '')))
        if 'comments' in lyric:
            for cmnt in lyric['comments']:
                rvec.append(('#'+cmnt))
        for verse in lyric['verses']:
            rvec.append(str(verse['no'])+(val_to_key(copy_dict,verse['copyright']) if 'copyright' in verse else '')+(verse['type'] if not 'supplement' in verse else get_supl_letter(verse['type'])))
            for line in verse['lines']:
                if 'redundant' in line and ((line['text'][0]=='*' and line['text'][-1]=='*') or verse['type']=='c'):
                    rvec.append(';')
                    continue
                txt_to_append=''
                txt_to_append+=(line.get('tabs', 0)*' ')
                txt_to_append+=('-' if 'compressable' in line else '')
                txt_to_append+=((':'+line['text'][1:-1]) if line['text'][0]=='*' and line['text'][-1]=='*' else line['text'])
                alt_str=(ALT_DELIMNETER.join([a['alt']+'%'+a['text']+txt_defootnoteify(a) for a in (line.get('alts',[]))]))
                txt_to_append+=txt_defootnoteify(line)
                txt_to_append+=((ALT_DELIMNETER+alt_str) if alt_str else '')
                rvec.append(txt_to_append)
    return rvec

def text_vol_fn_vec(line, fn_vec):
    txt = line['text']
    if 'footnote' in line:
        for fn in line['footnote']:
            idx_a = txt.find(fn['id']) if 'id' in fn else -1
            idx = txt.find(' ',idx_a+len(fn['id'])-1) if idx_a!=-1 else -1
            fn_vec.append(fn['text'])
            if idx!=-1:
                txt = txt[:idx]+ '['+str(len(fn_vec))+']' +txt[idx:]
            else:
                txt = txt+'['+str(len(fn_vec))+']'
    return txt

def text_sub_line(text, vec):
    rval,start = '',0
    for v in vec:
        rval+=text[start:v['from']]+'_'+text[v['from']:v['to']]+'_'
        start=v['to']
    rval+=text[start:]
    return rval

def text_authors_to_append(authors):
    txt_string = ""
    for author in authors:
        txt_string += ('\n  + ' + author['name'][0] + ((' *'+str(author['birth'])) if 'birth' in author else '') + ((' \u2020'+str(author['death'])) if 'death' in author else ''))
        txt_string += (" ("+str(author['composed'])+((", "+author['what']) if 'what' in author else '')+')')
    return txt_string

def print_tunes(contents):
    txt_string = ''
    for publ in contents:
        txt_string += '\n'+publ['title']
        if 'count' in publ and ('penalty' not in publ or not publ['penalty']): txt_string+=' ['+str(publ['count'])+' publ. '+('(this)' if 'published' in publ and publ['published'] else '')+']'
        if 'penalty' in publ: txt_string += ' [pen. '+str(publ['penalty'])+(', part. '+(str(publ['partial'].get('song','-'))+'/'+str(publ['partial'].get('tune','-'))) if 'partial' in publ else '') + ']'
        txt_string += text_authors_to_append(publ['composers'])
        for links in publ['links']:
            txt_string += ('\n  - '+links['url']+' ('+links['format']+', '+links['description']+')')
    return txt_string
    

def tabs_to_use(lines, idx, should_compress):
    if not should_compress:
        return lines[idx].get('tabs',0)
    tabs = 5
    for i in range(idx, len(lines)):
        if not lines[i].get('compressable',False) and i>idx:
            break
        this_tab = lines[i].get('tabs',0)
        if this_tab < tabs: tabs=this_tab
    return tabs

def kjsong_to_txt(song, should_compress=False, hide_redundant=False, force_compress=[]):
    txt_string = ""
    for instance in song['lyrics']:
        alt_dict = OrderedDict()
        foot_note_vec = []
        txt_string += instance['language']
        if 'variant' in instance: txt_string += " ("+instance['variant']+")"
        for title in instance['titles']:
            txt_string += ('\n' + title)
        txt_string += text_authors_to_append(instance['authors'])
        txt_string += '\n'
        for verse in instance['verses']:
            spl = True if 'supplement' in verse and verse['supplement'] else False
            txt_string += '\n'
            if verse['type']=='c':
                txt_string += ' Refr'
                if 'args' in verse:
                    txt_string += ('{' + ', '.join([(a['from']+'=>'+a['to']) for a in verse['args']]) + '}')
                    if hide_redundant:
                        txt_string+='.\n'
                        continue    
                txt_string+=':'
            if 'copyright' in verse:
                txt_string+= ('\u00a9' if verse['copyright'][0] == 'p' else '\u00ae' if verse['copyright'][0] == 'r' else 'blocked verse!')
            if verse['type']=='v':
                txt_string += ('s' if spl else '')+verse['no']+'.'
            for nr in range(0, len(verse['lines'])):
                line=verse['lines'][nr]
                if 'redundant' in line and line['redundant'] and hide_redundant: continue
                txt_string += (' \u2014 ' if should_compress and (line['no'] in force_compress or (not force_compress and line.get('compressable',False))) else ('\n' + ('  '*tabs_to_use(verse['lines'], nr, should_compress)))) + ('(' if spl else '') + text_vol_fn_vec(line, foot_note_vec)+(('{'+('+' if line['syllable-diff']>0 else '')+str(line['syllable-diff'])+'}') if 'syllable-diff' in line else '')
                spl = False
                if 'alts' in line:
                    for alt in line['alts']:
                        alt_dict.setdefault(alt['alt'], OrderedDict())[(verse['type'],verse['no'], line['no'])] = text_sub_line(alt['text'], alt.get('new_words_idx', []))+(('{'+('+' if alt['syllable-diff']>0 else '')+str(alt['syllable-diff'])+'}') if 'syllable-diff' in alt else '')
            if 'args' in verse and hide_redundant:
                txt_string += ('\n {' + ', '.join([(a['from']+'=>'+a['to']) for a in verse['args']]) + '}')
            if 'supplement' in verse and verse['supplement']: txt_string += ')'
            txt_string += '\n'
        if foot_note_vec:
            idx=1
            for note in foot_note_vec:
                txt_string += ("\n["+str(idx)+"] "+ note)
                idx+=1
            txt_string += '\n'
        if alt_dict:
            for alt, lvl_two in alt_dict.items():
                txt_string += 'alt "'+alt+'":\n'
                for (t,v,l), txt in lvl_two.items():
                    txt_string += '   '+t+v+'.'+str(l)+': '+txt+'\n'
        if 'comments' in instance:
            txt_string += '\nanm: '
            for cmnt in instance['comments']:
                txt_string += (cmnt + '\n')
        if 'comments' in song and 'variant' not in instance:
            for cmnt in song['comments']:
                if cmnt['language']==instance['language']:
                    txt_string += (('\n' if not foot_note_vec else '')+'----\n'+cmnt['comment']+'\n')
            
        txt_string += '\n------------------------------\n'
    if song['tunes']:
        txt_string+='_Tunes:_'
        txt_string+=print_tunes(song['tunes'])+'\n'
    return txt_string

def txt_vec_to_kjbook(txt):
    book = {'key':txt[0],'title':txt[1], 'year':int(txt[2])}
    if txt[3][0]=='#': book['comment'] = txt[3][1:]
    start_id = 4 if 'comment' in book else 3
    book['contents'] = [{'entry':int(l[0]),'song':{'key':l[1],'lyrics':[{'language':l[2],'variant':l[3]}]},'tune':{'key':l[4]},'comment':l[5]} for l in [t.split('/',5) for t in txt[start_id:]]]
    return book
    
def kjbook_to_txt_vec(kjbook):
    rval = [kjbook['key'],kjbook['title'],str(kjbook['year'])]+([('#'+kjbook['comment'])] if 'comment' in kjbook else [])
    part2 = []
    for c in kjbook['contents']:
        part2.append(('/'.join([str(c['entry']),c['song']['key'],c['song']['lyrics'][0]['language'],c['song']['lyrics'][0].get('variant',''),c['tune']['key'],c.get('comment','')])))
    return rval+part2
