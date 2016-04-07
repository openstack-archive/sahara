#!/bin/sh
useradd -p `openssl passwd -1 $2` $1
