#!/bin/sh
# Run only after Quiet Home and its quick settings work. Pass a NEW snapshot name.
set -eu
test "$(id -u)" = 0
name=${1:?Snapshot name required}
case "$name" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
K=${UNTIZEN_SETTINGS_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$K" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid settings container' >&2; exit 1;; esac
C=${UNTIZEN_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$C" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid launcher container' >&2; exit 1;; esac
Q=/opt/usr/apps/$K
S=${UNTIZEN_STAGE:-/home/owner/share/tmp/sdk_tools/untizen}/unpacked
test -s "$D/.app-context.db"
test -s "$S/QuickLaunch.dll"
test -s "$Q/bin/QuickLaunch.dll"
test "$(stat -c %u:%g "$Q/bin/QuickLaunch.dll")" = 201:0
test ! -e "$D/QuickLaunch-before.dll"
# Inspect semantic identities, not row numbers from another TV.
test "$(sqlite3 -readonly /opt/dbspace/.app-context.db "SELECT count(*) FROM key_filter WHERE appid='$K' AND key='XF86More';")" = 1
test "$(sqlite3 -readonly /opt/dbspace/.app-context.db "SELECT count(*) FROM key_filter WHERE appid='org.tizen.menu' AND key='XF86SysMenu';")" = 1
cp -a "$Q/bin/QuickLaunch.dll" "$D/QuickLaunch-before.dll"
app_launcher -u 5001 -k "$K" || true
if [ -d "$Q/bin/.native_image" ]; then mv "$Q/bin/.native_image" "$D/quicklaunch-native-image"; fi
cp "$S/QuickLaunch.dll" "$Q/bin/QuickLaunch.dll"
chown 201:0 "$Q/bin/QuickLaunch.dll"
chmod 644 "$Q/bin/QuickLaunch.dll"
chsmack -a User::Pkg::$K::RO "$Q/bin/QuickLaunch.dll"
sha256sum "$Q/bin/QuickLaunch.dll" > "$D/installed-bridge.sha256"
sqlite3 -bail /opt/dbspace/.app-context.db <<SQL
ATTACH '$D/.app-context.db' AS before;
BEGIN IMMEDIATE;
CREATE TEMP TABLE guard(ok INTEGER CHECK(ok=1));
INSERT INTO guard SELECT count(*)=2 FROM key_filter live JOIN before.key_filter old ON live.appid=old.appid AND live.key=old.key
WHERE ((live.appid='$K' AND live.key='XF86More') OR (live.appid='org.tizen.menu' AND live.key='XF86SysMenu'))
AND live.target_selector IS old.target_selector AND live.args IS old.args;
UPDATE key_filter SET target_selector='package:$C',args='quiet_page:settings __K_SPLASH_SCREEN:LA_UI_VR_TRANSPARENT'
WHERE (appid='$K' AND key='XF86More') OR (appid='org.tizen.menu' AND key='XF86SysMenu');
DROP TABLE guard;
COMMIT;
SQL
vconftool set -f -t int memory/appfw/app_context_db_change 1
echo 'QuickLaunch and Settings-key routing changed. Test both buttons before disabling the sidebar/browser.'
