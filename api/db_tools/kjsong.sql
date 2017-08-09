CREATE TABLE IF NOT EXISTS Metre(
       metre 	    SERIAL PRIMARY KEY AUTO_INCREMENT,
       metre_key    VARCHAR(20) UNIQUE DEFAULT NULL,
       metre_string VARCHAR(255) UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS Edge(
       A     BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       i     TINYINT UNSIGNED NOT NULL,
       B     BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       j     TINYINT UNSIGNED NOT NULL,
       U     TINYINT UNSIGNED NOT NULL,
       X     TINYINT UNSIGNED NOT NULL,
       PRIMARY KEY(A,i,B,j)
);

CREATE TABLE IF NOT EXISTS Part(
       comp	BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       part	BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       loops	TINYINT UNSIGNED NOT NULL,
       ord	TINYINT UNSIGNED NOT NULL,
       PRIMARY KEY(comp,part,ord)
);

CREATE TABLE IF NOT EXISTS Lyric(
       lyric	  SERIAL PRIMARY KEY AUTO_INCREMENT,
       lyric_key  VARCHAR(50) UNIQUE NOT NULL,
       orig_lang  CHAR(3) NOT NULL,
       metre 	  BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       loops  	  TINYINT UNSIGNED NOT NULL
);

CREATE TABLE IF NOT EXISTS Tune(
       tune	  SERIAL PRIMARY KEY AUTO_INCREMENT,
       tune_key   VARCHAR(60) UNIQUE NOT NULL,
       ttl	  VARCHAR(255) NOT NULL,
       metre 	  BIGINT UNSIGNED NOT NULL REFERENCES Metre,
       loops  	  TINYINT UNSIGNED NOT NULL
);
CREATE TABLE IF NOT EXISTS TuneCode(
       tune	BIGINT UNSIGNED NOT NULL REFERENCES Tune,
       stem	VARCHAR(50) NOT NULL DEFAULT '',
       code	VARCHAR(1023) NOT NULL,
       PRIMARY KEY(tune,stem)
);
CREATE TABLE IF NOT EXISTS TuneHarmony(
       tune	 BIGINT UNSIGNED NOT NULL REFERENCES Tune,
       stem	 VARCHAR(50) NOT NULL REFERENCES TuneCode,
       var	 VARCHAR(50) NOT NULL DEFAULT '',
       nwns	 VARCHAR(1023) NOT NULL,
       PRIMARY KEY(tune,stem,var)
);
CREATE TABLE IF NOT EXISTS TuneRythm(
       tune	BIGINT UNSIGNED NOT NULL REFERENCES Tune,
       stem	VARCHAR(50) NOT NULL REFERENCES TuneCode,
       var 	VARCHAR(50) NOT NULL DEFAULT '',
       len	VARCHAR(1023) NOT NULL,
       k	VARCHAR(15) NOT NULL,
       PRIMARY KEY(tune,stem,var)
);

CREATE TABLE IF NOT EXISTS TuneLinks(
       tune	BIGINT UNSIGNED NOT NULL REFERENCES Tune,
       format	VARCHAR(5) NOT NULL,
       descr	VARCHAR(60) NOT NULL,
       url	VARCHAR(255) NOT NULL,
       PRIMARY KEY(tune,format,descr)
);

CREATE TABLE IF NOT EXISTS Keyword(
       lyric	BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       keyword 	VARCHAR(50) NOT NULL,
       PRIMARY KEY(lyric,keyword)
);

CREATE TABLE IF NOT EXISTS Person(
       person		SERIAL PRIMARY KEY AUTO_INCREMENT,
       person_key	VARCHAR(70) UNIQUE NOT NULL,
       birthYear 	INTEGER DEFAULT NULL,
       deathYear 	INTEGER DEFAULT NULL,
       comment 		VARCHAR(255) DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS PersonName(
       person	BIGINT UNSIGNED NOT NULL REFERENCES Person,
       nm	VARCHAR(225) NOT NULL,
       main	BOOLEAN NOT NULL DEFAULT FALSE,
       PRIMARY KEY(person,nm)
);

CREATE TABLE IF NOT EXISTS Composer(
       tune	INTEGER NOT NULL REFERENCES Tune,
       person   INTEGER NOT NULL REFERENCES Person,
       yr    	INTEGER NOT NULL,
       what  	VARCHAR(255) DEFAULT NULL,
       PRIMARY KEY(tune,person)
); 

CREATE TABLE IF NOT EXISTS Songbook(
       sb	SERIAL PRIMARY KEY AUTO_INCREMENT,
       sb_key	VARCHAR(50) UNIQUE NOT NULL,
       ttl	VARCHAR(225) NOT NULL,
       yr    	INTEGER NOT NULL,
       comment 	VARCHAR(255) DEFAULT NULL,
       sbisbn	BOOLEAN NOT NULL DEFAULT FALSE,
       UNIQUE(ttl,yr)
);

CREATE TABLE IF NOT EXISTS Title(
       lyric BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       ttl   VARCHAR(225) NOT NULL,
       lang  CHAR(3) NOT NULL,
       var   VARCHAR(30) NOT NULL DEFAULT '',
       main  BOOLEAN NOT NULL DEFAULT FALSE,
       PRIMARY KEY(lyric,ttl,lang,var)
);
CREATE TABLE IF NOT EXISTS Line(
       lyric BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       lang  CHAR(3) NOT NULL,
       var   VARCHAR(30) NOT NULL DEFAULT '',
       alt   VARCHAR(30) NOT NULL DEFAULT '',
       type  CHAR(1) NOT NULL DEFAULT 'v',
       vnr   TINYINT UNSIGNED NOT NULL,
       vch   CHAR(1) NOT NULL DEFAULT '',
       lnr   TINYINT UNSIGNED NOT NULL,
       stat  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
       line  VARCHAR(255) NOT NULL,
       cmnt  VARCHAR(255) DEFAULT NULL,
       UNIQUE(lyric,lang,var,alt,type,vnr,vch,lnr)
);
CREATE TABLE IF NOT EXISTS Comments(
       lyric BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       lang  CHAR(3) NOT NULL,
       var   VARCHAR(30) NOT NULL DEFAULT '',
       trans BOOLEAN NOT NULL DEFAULT FALSE,
       cmnt  VARCHAR(1023) NOT NULL,
       UNIQUE(lyric,lang,var,trans)
);
CREATE TABLE IF NOT EXISTS Publ(
       lyric	BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       lang	CHAR(3) NOT NULL,
       var	VARCHAR(30) NOT NULL DEFAULT '',
       tune   	BIGINT NOT NULL REFERENCES Tune,
       sb     	BIGINT NOT NULL REFERENCES Songbook,
       entry  	SMALLINT UNSIGNED,
       comment 	VARCHAR(255) DEFAULT NULL,
       PRIMARY KEY(lyric,lang,var,tune,sb,entry)
);
CREATE TABLE IF NOT EXISTS Author(
       lyric	BIGINT UNSIGNED NOT NULL REFERENCES Lyric,
       person  	BIGINT UNSIGNED NOT NULL REFERENCES Person,
       lang  	CHAR(3) NOT NULL,
       yr    	INTEGER NOT NULL,
       var   	VARCHAR(30) NOT NULL DEFAULT '',
       what  	VARCHAR(255) DEFAULT NULL,
       PRIMARY KEY(lyric,person,lang,yr,var)
);

ALTER TABLE Title CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE Line CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE Person CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE Tune CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE Songbook CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;
ALTER TABLE TuneLinks DROP INDEX tune;

GRANT ALL ON `kjsong`.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT FILE ON *.* TO 'updater'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON `kjsong`.* TO 'searcher'@'localhost' IDENTIFIED BY 'password';
