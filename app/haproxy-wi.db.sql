CREATE TABLE IF NOT EXISTS `user` (`id`	INTEGER NOT NULL AUTO_INCREMENT,`username`	VARCHAR ( 64 ) UNIQUE,`email` VARCHAR ( 120 ) UNIQUE, `password` VARCHAR ( 128 ),`role`	VARCHAR ( 128 ),`groups` VARCHAR ( 120 ), ldap_user INTEGER NOT NULL DEFAULT 0, activeuser INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(`id`) );
INSERT INTO `user` (username, email, password, role, groups) VALUES ('admin','admin@localhost','21232f297a57a5a743894a0e4a801fc3','admin','1');
INSERT INTO `user` (username, email, password, role, groups) VALUES ('editor','editor@localhost','5aee9dbd2a188839105073571bee1b1f','editor','1');
INSERT INTO `user` (username, email, password, role, groups) VALUES ('guest','guest@localhost','084e0343a0486ff05530df6c705c8bb4','guest','1');
CREATE TABLE IF NOT EXISTS `servers` (`id`	INTEGER NOT NULL AUTO_INCREMENT,`hostname` VARCHAR ( 64 ),`ip` VARCHAR ( 64 ) UNIQUE,`groups` VARCHAR ( 64 ), type_ip INTEGER NOT NULL DEFAULT 0, enable INTEGER NOT NULL DEFAULT 1, master INTEGER NOT NULL DEFAULT 0, cred INTEGER NOT NULL DEFAULT 1, alert INTEGER NOT NULL DEFAULT 0, metrics INTEGER NOT NULL DEFAULT 0, port INTEGER NOT NULL DEFAULT 22, `desc` varchar(64), active INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(`id`) );
CREATE TABLE IF NOT EXISTS `role` (`id`	INTEGER NOT NULL AUTO_INCREMENT,`name`	VARCHAR ( 80 ) UNIQUE,`description`	VARCHAR ( 255 ),PRIMARY KEY(`id`) );
INSERT INTO `role` (name, description) VALUES ('admin','Can do everything');
INSERT INTO `role` (name, description) VALUES ('editor','Can edit configs');
INSERT INTO `role` (name, description) VALUES ('guest','Read only access');
CREATE TABLE IF NOT EXISTS `groups` (`id`	INTEGER NOT NULL AUTO_INCREMENT,`name` VARCHAR ( 80 ) UNIQUE,`description` VARCHAR ( 255 ),PRIMARY KEY(`id`));
INSERT INTO `groups` (name, description) VALUES ('All','All servers enter in this group');	
CREATE TABLE IF NOT EXISTS `uuid` (`user_id` INTEGER NOT NULL, `uuid` varchar ( 64 ),`exp` DATETIME default CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS `token` (`user_id` INTEGER, `token` varchar(64), `exp` timestamp default CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS `cred` (`id` integer primary key AUTO_INCREMENT, `name` VARCHAR ( 64 ), `enable` INTEGER NOT NULL DEFAULT 1, `username` VARCHAR ( 64 ) NOT NULL, `password` VARCHAR ( 64 ) NOT NULL, groups INTEGER NOT NULL DEFAULT 1, UNIQUE(name,groups));
CREATE TABLE IF NOT EXISTS `telegram` (`id` integer primary key auto_increment, `token` VARCHAR ( 64 ), `chanel_name` INTEGER NOT NULL DEFAULT 1, `groups` INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS `metrics` (`serv` varchar(64), curr_con INTEGER, cur_ssl_con INTEGER, sess_rate INTEGER, max_sess_rate INTEGER,`date`  DATETIME default '0000-00-00 00:00:00');
CREATE TABLE IF NOT EXISTS `settings` (`param` varchar(64), value varchar(64), section varchar(64), `desc` varchar(100), `group` INTEGER NOT NULL DEFAULT 1, UNIQUE(param, `group`));
CREATE TABLE IF NOT EXISTS `version` (`version` varchar(64));
CREATE TABLE IF NOT EXISTS `options` ( `id`	INTEGER NOT NULL, `options`	VARCHAR ( 64 ), `groups`	VARCHAR ( 120 ), PRIMARY KEY(`id`));
CREATE TABLE IF NOT EXISTS `saved_servers` ( `id` INTEGER NOT NULL, `server` VARCHAR ( 64 ), `description` VARCHAR ( 120 ), `groups` VARCHAR ( 120 ), PRIMARY KEY(`id`)); 
CREATE TABLE IF NOT EXISTS `backups` ( `id` INTEGER NOT NULL, `server` VARCHAR ( 64 ), `rhost` VARCHAR ( 120 ), `rpath` VARCHAR ( 120 ), `time` VARCHAR ( 120 ),  cred INTEGER, `description` VARCHAR ( 120 ), PRIMARY KEY(`id`));
CREATE TABLE IF NOT EXISTS `waf` (`server_id` INTEGER UNIQUE, metrics INTEGER);
CREATE TABLE IF NOT EXISTS `waf_metrics` (`serv` varchar(64), conn INTEGER, `date`  DATETIME default '0000-00-00 00:00:00');
CREATE TABLE IF NOT EXISTS user_groups(user_id INTEGER NOT NULL, user_group_id INTEGER NOT NULL, UNIQUE(user_id,user_group_id));