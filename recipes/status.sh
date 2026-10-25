#!/bin/sh
set -eu
printf 'Memory (KiB)\n'
grep -E '^(MemAvailable|SwapFree|CmaTotal|CmaFree):' /proc/meminfo
printf '\nCore services\n'
systemctl show -p Id -p ActiveState display-manager.service ac.service \
    pkgmgr-info.service connman.service pulseaudio.service
printf '\nBackground services\n'
systemctl show -p Id -p ActiveState -p ConditionResult adagent-service.service \
    pisa-service.service canalysis-service.service \
    com.samsung.tv.ondevice-voice.service org.tizen.voice-client.service \
    com.samsung.tv.context-aware-service.service ipa.service \
    contents-recognition-service.service org.tizen.tv.sp-kpi.service \
    data-service.service slive-provider-daemon.service
printf '\nHome selection\n'
vconftool get db/appfw/home_appid
vconftool get db/appfw/startup_appid
printf '\nPreload preference\n'
vconftool get db/was/preload_by_country
sqlite3 -readonly /opt/dbspace/.webappservice.db \
    "SELECT json_extract(value,'$.rsp.preloadByCountry') FROM WASConfigTable WHERE name='RESERVED_18' AND json_valid(value);"
printf '\nLauncher diagnostic state (local, overwritten)\n'
if [ -f /tmp/quiet-home-state.txt ]; then cat /tmp/quiet-home-state.txt; fi
