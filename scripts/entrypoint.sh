#!/bin/bash
set -e

PGDATA=/var/lib/postgresql/data

# initialize data directory if empty
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    mkdir -p "$PGDATA"
    chown postgres:postgres "$PGDATA"
    su - postgres -c "initdb -D $PGDATA"
fi

su - postgres -c "pg_ctl -D $PGDATA -o '-c listen_addresses=*' -w start"

# ensure postgres is ready
until pg_isready -U postgres; do
    echo "Waiting for postgres..."
    sleep 1
done

# set password and create database
su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'banco@mep';\""

su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='BD_MEP'\" | grep -q 1 || createdb BD_MEP"

su - postgres -c "psql BD_MEP < /app/scripts/create_tables.sql"

exec python /app/MEVA/MEVA.py
