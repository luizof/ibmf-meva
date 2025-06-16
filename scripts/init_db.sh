#!/bin/bash

# Aguarda o banco de dados iniciar
while ! pg_isready -h db -p 5432 -U postgres; do
  echo "Aguardando o banco de dados..."
  sleep 2
done

# Executa os comandos para criar as tabelas
PGPASSWORD=banco@mep psql -h db -U postgres -d BD_MEP -f /app/scripts/create_tables.sql
