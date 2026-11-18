#!/bin/sh
# Install only. Home/startup routing is changed AFTER manual launch is verified.
# Input: snapshot name. Stage with `tv push .local/package.tar.gz package.tar.gz`;
# it resolves this recipe's stage folder. A raw `sdb push` with a relative name
# lands somewhere else and the recipe applies the tarball another run left behind.
set -eu
test "$(id -u)" = 0
name=${1:?Snapshot name required}
case "$name" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
D=${UNTIZEN_BACKUP_DIR:-/opt/usr/share/untizen-backups}/$name
C=${UNTIZEN_CONTAINER:?Run this through tools/tv.py exec --script so the profile supplies it}
case "$C" in ''|*[!A-Za-z0-9_.-]*) echo 'Invalid launcher container' >&2; exit 1;; esac
A=/opt/usr/apps/$C
S=${UNTIZEN_STAGE:-/home/owner/share/tmp/sdk_tools/untizen}
test -s "$D/.pkgmgr_parser.db"
test -s "$S/package.tar.gz"
echo "Staged: $(md5sum "$S/package.tar.gz" | cut -c1-12) $(ls -l "$S/package.tar.gz" | awk '{print $5"B", $6, $7, $8}')"
test -s "$A/bin/BixbyPromotion.dll"
test "$(stat -c %u:%g "$A/bin/BixbyPromotion.dll")" = 201:0
test ! -e "$D/container-original"
test ! -e "$A/res/quiet-home" # First install only; do not silently overwrite an existing custom launcher.
# "unpacked" is scratch: clear our own extraction from an earlier run, but keep
# refusing a directory that does not look like the package we staged.
if [ -e "$S/unpacked" ]; then
if [ -z "$(ls -A "$S/unpacked" 2>/dev/null)" ] || [ -f "$S/unpacked/Probe.dll" ]; then rm -rf "$S/unpacked";
else echo "$S/unpacked is not our extraction; inspect it before installing." >&2; exit 1; fi
fi
# The archive is generated from our local build, not downloaded from an unknown party.
mkdir "$S/unpacked"
tar -xzf "$S/package.tar.gz" -C "$S/unpacked"
test -s "$S/unpacked/BixbyPromotion.dll"
test -s "$S/unpacked/Probe.dll"
test -s "$S/unpacked/quiet-home/apps.json"
cp -a "$A" "$D/container-original"
cp "$S/unpacked/Probe.dll" "$D/Probe.dll"
/usr/bin/dotnet "$D/Probe.dll" > "$D/operation-and-sources-before.txt"
app_launcher -u 5001 -k "$C" || true
if [ -d "$A/bin/.native_image" ]; then mv "$A/bin/.native_image" "$D/home-native-image"; fi
cp "$S/unpacked/BixbyPromotion.dll" "$A/bin/BixbyPromotion.dll"
cp -R "$S/unpacked/quiet-home" "$A/res/"
chown 201:0 "$A/bin/BixbyPromotion.dll"
chmod 644 "$A/bin/BixbyPromotion.dll"
chsmack -a User::Pkg::$C::RO "$A/bin/BixbyPromotion.dll"
sha256sum "$A/bin/BixbyPromotion.dll" > "$D/installed-home.sha256"
find "$A/res/quiet-home" -type d -exec chmod 755 {} \;
find "$A/res/quiet-home" -type f -exec chmod 644 {} \;
find "$A/res/quiet-home" -exec chown 201:0 {} \;
find "$A/res/quiet-home" -exec chsmack -a User::Pkg::$C::RO {} \;
sqlite3 -bail "${UNTIZEN_REGISTRY:-/opt/dbspace/.pkgmgr_parser.db}" <<SQL
BEGIN IMMEDIATE;
CREATE TEMP TABLE guard(ok INTEGER CHECK(ok=1));
INSERT INTO guard SELECT count(*)=1 FROM package_app_info WHERE app_id='$C';
UPDATE package_app_info SET app_disable='false',app_onboot='false',app_autorestart='false' WHERE app_id='$C';
DROP TABLE guard;
COMMIT;
SQL
app_launcher -u 5001 -s "$C"
rm -rf "$S/unpacked" # Scratch only; the staged package stays for a rollback.
echo 'Installed and launch requested. Verify the visible UI, remote, sound, apps and HDMI before changing Home routing.'
echo "Original package and operation/source record: $D"
