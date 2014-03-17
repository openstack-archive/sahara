#!/bin/bash -x

dir=/tmp/MapReduceTestOutput
log=$dir/log.txt

HADOOP_VERSION=""
HADOOP_DIRECTORY=""
HADOOP_LOG_DIRECTORY=""
HADOOP_USER=""

NODE_COUNT=""
PLUGIN_NAME=""

case $1 in
    run_pi_job)
        FUNC="run_pi_job"
    ;;

    get_pi_job_name)
        FUNC="get_pi_job_name"
    ;;

    check_directory)
        FUNC="check_job_directory_existence"
    ;;

    run_wordcount_job)
        FUNC="run_wordcount_job"
    ;;
esac
shift

if [ "$1" = "-job_name" ]
then
    JOB_NAME="$2"
fi
shift

check_submitted_parameter() {

    case "$1" in
        job_name)
            if [ -z "$JOB_NAME" ]
            then
                echo "Job name not specified"
                exit 1
            fi
        ;;
    esac
}

check_job_directory_existence() {

    check_submitted_parameter job_name

    if ! [ -d $HADOOP_LOG_DIRECTORY/$JOB_NAME ]
    then
        echo "Log file of \"PI\" job not found"
        exit 1
    fi
}

create_log_directory() {

    if ! [ -d $dir ]
    then
        mkdir $dir
        chmod -R 777 $dir
        touch $log
    fi
}

run_pi_job() {

    create_log_directory

    echo -e "****************************** NETSTAT ***************************\n" >> $log

    echo -e "`sudo netstat -plten | grep java` \n\n\n" >> $log

    hadoop_version=""
    if [ "$PLUGIN_NAME" = "vanilla" ]
    then
        hadoop_version=-$HADOOP_VERSION
    fi

    echo -e "************************ START OF \"PI\" JOB *********************\n" >> $log

    echo -e "`sudo -u $HADOOP_USER bash -c \"cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples$hadoop_version.jar pi $[$NODE_COUNT*10] $[$NODE_COUNT*1000]\"` \n" >> $log

    echo -e "************************ END OF \"PI\" JOB ***********************" >> $log
}

get_pi_job_name() {

    #This sleep needs here for obtaining correct job name. Not always job name may immediately appear in job list.
    sleep 60

    job_name=`hadoop job -list all | tail -n1 | awk '{print $1}'`

    if [ $job_name = "JobId" ]
    then
        echo "\"PI\" job name has not been obtained since \"PI\" job was not launched" >> $log
        exit 1
    fi

    echo "$job_name"
}

check_return_code_after_command_execution() {

    if [ "$1" = "-exit" ]
    then
        if [ "$2" -ne 0 ]
        then
            exit 1
        fi
    fi

    if [ "$1" = "-clean_hdfs" ]
    then
        if [ "$2" -ne 0 ]
        then
            sudo -u $HADOOP_USER bash -c "hadoop dfs -rmr /map-reduce-test" && exit 1
        fi
    fi
}

run_wordcount_job() {

    create_log_directory

    dmesg > $dir/input

    sudo -u $HADOOP_USER bash -c "hadoop dfs -ls /"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -c "hadoop dfs -mkdir /map-reduce-test"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -c "hadoop dfs -copyFromLocal $dir/input /map-reduce-test/mydata"
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    hadoop_version=""
    if [ "$PLUGIN_NAME" = "vanilla" ]
    then
        hadoop_version=-$HADOOP_VERSION
    fi

    sudo -u $HADOOP_USER bash -c "cd $HADOOP_DIRECTORY && hadoop jar hadoop-examples$hadoop_version.jar wordcount /map-reduce-test/mydata /map-reduce-test/output"
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo -u $HADOOP_USER bash -c "hadoop dfs -copyToLocal /map-reduce-test/output/ $dir/output/"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -c "hadoop dfs -rmr /map-reduce-test"
    check_return_code_after_command_execution -exit `echo "$?"`
}

$FUNC
