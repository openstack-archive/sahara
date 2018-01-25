CREATE DATABASE metastore;
USE metastore;
SOURCE /opt/hive/scripts/metastore/upgrade/mysql/hive-schema-2.3.0.mysql.sql;
CREATE USER 'hive'@'localhost' IDENTIFIED BY '{{password}}';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'hive'@'localhost';
GRANT ALL PRIVILEGES ON metastore.* TO 'hive'@'localhost' IDENTIFIED BY '{{password}}';
GRANT ALL PRIVILEGES ON metastore.* TO 'hive'@'%' IDENTIFIED BY '{{password}}';
FLUSH PRIVILEGES;
exit
