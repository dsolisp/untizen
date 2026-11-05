#!/bin/sh
# Desinstalar UNA aplicacion por raiz: el launcher no ofrece el gesto.
#   list                -> que se puede borrar en este tele
#   <package> confirm   -> la desinstala con pkgcmd
# Uso: tv exec --script recipes/uninstall-app.sh --arg list
set -eu
test "$(id -u)" = 0
DB=${UNTIZEN_REGISTRY:-/opt/dbspace/.pkgmgr_parser.db}
KEEP="${UNTIZEN_CONTAINER:-com.samsung.tv.bixby-promotion}"
KEEP_SETTINGS="${UNTIZEN_SETTINGS_CONTAINER:-$KEEP}"

# Paquetes que sostienen algo del proyecto: el contenedor del launcher, el
# puente de ajustes y el que tiene su widget montado por un loop (ahi vive
# Marea TV). Se detecta por el backing file real, no por el nombre del .tmg:
# casi toda app de la tienda tambien trae su .tmg en res/.
hosts() {
    for lb in /sys/block/loop*/loop/backing_file; do
        test -r "$lb" || continue
        f=$(cat "$lb" 2>/dev/null) || continue
        case "$f" in
            /opt/usr/apps/*) basename "$(dirname "$(dirname "$f")")" ;;
        esac
    done
}

is_protected() {
    for keep in "$KEEP" "$KEEP_SETTINGS"; do
        test "$1" = "$keep" && return 0
    done
    for h in $(hosts); do
        test "$1" = "$h" && return 0
    done
    return 1
}

case "${1:-list}" in
list)
    running=$(hosts | tr '\n' ' ')
    sqlite3 -readonly "$DB" "SELECT DISTINCT package, package_type, mainapp_id
        FROM package_info
        WHERE package_system='false' AND package_removable='true' AND package_preload='false'
        ORDER BY package;" | while IFS='|' read -r pkg type app; do
        hit=no
        for h in $running; do test "$h" = "$pkg" && hit=MONTADO; done
        echo "$pkg  $type  $app  $hit"
    done
    echo '# removible, no sistema, no preinstalada. MONTADO = su widget esta'
    echo '# montado ahora (es el huesped de Marea TV si el app id es Smarters).'
    echo '# Antes de borrar: tv exec --script recipes/snapshot.sh --arg <nombre>'
    ;;
*)
    pkg=$1
    test "${2:-}" = confirm || { echo 'El segundo argumento debe ser confirm' >&2; exit 1; }
    case "$pkg" in ''|*[!A-Za-z0-9_.-]*) echo 'Nombre de paquete invalido' >&2; exit 1;; esac
    if is_protected "$pkg"; then
        echo "PROTEGIDO: $pkg es el contenedor del launcher o tiene su widget montado." >&2
        exit 1
    fi
    row=$(sqlite3 -readonly "$DB" "SELECT package FROM package_info WHERE package='$pkg'")
    test "$row" = "$pkg" || { echo "$pkg no esta instalado" >&2; exit 1; }
    /usr/bin/pkgcmd -u -n "$pkg"
    left=$(sqlite3 -readonly "$DB" "SELECT count(*) FROM package_info WHERE package='$pkg'")
    if [ "$left" = 0 ]; then
        echo "Desinstalada $pkg. Se puede volver a registrar con pkgcmd -i."
    else
        echo "pkgcmd termino pero $pkg sigue en el registro; revisa los procesos:"
        ps -ef 2>/dev/null | grep -i "$pkg" | grep -v grep || true
    fi
    echo 'Reinicia el televisor y regenera el launcher (build.py launcher + update-launcher).'
    ;;
esac
exit 0
