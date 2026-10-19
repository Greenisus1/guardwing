# guardwing

Self-healing backup access for a Raspberry Pi (DietPi). When the pi-bridge services die or wifi flaps, guardwing notices within a minute and fixes it - and if the usual remote route is dead, a free tor onion SSH endpoint is always there as the back door.

## Install (one line, as root)

```
wget -qO- https://raw.githubusercontent.com/Greenisus1/guardwing/main/install.sh | sudo bash
```

The installer prints your onion address at the end. That's the backup route.

## What it does

- **Bridge watchdog** (cron, every minute): restarts `pi-bridge` and `pi-bridge2` when the service is down, or when its heartbeat file (`/run/<svc>.heartbeat`, if the service writes one) goes stale for 2+ minutes.
- **Wifi healer**: when the wireless link drops association or the default route vanishes, it reassociates with `wpa_cli`, and restarts networking if that doesn't bring it back. If guestwing's hotspot is currently running, it leaves the radio alone - healing never fights the hotspot.
- **Backup remote route**: a tor onion (hidden) service exposing local SSH. Free, no accounts, no paid service, no router changes, works behind any NAT or router channel hop. The watchdog keeps tor running.

## Using the backup route

From a Mac/Linux machine with tor installed (`brew install tor && brew services start tor`):

```
torsocks ssh pi@<your>.onion
```

or

```
ssh -o ProxyCommand='nc -x 127.0.0.1:9050 %h %p' pi@<your>.onion
```

It's slower than a direct tunnel - it's the spare tire, not the highway.

## Guarantees

- Never deletes anything. Never touches guestwing's state, iptables, or interfaces.
- Footprint: `/opt/guardwing/guardwing.sh`, `/etc/cron.d/guardwing`, two lines in `/etc/tor/torrc`, the tor hidden-service dir, and `/var/log/guardwing.log`.
- The watchdog is a single bash script - read it before you run it: `guardwing.sh` above.

MIT, Greenisus1. Built with AI assistance from my design.
