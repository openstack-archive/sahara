create database oozie;
grant all privileges on oozie.* to 'oozie'@'localhost' identified by 'password';
grant all privileges on oozie.* to 'oozie'@'%' identified by 'password';
flush privileges;
exit
