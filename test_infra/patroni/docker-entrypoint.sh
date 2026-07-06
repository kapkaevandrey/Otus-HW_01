#!/bin/bash
set -e

chown -R postgres:postgres /var/lib/postgresql
chmod 700 /var/lib/postgresql

if [ -d /var/lib/postgresql/data ]; then
    chmod 700 /var/lib/postgresql/data
fi

exec gosu postgres patroni /etc/patroni.yml
