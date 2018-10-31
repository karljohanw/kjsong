CREATE TABLE IF NOT EXISTS Words(
       lang  	   CHAR(3) NOT NULL,
       word	   VARCHAR(50) NOT NULL,
       stress	   TINYINT UNSIGNED NOT NULL DEFAULT 0,
       distress	   TINYINT UNSIGNED NOT NULL DEFAULT 0,
       pattern	   VARCHAR(50) NOT NULL,
       flag	   INTEGER UNSIGNED NOT NULL DEFAULT 0,
       UNIQUE(lang,word,pattern)
);

CREATE TABLE IF NOT EXISTS HarmonyTransitions(
       a     CHAR(16) NOT NULL,
       b     CHAR(16) NOT NULL,
       nr    BIGINT UNSIGNED NOT NULL DEFAULT 1,
       UNIQUE(a,b)
);

CREATE TABLE IF NOT EXISTS HarmonyObservations(
       st    CHAR(16) NOT NULL,
       obs   CHAR(16) NOT NULL,
       nr    BIGINT UNSIGNED NOT NULL DEFAULT 1,
       UNIQUE(st,obs)
);

CREATE TABLE IF NOT EXISTS MelodyTransitions(
       a     CHAR(16) NOT NULL,
       b     CHAR(16) NOT NULL,
       stem  VARCHAR(50) NOT NULL DEFAULT '',
       nr    BIGINT UNSIGNED NOT NULL DEFAULT 1,
       UNIQUE(a,b,stem)
);

CREATE TABLE IF NOT EXISTS MelodyObservations(
       st    CHAR(16) NOT NULL,
       obs   CHAR(16) NOT NULL,
       stem  VARCHAR(50) NOT NULL DEFAULT '',
       nr    BIGINT UNSIGNED NOT NULL DEFAULT 1,
       UNIQUE(st,obs,stem)
);

CREATE TABLE IF NOT EXISTS UsedLyrics(
       lyric  BIGINT UNIQUE NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS UsedTunes(
       tune  BIGINT UNIQUE NOT NULL DEFAULT 0
);

GRANT ALL ON `kjstats`.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT FILE ON *.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON `kjstats`.* TO 'searcher'@'localhost' IDENTIFIED BY 'password';
