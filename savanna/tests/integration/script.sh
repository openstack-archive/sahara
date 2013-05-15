#!/bin/bash
#cd / && touch script.sh && chmod +x script.sh && vim script.sh
dir=/outputTestMapReduce
directory=/usr/share/hadoop
rm -r $dir
mkdir $dir
log=$dir/log.txt
echo `dmesg > $dir/input` 2>>$log
touch $log
chmod -R 777 $dir
echo "[------ dpkg------]">>$log
echo `dpkg --get-selections | grep hadoop` >>$log
echo "[------jps------]">>$log
echo `jps | grep -v Jps` >>$log
echo "[------netstat------]">>$log
echo `sudo netstat -plten | grep java` &>>$log
echo "[------test for hdfs------]">>$log
echo `dmesg > $dir/input` 2>>$log
su -c "hadoop dfs -ls /" hadoop
su -c "hadoop dfs -mkdir /test" hadoop &&
su -c "hadoop dfs -copyFromLocal $dir/input /test/mydata" hadoop 2>>$log &&
echo "[------start job------]">>$log &&
su -c "cd $directory && hadoop jar hadoop-examples-1.1.1.jar wordcount /test/mydata /test/output" hadoop 2>>$log &&
su -c "hadoop dfs -copyToLocal /test/output/ $dir/out/" hadoop 2>>$log &&
su -c "hadoop dfs -rmr /test" hadoop 2>>$log