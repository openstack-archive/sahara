#!/bin/bash

if [[ $1 == *"Ubuntu"* ]]; then
    sudo apt-get install --force-yes -y mysql-client
elif [[ $1 == *"CentOS"* ]] || [[ $1 == *"Red Hat Enterprise Linux"* ]]; then
    sudo yum install -y mysql
elif [[ $1 == *"SUSE"* ]]; then
    sudo zypper install mysql-community-server-client
else
    echo "Unknown distribution"
    exit 1
fi
