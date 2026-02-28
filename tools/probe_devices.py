"""
Probe Logitech Bolt receiver to discover device slots and IDs.

Sends HID++ ping packets to all slot/device combinations and reports
which ones respond. Run from project root:

    python tools/probe_devices.py [VID:PID]

Default VID:PID is 046D:C548 (Bolt). Pass 046D:C52B for Unifying.
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils import get_absolute_file_data_path, creation_flags


def get_hidapitester():
    import platform
    system = platform.system().lower()
    arch = platform.machine()
    if system == 'windows':
        return get_absolute_file_data_path('hidapitester', 'hidapitester-windows-x86_64.exe')
    elif system == 'darwin':
        name = 'hidapitester-macos-arm64' if arch == 'arm64' else 'hidapitester-macos-x86_64'
        return get_absolute_file_data_path('hidapitester', name)
    else:
        name = 'hidapitester-linux-armv7l' if arch == 'armv7l' else 'hidapitester-linux-x86_64'
        return get_absolute_file_data_path('hidapitester', name)


def probe(exec_path, vidpid, slot, device_id):
    """Send a HID++ root ping (feature 0x0000, ping) to slot/device."""
    # HID++ short message: [0x10, slot, device_id, 0x00, 0x00, 0x00, 0x00]
    # Feature index 0x00 = IRoot, function 0 = ping
    msg = [0x10, slot, device_id, 0x00, 0x00, 0x00, 0x00]
    hex_string = ','.join(f'0x{b:02X}' for b in msg)
    cmd = [
        exec_path, '--vidpid', vidpid,
        '--usage', '1', '--usagePage', '0xFF00', '--open',
        '--length', '7', '--send-output', hex_string,
        '--length', '7', '--read-input',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=3, creationflags=creation_flags)
        output = result.stdout + result.stderr
        # Check if we got a response (read more than 0 bytes)
        if 'read 7 bytes' in output or 'read 20 bytes' in output:
            return True, output
        # Also check for any non-zero read
        for line in output.split('\n'):
            if 'read' in line and 'bytes' in line and 'read 0 bytes' not in line:
                return True, output
        return False, output
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except Exception as e:
        return False, str(e)


def main():
    vidpid = sys.argv[1] if len(sys.argv) > 1 else '046D:C548'
    exec_path = get_hidapitester()

    print(f'Probing receiver {vidpid}')
    print(f'Using: {exec_path}')
    print()

    # Slots 0x01-0x06 cover all possible Unifying/Bolt device slots
    # Device IDs 0x01-0x0F cover common range
    found = []

    for slot in range(0x01, 0x07):
        for dev_id in range(0x01, 0x10):
            label = f'slot=0x{slot:02X} device_id=0x{dev_id:02X}'
            sys.stdout.write(f'\r  Testing {label}...   ')
            sys.stdout.flush()
            ok, output = probe(exec_path, vidpid, slot, dev_id)
            if ok:
                sys.stdout.write(f'\r  FOUND: {label}      \n')
                found.append((slot, dev_id, output))

    sys.stdout.write('\r' + ' ' * 60 + '\r')

    if found:
        print(f'\nFound {len(found)} responding device(s):\n')
        for slot, dev_id, output in found:
            print(f'  Slot: 0x{slot:02X}  Device ID: 0x{dev_id:02X}')
            # Print response bytes if visible
            for line in output.split('\n'):
                if 'read' in line.lower() and 'bytes' in line:
                    print(f'    {line.strip()}')
            print()
    else:
        print('\nNo devices responded. Check that:')
        print('  - Receiver is plugged in')
        print('  - Keyboard/mouse are on and paired')
        print(f'  - VID:PID {vidpid} is correct')


if __name__ == '__main__':
    main()
