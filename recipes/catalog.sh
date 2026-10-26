#!/bin/sh
# Read-only installed-app dump for tools/tv.py catalog. Prints labeled sections;
# writes nothing under /opt and changes no registry flags, vconf keys or Home.
set -eu
test "$(id -u)" = 0
R="${UNTIZEN_REGISTRY:-/opt/dbspace/.pkgmgr_parser.db}"
printf '=== schema ===\n'
sqlite3 -readonly "$R" ".schema"
printf '=== apps ===\n'
sqlite3 -readonly "$R" "SELECT app_id FROM package_app_info ORDER BY app_id;"
