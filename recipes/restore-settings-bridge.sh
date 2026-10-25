#!/bin/sh
# Restore light-shell registry flags with that phase's generated restore.sh first.
set -eu
test "$(id -u)" = 0
name=${1:?Settings-bridge snapshot name required}
case "$name" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
K=${UNTIZEN_SETTINGS_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$K" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid settings container' >&2; exit 1;; esac
C=${UNTIZEN_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$C" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid launcher container' >&2; exit 1;; esac
Q=/opt/usr/apps/$K
test -s "$D/QuickLaunch-before.dll"
test -s "$D/.app-context.db"
sha256sum -c "$D/installed-bridge.sha256"
for database in /opt/dbspace/.app-context.db "$D/.app-context.db"; do
    test "$(sqlite3 -readonly "$database" "SELECT count(*) FROM key_filter WHERE appid='$K' AND key='XF86More';")" = 1
    test "$(sqlite3 -readonly "$database" "SELECT count(*) FROM key_filter WHERE appid='org.tizen.menu' AND key='XF86SysMenu';")" = 1
done
sqlite3 -bail /opt/dbspace/.app-context.db <<SQL
ATTACH '$D/.app-context.db' AS before;
BEGIN IMMEDIATE;
CREATE TEMP TABLE guard(ok INTEGER CHECK(ok=1));
INSERT INTO guard SELECT count(*)=2 FROM key_filter live JOIN before.key_filter old ON live.appid=old.appid AND live.key=old.key
WHERE ((live.appid='$K' AND live.key='XF86More') OR (live.appid='org.tizen.menu' AND live.key='XF86SysMenu'))
AND live.target_selector='package:$C'
AND live.args='quiet_page:settings __K_SPLASH_SCREEN:LA_UI_VR_TRANSPARENT';
UPDATE key_filter SET target_selector=(SELECT old.target_selector FROM before.key_filter old WHERE old.appid=key_filter.appid AND old.key=key_filter.key),
args=(SELECT old.args FROM before.key_filter old WHERE old.appid=key_filter.appid AND old.key=key_filter.key)
WHERE (appid='$K' AND key='XF86More') OR (appid='org.tizen.menu' AND key='XF86SysMenu');
DROP TABLE guard;
COMMIT;
SQL
app_launcher -u 5001 -k "$K" || true
cp -a "$D/QuickLaunch-before.dll" "$Q/bin/QuickLaunch.dll"
chsmack -a User::Pkg::$K::RO "$Q/bin/QuickLaunch.dll"
if [ -d "$D/quicklaunch-native-image" ]; then
    test ! -e "$Q/bin/.native_image"
    cp -a "$D/quicklaunch-native-image" "$Q/bin/.native_image"
fi
vconftool set -f -t int memory/appfw/app_context_db_change 1
echo 'Original settings routing and QuickLaunch restored. Restart after all restoration steps finish.'
