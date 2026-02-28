"""
Probe Logitech Bolt/Unifying receiver to discover device slots and IDs.

Sends HID++ ping packets to all slot/device combinations and reports
which ones respond. Run from project root:

    python tools/probe_devices.py [--protocol bolt|unifying] [VID:PID]

Default: Bolt protocol with VID:PID 046D:C548.
For Unifying: python tools/probe_devices.py --protocol unifying 046D:C52B
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


def probe(exec_path, vidpid, protocol, slot, device_id):
    """Send a HID++ ping to slot/device using the appropriate packet format."""
    if protocol == 'bolt':
        # HID++ long message (20 bytes): [0x11, slot, device_id, 0x00, ...padding]
        msg = [0x11, slot, device_id, 0x00, 0x00] + [0x00] * 15
        length = '20'
        usage = '2'
    else:
        # HID++ short message (7 bytes): [0x10, slot, device_id, 0x00, 0x00, 0x00, 0x00]
        msg = [0x10, slot, device_id, 0x00, 0x00, 0x00, 0x00]
        length = '7'
        usage = '1'

    hex_string = ','.join(f'0x{b:02X}' for b in msg)
    cmd = [
        exec_path, '--vidpid', vidpid,
        '--usage', usage, '--usagePage', '0xFF00', '--open',
        '--length', length, '--send-output', hex_string,
        '--length', length, '--read-input',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=3, creationflags=creation_flags)
        output = result.stdout + result.stderr
        # Check if we got a response (read more than 0 bytes)
        if 'read 7 bytes' in output or 'read 20 bytes' in output:
            return True, output
        for line in output.split('\n'):
            if 'read' in line and 'bytes' in line and 'read 0 bytes' not in line:
                return True, output
        return False, output
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except Exception as e:
        return False, str(e)


def main():
    protocol = 'bolt'
    vidpid = '046D:C548'

    args = sys.argv[1:]
    if '--protocol' in args:
        idx = args.index('--protocol')
        protocol = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if args:
        vidpid = args[0]

    if protocol == 'unifying' and vidpid == '046D:C548':
        vidpid = '046D:C52B'

    print(f'Probing receiver {vidpid} (protocol: {protocol})')
    print(f'Using: {get_hidapitester()}')
    print()

    exec_path = get_hidapitester()
    found = []

    for slot in range(0x01, 0x07):
        for dev_id in range(0x01, 0x10):
            label = f'slot=0x{slot:02X} device_id=0x{dev_id:02X}'
            sys.stdout.write(f'\r  Testing {label}...   ')
            sys.stdout.flush()
            ok, output = probe(exec_path, vidpid, protocol, slot, dev_id)
            if ok:
                sys.stdout.write(f'\r  FOUND: {label}      \n')
                found.append((slot, dev_id, output))

    sys.stdout.write('\r' + ' ' * 60 + '\r')

    if found:
        print(f'\nFound {len(found)} responding device(s):\n')
        for slot, dev_id, output in found:
            print(f'  Slot: 0x{slot:02X}  Device ID: 0x{dev_id:02X}')
            for line in output.split('\n'):
                if 'read' in line.lower() and 'bytes' in line:
                    print(f'    {line.strip()}')
            print()
    else:
        print('\nNo devices responded. Check that:')
        print('  - Receiver is plugged in')
        print('  - Keyboard/mouse are on and paired')
        print(f'  - VID:PID {vidpid} is correct')
        print(f'  - Protocol "{protocol}" matches your receiver')


if __name__ == '__main__':
    main()
