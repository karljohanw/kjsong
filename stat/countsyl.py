#!/usr/bin/env python

# Count syllables in a word.
#
# Doesn't use any fancy knowledge, just a few super simple rules:
# a vowel starts each syllable;
# a doubled vowel doesn't add an extra syllable;
# two or more different vowels together are a diphthong,
# and probably don't start a new syllable but might;
# y is considered a vowel when it follows a consonant.
#
# Even with these simple rules, it gets results far better
# than python-hyphenate with the libreoffice hyphenation dictionary.
#
# Copyright 2013 by Akkana Peck http://shallowsky.com.
# Share and enjoy under the terms of the GPLv2 or later.

def count_syllables(word, vowels = ['a', 'e', 'i', 'o', 'u'], lang='eng'):
    on_vowel = None
    in_diphthong = False
    minsyl = 0
    maxsyl = 0
    lastchar = None

    word = word.lower()
    for c in word:
        is_vowel = c in vowels

        # y is a special case in english
        if lang=='eng' and c == 'y':
            is_vowel = (on_vowel==False)

        if is_vowel:
            if not on_vowel:
                # We weren't on a vowel before.
                # Seeing a new vowel bumps the syllable count.
                minsyl += 1
                maxsyl += 1
                in_diphthong = False
            elif on_vowel and not in_diphthong and c != lastchar:
                # We were already in a vowel.
                # Don't increment anything except the max count,
                # and only do that once per diphthong.
                in_diphthong = True
                if lang!='ger': #german language does not pronounce diphthongs over more syllables
                    maxsyl += 1
        else:
            in_diphthong = False

        on_vowel = is_vowel
        lastchar = c

    # Some special cases:
    # Mute e if last in english word
    # KNOWN BUG: Will cause problem with words like "pipeline", answer 3 syllables but just 2
    if lang=='eng' and word[-1] == 'e' and maxsyl>1 and not minsyl==1:
        minsyl -= (not in_diphthong)
        maxsyl -= 1
    # Mute e or es if last in french word (but possible to pronounce to simulate a feminine rhyme)
    if lang=='fre' and (word[-1]=='e' or word[-2:]=='es') and maxsyl>1 and not minsyl==1:
        minsyl -= (not in_diphthong)
    if lang=='hun' and word[-1]=='y' and maxsyl>1 and not minsyl==1:
        minsyl -= (not in_diphthong)

    return (minsyl,maxsyl)
