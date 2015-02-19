CREATE DATABASE {{ db_name }};
CREATE USER {{ user }}@'localhost' IDENTIFIED BY '{{ password }}';
CREATE USER {{ user }}@'127.0.0.1' IDENTIFIED BY '{{ password }}';
GRANT ALL PRIVILEGES ON {{ db_name }}.* TO {{ user }}@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON {{ db_name }}.* TO {{ user }}@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
FLUSH HOSTS;