#!/bin/sh
# Read-only installed-app dump for tools/tv.py catalog. Prints labeled sections;
# writes nothing under /opt and changes no registry flags, vconf keys or Home.
#
# "Usable app" is observed, not documented: user-installable packages carry
# app_package_system='false', while the Samsung shell uses 'true'. The curated
# IDs from launcher/assets/apps.json are unioned in so a preloaded streaming
# app (YouTube ships as a system package) stays visible.
set -eu
test "$(id -u)" = 0
R="${UNTIZEN_REGISTRY:-/opt/dbspace/.pkgmgr_parser.db}"
ALBL="(SELECT MAX(CASE WHEN l.app_locale='en_US' THEN l.app_label WHEN l.app_locale='No Locale' THEN l.app_label END) FROM package_app_localized_info l WHERE l.app_id=a.app_id)"
PLBL="(SELECT MAX(CASE WHEN l.package_locale='en_US' THEN l.package_label WHEN l.package_locale='No Locale' THEN l.package_label END) FROM package_localized_info l WHERE l.package=a.package)"
AICO="(SELECT MAX(CASE WHEN l.app_locale='en_US' THEN l.app_icon WHEN l.app_locale='No Locale' THEN l.app_icon END) FROM package_app_localized_info l WHERE l.app_id=a.app_id)"
PICO="(SELECT MAX(CASE WHEN l.package_locale='en_US' THEN l.package_icon WHEN l.package_locale='No Locale' THEN l.package_icon END) FROM package_localized_info l WHERE l.package=a.package)"
printf '=== schema ===\n'
sqlite3 -readonly "$R" ".schema"
printf '=== apps ===\n'
sqlite3 -readonly "$R" "SELECT a.app_id||'|'||IFNULL(NULLIF($ALBL,''),IFNULL($PLBL,''))||'|'||IFNULL(NULLIF($AICO,''),IFNULL($PICO,''))
FROM package_app_info a JOIN package_info p ON p.package=a.package
WHERE a.app_nodisplay='false' AND a.app_disable='false'
  AND p.package_disable='false' AND p.package_nodisplay='false'
  AND (a.app_id IN (__CURATED_IDS__) OR (a.component_type='uiapp' AND a.app_package_system='false'));"
