#!/bin/bash -x

connect_server_list_jobs(){
exec sqoop2 << EOF
set server --host localhost --port 12000
show server --all
show job --all
exit
EOF
}

check_sqoop2(){
    res=`connect_server_list_jobs`
    if [ `echo $res | grep "localhost" | wc -l` -lt 1 ]; then
        echo "sqoop2 is not available"
        exit 1
    else
        if [ `echo $res | grep "job(s) to show" | wc -l` -lt 1 ]; then
            echo "sqoop2 is not available"
            exit 1
        else
            echo "sqoop2 is available"
                exit 0
        fi
    fi
}

check_sqoop2
