#!/bin/bash
set -e

# initialize data directory if empty
if [ ! -s /var/lib/postgresql/13/main/PG_VERSION ]; then
    su postgres -c "/usr/lib/postgresql/13/bin/initdb -D /var/lib/postgresql/13/main"
fi

service postgresql start

# ensure postgres is ready
until pg_isready -U postgres; do
    echo "Waiting for postgres..."
    sleep 1
done

# set password and create database
su postgres -c "psql -c \"ALTER USER postgres PASSWORD 'banco@mep';\""

su postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='BD_MEP'\" | grep -q 1 || createdb BD_MEP"

su postgres -c "psql BD_MEP < /app/scripts/create_tables.sql"

exec python /app/MEVA/MEVA.py
