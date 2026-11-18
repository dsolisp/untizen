#!/bin/sh
# Desinstalar UNA aplicacion por raiz: el launcher no ofrece el gesto.
#   list                    -> que se puede borrar en este tele
#   find <texto>            -> que paquetes responde ese texto, sin borrar
#   remove <texto>          -> muestra el unico paquete que va a caer
#   remove <texto> confirm  -> lo desinstala
#   <package> confirm       -> la desinstala con pkgcmd
# Uso: tv exec --script recipes/uninstall-app.sh --arg find --arg ego
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

# El titulo que ve el dueno vive en tablas localizadas aparte. Aqui alcanza con
# el nombre del paquete y el id de la app, que ya traen el nombre legible
# (V1ZDXtYqnR y V1ZDXtYqnR.EgoIPTV coinciden con "ego").
matches() {
    pat=$(printf '%s' "$1" | tr 'A-Z' 'a-z')
    sqlite3 -readonly "$DB" "SELECT DISTINCT package FROM package_info
        WHERE package_system='false' AND package_removable='true' AND package_preload='false'
          AND (lower(package) LIKE '%${pat}%' OR lower(mainapp_id) LIKE '%${pat}%')
        ORDER BY package;"
}

state_of() {
    for h in $(hosts); do test "$1" = "$h" && { echo 'MONTADO, no se toca'; return; }; done
    app=$(sqlite3 -readonly "$DB" "SELECT mainapp_id FROM package_info WHERE package='$1' LIMIT 1;")
    echo "$1  $app  removible"
}

remove_pkg() {
    pkg=$1
    case "$pkg" in ''|*[!A-Za-z0-9_.-]*) echo 'Nombre de paquete invalido' >&2; exit 1;; esac
    if is_protected "$pkg"; then
        echo "PROTEGIDO: $pkg es el contenedor del launcher o tiene su widget montado." >&2
        exit 1
    fi
    row=$(sqlite3 -readonly "$DB" "SELECT package FROM package_info WHERE package='$pkg'")
    test "$row" = "$pkg" || { echo "$pkg no esta instalado" >&2; exit 1; }
    /usr/bin/pkgcmd -u -n "$pkg" || true
    left=$(sqlite3 -readonly "$DB" "SELECT count(*) FROM package_info WHERE package='$pkg'")
    if [ "$left" = 0 ]; then
        echo "Desinstalada $pkg. Vuelve a instalarla desde la tienda o con pkgcmd -i."
    else
        echo "pkgcmd la rechazo y $pkg sigue en el registro."
        echo 'Si fue instalada sin la tienda, pkgmgr no la puede deshacer: queda'
        echo 'ocultarla del launcher o borrar archivos y filas a mano, que es cirugia de registro.'
        ps -ef 2>/dev/null | grep -i "$pkg" | grep -v grep || true
        exit 1
    fi
    echo 'Reinicia el televisor y regenera el launcher (build.py launcher + update-launcher).'
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
    echo '# Atajo: --arg find --arg ego  y despues  --arg remove --arg ego --arg confirm'
    ;;
find)
    text=${2:?que buscar}
    case "$text" in ''|*[!A-Za-z0-9_.-]*) echo 'Texto invalido: letras, digitos, punto, guiones.' >&2; exit 1;; esac
    found=$(matches "$text")
    test -n "$found" || { echo "nada removible coincide con $text"; exit 0; }
    printf '%s\n' "$found" | while read -r p; do state_of "$p"; done
    ;;
remove)
    text=${2:?que buscar}
    case "$text" in ''|*[!A-Za-z0-9_.-]*) echo 'Texto invalido: letras, digitos, punto, guiones.' >&2; exit 1;; esac
    found=$(matches "$text")
    n=$(printf '%s\n' "$found" | grep -c . || true)
    if [ "$n" = 0 ]; then
        echo "$text no coincide con nada removible; mira la lista completa." >&2
        exit 1
    fi
    if [ "$n" != 1 ]; then
        echo "$text coincide con $n paquetes; baja el texto hasta uno:" >&2
        printf '%s\n' "$found" | while read -r p; do state_of "$p" >&2; done
        exit 1
    fi
    pkg=$(printf '%s\n' "$found" | head -1)
    if is_protected "$pkg"; then
        echo "PROTEGIDO: $pkg es el contenedor del launcher o tiene su widget montado; ni preview." >&2
        exit 1
    fi
    if [ "${3:-}" != confirm ]; then
        state_of "$pkg"
        echo 'preview: nada se borro todavia. Repite con --arg confirm:'
        echo "  tv exec --script recipes/uninstall-app.sh --arg remove --arg $text --arg confirm"
        exit 0
    fi
    remove_pkg "$pkg"
    ;;
*)
    test "${2:-}" = confirm || { echo 'El segundo argumento debe ser confirm' >&2; exit 1; }
    remove_pkg "$1"
    ;;
esac
exit 0
