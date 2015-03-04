#!/bin/bash -x

set -e

check_solr_availability(){
    solrctl instancedir --generate $HOME/solr_configs
    sleep 3
    solrctl instancedir --create collection2 $HOME/solr_configs
    sleep 30
    solrctl collection --create collection2 -s 1 -c collection2
    sleep 3
    cd /usr/share/doc/solr-doc/example/exampledocs
    /usr/lib/jvm/java-7-oracle-cloudera/bin/java -Durl=http://localhost:8983/solr/collection2/update -jar post.jar monitor.xml
    if [ `curl "http://localhost:8983/solr/collection2_shard1_replica1/select?q=UltraSharp&wt=json&indent=true" | grep "Dell Widescreen UltraSharp 3007WFP" | wc -l` -ge 1 ]; then
        echo "solr is available"
        exit 0
    else
        echo "solr is not available"
        exit 1
    fi
}

check_solr_availability
