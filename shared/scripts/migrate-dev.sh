#!/bin/bash
# Migrate DEV database
# Usage: migrate-dev [up|down|version|force N]

DEV_PW=$(grep "POSTGRES_PASSWORD_URLENCODED" /opt/leveredge/data-plane/dev/supabase/.env | cut -d= -f2)

export PATH=$HOME/bin:$PATH

migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:${DEV_PW}@localhost:54323/postgres?sslmode=disable" \
    "$@"
