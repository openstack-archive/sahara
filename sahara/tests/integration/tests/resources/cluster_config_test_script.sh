#!/bin/bash -x

log=/tmp/config-test-log.txt

case $1 in
    NameNodeHeapSize)
        FUNC="check_nn_heap_size"
    ;;

    SecondaryNameNodeHeapSize)
        FUNC="check_snn_heap_size"
    ;;

    JobTrackerHeapSize)
        FUNC="check_jt_heap_size"
    ;;

    DataNodeHeapSize)
        FUNC="check_dn_heap_size"
    ;;

    TaskTrackerHeapSize)
        FUNC="check_tt_heap_size"
    ;;

    OozieHeapSize)
        FUNC="check_oozie_heap_size"
    ;;

    oozie.notification.url.connection.timeout)
        FUNC="check_oozie_notification_url_connection_timeout"
    ;;

    dfs.replication)
        FUNC="check_dfs_replication"
    ;;

    mapred.map.tasks.speculative.execution)
        FUNC="check_mapred_map_tasks_speculative_execution"
    ;;

    mapred.child.java.opts)
        FUNC="check_mapred_child_java_opts"
    ;;
esac
shift

if [ "$1" = "-value" ]; then
    VALUE="$2"
fi
shift

check_submitted_parameter() {

    case "$1" in
        config_value)
            if [ -z "$VALUE" ]; then
                echo "Config value is not specified" >> $log
                exit 1
            fi
        ;;
    esac
}

compare_config_values() {

    check_submitted_parameter config_value

    if [ "$VALUE" = "$1" ]; then
        echo -e "CHECK IS SUCCESSFUL \n\n" >> $log && exit 0
    else
        echo -e "Config value while cluster creation request: $VALUE \n" >> $log
        echo -e "Actual config value on node: $1 \n" >> $log
        echo "$VALUE != $1" >> $log && exit 1
    fi
}

check_heap_size() {

    heap_size=`ps aux | grep java | grep $1 | grep -o 'Xmx[0-9]\{1,10\}m' | tail -n 1 | grep -o '[0-9]\{1,100\}'`

    compare_config_values $heap_size
}

check_nn_heap_size() {

    echo -e "*********************** NAME NODE HEAP SIZE **********************\n" >> $log

    check_heap_size "namenode"
}

check_snn_heap_size() {

    echo -e "*********************** SECONDARY NAME NODE HEAP SIZE **********************\n" >> $log

    check_heap_size "secondarynamenode"
}

check_jt_heap_size() {

    echo -e "********************** JOB TRACKER HEAP SIZE *********************\n" >> $log

    check_heap_size "jobtracker"
}

check_dn_heap_size() {

    echo -e "*********************** DATA NODE HEAP SIZE **********************\n" >> $log

    check_heap_size "datanode"
}

check_tt_heap_size() {

    echo -e "********************* TASK TRACKER HEAP SIZE *********************\n" >> $log

    check_heap_size "tasktracker"
}

check_oozie_heap_size() {

    echo -e "************************* OOZIE HEAP SIZE ************************\n" >> $log

    check_heap_size "oozie"
}

check_oozie_notification_url_connection_timeout() {

    echo -e "************ OOZIE.NOTIFICATION.URL.CONNECTION.TIMEOUT ***********\n" >> $log

    value=`cat /opt/oozie/conf/oozie-site.xml | grep -A 1 '.*oozie.notification.url.connection.timeout.*' | tail -n 1 | grep -o "[0-9]\{1,10\}"`

    compare_config_values $value
}

check_dfs_replication() {

    echo -e "************************* DFS.REPLICATION ************************\n" >> $log

    value=`cat /etc/hadoop/hdfs-site.xml | grep -A 1 '.*dfs.replication.*' | tail -n 1 | grep -o "[0-9]\{1,10\}"`

    compare_config_values $value
}

check_mapred_map_tasks_speculative_execution() {

    echo -e "************* MAPRED.MAP.TASKS.SPECULATIVE.EXECUTION *************\n" >> $log

    value=`cat /etc/hadoop/mapred-site.xml | grep -A 1 '.*mapred.map.tasks.speculative.execution.*' | tail -n 1 | grep -o "[a-z,A-Z]\{4,5\}" | grep -v "value"`

    compare_config_values $value
}

check_mapred_child_java_opts() {

    echo -e "********************* MAPRED.CHILD.JAVA.OPTS *********************\n" >> $log

    value=`cat /etc/hadoop/mapred-site.xml | grep -A 1 '.*mapred.child.java.opts.*' | tail -n 1 | grep -o "\-Xmx[0-9]\{1,10\}m"`

    compare_config_values $value
}

$FUNC
