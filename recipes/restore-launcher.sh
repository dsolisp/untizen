#!/bin/sh
# SNAPSHOT_NAME ORIGINAL_MAIN_OPERATION_APP ORIGINAL_HOME_APP ORIGINAL_STARTUP_APP
# Read all three original IDs from that TV's saved records; do not guess them.
set -eu
test "$(id -u)" = 0
name=${1:?}; operation=${2:?}; home=${3:?}; startup=${4:?}
case "$name" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
for app in "$operation" "$home" "$startup"; do
    case "$app" in ''|*[!A-Za-z0-9_.-]*) exit 1;; esac
done
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
C=${UNTIZEN_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$C" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid launcher container' >&2; exit 1;; esac
A=/opt/usr/apps/$C
test -s "$D/Probe.dll"
test -s "$D/container-original/bin/BixbyPromotion.dll"
test -s "$D/.pkgmgr_parser.db"
sha256sum -c "$D/installed-home.sha256"
/usr/bin/dotnet "$D/Probe.dll" set-home "$operation"
vconftool set -f -t string db/appfw/home_appid "$home"
vconftool set -f -t string db/appfw/startup_appid "$startup"
app_launcher -u 5001 -k "$C" || true
cp -a "$D/container-original/bin/BixbyPromotion.dll" "$A/bin/BixbyPromotion.dll"
chsmack -a User::Pkg::$C::RO "$A/bin/BixbyPromotion.dll"
if [ -d "$D/home-native-image" ]; then
    test ! -e "$A/bin/.native_image"
    cp -a "$D/home-native-image" "$A/bin/.native_image"
fi
sqlite3 -bail "${UNTIZEN_REGISTRY:-/opt/dbspace/.pkgmgr_parser.db}" <<SQL
ATTACH '$D/.pkgmgr_parser.db' AS before;
BEGIN IMMEDIATE;
CREATE TEMP TABLE guard(ok INTEGER CHECK(ok=1));
INSERT INTO guard SELECT count(*)=1 FROM before.package_app_info WHERE app_id='$C';
INSERT INTO guard SELECT count(*)=1 FROM package_app_info WHERE app_id='$C';
UPDATE package_app_info SET
app_disable=(SELECT app_disable FROM before.package_app_info WHERE app_id='$C'),
app_onboot=(SELECT app_onboot FROM before.package_app_info WHERE app_id='$C'),
app_autorestart=(SELECT app_autorestart FROM before.package_app_info WHERE app_id='$C')
WHERE app_id='$C';
DROP TABLE guard;
COMMIT;
SQL
app_launcher -u 5001 -s "$home"
echo 'Original launcher routing and assembly restored. Extra Quiet Home resources remain inert for recovery.'
