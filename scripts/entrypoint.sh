#!/bin/bash
set -e

# ensure postgres binaries are on PATH
PG_BIN_DIR=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -n 1)
if [ -n "$PG_BIN_DIR" ]; then
    POSTGRES_PATH="$PG_BIN_DIR:$PATH"
else
    POSTGRES_PATH="$PATH"
fi

PGDATA=/var/lib/postgresql/data

# initialize data directory if empty
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    mkdir -p "$PGDATA"
    chown postgres:postgres "$PGDATA"

    su - postgres -c "PATH=$POSTGRES_PATH initdb -D $PGDATA"
fi

su - postgres -c "PATH=$POSTGRES_PATH pg_ctl -D $PGDATA -o '-c listen_addresses=*' -w start"


# ensure postgres is ready
until pg_isready -U postgres; do
    echo "Waiting for postgres..."
    sleep 1
done

# set password and create database

su - postgres -c "PATH=$POSTGRES_PATH psql -c \"ALTER USER postgres PASSWORD 'banco@mep';\""

su - postgres -c "PATH=$POSTGRES_PATH psql -tc \"SELECT 1 FROM pg_database WHERE datname='BD_MEP'\" | grep -q 1 || createdb BD_MEP"

su - postgres -c "PATH=$POSTGRES_PATH psql BD_MEP < /app/scripts/create_tables.sql"


exec python /app/MEVA/MEVA.py
