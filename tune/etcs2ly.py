import sys, math

id_key_start = [2,6,3,0,4,1,5]
to_sharp_flat = 'fcgdaeb'
mod_nash_2_ly = {'-':'m', '⁷':'7', '°':'dim', '+':'aug', 'Δ':'maj','ø':'m7.5-', '⁹':'9', '⁶':'6', '+':'aug','⁺':'+', '¹':'1', '²':'2', '³':'3', '⁴':'4', '⁵':'5', '⁸':'8','s':'sus2','u':'sus4'}

def nr2Note(nr, key=0):
    if nr[0]=='r':
        return nr
    c = chr((id_key_start[key] + int(nr[0])-1)%7 + ord('a'))
    if key<0 and c in to_sharp_flat[key:]:
        if not (len(nr)>1 and nr[1]=='#'):
            c+=('es'+('es' if len(nr)>1 else ''))
    elif key>0 and c in to_sharp_flat[:key]:
        if not (len(nr)>1 and nr[1]=='b'):
            c+=('is'+('is' if len(nr)>1 else ''))
    else:
        if len(nr)>1:
            c+=('is' if nr[1]=='#' else 'es')
    return c

def nr2Chord(nr, key=0):
    if len(nr)>1 and nr[1] in '#b':
        v,b = nr2Note(nr, key) , 2
    else:
        v,b = nr2Note(nr[0], key), 1
    return (v, ''.join([mod_nash_2_ly[a] for a in nr[b:]]))

def pos_key(c, pos, key):
    n = ord(c[0]) - ord('a')
    if key!=0 and n>=2 and id_key_start[key]>2 and n<id_key_start[key]:
        return update_pos(pos, 'U')
    elif key!=0 and n<2 and id_key_start[key]<2 and n>=id_key_start[key]:
        return update_pos(pos, 'D')
    else:
        return pos

def update_pos(pos, idx):
    if idx=='D':
        if "'" in pos:
            return pos[:-1]
        else:
            return pos+','
    elif idx=='U':
        if ',' in pos:
            return pos[:-1]
        else:
            return pos+"'"
    return pos

def kjw_index(s, c, *args, **kwargs):
    try:
        return s.index(c, *args, **kwargs)
    except ValueError:
        return -1

def to_max(i, length):
    return i if i!=-1 else length

def volta(note, excl=False, idx=0, a='{', b='}', times=1):
    l = len(note)
    s = to_max(kjw_index(note, a,idx), l)
    m = to_max(kjw_index(note, '|',idx), l)
    e = to_max(kjw_index(note, b,idx), l)
    if s==l and e==l:
        return [n for n in note if not (n==a or n=='|' or n==b)]
    if s < m or s < e:
        return volta(note, excl, s+1, a, b, times)
    else:
        return volta((note[:idx-1] + (times*([] if excl else [n for n in note[idx:e] if n!='|']) + note[idx:min(m,e)])) + note[e+1:], excl, 0, a, b, times)

def da_al(note, segno=False, coda=False, volt=False):
    s, a, c, l = 0, -1, -1, len(note)
    if segno:
        s = max(kjw_index(note, '$'), 0)
    if coda:
        a = to_max(kjw_index(note, 'C'), l)
        c = to_max(kjw_index(note, '¤'), l)
    else:
        a = to_max(kjw_index(note, 'F'), l)
        c = l
    rval = [n for n in (volta(note[0:c]) + ([] if a==c else volta(note[s:a], not volt)) + volta(note[c:])) if not (n=='$' or n=='C' or n=='¤' or n=='F')]
    return rval

def deal_with_dots(time, tm):
    while time and time[0]=='.':
        time=time[1:]
        tm+='.'
    if time and time[0]==',':
        time=time[1:]
        tm+='\\fermata'
    return time, tm

def merge_nrs(note, time, chords=[]):
    rval = []
    nlen = len(note)
    i=0
    while i<nlen:
        n = note[i]
        if n=='#' or n=='b':
            try:
                if rval[-1][0]=='r':
                    raise IndexError("HACK")
                rval[-1][0] = rval[-1][0]+n
            except:
                rval[-2][0]= rval[-2][0]+n
        elif n==')' and rval[-1] == '(':
            rval=rval[:-1]
        elif n==')' and len(rval[-1])>1 and rval[-1][0]=='r':
            r = rval[-1]
            rval[-1] = ')'
            rval.append(r)
        elif n not in '1234567':
            rval.append(n)
        else:
            done = False
            add_paren = False
            while time and time[0] in 'abcdefghij':
                t = time[0]
                tm = str( 1<<(ord(t)-ord('a')) )
                time = time[1:]
                time, tm = deal_with_dots(time, tm)
                rval.append(['r' , tm])
                if chords:
                    rval[-1].append(chords[0])
                    chords[0]='_'
            while not done and time:
                t=time[0]
                time=time[1:]
                if t=='-' or t in 'abcdefghij':
                    done=True
                    if t=='-' and chords:
                        if chords[0]!='_' and chords[1]=='_':
                            chords[1] = chords[0]
                        chords = chords[1:]
                    if t=='-' and i+1<nlen and note[i+1] in '#b':
                        i+=1
                if t in 'klmnopqrst':
                    tm = str( 1<<(ord(t)-ord('k')) )
                    time, tm = deal_with_dots(time, tm)
                    rval.append(['r' , tm])
                    if chords:
                        chords = chords[1:]
                        rval[-1].append('_')
                    done = True
                if t in '1234567890':
                    t = str( 1 << int(t) )
                    time, t = deal_with_dots(time, t)
                    rval.append([n,t])
                    if chords:
                        rval[-1].append(chords[0])
                    if add_paren:
                        if rval[-1]=='(':
                            rval = rval[:-1]
                        else:
                            rval.append(')')
                        add_paren = False
                    if time and time[0]!='_' and time[0] not in 'klmnopqrst':
                        done=True
                        if chords:
                            chords = chords[1:]
                    elif time and time[0]=='_':
                        if i+1<nlen and note[i+1] in '#b':
                            rval[-1][0] += note[i+1]
                        rval.append('(')
                        add_paren=True
                        if chords:
                            chords[0] = '_'
        i+=1
    return rval
    
def time_len(time):
    return len([i for i in time if i in '1234567890-']) - len([i for i in time if i in '_'])

def unmerge(note):
    volt = True if 'c' in note or 'f' in note else False
    note = [('C' if n=='c' else ('F' if n=='f' else n)) for n in note]
    if 'C' in note or 'F' in note or '¤' in note or '$' in note:
        note = da_al(note, '$' in note, 'C' in note, volt)
    elif '{' in note or '|' in note or '}' in note:
        note = volta(note)
    return note

def chords_if_possible(chords, nl):
    cl = len(chords)
    if cl != nl:
        print(("%s!=%s. (chrd)" % (cl,nl)), file=sys.stderr)
        chords = unmerge(chords)
        cl = len(chords)
        if cl != nl:
            print(("%s!=%s. (chrd unm.)" % (cl,nl)), file=sys.stderr)
            chords = None
    return chords

def musika(note, time, chords=None):
    time = volta(list(time))
    time = volta(list(time), False, 0, '[',']',2)
    tl = time_len(time)
    nl = len([i for i in note if i in '1234567'])
    new_notes = None
    if tl == nl:
        if chords:
            chords = chords_if_possible(chords, nl)
        new_notes = merge_nrs(list(note), time, chords)
    else:
        print(("%s!=%s." % (nl,tl)), file=sys.stderr)
        note = unmerge(note)
        nl = len([i for i in note if i in '1234567'])
        if tl == nl:
            if chords:
                chords = chords_if_possible(chords, nl)
            new_notes = merge_nrs(list(note), time, chords)
    if not new_notes:
        raise ValueError('MISMATCH (%s, %s)' % (nl, tl))
    else:
        new_chords = None
        if chords:
            new_chords = [(n if isinstance(n,str) or len(n)<3 else (n[2],n[1])) for n in new_notes if n and n!='D' and n!='U' and n!='(' and n!=')']
        newnew_notes = [(n if isinstance(n,str) or len(n)<2 else (n[0],n[1])) for n in new_notes]
        return newnew_notes, new_chords

def add_markup(rval, markup):
    olde = rval[-1]
    if olde!=')':
        rval[-1] = markup
        rval.append(olde)
    else:
        rval.append(markup)

def add_rep_cmd(rval, text):
    if rval and "\set Score.repeatCommands = #'(" in rval[-1]:
        rval[-1] = '%s %s)' % (rval[-1][0:-1], text)
    else:
        rval.append("\set Score.repeatCommands = #'(%s)" % text)

def to_ly(inp, pos=',', key=0, time=1.0, anacrusis=[]):
    rval = []
    inalt, conrep, fine, segn = None, False, False, False
    nextsegn, codpos, nextaltend = False, None, False
    finetext = '\\mark \\markup { \\small "Fine" }'
    finebar = '\\bar "."'
    alttime = None
    first = True
    repeatnest,past_nest = 0,False
    volta_nr=[['1','1, 3'],['2','2, 4']]
    for i in inp:
        if i=='U' or i=='D':
            pos = update_pos(pos, i)
        elif i=='{':
            if rval and rval[-1] == finebar:
                rval = rval[0:-1]
            if not first:
                anacrusis = []
                add_rep_cmd(rval, 'start-repeat')
            repeatnest+=1
        elif i=='|':
            if past_nest and '(volta "2, 4")' in rval[-1]: rval[-1] = rval[-1].replace('(volta "2, 4")','')
            add_rep_cmd(rval, '(volta "%s")' % ('2' if past_nest else volta_nr[0][repeatnest-1]))
            inalt = pos
            alttime = [str(1<<int(a)) for a in anacrusis]
        elif i=='}':
            if '(volta "' in rval[-1]:
                hasvoltafinal = ('(volta #f)' in rval[-1])
                rval = rval[0:-1]
                if rval[-1] == finebar: rval=rval[0:-1]
                if hasvoltafinal: add_rep_cmd(rval, '(volta #f)')
                add_rep_cmd(rval, 'end-repeat')
                pos = inalt
                inalt = None
            else:
                if rval[-1] == finebar: rval=rval[0:-1]
                if inalt is not None:
                    add_rep_cmd(rval, '(volta #f)')
                    add_rep_cmd(rval, 'end-repeat')
                    add_rep_cmd(rval, '(volta "%s")' % ('4' if past_nest else volta_nr[1][repeatnest-1]))
                    pos = inalt
                    val, times = unify(alttime, False)
                    modulo = times%int(val*time)
                    if modulo:
                        rval.append("\\partial %s*%s" % (val, modulo))
                    elif inalt and anacrusis:
                        rval.append("\\partial %s*%s" % (16, int(16*time)))
                    alttime = None
                    inalt = None
                    anacrusis = []
                    nextaltend = True
                else:
                    add_rep_cmd(rval, 'end-repeat')
            repeatnest-=1
            past_nest = (repeatnest==1)
        elif i=='F' or i=='f':
            rval.append(finetext)
            rval.append(finebar)
            fine = True
            if i=='f': conrep = True
        elif i=='C' or i=='c':
            rval.append('\\mark \\markup { \\small "al Coda" }')
            codpos = pos
            if i=='c': conrep = True
        elif i=='$':
            segn = True
            nextsegn = True
        elif i=='¤':
            idx = -1
            while rval[idx][0] not in 'abcdefgr':
                idx-=1
            rval = rval[:idx] + ['\\mark \\markup { \\small "D.%s.%s al Coda" }' % ('S' if segn else 'C', ' con rep.' if conrep else '')] + rval[idx:]
            rval.append('\\mark \\markup { \\musicglyph #"scripts.coda" }')
            if 'end-repeat' not in rval[-2]: rval.append('\\bar "||"')
            pos = codpos
        elif i=='(' or i==')' or len(i)==1:
            if rval[-1] == "\set Score.repeatCommands = #'((volta #f))" or rval[-1][1:5]=='mark':
                olde = rval[-1]
                rval[-1]=i
                rval.append(olde)
            else:
                rval.append(i)
        else:
            n, t = i[0], i[1]
            v = nr2Note(n, key)
            rval.append(('%s%s%s' % (v, ('' if v=='r' else pos_key(v, pos, key)), t)))
            if alttime is not None:
                alttime.append(t)
            if nextsegn:
                rval.append('\\segno')
                nextsegn = False
            if nextaltend:
                add_rep_cmd(rval, '(volta #f)')
                nextaltend = False
        first = False
    if 'end-repeat' not in rval[-1] and 'partial' not in rval[-1]: rval.append('\\bar "|."')
    if fine:
        if 'partial' in rval[-1]: rval = rval[0:-1]
        if '(volta "' in rval[-1]:
            rval[-1] = rval[-1].replace('(volta "2, 4")','').replace('(volta "4")','').replace('(volta "2")','')
            nextaltend=False
        rval.append('\\mark \\markup { \\small "D.%s.%s al Fine" }' % ('S' if segn else 'C', ' con rep.' if conrep else ''))
    if nextaltend:
        add_rep_cmd(rval, '(volta #f)')
    return ' '.join(rval)

def to_ly_harm(inp, key=0):
    rval = ''
    for i in inp:
        if len(i)==1 or i=='(' or i==')':
            #rval += i
            pass
        else:
            n, t = str(i[0]), i[1]
            if '/' in n:
                ns = n.split('/')
                v1,p1 = nr2Chord(ns[0], key)
                v2,p2 = nr2Chord(ns[1], key)
                rval += ('%s%s:%s/%s:%s ' % (v1, t, (p1 if p1 else '5'), v2, (p2 if p2 else '5')))
            else:
                v,p = nr2Chord(n, key)
                rval += (('%s%s:%s ' % (v, t, (p if p else '5'))) if n!='0' else ('r%s ' %t))
    return rval

def all_numbers(vec, powr=True):
    svec = [ord(t)-ord('k') if t in 'klmnopqrst' else (int(t) if t in '1234567890' else (ord(t)-ord('a') if t in 'abcdefghij' else t)) for t in vec if t not in '{|()}[]']
    to_append = []
    for i in range(0,len(svec)):
        try:
            svec[i] = svec[i].strip('\\fermata')
        except:
            pass
        if svec[i]=='.':
            svec[i]=((int(svec[i-1]) + 1) if powr else (int(svec[i-1]) * 2))
        elif isinstance(svec[i], str):
            if len(svec[i])>1 and svec[i][-2]=='.':
                svec[i] = int(svec[i][:-2])
                to_append.append(((int(svec[i-2])+2) if powr else (int(svec[i]) * 4)))
                to_append.append(((int(svec[i-2])+1) if powr else (int(svec[i]) * 2)))
            elif svec[i][-1]=='.':
                svec[i] = int(svec[i][:-1])
                to_append.append(((int(svec[i-1])+1) if powr else (int(svec[i]) * 2)))
            else:
                svec[i] = int(svec[i])
    svec = svec + to_append
    return svec

def unify(vec, powr=True):
    svec = all_numbers(vec, powr)
    val,times=max(svec),0
    for s in svec:
        times += ((1 << (val-s)) if powr else (val//s))
    return (1<<val if powr else val), times

def partial_notes(time):
    idx = kjw_index(time, '!')
    if idx==-1: return []
    return time[0:idx]

def partial(time):
    pn = partial_notes(time)
    if pn:
        val, times = unify(pn)
        return '\\partial %s*%s ' % (val, times)
    return ''

def harm2vec(harm):
    harmvec = []
    while harm:
        h = harm[0]
        harm = harm[1:]
        if h=='/':
            harmvec[-1] += ('/%s' % harm[0])
            harm = harm[1:]
        elif h=='\\':
            harmvec[-1] += ('\\%s' % harm[0])
            harm = harm[1:]
        elif h in '01234567_{|}CF¤cf$' or not harmvec:
            harmvec.append(h)
        else:
            harmvec[-1] += h
    return harmvec

def tune2frac(tune):
    dots = 0
    if isinstance(tune, str):
        tune = tune.strip('\\fermata')
        while tune and tune[-1]=='.':
            tune = tune[:-1]
            dots += 1
    t = int(tune)
    rval = 1.0/float(t)
    for i in range(0,dots):
        t *= 2
        rval += 1.0/float(t)
    return rval

def frac2tunes(frac, tune_max=1.0):
    rval = []
    prev_base = 0
    while frac>=tune_max:
        rval.append(int(1/tune_max))
        frac -= tune_max
    while frac>0.0:
        base, new_frac = frac2tune(frac)
        frac = new_frac
        if rval and base//2==prev_base:
            rval[-1] = '%s.' % rval[-1]
        else:
            rval.append(base)
        prev_base = base
    return rval

def frac2tune(frac):
    val = 1 << math.ceil(math.log(1.0/frac, 2))
    return val, frac - 1.0/val

def merge_harm(harm_merged, time=1.0):
    rvec, added = [], False
    for hm in harm_merged:
        try:
            (h,t) = hm
        except ValueError:
            #rvec.append(hm)
            pass
        else:
            if not rvec or (h!='_' and h!='r' and rvec[-1]!=h):
                if rvec:
                    chrds = str(rvec[-1][0]).split('\\')
                    notes = frac2tunes(rvec[-1][1]/len(chrds), time)
                    rvec = rvec[:-1]
                    for chrd in chrds:
                        for note in notes:
                            rvec.append([chrd, note])
                rvec.append([h if h!='_' else 0, tune2frac(t)])
            else:
                rvec[-1][1] += tune2frac(t)
    if isinstance(rvec[-1][1], float):
        chrds = str(rvec[-1][0]).split('\\')
        notes = frac2tunes(rvec[-1][1]/len(chrds), time)
        rvec = rvec[:-1]
        for chrd in chrds:
            for note in notes:
                rvec.append([chrd, note])
    return rvec

def is_lower(a, b, complete=False):
    if not a and not b:
        return True
    prev = True
    if complete:
        prev = is_lower(a[1:], b[1:])
    if a[0] == b[0]:
        return is_lower(a[1:], b[1:])
    elif a[0] in '1234567' and b[0] in '1234567':
        return (a[0] < b[0]) and prev
    elif a[0]=='U' or b[0]=='D':
        return False
    elif b[0]=='U' or a[0]=='D':
        return True and prev

def only_notes(string):
    return [s for s in string if s in '1234567UD']
    
def startdetect(tune_inp_str):
    tune_str = [c for c in unmerge(tune_inp_str) if c!='(' or c!=')' or c!='#' or c!='b']
    add_val = 0
    rval=[]
    diff = 2
    for c in tune_str:
        try:
            rval.append(int(c) + add_val)
        except ValueError:
            if c=='U':
                add_val+=8
            elif c=='D':
                add_val-=8
    mean = sum(rval)/len(rval)
    minval = min(rval)
    maxval = max(rval)
    d = maxval - minval
    amend = min(2,int(max(0,d-11)))
    best_key = [0,-2,3,1,-1,-3,2][((minval % 8) - 1 + amend)%7]
    print((mean, minval, maxval), file=sys.stderr)
    minval+=amend
    if minval < -4:
        return "''", best_key
    elif -4 <= minval and minval < 4:
        return "'", best_key
    elif 4 <= minval:
        return "", best_key

def detect_startpos(vector, start=None):
    try:
        sop_str = [v for v in vector if v['name']=='soprano'][0]['code']
    except:
        sop_str = [v for v in vector if not v['name']][0]['code']
    soprano = only_notes(sop_str)
    if start is None:
        start, best_key = startdetect(sop_str)
    else:
        best_key=0
    rval = {'':start,'soprano':start}
    try:
        alto = only_notes([v for v in vector if v['name']=='alto'][0]['code'])
        rval['alto'] = update_pos(rval['soprano'],'D') if is_lower(soprano, alto) else rval['soprano']
    except:
        pass
    try:
        tenor = only_notes([v for v in vector if v['name']=='tenor'][0]['code'])
        bass = only_notes([v for v in vector if v['name']=='bass'][0]['code'])
        rval['tenor'] = update_pos(rval['alto'],'D') if not is_lower(tenor, alto, True) else rval['alto']
        rval['bass'] = update_pos(rval['tenor'],'D') if is_lower(tenor, bass) else rval['tenor']
    except:
        pass
    return rval, best_key

#TODO(?): partial synccheck
def synccheck(vector):
    vec = [v for v in vector if v!='U' and v!='D' and v!='(' and v!=')']
    rvec = []
    temptime = 0.0
    for v in vec:
        try:
            (h, t) = v
            temptime += tune2frac(t)
        except:
            if temptime:
                rvec.append(temptime)
            temptime = 0.0
    if temptime:
        rvec.append(temptime)
    return rvec

def theheader(vector):
    import re
    rval = '\header{\n'
    title,subtitle = vector['title'],None
    if re.match(r'^.*\(“.*”\)$', title):
        tvec = title.split('“')
        title = tvec[0][:-1].strip()
        subtitle = tvec[1][:-2].strip()
    composer = ', '.join([v['name'][0]+(' (attr.)' if 'what' in v and v['what']=='?' else '') for v in vector['composers'] if 'what' not in v or ('alto' not in v['what'] and 'arr.' not in v['what'])])
    arr = ', '.join([v['name'][0] for v in vector['composers'] if 'what' in v and ('alto' in v['what'] or 'arr.' in v['what'])])
    rval+=('title = "%s"\n' % title)
    if subtitle:
        rval+=('subtitle = "%s"\n' % subtitle)
    if composer:
        rval+=('composer = "%s"\n' % composer)
    if arr:
        rval+=('arranger = "%s"\n' % arr)
    rval+='}\n'
    return rval

### FUNCTIONS REGARDING HMMS
def trim_observation(chunk):
    l = len(chunk)
    if (l<2):
        return chunk
    elif (l==2):
        return (chunk[0] if chunk[0]==chunk[1] else chunk)
    else:
        a = trim_observation(chunk[0:(l//2)])
        b = trim_observation(chunk[(l//2):])
        al,bl = len(a), len(b)
        if (al == bl):
            if a==b:
                return a
            else:
                return a+b
        else:
            if al<bl:
                return ((a*(bl//al)) + b)
            else:
                return (a + (b*(al//bl)))
    return chunk

def merge_to_observation(vector, time=1.0, tt_start=0.0):
    vec = [v for v in vector if v!='U' and v!='D' and v!='(' and v!=')']
    rval, chunk = [], ''
    max_denominator = max([int(t[1].strip('.').strip('\\fermata')) for t in vec if len(t)==2])
    max_pieces = int(max_denominator * time)
    chunk = ('0' * int(max_denominator * (time-tt_start))) if (tt_start>0.01) else ''
    for v in vec:
        try:
            (h,t) = v
            h = '0' if h=='r' else h
            h = chr(ord(h[0:-1])+16) if h[-1]=='#' else h
            h = chr(ord(h[0:-1])+24) if h[-1]=='b' else h
            td = int(tune2frac(t) * max_denominator)
            chunk += h*td
            while len(chunk) >= max_pieces:
                rval.append(trim_observation(chunk[0:max_pieces]))
                chunk = chunk[max_pieces:]
        except ValueError:
            if chunk:
                print("WARNING! SOME FUZZ (%s, %s) IN THE MIDDLE OF A BEAT!" % (chunk, v) , file=sys.stderr)
                raise ValueError("WARNING! SOME FUZZ (%s, %s) IN THE MIDDLE OF A BEAT!" % (chunk, v))
            rval.append(v)
    return rval
###

def etcs2ly(vector, startpos=None, rythmvar=None, harmvar=None, key=0, tempo=100, force_harm=False, compact=True, instr='choir aahs', chord_instr='acoustic guitar (nylon)'):
    key=int(key)
    header = ''
    if 'codes' in vector:
        header = theheader(vector)
        vector = vector['codes']
    rval = ('\\version "2.18.2"\n%s\n' % header)
    staffvec, staffcompvec, harmvec, harmcompvec = [],[],[],[]
    sync, prev_sc = compact, None
    print(startpos, file=sys.stderr)
    if [v for v in vector if v['name']=='soprano']:
        vector=[v for v in vector if v['name']]
    for v in vector:
        try:
            pos = startpos[v['name'] if v['name'] else '']
        except:
            pos = ''
        rythm = [i for i in v['rythm'] if i['variant']==rythmvar]
        if not rythm:
            rythm = [i for i in v['rythm'] if not i['variant']]
            #continue
        if 'harmony' in v:
            harm = harm2vec([i for i in v['harmony'] if i['variant']==harmvar][0]['code'])
        else:
            harm = None
        try:
            music, harmony = musika(v['code'], rythm[0]['code'], harm)
            sc = synccheck(music)
            print(sc, file=sys.stderr)
            if (prev_sc is not None) and sync==True:
                sync = (sc == prev_sc)
            prev_sc = sc
            time_idx = 1.0/float(rythm[0]['time'].split('/')[1])
            time_value = float(rythm[0]['time'].split('/')[0]) / float(rythm[0]['time'].split('/')[1])
            anacrusis = all_numbers([c for c in partial_notes(rythm[0]['code'])])
            if harmony:
                harmvec.append('\\new ChordNames { \\set chordChanges = ##t\n \\set ChordNames.midiInstrument = "'+chord_instr+'" \n \\chordmode {%s}}\n' % to_ly_harm(merge_harm(unmerge(harmony), time_idx), key))
                #print(merge_harm(harmony, time_idx), file=sys.stderr)
                harmcompvec.append('\\new ChordNames { \\set chordChanges = ##t\n \\set ChordNames.midiInstrument = "'+chord_instr+'" \n \\chordmode {%s}}\n' % to_ly_harm(merge_harm(harmony, time_idx), key))
            lycode = to_ly( music , pos, key, time_value, anacrusis)
            staffcompvec.append('\\new Staff { '+('\\clef bass' if v['name'] in ['bass','tenor'] else '')+' \\set Staff.midiInstrument = #"'+instr+'"\n\\key '+nr2Note('1', key)+' \\major \\time '+rythm[0]['time']+' '+partial(rythm[0]['code'])+' {'+lycode+'\n}}\n')
            lycode = to_ly( unmerge(music) , pos, key, time_value, anacrusis)
            staffvec.append('\\new Staff { '+('\\clef bass' if v['name'] in ['bass','tenor'] else '')+' \\set Staff.midiInstrument = #"'+instr+'"\n\\key '+nr2Note('1', key)+' \\major \\time '+rythm[0]['time']+' '+partial(rythm[0]['code'])+' {'+lycode+'\n}}\n')
        except ValueError as ve:
            print(("value error: %s at %s." % (ve, v['name'])), file=sys.stderr)
        except IndexError as ie:
            print(("index error: %s at %s." % (ie, v['name'])), file=sys.stderr)
    onlyone = len(staffvec)==1
    rval += ('\\score{\n<<\n\\new ChoirStaff\n<<%s\n>>\n>>\n  \\layout{ }\n} \\score{\n<<\n%s\n>>\n\\midi{ \\tempo 4=%s }\n}' % ('\n'.join(['\n'.join(harmcompvec if (onlyone or sync==True) else harmvec), '\n'.join(staffcompvec if (onlyone or sync==True) else staffvec)]), '\n'.join(['\n'.join(harmvec if (onlyone or force_harm) else []), '\n'.join(staffvec)]), tempo))
    return rval
