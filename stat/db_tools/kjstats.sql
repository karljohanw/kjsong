CREATE TABLE IF NOT EXISTS Words(
       lang  	   CHAR(3) NOT NULL,
       word	   VARCHAR(50) NOT NULL,
       stress	   TINYINT UNSIGNED NOT NULL DEFAULT 0,
       distress	   TINYINT UNSIGNED NOT NULL DEFAULT 0,
       pattern	   VARCHAR(50) NOT NULL,
       flag	   INTEGER UNSIGNED NOT NULL DEFAULT 0,
       UNIQUE(lang,word,pattern)
);

GRANT ALL ON `kjstats`.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT FILE ON *.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON `kjstats`.* TO 'searcher'@'localhost' IDENTIFIED BY 'password';
