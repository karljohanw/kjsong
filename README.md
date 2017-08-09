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

In the catalogs *song* and *tune* respectively, there is a sample.txt file contaning the hymn "Amazing Grace" and the Finnish anthem "Maame/Vårt land", and corresponding tunes, in "plotter" mode (swe. *plottrig*≈messy), a more compact way to prepare the data than in traditional JSON. The sample-files can be converted to JSON and sent to the API with the command

```
song|tune> ./textput sample.txt
```

Afterwards, run

```
api> ./forecast
```

to rebuild the graph containing the meters. Now you should be able to call the API for this two songs, for the full API definition, please see *api_definition.txt*.

