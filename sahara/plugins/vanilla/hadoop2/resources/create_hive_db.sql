CREATE DATABASE metastore;
USE metastore;
SOURCE /opt/hive/scripts/metastore/upgrade/mysql/hive-schema-0.10.0.mysql.sql;
CREATE USER 'hive'@'localhost' IDENTIFIED BY 'pass';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'hive'@'localhost';
GRANT ALL PRIVILEGES ON metastore.* TO 'hive'@'localhost' IDENTIFIED BY 'pass';
GRANT ALL PRIVILEGES ON metastore.* TO 'hive'@'%' IDENTIFIED BY 'pass';
FLUSH PRIVILEGES;
exit