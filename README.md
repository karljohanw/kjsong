# KJSONG
A RESTful API for tune-to-lyrics-matching (and vice versa), with possibility to derive how words are pronounced

This is a spare-time project of mine, which I have been working on for several years. The main intention is to store lyrics, tunes and, if possible, published instances (a specific tune published with specific lyrics). By letting each syllable in the lyrics, and each note in the tune, correspond to a letter (U for unstressed syllable, X for stressed) it is possible to derive how tunes and lyrics match eachother, metrically/rythmically, with a modified NW-alignment algorithm (only allowing gaps in the shorter string). A directed graph is then built, representing smaller/larger metres/rythms in the vertices/nodes.

There is also a possibility to derive how the words in the lyrics are supposed to be pronounced when sung, which in turn could create a base for CMU-like dictionaries of other languages than English. Work has also been made on how to derive the metre of lyrics automatically.

Please note, lots of the code is write-only-oneliners!

## How to start use

First, run the api_server:

```
api> ./api_server
```

In the catalogs *song* and *tune* respectively, there is a file [sample.txt](song/sample.txt) contaning the hymn "Amazing Grace" and the Finnish anthem "Maame/Vårt land", and corresponding [tunes](tune/sample.txt), in "plotter" mode (swe. *plottrig*≈messy), a more compact way to prepare the data than in traditional JSON. The sample-files can be converted to JSON and sent to the API with the command

```
song|tune> ./textput sample.txt
```

Afterwards, run

```
api> ./forecast
```

to rebuild the graph containing the meters. Now you should be able to call the API for this two songs, for the full API definition, please see [api_definition.txt](api/api_definition.txt).

## Dealing with lyrics

To be able to deal with lyrics/song text in the API, I have created a fronted-ish format "plotter", which shall make the handling of lyrics easier than using raw JSON. A similar "plotter"-mode is created for handling tunes.

### Backus-Naur Form

Here follows the formal definition of the "plotter" mode conerning lyrics. (The reader might perhaps understand better after studing [some practical examples](song/sample.txt).)

```
<lang_and_type> ::= <language_iso_639-2/B> [<variant>]
<person_line> ::= @<person_idx> <year>[ <what> [[<birth>]-[<death>] <full_name>{;<full_name>}]]

<syllable> ::= X | U
<verse_feet> ::= I | T | D | B | P
<base_metre> ::= (<integer><verse_feet>)+ | <syllable>+
<metre> ::= <base_metre>-<integer>{;<base_metre>-<integer>}

<tags> ::= <tag>{,<tag>}
<what> ::= n/a | [<verse_ranges>{;<verse_ranges>}][/<alternative>]

<footnotes> ::= [<word>=]<text>{;[<word>=]<text>}

<contractable> ::= - | <empty>
<repeatable> ::= : | <empty>
<repeated> ::= ;
<extra_syllables> ::= [~<integer>]

<publication> ::= $<book_idx> <index> <tune_idx>[ <what>]

<verse_class> ::= <verse_class_ordinary> | <verse_class_supplementary>
<verse_class_ordinary> ::= i | v | c | o
<verse_class_supplementary> ::= j | w | d | p
<verse_nr> ::= <integer>[<letter>]
<verse_header> ::= <verse_nr><verse_class>
<verse_line> ::= <indent><contractable><repeatable><line_text><extra_syllables>[#<footnotes>]{\<alternative>%<line_text><extra_syllables>} | <repeated>

<verse_range> ::= <verse_nr>[-<verse_nr>]
<verse_ranges> ::= <verse_class>.<verse_range>{,<verse_range>}

<verse> ::= <verse_header>(<EOL><verse_line>)+<EOL>

<lyric_instance> ::= <lang_and_type><EOL>{<title><EOL>}{<person_line><EOL>}{<publication><EOL>}<verse>+
<lyric> ::= <lyric_idx><EOL><metre><EOL>[%<tags><EOL>]{#<language_iso_639-2/B> <comment><EOL>}(<EOL><lyrics_insance><EOL>)+
<lyrics> ::= <lyric>{<EOL>===<EOL><lyric>}
```

## Dealing with tunes

The definition of a tune melody is derived from [Tune Code System](http://hymntune.library.uiuc.edu/hti1/hti.works10.asp):
- Each pitch is represented with a digit 1-7.
    - 1 beeing the keynote in the major scale, and 6 the keynote in the (relative) minor scale.
- When the tune passes 7 into the next octave, a `U` is added before next digit.
- Similarly, a `D` is added when the tune passes 1 into the lower octave.
- Melismas (inteded by composer) are marked by setting all the included notes, after the first one, into parentheses.

What's new:
- If a note is an [accidental](https://en.wikipedia.org/wiki/Accidental_(music)), the digit is followed by a `#` for sharp or a `b` for flat.
- A reprise can be marked with braces, Ex.: `{12} = 1212`.
    - Alternate endings can be dealt with using a bar, Ex.: `{12|3}4 = 123124`.
- A `F` indicates a Fine-mark, which assumes that the tune to be played *Da Capo* (or *Dal Segno*) *al Fine*, leaving out any reprises and/or alt. endings, Ex.: `{1|2}3F4 = 1213413`.
    - If reprises and/or alt. endings should be included, use `f`, Ex.: `{1|2}3f4 = 121341213`.
- A `$` indicates a *Segno*, which can be used together with the Fine-mark described above, Ex.: `1$2F3 = 1232`.
- A `¤` indicates the beginning of a Coda, which assumes the tune to be played *Da Capo* (or *Dal Segno*) *al Coda*.
    - A `C` indicates a *al Coda*-mark, _leaving out_ reprises and/or alt. endings, Ex.: `{1|2}3C4¤5 = 12134135`.
    - A `c` indicates a *al Coda*-mark, _including_ reprises and/or alt. endings, Ex.: `{1|2}3c4¤5 = 1213412135`.

### Note lengths/rests

Since the traditional Tune Code System omitts note lengths and rests, and there might even be alternate variants of the rythm, note length and rests are stored in a complementary string:
- The basic note length is stored as an digit *n*, such that the note value *N = 2^(-n)*. Hence, 0 is a whole note, 1 is a half note, 2 is a quarter note, 3 is a eigth etc.
- In similar sense, a rest is dealt with as a letter:
    - k...z  if the rest is assumed to "cling" to the previous note, or
    - a...j if the rest is assumed to "cling" to the next note (useful when dealing with reprises/alt. endings/codas etc.)
    - Of course, a/k is a whole rest, b/l is a half rest etc.
- If a note/rest is dotted, one (or two) dots will follow the digit/letter.
- If a fermata is supposed to be placed on a note/rest, a comma will follow the digit/letter.
- It is also possible to use braces for "reprising" a series of note length/rests.
- A `-` will omitt the corresponding note in the "main" string.
- A `_` will make the note played as two, with a slur connecting them, Ex.: `1_3` will play the note a one whole note and then as a quarter note.

### Harmony

Optionally, the harmony of a tune can be stored in a *third* string, based on the [Nashville Number System](https://en.wikipedia.org/wiki/Nashville_number_system), but with binding to *notes* rather than just rely on time/beats, with `_` representing keeping the previous chords over the next note (and hence exclude any dots/bars used in traditional NNS).

### Backus-Naur Format

With this definitions, it is finally possible to store a tune in the API. The definition of the "plotter"-mode for tunes, similiar to the one used for lyrics:

```
<person_line> ::= @<person_idx> <year>[ <what> [[<birth>]-[<death>] <full_name>{;<full_name>}]]

<syllable> ::= X | U
<verse_feet> ::= I | T | D | B | P
<base_metre> ::= <integer><verse_feet> | <syllable>+
<metre> ::= <base_metre>-<integer>{;<base_metre>-<integer>}

<what> ::= n/a | <stem_name>{,<stem_name>}

<time> ::= <integer>/<integer>
<note> ::= 1 | 2 | 3 | 4 | 5 | 6 | 7
<tune_code_sequence> ::= ( <note> | D | U | \| | # | b | \{ | \} | f | F | $ | c | C | ¤ )+
<tune_rythm_sequence> ::= ( <integer> | <letter> | . | \{ | \} | _ | - )+
<tune_harmony_sequence> ::= ( <note> | _ | - | ⁷ | ° | + | Δ | ⁹ | ⁶ | + | ¹ | ² | ³ | ⁴ | ⁵ | ⁸ )+
<tune_stem_line> ::= %[<stem_name>]:<extended_tune_code_sequence>(%[<rythm_name>]:<time>:<tune_rythm_sequence>>)+{%[<harmony_name>]:<tune_harmony_sequence>}

<tune_link> ::= $<file_format>$<description>$<URL>

<tune> ::= <tune_idx><EOL><title><EOL><metre><EOL>{<person_line><EOL>}{#<language_iso_639-2/B> <comment><EOL>}(<tune_stem_line><EOL>)+{<tune_link><EOL>}
<tunes> ::= <tune>{<EOL>===<EOL><tune>}
```

There is also some practical [examples](tune/sample.txt) as well.
