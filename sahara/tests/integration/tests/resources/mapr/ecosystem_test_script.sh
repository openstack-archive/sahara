#!/bin/bash -x

dir=/tmp/MapReduceTestOutput
log=$dir/log.txt

HADOOP_EXAMPLES_JAR_PATH=""
HADOOP_LOG_DIRECTORY=""
HADOOP_USER=""

NODE_COUNT=""

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

if [ "$1" = "-job_name" ]; then
    JOB_NAME="$2"
fi
shift

check_submitted_parameter() {

    case "$1" in
        job_name)
            if [ -z "$JOB_NAME" ]; then
                echo "Job name not specified"
                exit 1
            fi
        ;;
    esac
}

check_job_directory_existence() {

    check_submitted_parameter job_name

    app_name=${JOB_NAME/"job"/"application"}
    if ! [ -d $HADOOP_LOG_DIRECTORY/$JOB_NAME -o -d $HADOOP_LOG_DIRECTORY/$app_name ]; then
        echo "Log file of \"PI\" job not found"
        exit 1
    fi
}

create_log_directory() {

    if ! [ -d $dir ]; then
        mkdir $dir
        chmod -R 777 $dir
        touch $log
    fi
}

run_pi_job() {

    create_log_directory

    echo -e "****************************** NETSTAT ***************************\n" >> $log

    echo -e "`sudo netstat -plten | grep java` \n\n\n" >> $log

    echo -e "************************ START OF \"PI\" JOB *********************\n" >> $log

    sudo -u $HADOOP_USER bash -lc "hadoop jar $HADOOP_EXAMPLES_JAR_PATH pi $(($NODE_COUNT*10)) $(($NODE_COUNT*1000))" >> $log

    echo -e "************************ END OF \"PI\" JOB ***********************" >> $log
}

get_pi_job_name() {

    #This sleep needs here for obtaining correct job name. Not always job name may immediately appear in job list.
    sleep 60

    job_name=`sudo -u $HADOOP_USER bash -lc "hadoop job -list all | grep '^[[:space:]]*job_' | sort | tail -n1" | awk '{print $1}'`

    if [ $job_name = "JobId" ]; then
        echo "\"PI\" job name has not been obtained since \"PI\" job was not launched" >> $log
        exit 1
    fi

    echo "$job_name"
}

check_return_code_after_command_execution() {

    if [ "$1" = "-exit" ]; then
        if [ "$2" -ne 0 ]; then
            exit 1
        fi
    fi

    if [ "$1" = "-clean_hdfs" ]; then
        if [ "$2" -ne 0 ]; then
            sudo -u $HADOOP_USER bash -lc "hadoop fs -rmr /map-reduce-test" && exit 1
        fi
    fi
}

run_wordcount_job() {

    create_log_directory

    dmesg > $dir/input

    sudo -u $HADOOP_USER bash -lc "hadoop fs -ls /"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -mkdir /map-reduce-test"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -copyFromLocal $dir/input /map-reduce-test/mydata"
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop jar $HADOOP_EXAMPLES_JAR_PATH wordcount /map-reduce-test/mydata /map-reduce-test/output"
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -copyToLocal /map-reduce-test/output $dir/output"
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -rmr /map-reduce-test"
    check_return_code_after_command_execution -exit `echo "$?"`
}
$FUNC
