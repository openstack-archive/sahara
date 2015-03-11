#!/bin/bash -x

set -e

log=/tmp/impala-test-log.txt

case $1 in
    query)
        FUNC="check_query"
    ;;
esac
shift

if [ "$1" = "-ip" ]; then
    IP="$2"
else
    echo -e "-ip is missing \n" >> $log
    exit 1
fi

check_query() {
    if (impala-shell -i $IP:21000 -q "SELECT 2 > 1" --quiet|grep 'true'); then
        echo -e "Impala Query Successful \n" >> $log
        exit 0
    else
        echo -e "Impala Query Fail \n" >> $log
        exit 1
    fi
}

$FUNC
