#!/bin/bash
MAPR_HOME=/opt/mapr

while [ $# -gt 0 ] ; do
    nodeArg=$1
    exec< ${MAPR_HOME}/topology.data
    result=""
    while read line ; do
        ar=( $line )
        if [ "${ar[0]}" = "$nodeArg" ]; then
            result="${ar[1]}"
        fi
    done
    shift
    if [ -z "$result" ]; then
        echo -n "/default/rack "
    else
        echo -n "$result "
    fi
done
