#!/bin/bash
# guardwing - self-healing lifelines for the Pi: bridge watchdog, wifi healer,
# tor backup-route keeper. Runs every minute from cron. Never deletes anything,
# never touches guestwing's running hotspot.
# pi-app-store: 1
LOG="${GUARDWING_LOG:-/var/log/guardwing.log}"
RUNDIR="${GUARDWING_RUNDIR:-/run}"
GW_STATE="${GUARDWING_GWSTATE:-/run/guestwing/pids.json}"
LOCK="${GUARDWING_LOCK:-/run/guardwing.lock}"
exec 9>"$LOCK" 2>/dev/null && flock -n 9 || exit 0   # one at a time

log(){ echo "$(date '+%F %T') $*" >>"$LOG" 2>/dev/null; }

# 1. bridges: restart when the service is down or its heartbeat file goes stale
for svc in pi-bridge pi-bridge2; do
  if ! systemctl is-active --quiet "$svc"; then
    systemctl restart "$svc" && log "restarted $svc (was inactive)"
    continue
  fi
  hb="$RUNDIR/$svc.heartbeat"
  if [ -f "$hb" ]; then
    age=$(( $(date +%s) - $(stat -c %Y "$hb") ))
    if [ "$age" -gt 120 ]; then
      systemctl restart "$svc" && log "restarted $svc (heartbeat ${age}s stale)"
    fi
  fi
done

# 2. wifi: reassociate when the link drops (but never while guestwing's
#    hotspot is running - its uplink rides the same radio)
WIFI="$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2; exit}')"
if [ -n "$WIFI" ]; then
  if ! iwgetid "$WIFI" >/dev/null 2>&1 || ! ip route show default 2>/dev/null | grep -q .; then
    if [ -f "$GW_STATE" ]; then
      log "wifi link down but guestwing hotspot state present - leaving the radio alone"
    else
      log "wifi link down - reassociating $WIFI"
      wpa_cli -i "$WIFI" reassociate >/dev/null 2>&1
      sleep 10
      if ! iwgetid "$WIFI" >/dev/null 2>&1; then
        log "reassociate failed - restarting networking"
        systemctl restart networking
      fi
    fi
  fi
fi

# 3. backup route: keep tor (onion SSH) alive
if ! systemctl is-active --quiet tor; then
  systemctl restart tor && log "restarted tor (backup SSH route)"
fi
exit 0
