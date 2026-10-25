# tools/relay.py

Forwards a loopback port on this computer to the TV's SDB port (26101). Use it
when a coding assistant's sandbox can reach this machine but not other devices
on the LAN (Cursor or Claude Code on macOS Local Network privacy).

```sh
# Ordinary terminal; leave it running:
python3 tools/relay.py 192.0.2.50

# Then the assistant uses loopback for SDB, and the real LAN IP for the
# root callback the TV must open:
tv() {
  python3 tools/tv.py --host 127.0.0.1 \
    --callback-host 192.0.2.10 \
    --firmware "$TV_FIRMWARE" "$@"
}
tv inventory
```

`192.0.2.50` is a documentation address. Use the owner's TV and this
computer's LAN IPv4.

## Safety

- Listens on `127.0.0.1` only. There is no flag to bind the LAN.
- Give the TV's real IPv4 to the relay, never `127.0.0.1`.
- Root sessions (`inventory`, `root-check`, `exec`, `pull`) still need
  `--callback-host` set to this computer's LAN address. `127.0.0.1` as the
  callback is unreachable from the TV.
- Stop the relay when the session ends, the same way you turn Developer Mode
  off. Check with `python3 tools/tv.py --host <TV_IP> port-closed`.
