#!/bin/sh
if [ "$1" = "Ubuntu" ]; then
    sudo apt-get update
    cat >> /etc/apt/sources.list.d/maprtech.list <<- EOF
    deb %(ubuntu_mapr_base_repo)s
    deb %(ubuntu_mapr_ecosystem_repo)s
EOF
    sudo apt-get install -y --force-yes wget
    wget -O - http://package.mapr.com/releases/pub/maprgpg.key | \
                                                            sudo apt-key add -
    sudo apt-get update

elif [ "$1" = 'CentOS' -o "$1" = 'RedHatEnterpriseServer' ]; then
    cat >> /etc/yum.repos.d/maprtech.repo <<- EOF
[maprtech]
name=MapR Technologies
baseurl=%(centos_mapr_base_repo)s
enabled=1
gpgcheck=0
protect=1

[maprecosystem]
name=MapR Technologies
baseurl=%(centos_mapr_ecosystem_repo)s
enabled=1
gpgcheck=0
protect=1
EOF
    rpm --import http://package.mapr.com/releases/pub/maprgpg.key
    yum install -y wget
    if [ ! -e /etc/yum.repos.d/epel.repo ]; then
        rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
    fi
else
    echo "Unknown distribution"
    exit 1
fi
