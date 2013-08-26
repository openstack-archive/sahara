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

    elif [ "$1" = "-hu" ]
    then
        HADOOP_USER="$2"

    elif [ "$1" = "-pn" ]
    then
        PLUGIN_NAME="$2"

    fi
    shift
done

f_var_check() {
    case "$1" in
        v_node_count)
            if [ -z "$NODE_COUNT" ]
            then
                echo "Node count not specified"
                exit 1
            fi
        ;;
        v_job_name)
            if [ -z "$JOB_NAME" ]
            then
                echo "Job name not specified"
                exit 1
            fi
        ;;
        v_hadoop_version)
            if [ -z "$HADOOP_VERSION" ]
            then
                echo "Hadoop version not specified"
                exit 1
            fi
        ;;
        v_hadoop_directory)
            if [ -z "$HADOOP_DIRECTORY" ]
            then
                echo "Hadoop directory not specified"
                exit 1
            fi
        ;;
        v_hadoop_log_directory)
            if [ -z "$HADOOP_LOG_DIRECTORY" ]
            then
                echo "Hadoop log directory not specified"
                exit 1
            fi
        ;;
        v_hadoop_user)
            if [ -z "$HADOOP_USER" ]
            then
                echo "Hadoop user not specified"
                exit 1
            fi
        ;;
        v_plugin_name)
            if [ -z "$PLUGIN_NAME" ]
            then
                echo "Plugin name not specified"
                exit 1
            fi
        ;;
    esac
}

f_create_log_dir() {
    if ! [ -d $dir ]
    then
        mkdir $dir
        chmod -R 777 $dir
        touch $log
    fi
}

map_reduce() {
    f_create_log_dir
    f_var_check v_hadoop_version
    f_var_check v_hadoop_directory
    f_var_check v_hadoop_user
    f_var_check v_plugin_name

    echo -e "<************************DPKG***********************> \n`dpkg --get-selections | grep hadoop` \n\n\n" >> $log
    echo -e "<************************JPS************************> \n`jps | grep -v Jps` \n\n\n" >> $log
    echo -e "<**********************NETSTAT**********************> \n`sudo netstat -plten | grep java` \n\n\n" >> $log

    echo -e "<*************************TEST FOR HDFS**************************> \n" >> $log
    `dmesg > $dir/input`

    echo -e "`sudo su -c \"hadoop dfs -ls /\" $HADOOP_USER` \n\n" >> $log
    echo -e "`sudo su -c \"hadoop dfs -mkdir /test\" $HADOOP_USER` \n\n" >> $log
    echo -e "`sudo su -c \"hadoop dfs -copyFromLocal $dir/input /test/mydata\" $HADOOP_USER` \n\n\n" >> $log

    echo -e "<*******************START OF JOB \"WORDCOUNT\"*******************> \n" >> $log

    hadoop_version=-$HADOOP_VERSION
    if [ "$PLUGIN_NAME" = "hdp" ]
    then
        hadoop_version=""
    fi

    echo -e "`sudo su -c \"cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples$hadoop_version.jar wordcount /test/mydata /test/output\" $HADOOP_USER` \n\n" >> $log

    echo -e "`sudo su -c \"hadoop dfs -copyToLocal /test/output/ $dir/out/\" $HADOOP_USER` \n\n" >> $log
    echo -e "`sudo su -c \"hadoop dfs -rmr /test\" $HADOOP_USER` \n\n\n" >> $log
}

run_pi_job() {
    f_var_check v_node_count
    f_var_check v_hadoop_version
    f_var_check v_hadoop_directory
    f_create_log_dir
    f_var_check v_hadoop_user
    f_var_check v_plugin_name

    hadoop_version=-$HADOOP_VERSION
    if [ "$PLUGIN_NAME" = "hdp" ]
    then
        hadoop_version=""
    fi

    echo -e "<***********************START OF JOB \"PI\"**********************> \n" >> $log
    echo -e "`sudo su -c \"cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples$hadoop_version.jar pi $[$NODE_COUNT*10] 1000\" $HADOOP_USER` \n\n\n" >> $log
}

get_job_name() {
    hadoop job -list all | tail -n1 | awk '{print $1}'
}

check_exist_directory() {
    f_var_check v_job_name
    f_var_check v_hadoop_log_directory

    if ! [ -d $HADOOP_LOG_DIRECTORY/$JOB_NAME ]
    then
        echo "Log file of job \"PI\" not found" && exit 1
    fi
}

$FUNC
