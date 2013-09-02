CREATE DATABASE metastore;
USE metastore;
SOURCE /opt/hive/scripts/metastore/upgrade/mysql/hive-schema-0.10.0.mysql.sql;
CREATE USER 'hive'@'localhost' IDENTIFIED BY 'hive';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'hive'@'localhost';
GRANT SELECT,INSERT,UPDATE,DELETE,LOCK TABLES,EXECUTE ON metastore.* TO 'hive'@'localhost';
FLUSH PRIVILEGES;
exit