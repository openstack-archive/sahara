#!/bin/bash -x

OS_TENANT_NAME=""
OS_USERNAME=""
OS_PASSWORD=""

HADOOP_USER=""

SWIFT_CONTAINER_NAME=""

compare_files() {

    a=`md5sum $1 | awk {'print \$1'}`
    b=`md5sum $2 | awk {'print \$1'}`

    if [ "$a" = "$b" ]
    then
        echo "md5-sums of files $1 and $2 are equal"
    else
        echo -e "\nUpload file to Swift: $1 \n"
        echo -e "Download file from Swift: $2 \n"
        echo -e "md5-sums of files $1 and $2 are not equal \n"
        echo "$1 != $2" && exit 1
    fi
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
            sudo su -c "hadoop dfs -rmr /swift-test" $HADOOP_USER && exit 1
        fi
    fi
}

check_swift_availability() {

    dd if=/dev/urandom of=/tmp/test-file bs=1048576 count=1

    sudo su -c "hadoop dfs -mkdir /swift-test/" $HADOOP_USER
    check_return_code_after_command_execution -exit `echo "$?"`

    sudo su -c "hadoop dfs -copyFromLocal /tmp/test-file /swift-test/" $HADOOP_USER
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo su -c "hadoop distcp -D fs.swift.service.savanna.username=$OS_USERNAME -D fs.swift.service.savanna.tenant=$OS_TENANT_NAME -D fs.swift.service.savanna.password=$OS_PASSWORD /swift-test/test-file swift://$SWIFT_CONTAINER_NAME.savanna/" $HADOOP_USER
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo su -c "hadoop distcp -D fs.swift.service.savanna.username=$OS_USERNAME -D fs.swift.service.savanna.tenant=$OS_TENANT_NAME -D fs.swift.service.savanna.password=$OS_PASSWORD swift://$SWIFT_CONTAINER_NAME.savanna/test-file /swift-test/swift-test-file" $HADOOP_USER
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo su -c "hadoop dfs -copyToLocal /swift-test/swift-test-file /tmp/swift-test-file" $HADOOP_USER
    check_return_code_after_command_execution -clean_hdfs `echo "$?"`

    sudo su -c "hadoop dfs -rmr /swift-test" $HADOOP_USER

    compare_files /tmp/test-file /tmp/swift-test-file

    sudo rm /tmp/test-file /tmp/swift-test-file
}

check_swift_availability
