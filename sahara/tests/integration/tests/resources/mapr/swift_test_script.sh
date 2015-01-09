#!/bin/bash -x

OS_TENANT_NAME=""
OS_USERNAME=""
OS_PASSWORD=""

HADOOP_USER=""

SWIFT_CONTAINER_NAME=""

SWIFT_PARAMS="-D fs.swift.service.sahara.username=$OS_USERNAME"
SWIFT_PARAMS+=" -D fs.swift.service.sahara.tenant=$OS_TENANT_NAME"
SWIFT_PARAMS+=" -D fs.swift.service.sahara.password=$OS_PASSWORD"


compare_files() {
    a=`md5sum $1 | awk {'print \$1'}`
    b=`md5sum $2 | awk {'print \$1'}`

    if [ "$a" = "$b" ]; then
        echo "md5-sums of files $1 and $2 are equal"
    else
        echo -e "\nUpload file to Swift: $1 \n"
        echo -e "Download file from Swift: $2 \n"
        echo -e "md5-sums of files $1 and $2 are not equal \n"
        echo "$1 != $2"; cleanup;  exit 1
    fi
}

clean_local() {
    sudo rm -rf /tmp/test-file /tmp/swift-test-file
}

clean_mapr_fs() {
    sudo -u $HADOOP_USER bash -lc "hadoop fs -rmr /swift-test"
}

cleanup() {
    clean_local; clean_mapr_fs
}

check_return_code_after_command_execution() {
    if [ "$1" -ne 0 ]; then
        cleanup; exit 1;
    fi
}

check_swift_availability() {
    dd if=/dev/urandom of=/tmp/test-file bs=1048576 count=1

    sudo -u $HADOOP_USER bash -lc "hadoop fs -mkdir /swift-test"
    check_return_code_after_command_execution `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -copyFromLocal /tmp/test-file /swift-test/test-file"
    check_return_code_after_command_execution `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs $SWIFT_PARAMS -cp /swift-test/test-file swift://$SWIFT_CONTAINER_NAME.sahara/test-file"
    check_return_code_after_command_execution `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs $SWIFT_PARAMS -cp swift://$SWIFT_CONTAINER_NAME.sahara/test-file /swift-test/swift-test-file"
    check_return_code_after_command_execution `echo "$?"`

    sudo -u $HADOOP_USER bash -lc "hadoop fs -copyToLocal /swift-test/swift-test-file /tmp/swift-test-file"
    check_return_code_after_command_execution `echo "$?"`

    compare_files /tmp/test-file /tmp/swift-test-file; cleanup
}

check_swift_availability
