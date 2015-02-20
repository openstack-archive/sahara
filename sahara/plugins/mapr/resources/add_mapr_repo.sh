#!/bin/sh
if [ "$1" = "Ubuntu" ]; then
    cat >> /etc/apt/sources.list.d/maprtech.list << EOF
deb %(ubuntu_mapr_base_repo)s
deb %(ubuntu_mapr_ecosystem_repo)s
EOF
    cat >> /etc/apt/sources.list.d/security_repo.list << EOF
deb http://security.ubuntu.com/ubuntu precise-security main
deb http://security.ubuntu.com/ubuntu lucid-security main
EOF
    sudo apt-get install -y --force-yes wget
    wget -O - http://package.mapr.com/releases/pub/maprgpg.key | sudo apt-key add -
    sudo apt-get update

elif [ "$1" = 'CentOS' -o "$1" = 'RedHatEnterpriseServer' ]; then
    cat >> /etc/yum.repos.d/maprtech.repo << EOF
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
    release=`cat /etc/*-release`
    if [[ $release =~ 6\.[0-9] ]]; then
        cd /tmp
        wget http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
        rpm -Uvh epel-release-6*.rpm

    elif [[ $release =~ 7\.[0-9] ]]; then
        cd /tmp
        wget http://download.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
        rpm -Uvh epel-release-7*.rpm
    else
        echo "Unsupported distribution version"
        exit 1
    fi
    rpm -Uvh ftp://rpmfind.net/linux/centos/6.6/os/x86_64/Packages/libevent-1.4.13-4.el6.x86_64.rpm
else
    echo "Unknown distribution"
    exit 1
fi
