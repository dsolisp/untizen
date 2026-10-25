#!/bin/sh
# Unit + marker MUST be a reviewed pair from the profile.
# apply|restore UNIT MARKER SNAPSHOT_NAME
set -eu
test "$(id -u)" = 0
action=${1:?}; unit=${2:?}; marker=${3:?}; name=${4:?}
case "$unit" in ''|*[!A-Za-z0-9_.-]*) exit 1;; esac
case "$marker" in ''|*[!A-Za-z0-9_.-]*) exit 1;; esac
case "$name" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
case "$action" in apply|restore) ;; *) exit 1;; esac
path=/opt/usr/share/systemd/system/$marker
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
test -s "$D/.pkgmgr_parser.db" # Require the corresponding fresh snapshot first.
test ! -L "$path"
test ! -e "$path" || test -f "$path"
# A similarly named file is NOT sufficient. This exact negated condition is required.
systemctl cat "$unit" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -Fqx "ConditionPathExists=!$path"
saved=$D/marker-$marker
if [ "$action" = apply ]; then
    test ! -e "$saved" || { echo 'Already recorded; do not overwrite original state.' >&2; exit 1; }
    if [ -e "$path" ]; then printf 'present\n'; else printf 'absent\n'; fi > "$saved"
    systemctl is-active "$unit" > "$saved.active" || true
    touch "$path"
    systemctl stop "$unit"
else
    test -f "$saved"
    case "$(cat "$saved")" in
        absent) rm -f "$path";;
        present) test -f "$path";;
        *) echo 'Invalid marker backup' >&2; exit 1;;
    esac
    systemctl reset-failed "$unit" || true
    # Restore registry flags first. Restart only a service that was active.
    if [ "$(cat "$saved.active")" = active ]; then systemctl start "$unit"; fi
fi
systemctl show -p Id -p ActiveState -p ConditionResult "$unit"
