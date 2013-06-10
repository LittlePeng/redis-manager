#!/bin/bash
tar -zxf manager.tar.gz

mkdir -p /usr/local/redis-manager
\cp -rf manager/* /usr/local/redis-manager
\cp -rf redis-manager /etc/init.d/
chmod 755 /etc/init.d/redis-manager

chkconfig --add redis-manager
service redis-manager start
