#!/usr/bin/env python3
"""Forward 127.0.0.1 to the TV's SDB port for agents whose sandbox cannot reach the LAN.

Run this in an ordinary terminal and leave it running:

    python3 tools/relay.py 192.0.2.50
    python3 tools/tv.py --host 127.0.0.1 --callback-host <this-computer-LAN-IP> \\
        --firmware "$TV_FIRMWARE" doctor

It listens on 127.0.0.1 only, never on the network. Root sessions still need
--callback-host set to this computer's real LAN address: the TV must connect
back, and 127.0.0.1 on the laptop is not reachable from the panel.
"""
import argparse
import ipaddress
import os
import socket
import sys
import threading

LISTEN = "127.0.0.1"
DEFAULT_TV_PORT = 26101


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for side in (src, dst):
            try:
                side.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def serve(server, tv_host, tv_port):
    while True:
        client, _ = server.accept()
        try:
            tv = socket.create_connection((tv_host, tv_port), timeout=10)
            tv.settimeout(None)
        except OSError as error:
            print(f"cannot reach {tv_host}:{tv_port}: {error}", flush=True)
            client.close()
            continue
        for left, right in ((client, tv), (tv, client)):
            threading.Thread(target=pipe, args=(left, right), daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tv_host",
        nargs="?",
        default=os.environ.get("TV_IP") or os.environ.get("TV_HOST"),
        help="The owner's TV IPv4; never scanned",
    )
    parser.add_argument("--tv-port", type=int, default=DEFAULT_TV_PORT,
                        help="SDB port on the TV (default 26101)")
    parser.add_argument("--port", type=int, default=DEFAULT_TV_PORT,
                        help="Local loopback port (default 26101 so --host 127.0.0.1 works)")
    args = parser.parse_args()
    if not args.tv_host:
        parser.error("give the TV's IPv4, e.g. python3 tools/relay.py 192.0.2.50")
    ipaddress.IPv4Address(args.tv_host)
    if ipaddress.IPv4Address(args.tv_host).is_loopback and args.tv_port == args.port:
        parser.error("that is the relay itself: give the TV's LAN IPv4, not 127.0.0.1")
    if not (1 <= args.tv_port <= 65535 and 1 <= args.port <= 65535):
        parser.error("ports must be in 1..65535")

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((LISTEN, args.port))
    except OSError as error:
        sys.exit(f"cannot listen on {LISTEN}:{args.port}: {error}. Is a relay already running?")
    server.listen(8)
    port = server.getsockname()[1]
    print(f"relay {LISTEN}:{port} -> {args.tv_host}:{args.tv_port}", flush=True)
    print(
        f"use --host {LISTEN} and --callback-host <this-computer-LAN-IP> "
        "with tools/tv.py; Ctrl-C stops the relay",
        flush=True,
    )
    try:
        serve(server, args.tv_host, args.tv_port)
    except KeyboardInterrupt:
        print("relay stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
