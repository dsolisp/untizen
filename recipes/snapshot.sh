#!/bin/sh
# Run via tools/tv.py exec --script recipes/snapshot.sh --arg UNIQUE_PHASE_NAME
set -eu
test "$(id -u)" = 0
name=${1:?Give this snapshot a unique phase name}
case "$name" in ''|*[!A-Za-z0-9_-]*) echo 'Invalid snapshot name' >&2; exit 1;; esac
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
umask 077
test ! -e "$D" || { echo 'Snapshot already exists; never overwrite the original.' >&2; exit 1; }
mkdir -p "$D"
for name in .pkgmgr_parser .app-context .webappservice; do
    test -f "/opt/dbspace/$name.db"
    sqlite3 -readonly "/opt/dbspace/$name.db" ".backup '$D/$name.db'"
    test "$(sqlite3 -readonly "$D/$name.db" 'PRAGMA quick_check;')" = ok
done
for key in db/appfw/home_appid db/appfw/startup_appid \
    db/was/preload_by_country db/menu/autorun_tv_plus \
    db/menu/voice/voice_activated db/menu/voice/wakeupless_status \
    db/si_service/voice_recog_enable db/multi-assistant/prelaunch_mode; do
    printf '%s\n' "$key"
    vconftool get "$key"
done > "$D/preferences-before.txt"
echo "Consistent snapshots: $D"
echo 'Record the main-operation home app with Probe.dll before changing launcher routing.'
