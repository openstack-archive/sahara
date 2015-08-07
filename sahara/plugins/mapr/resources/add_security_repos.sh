#!/bin/sh

cat >> /etc/apt/sources.list.d/security_repo.list << EOF
deb http://security.ubuntu.com/ubuntu precise-security main
deb http://security.ubuntu.com/ubuntu lucid-security main
EOF
