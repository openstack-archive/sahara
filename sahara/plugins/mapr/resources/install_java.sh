#!/bin/bash

set -e

JAVA_TARGET_LOCATION="/usr/java"

export JAVA_DOWNLOAD_URL=${JAVA_DOWNLOAD_URL:-"http://download.oracle.com/otn-pub/java/jdk/7u51-b13/jdk-7u51-linux-x64.tar.gz"}

JAVA_HOME=$TARGET_ROOT$JAVA_TARGET_LOCATION

mkdir -p $JAVA_HOME

JAVA_FILE=$(basename $JAVA_DOWNLOAD_URL)
wget --no-check-certificate --no-cookies -c \
    --header "Cookie: gpw_e24=http://www.oracle.com/; \
                        oraclelicense=accept-securebackup-cookie" \
    -O $JAVA_HOME/$JAVA_FILE $JAVA_DOWNLOAD_URL
if [ $? -eq 0 ]; then
    echo "Java download successful"
else
    echo "Error downloading $JAVA_DOWNLOAD_URL, exiting"
    exit 1
fi


cd $JAVA_HOME
if [[ $JAVA_FILE == *.tar.gz ]]; then
    echo -e "\n" | tar -zxf $JAVA_FILE
    JAVA_NAME=`ls -1 $JAVA_TARGET_LOCATION | grep -v tar.gz`
    chown -R root:root $JAVA_HOME
    cat >> /etc/profile.d/java.sh <<- EOF
    # Custom Java install
    export JAVA_HOME=$JAVA_TARGET_LOCATION/$JAVA_NAME
    export PATH=\$PATH:$JAVA_TARGET_LOCATION/$JAVA_NAME/bin
EOF
    case "$1" in
        Ubuntu )
            update-alternatives --install "/usr/bin/java" "java" \
                                "$JAVA_TARGET_LOCATION/$JAVA_NAME/bin/java" 1
            update-alternatives --install "/usr/bin/javac" "javac" \
                                "$JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javac" 1
            update-alternatives --install "/usr/bin/javaws" "javaws" \
                                "$JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javaws" 1

            update-alternatives --set java \
                                    $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/java
            update-alternatives --set javac \
                                    $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javac
            update-alternatives --set javaws \
                                    $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javaws
        ;;
        Fedora | RedHatEnterpriseServer | CentOS )
            alternatives --install /usr/bin/java java \
                            $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/java 200000
            alternatives --install /usr/bin/javaws javaws \
                            $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javaws 200000
            alternatives --install /usr/bin/javac javac \
                            $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/javac 200000
            alternatives --install /usr/bin/jar jar \
                            $JAVA_TARGET_LOCATION/$JAVA_NAME/bin/jar 200000
        ;;
    esac
elif [[ $JAVA_FILE == *.bin ]]; then
    echo -e "\n" | sh $JAVA_FILE
else
    echo "Unknown file type: $JAVA_FILE, exiting"
    exit 1
fi
rm $JAVA_FILE
