#!/bin/bash

dir=/tmp
log=$dir/log_config.txt

case $1 in
        NameNodeHeapSize)
                FUNC="nn_size"
        ;;
        JobTrackerHeapSize)
                FUNC="jt_size"
        ;;
        DataNodeHeapSize)
                FUNC="dn_size"
        ;;
        TaskTrackerHeapSize)
                FUNC="tt_size"
        ;;
        EnableSwift)
                FUNC="check_swift"
        ;;
        dfs.replication)
                FUNC="dfs_replication"
        ;;
        mapred.map.tasks.speculative.execution)
                FUNK="mapred_map_tasks_speculative_execution"
        ;;
        mapred.child.java.opts)
                FUNK="mapred_child_java_opts"
        ;;
esac

shift

until [ -z $1 ]
do
        if [ "$1" = "-val" ]
        then
                VALUE="$2"
        fi
        if [ "$1" = "-url" ]
        then
                URL="$2"
        fi
        shift
done

f_var_check() {
        case "$1" in
                config_value)
                        if [ -z "$VALUE" ]
                        then
                                echo "config_value_is_not_specified"
                                exit 0
                        fi
                ;;
                v_url)
                        if [ -z "$URL" ]
                        then
                                echo "url_is_not_specified"
                                exit 0
                        fi
                ;;
        esac
}

compare_and_exit() {
f_var_check config_value
if [ "$VALUE" = "$1" ]; then exit 0; else echo "$VALUE != $1" && exit 1; fi
}

check_size() {
    s=`ps aux | grep java | grep $1 | grep -o 'Xmx[0-9]\{1,10\}m' | tail -n 1 | grep -o '[0-9]\{1,100\}'`
    compare_and_exit "$s"
}

nn_size() {
    check_size "namenode"
}

jt_size() {
    check_size "jobtracker"
}

dn_size() {
    check_size "datanode"
}

tt_size() {
    check_size "tasktracker"
}

check_swift() {
    f_var_check config_value
    f_var_check v_url
    sudo apt-get -y --force-yes install python-pip
    sleep 1
    sudo pip install python-swiftclient==1.2.0
    sleep 1
    sudo pip install python-keystoneclient
    sleep 1
    echo "$URL"
    export ST_AUTH="$URL"
    export ST_USER="ci:admin"
    export ST_KEY="swordfish"
    sleep 1
    swift -V2.0 delete configTesting
    swift -V2.0 post configTesting
    echo "Test hadoop config- Enable Swift" > /tmp/swiftlog.txt
    sudo su -c "hadoop dfs -copyFromLocal /tmp/swiftlog.txt /" hadoop
    sudo su -c "hadoop distcp -D fs.swift.service.savanna.username=admin -D fs.swift.service.savanna.tenant=ci -D fs.swift.service.savanna.password=swordfish /swiftlog.txt swift://configTesting.savanna/" hadoop
    if [ -z `swift -V2.0 list configTesting | grep -o "swiftlog.txt"` ]; then val="False"; else val="True"; fi
    compare_and_exit "$val" "$VALUE"
}

dfs_replication() {
    s=`cat /etc/hadoop/hdfs-site.xml | grep -A 1 '.*dfs.replication.*' | tail -n 1 | grep -o "[0-9]\{1,10\}"`
    compare_and_exit "$s"
}

mapred_map_tasks_speculative_execution() {
    s=`cat /etc/hadoop/mapred-site.xml | grep -A 1 '.*mapred.map.tasks.speculative.execution.*' | tail -n 1 | grep -o "[a-z]\{4,5\}" | grep -v "value"`
    compare_and_exit "$s"
}

mapred_child_java_opts() {
    s=`cat /etc/hadoop/mapred-site.xml | grep -A 1 '.*mapred.child.java.opts.*' | tail -n 1 | grep -o "\-Xmx[0-9]\{1,10\}m"`
    compare_and_exit "$s"
}

$FUNC