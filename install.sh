#!/bin/bash
# guardwing installer. One line:
#   wget -qO- https://raw.githubusercontent.com/Greenisus1/guardwing/main/install.sh | sudo bash
set -e
[ "$(id -u)" = 0 ] || { echo "needs root: wget -qO- https://raw.githubusercontent.com/Greenisus1/guardwing/main/install.sh | sudo bash"; exit 1; }
apt-get update -qq
apt-get install -y -qq tor wireless-tools wpasupplicant iw cron openssh-server
mkdir -p /opt/guardwing
B=https://raw.githubusercontent.com/Greenisus1/guardwing/main
curl -sSL "$B/guardwing.sh" -o /opt/guardwing/guardwing.sh 2>/dev/null || wget -qO /opt/guardwing/guardwing.sh "$B/guardwing.sh"
chmod +x /opt/guardwing/guardwing.sh
# backup remote route: tor onion service exposing local SSH - free, no accounts,
# no router changes, works behind NAT
if ! grep -q guardwing_ssh /etc/tor/torrc 2>/dev/null; then
  printf '\nHiddenServiceDir /var/lib/tor/guardwing_ssh/\nHiddenServicePort 22 127.0.0.1:22\n' >> /etc/tor/torrc
fi
systemctl enable --now tor
systemctl restart tor
# watchdog every minute
echo '* * * * * root /opt/guardwing/guardwing.sh' > /etc/cron.d/guardwing
systemctl restart cron 2>/dev/null || true
echo "guardwing installed: watchdog live (cron, every minute)."
echo -n "backup SSH route (tor onion): "
for i in $(seq 1 45); do
  [ -s /var/lib/tor/guardwing_ssh/hostname ] && break
  sleep 2
done
ONION=$(cat /var/lib/tor/guardwing_ssh/hostname 2>/dev/null || echo "(still generating - check /var/lib/tor/guardwing_ssh/hostname in a minute)")
echo "$ONION"
echo "from your Mac: torsocks ssh pi@$ONION   (or: ssh -o ProxyCommand='nc -x 127.0.0.1:9050 %h %p' pi@$ONION with tor running locally)"
