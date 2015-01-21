#!/bin/bash -x

case $1 in
    create_data)
        FUNC="create_data"
    ;;
    check_get_data)
        FUNC="check_get_data"
    ;;
    check_delete_data)
        FUNC="check_delete_data"
    ;;
esac

create_data(){
exec hbase shell << EOF
disable 'scores'
drop 'scores'
create 'scores','grade','course'
put 'scores','Jack','grade','5'
put 'scores','Jack','course:math','90'
put 'scores','Jack','course:art','deleteme'
exit
EOF
}

get_data(){
exec hbase shell << EOF
get 'scores','Jack','course:art'
exit
EOF
}

delete_data(){
exec hbase shell << EOF
delete 'scores','Jack','course:art'
exit
EOF
}

check_get_data(){
    res=`get_data`
    if ! [[ `echo $res | grep "deleteme" | wc -l` -ge 1 ]]; then
        echo "Insert data failed"
        exit 1
    else
        echo "Insert data successful"
        exit 0
    fi
}

check_delete_data(){
    res1=`delete_data`
    res2=`get_data`
    if ! [[ `echo $res2 | grep "deleteme" | wc -l` -eq 0 ]]; then
        echo "Delete data failed"
        exit 1
    else
        echo "Delete data successful"
        exit 0
    fi
}

$FUNC
