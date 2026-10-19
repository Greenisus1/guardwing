#!/bin/bash
# pi-app-store: 1
# pi-app-store-category: tools
# pi-app-store-description: Self-healing lifelines: restarts pi-bridge when its heartbeat dies, heals dropped wifi, keeps a free tor onion SSH route open as backup remote access. Install once via install.sh.
set -e
cd "$(dirname "$0")"
case "${1:-run}" in
  run) [ "$#" -eq 0 ] || shift; exec bash guardwing.sh "$@" ;;
  test) python3 -m unittest test_guardwing ;;
  *) echo "usage: $0 [run|test]" >&2; exit 2 ;;
esac
