#!/bin/bash
#touch script.sh && chmod +x script.sh && vim script.sh

dir=/tmp/outputTestMapReduce
log=$dir/log.txt

case $1 in
        mr)
                FUNC="map_reduce"
        ;;
        pi)
                FUNC="run_pi_job"
        ;;
        gn)
                FUNC="get_job_name"
        ;;
        ed)
                FUNC="check_exist_directory"
        ;;
esac

shift

until [ -z $1 ]
do
        if [ "$1" = "-nc" ]
        then
                NODE_COUNT="$2"
        elif [ "$1" = "-jn" ]
        then
                JOB_NAME="$2"
        elif [ "$1" = "-hv" ]
        then
                HADOOP_VERSION="$2"
        elif [ "$1" = "-hd" ]
        then
                HADOOP_DIRECTORY="$2"
        elif [ "$1" = "-hld" ]
        then
                HADOOP_LOG_DIRECTORY="$2"
        fi
        shift
done

f_var_check() {
        case "$1" in
                v_node_count)
                        if [ -z "$NODE_COUNT" ]
                        then
                                echo "count_of_node_not_specified"
                                exit 0
                        fi
                ;;
                v_job_name)
                        if [ -z "$JOB_NAME" ]
                        then
                                echo "job_name_not_specified"
                                exit 0
                        fi
                ;;
                v_hadoop_version)
                        if [ -z "$HADOOP_VERSION" ]
                        then
                                echo "hadoop_version_not_specified"
                                exit 0
                        fi
                ;;
                v_hadoop_directory)
                        if [ -z "$HADOOP_DIRECTORY" ]
                        then
                                echo "hadoop_directory_not_specified"
                                exit 0
                        fi
                ;;
                v_hadoop_log_directory)
                        if [ -z "$HADOOP_LOG_DIRECTORY" ]
                        then
                                echo "hadoop_log_directory_not_specified"
                                exit 0
                        fi
                ;;
        esac
}

f_create_log_dir() {
    rm -r $dir 2>/dev/null
    mkdir $dir
    chmod -R 777 $dir
    touch $log
}

map_reduce() {
    f_create_log_dir
    f_var_check v_hadoop_version
    f_var_check v_hadoop_directory
    echo "
    [------ dpkg------]
    `dpkg --get-selections | grep hadoop`
    [------jps------]
    `jps | grep -v Jps`
    [------netstat------]
    `sudo netstat -plten | grep java`
    [------test for hdfs------]">>$log
    echo `dmesg > $dir/input` 2>>$log
    sudo su -c "hadoop dfs -ls /" hadoop &&
    sudo su -c "hadoop dfs -mkdir /test" hadoop &&
    sudo su -c "hadoop dfs -copyFromLocal $dir/input /test/mydata" hadoop 2>>$log
    echo "[------start job------]">>$log &&
    sudo su -c "cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples-$HADOOP_VERSION.jar wordcount /test/mydata /test/output" hadoop 2>>$log &&
    sudo su -c "hadoop dfs -copyToLocal /test/output/ $dir/out/" hadoop 2>>$log &&
    sudo su -c "hadoop dfs -rmr /test" hadoop 2>>$log
}

run_pi_job() {
    f_var_check v_node_count
    f_var_check v_hadoop_version
    f_var_check v_hadoop_directory
    f_create_log_dir
    sudo su -c "cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples-$HADOOP_VERSION.jar pi $[$NODE_COUNT*10] 1000" hadoop 2>>$log
}

get_job_name() {
    f_var_check v_hadoop_directory
    sudo su -c "cd $HADOOP_DIRECTORY && hadoop job -list all | tail -n1" hadoop | awk '{print $1}' 2>>$log
}

check_exist_directory() {
    f_var_check v_job_name
    f_var_check v_hadoop_log_directory
    if ! [ -d $HADOOP_LOG_DIRECTORY/$JOB_NAME ];
    then echo "directory_not_found" && exit 1
    fi
}

$FUNC