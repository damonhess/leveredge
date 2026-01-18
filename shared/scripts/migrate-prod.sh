#!/bin/bash
# Migrate PROD database
# Usage: migrate-prod [up|down|version|force N]
#
# WARNING: This affects production data. Always backup first!

PROD_PW=$(grep "POSTGRES_PASSWORD_URLENCODED" /opt/leveredge/data-plane/prod/supabase/.env | cut -d= -f2)

export PATH=$HOME/bin:$PATH

migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:${PROD_PW}@localhost:54322/postgres?sslmode=disable" \
    "$@"
