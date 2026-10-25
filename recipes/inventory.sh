#!/bin/sh
# Read-only dump for tools/tv.py inventory. Prints labeled sections; writes nothing
# under /opt and does not change registry flags, vconf or Home.
set -eu
test "$(id -u)" = 0
printf '=== kernel ===\n'
uname -srmo
printf '=== runtime ===\n'
readlink -f /usr/share/dotnet.tizen/netcoreapp 2>/dev/null || true
if [ -d /usr/share/dotnet.tizen/netcoreapp ]; then
    ls /usr/share/dotnet.tizen/netcoreapp | head -n 20
fi
printf '=== registry ===\n'
printf '%s\n' /opt/dbspace/.pkgmgr_parser.db
printf '=== schema ===\n'
sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db ".schema package_app_info"
printf '=== apps ===\n'
sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db \
    "SELECT app_id FROM package_app_info ORDER BY app_id;"
printf '=== home ===\n'
vconftool get db/appfw/home_appid || true
vconftool get db/appfw/startup_appid || true
printf '=== containers ===\n'
for container in com.samsung.tv.bixby-promotion com.samsung.tv.quicklaunch; do
    if [ -d "/opt/usr/apps/$container" ]; then
        printf '%s\n' "$container"
    fi
done
printf '=== probe ===\n'
if [ -f /home/owner/share/tmp/sdk_tools/untizen/Probe.dll ]; then
    /usr/bin/dotnet /home/owner/share/tmp/sdk_tools/untizen/Probe.dll || true
fi
