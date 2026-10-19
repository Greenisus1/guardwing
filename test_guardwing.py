import os, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'guardwing.sh')

def make_bins(d, behaviors):
    """Write fake binaries: name -> shell body. Records calls to <d>/calls.log."""
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'calls.log'), 'w').close()
    for name, body in behaviors.items():
        p = os.path.join(d, name)
        with open(p, 'w') as f:
            f.write('#!/bin/bash\necho "%s $*" >>"%s"\n%s\n' % (name, os.path.join(d, 'calls.log'), body))
        os.chmod(p, 0o755)

BASE = {
    'date': 'echo 1000; exit 0',           # frozen clock
    'stat': 'echo 700; exit 0',            # heartbeat mtime: 300s ago = stale
    'iw': 'echo "Interface wlan0"; exit 0',
    'iwgetid': 'exit 0',                   # associated
    'ip': '[ "$2" = "route" ] && echo "default via 192.168.1.1 dev wlan0"; exit 0',
    'wpa_cli': 'exit 0',
    'sleep': 'exit 0',
    'flock': 'exit 0',
    'awk': 'echo wlan0',
    'grep': 'grep.real "$@" 2>/dev/null || exit 0',
    'systemctl': 'exit 0',
}

def run_watchdog(behaviors, rundir=None, gwstate=False):
    tmp = tempfile.mkdtemp()
    b = dict(BASE); b.update(behaviors)
    make_bins(os.path.join(tmp, 'bin'), b)
    env = dict(os.environ)
    env.update({'PATH': os.path.join(tmp, 'bin') + ':' + os.environ.get('PATH', ''),
                'GUARDWING_LOG': os.path.join(tmp, 'guardwing.log'),
                'GUARDWING_RUNDIR': rundir or os.path.join(tmp, 'run'),
                'GUARDWING_GWSTATE': os.path.join(tmp, 'gw', 'pids.json'),
                'GUARDWING_LOCK': os.path.join(tmp, 'lock')})
    os.makedirs(env['GUARDWING_RUNDIR'], exist_ok=True)
    if gwstate:
        os.makedirs(os.path.dirname(env['GUARDWING_GWSTATE']), exist_ok=True)
        open(env['GUARDWING_GWSTATE'], 'w').write('{}')
    r = subprocess.run(['bash', SCRIPT], env=env, capture_output=True, text=True, timeout=30)
    calls = open(os.path.join(tmp, 'bin', 'calls.log')).read()
    log = open(env['GUARDWING_LOG']).read() if os.path.exists(env['GUARDWING_LOG']) else ''
    return r, calls, log

class GuardwingTests(unittest.TestCase):
    def test_bridge_inactive_restarted(self):
        b = {'systemctl': 'if [ "$3" = "pi-bridge" ] && [ "$1" = "is-active" ]; then exit 1; fi; exit 0'}
        r, calls, log = run_watchdog(b)
        self.assertEqual(r.returncode, 0)
        self.assertIn('systemctl restart pi-bridge\n', calls)
        self.assertIn('restarted pi-bridge (was inactive)', log)
    def test_bridge_stale_heartbeat_restarted(self):
        tmp = tempfile.mkdtemp()
        open(os.path.join(tmp, 'pi-bridge.heartbeat'), 'w').write('x')
        r, calls, log = run_watchdog({}, rundir=tmp)
        self.assertIn('systemctl restart pi-bridge\n', calls)
        self.assertIn('heartbeat 300s stale', log)
    def test_fresh_heartbeat_left_alone(self):
        b = dict(BASE)
        b['stat'] = 'echo 950; exit 0'    # 50s old
        tmp = tempfile.mkdtemp()
        open(os.path.join(tmp, 'pi-bridge.heartbeat'), 'w').write('x')
        r, calls, log = run_watchdog(b, rundir=tmp)
        self.assertNotIn('systemctl restart pi-bridge\n', calls)
    def test_wifi_down_reassociates(self):
        b = {'iwgetid': 'exit 1'}
        r, calls, log = run_watchdog(b)
        self.assertIn('wpa_cli -i wlan0 reassociate', calls)
        self.assertIn('reassociating wlan0', log)
    def test_wifi_down_but_guestwing_active(self):
        b = {'iwgetid': 'exit 1'}
        r, calls, log = run_watchdog(b, gwstate=True)
        self.assertNotIn('wpa_cli', calls)
        self.assertNotIn('systemctl restart networking', calls)
        self.assertIn('leaving the radio alone', log)
    def test_reassociate_failure_restarts_networking(self):
        b = {'iwgetid': 'exit 1'}           # still down after reassociate
        r, calls, log = run_watchdog(b)
        self.assertIn('systemctl restart networking', calls)
    def test_tor_restarted_when_down(self):
        b = {'systemctl': 'if [ "$3" = "tor" ] && [ "$1" = "is-active" ]; then exit 1; fi; exit 0'}
        r, calls, log = run_watchdog(b)
        self.assertIn('systemctl restart tor', calls)
    def test_all_healthy_no_action(self):
        r, calls, log = run_watchdog({})
        self.assertEqual(r.returncode, 0)
        self.assertNotIn('restart pi-bridge', calls)
        self.assertNotIn('reassociate', calls)
        self.assertNotIn('restart tor', calls)
    def test_install_script_markers(self):
        sh = open(os.path.join(HERE, 'install.sh')).read()
        self.assertIn('HiddenServicePort 22 127.0.0.1:22', sh)
        self.assertIn('/etc/cron.d/guardwing', sh)
        self.assertNotIn('rm -rf', sh)      # never deletes anything

if __name__ == '__main__':
    unittest.main()
