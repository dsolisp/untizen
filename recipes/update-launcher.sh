#!/bin/sh
# Update an installed UnTizen launcher: replace the assembly and refresh
# res/quiet-home from the staged package, keeping a rollback of both.
# install-launcher.sh owns first installs (it refuses to touch res/quiet-home);
# this recipe owns every later change. Input: snapshot name.
# Stage with `tv push .local/package.tar.gz package.tar.gz`, which puts the file in
# this recipe's stage folder. A raw `sdb push <local> package.tar.gz` lands in sdb's
# own working directory instead, so the OLD tarball stays here and the update
# "succeeds" with yesterday's resources. Raw sdb needs the absolute destination:
#   sdb push .local/package.tar.gz /home/owner/share/tmp/sdk_tools/untizen/package.tar.gz
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
# Name and size alone do not prove the stage is the build we just made, so the
# recipe prints the digest it is about to apply; compare it with the local tarball.
echo "Staged: $(md5sum "$S/package.tar.gz" | cut -c1-12) $(ls -l "$S/package.tar.gz" | awk '{print $5"B", $6, $7, $8}')"
test -d "$A/res/quiet-home" # Update only; a first install uses install-launcher.sh.
test "$(stat -c %u:%g "$A/bin/BixbyPromotion.dll")" = 201:0
# "unpacked" is this recipe's scratch directory. A leftover from an earlier run
# used to stop the whole update at a bare guard with no output at all, so clear
# our own extraction and still refuse a directory we cannot account for.
if [ -e "$S/unpacked" ]; then
if [ -z "$(ls -A "$S/unpacked" 2>/dev/null)" ] || [ -f "$S/unpacked/Probe.dll" ]; then rm -rf "$S/unpacked";
else echo "$S/unpacked is not our extraction; inspect it before updating." >&2; exit 1; fi
fi
# The archive is generated from our local build, not downloaded from an unknown party.
mkdir "$S/unpacked"
tar -xzf "$S/package.tar.gz" -C "$S/unpacked"
test -s "$S/unpacked/BixbyPromotion.dll"
test -s "$S/unpacked/Probe.dll"
test -s "$S/unpacked/quiet-home/apps.json"
# Keep the running build so a bad update reverts without touching the snapshot.
mkdir -p "$D/update-previous"
cp -a "$A/bin/BixbyPromotion.dll" "$D/update-previous/BixbyPromotion.dll"
cp -a "$A/res/quiet-home" "$D/update-previous/quiet-home"
/usr/bin/dotnet "$S/unpacked/Probe.dll" > "$D/operation-and-sources-before.txt" 2>&1 || true
app_launcher -u 5001 -k "$C" || true
if [ -d "$A/bin/.native_image" ]; then mv "$A/bin/.native_image" "$D/update-native-image"; fi
cp "$S/unpacked/BixbyPromotion.dll" "$A/bin/BixbyPromotion.dll"
rm -rf "$A/res/quiet-home"
cp -R "$S/unpacked/quiet-home" "$A/res/"
chown 201:0 "$A/bin/BixbyPromotion.dll"
chmod 644 "$A/bin/BixbyPromotion.dll"
chsmack -a User::Pkg::$C::RO "$A/bin/BixbyPromotion.dll"
sha256sum "$A/bin/BixbyPromotion.dll" > "$D/installed-home.sha256"
find "$A/res/quiet-home" -type d -exec chmod 755 {} \;
find "$A/res/quiet-home" -type f -exec chmod 644 {} \;
find "$A/res/quiet-home" -exec chown 201:0 {} \;
find "$A/res/quiet-home" -exec chsmack -a User::Pkg::$C::RO {} \;
# The catalog is the file that decides which tiles exist. Its digest must match
# the local launcher/assets/apps-installed.json; if not, the stage was stale.
echo "Catalogo aplicado: $(md5sum "$A/res/quiet-home/apps-installed.json" 2>/dev/null | cut -c1-12)"
# Killing the running home can drop this channel; verify with recipes/status.sh.
app_launcher -u 5001 -s "$C"
rm -rf "$S/unpacked" # Scratch only; the staged package stays for a rollback.
echo 'Updated. Verify the visible UI, apps list, remote and HDMI before stopping here.'
echo "Previous assembly and resources: $D/update-previous"
