#!/bin/sh

while True; do
    if [ -f '/tmp/launching-mapr-mfs.lck' ]; then
        sleep 5
    else
        break
    fi
done
