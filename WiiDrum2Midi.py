#!/usr/bin/env python3
# convert Wii Drum events to GENERAL MIDI Drum Note 
# original code: https://github.com/aib/PyMIDIK/  

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import evdev
from evdev import ecodes

import rtmidi
from rtmidi import midiconstants

kcodes = ecodes.ecodes
keyMap = {
    kcodes['ABS_HAT0X']:38,
    kcodes['ABS_HAT0Y']:48,
    kcodes['ABS_HAT1X']:41,
    kcodes['ABS_HAT2X']:42,
    kcodes['ABS_HAT2Y']:49,
    kcodes['ABS_HAT3X']:35
}

args = None

def key_code_to_midi_note(code):
    try:
        return keyMap[code]
    except KeyError:
        return None

def list_ports_and_devices():
    print("MIDI input ports:")
    with rtmidi.MidiOut() as mo:
        ports = mo.get_ports()
    for port in ports:
        print("    %s" % (port,))

    print("Devices:")
    devs = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    for dev in devs:
        print("    %s %s" % (dev.path, dev.name))

def parse_channel(string):
    val = int(string)
    if val < 1 or val > 16:
        raise argparse.ArgumentTypeError("Invalid channel number %r" % string)
    return val - 1

def parse_transpose(string):
    val = int(string)
    if val <= -127 or val >= 127:
        raise argparse.ArgumentTypeError("Invalid transpose amount %r" % string)
    return val

def _send_message(port, msg):
    if args.verbose:
        print("Sent", msg)
    port.send_message(msg)

def _parse_ev(ev):
    if ev.type == evdev.ecodes.EV_ABS:
        note = key_code_to_midi_note(ev.code)
        if note is not None:
            if ev.value == 0:
                if args.verbose:
                    print('note off')
                #_send_message(midiout, [midiconstants.NOTE_OFF + args.channel, (note + args.transpose) % 127, 0])
            else:
                velocity =round((127.0 / 7.0 ) * ev.value) % 128
                if args.verbose:
                    print('value: {} vel: {}'.format(ev.value, velocity))

                _send_message(midiout, [midiconstants.NOTE_ON + args.channel, (note + args.transpose) % 127, velocity])
                time.sleep(0.5)
                _send_message(midiout, [midiconstants.NOTE_OFF + args.channel, (note + args.transpose) % 127, 0])




def main():
    parser = argparse.ArgumentParser(description="WII Drum to MIDI")

    parser.add_argument(
        'device', help="Evdev input device",
        nargs='?')

    parser.add_argument(
        '-l', '--list', help="List MIDI input ports, input devices and quit",
        dest='list', action='store_true')

    parser.add_argument('-n', '--port-name', help="MIDI output port name to create",
        dest='port_name', default="WiiDrum2Midi")

    parser.add_argument('-o', '--connect', help="MIDI input port to connect to",
        dest='connect_port')

    parser.add_argument('-c', '--channel', help="MIDI channel number (1-16)",
        dest='channel', type=parse_channel, default=10)

    parser.add_argument('-t', '--transpose', help="Transpose MIDI notes by amount (+/- 0-126)",
        dest='transpose', type=parse_transpose, default=0)

    parser.add_argument('-g', '--grab', help="Grab input device, swallow input events",
        dest='grab', action='store_true')

    parser.add_argument('-v', '--verbose', help="Print MIDI messages",
        dest='verbose', action='store_true')

    global args
    args = parser.parse_args()

    if args.list:
        list_ports_and_devices()
        sys.exit(0)

    if args.device is None:
        parser.print_help()
        sys.exit(1)

    midiout = rtmidi.MidiOut()

    if args.connect_port is None:
        midiout.open_virtual_port(args.port_name)
        print("Opened virtual port \"%s\"" % (args.port_name,))
    else:
        ports = list(filter(lambda p: p[1].startswith(args.connect_port), enumerate(midiout.get_ports())))
        if len(ports) == 0:
            print("No MIDI input ports found matching \"%s\"" % (args.connect_port,))
            sys.exit(3)
        else:
            port = ports[0]
            midiout.open_port(port[0])
            print("Connected to port \"%s\"" % (port[1]))

    dev = evdev.InputDevice(args.device)

    if args.grab:
        dev.grab()
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        for ev in dev.read_loop():
            future=executor.submit(_parse_ev,ev)
        
    if args.grab:
        dev.ungrab()

if __name__ == '__main__':
    try:
       ret = main()
    except (KeyboardInterrupt, EOFError):
        ret = 0
    sys.exit(ret)
