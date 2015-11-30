#!/bin/bash

#Current available version
DEF_VERSION="2.11.5"

VERSION=$(wget -qO- http://www.scala-lang.org |\
    grep 'scala-version' | grep -Eo '([0-9]\.?)+')

if [ $? != 0 -o -z ${VERSION} ]; then
    VERSION=${DEF_VERSION}
fi

PKG=scala-${VERSION}

URL="http://downloads.typesafe.com/scala/${VERSION}"

if [ "$1" = "Ubuntu" ]; then
    wget -N ${URL}/${PKG}.deb
    dpkg -i ${PKG}.deb
    rm ${PKG}.deb
    # install java if missing
    apt-get install -f -y --force-yes
elif [ "$1" = 'CentOS' -o "$1" = 'RedHatEnterpriseServer' ]; then
    rpm -Uhv ${URL}/${PKG}.rpm
else
    echo "Unknown distribution"
    exit 1
fi
