#!/bin/bash -x

set -e

log=/tmp/key-value-store-test-log.txt

case $1 in
    create_table)
        FUNC="create_table"
    ;;
    create_solr_collection)
        FUNC="create_solr_collection"
    ;;
    add_indexer)
        FUNC="add_hbase_indexer"
    ;;
    create_data)
        FUNC="create_data"
    ;;
    check_solr)
        FUNC="check_solr_query"
    ;;
    remove_data)
        FUNC="remove_data"
    ;;
esac
shift

if [ "$1" = "-ip"  ]; then
    IP="$2"
else
    IP="127.0.0.1"
fi

create_table(){
exec hbase shell << EOF
disable 'test-keyvalue'
drop 'test-keyvalue'
create 'test-keyvalue', { NAME => 'info', REPLICATION_SCOPE => 1 }
exit
EOF
}

create_solr_collection(){
    solrctl instancedir --generate $HOME/solr_keyvalue_configs
    sleep 3
    solrctl instancedir --create keyvalue_collection $HOME/solr_keyvalue_configs
    sleep 30
    solrctl collection --create keyvalue_collection -s 1 -c keyvalue_collection
    sleep 3
}

add_hbase_indexer(){
    hbase-indexer add-indexer -n myindexer -c key_value_store_indexer.xml -cp solr.zk=localhost:2181/solr -cp solr.collection=keyvalue_collection
    sleep 3
}

create_data(){
exec hbase shell << EOF
put 'test-keyvalue', 'row1', 'info:firstname', 'John'
put 'test-keyvalue', 'row1', 'info:lastname', 'Smith'
exit
EOF
}

remove_data(){
exec hbase shell << EOF
delete 'test-keyvalue', 'row1', 'info:firstname', 'John'
delete 'test-keyvalue', 'row1', 'info:lastname', 'Smith'
exit
EOF
}

check_solr_query(){
    sleep 3
    if [ `curl "http://$IP:8983/solr/keyvalue_collection_shard1_replica1/select?q=*:*&wt=json&indent=true" | grep "John" | wc -l` -ge 1 ]; then
        echo -e "Solr query is Successful. \n" >> $log
        exit 0
    else
        echo -e "Solr query is Failed. \n" >> $log
        exit 1
    fi
}

$FUNC
