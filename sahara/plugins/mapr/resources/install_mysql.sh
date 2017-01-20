#!/bin/bash

if [ ! -f /etc/init.d/mysql* ]; then
    if [[ $1 == *"Ubuntu"* ]]; then
        sudo debconf-set-selections <<< \
                        'mysql-server mysql-server/root_password password root'
        sudo debconf-set-selections <<< \
                'mysql-server mysql-server/root_password_again password root'
        sudo apt-get install --force-yes -y mysql-server
        sudo apt-get install --force-yes -y libmysqlclient16
        mysql -uroot -proot mysql -e "UPDATE user SET Password=PASSWORD('') \
                                        WHERE User='root'; FLUSH PRIVILEGES;"
        sudo sed -i "s/^\(bind-address\s*=\s*\).*\$/\10.0.0.0/" \
                                                        /etc/mysql/my.cnf
        sudo service mysql restart
    elif [[ $1 == *"CentOS"* ]] || \
        [[ $1 == "RedHatEnterpriseServer" ]]; then
            if [[ $2 == "7" ]]; then
                sudo yum install -y mariadb-server
            else
                sudo yum install -y mysql-server
            fi
    elif [[ $1 == *"SUSE"* ]]; then
        sudo zypper mysql-server
    else
        echo "Unknown distribution"
        exit 1
    fi
else
    echo "Mysql server already installed"
fi
