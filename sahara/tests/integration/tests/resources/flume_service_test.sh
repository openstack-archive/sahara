#!/bin/bash -x

sudo flume-ng agent -n a1 -f flume.conf > flume.log 2>&1 &
sleep 5
sudo flume-ng avro-client -H localhost -p 44444 -F flume.data
sleep 5
cd /var/log/flume-ng
file=`ls -l|grep 1[0-9].*-1|grep 5|awk -F" " '{print $NF}'`
num=`cat $file | grep "hello world" | wc -l`

check_flume_availability(){
    echo $num
    if [ $num -lt 1 ]; then
        echo "Flume Agent is not available"
        exit 1
    else
        echo "Flume Agent is available"
    fi
}

check_flume_availability
