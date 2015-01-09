#!/bin/bash

disk_list_file=/tmp/disk.list

if [ -f ${disk_list_file} ]; then
    rm -f ${disk_list_file}
fi

for path in $*; do
    device=`findmnt ${path} -cno SOURCE`
    umount -f ${device}
    echo ${device} >> ${disk_list_file}
done
