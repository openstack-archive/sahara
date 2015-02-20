#!/bin/bash -x

set -e
log=/tmp/config-sentry-test-log.txt

check_sentry(){
    conffile_dir=$(sudo find / -name "*-sentry-SENTRY_SERVER" | head -1)
    if [ -z $conffile_dir ]; then
        echo "Sentry configuration file directory not found" >> $log
        exit 1
    else
        conffile=$conffile_dir"/sentry-site.xml"
    fi

    conffile_tmp=/tmp/sentry-site.xml
    sudo cp $conffile $conffile_tmp
    sudo chmod 664 $conffile_tmp

    psql_jar=$(ls /usr/share/cmf/lib/postgresql* | head -1)
    export HADOOP_CLASSPATH=:$psql_jar
    sentry --command schema-tool -conffile $conffile_tmp -dbType postgres -info &>> $log
}

check_sentry
