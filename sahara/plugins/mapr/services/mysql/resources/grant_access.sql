{% for host in hosts %}
CREATE USER {{ user }}@'{{ host }}' IDENTIFIED BY '{{ password }}';
GRANT ALL PRIVILEGES ON {{ db_name }}.* TO {{ user }}@'{{ host }}' WITH GRANT OPTION;
{% endfor %}
FLUSH PRIVILEGES;
FLUSH HOSTS;