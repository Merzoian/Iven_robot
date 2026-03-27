import serial

class ServoController:
    def __init__(self, port='/dev/ttyACM0'):
        try:
            self.usb = serial.Serial(port)
            print(f"Connected to Maestro at {port}")
        except:
            print(f"Error: Could not connect to Maestro at {port}. Check connections.")
            self.usb = None

        self.servos = {
            1: {'name': 'Left Eye L/R',  'neutral': 1447, 'minleft': 1350, 'maxright': 1650},
            2: {'name': 'Lid Left',      'neutral': 1550, 'minclosed': 1550, 'maxopen': 1700},
            3: {'name': 'Lid Right',     'neutral': 1780, 'minclosed': 1780, 'maxopen': 1580}, 
            4: {'name': 'Right Eye L/R', 'neutral': 1559, 'minleft': 1350, 'maxright': 1720},
            5: {'name': 'Both Eyes U/D', 'neutral': 1500, 'mindown': 1700, 'maxup': 1250},
            6: {'name': 'Jaw',           'neutral': 1450, 'minclosed': 1450, 'maxopen': 1650},
            7: {'name': 'Face Pitch',    'neutral': 1500, 'minstraghit': 1330, 'maxup': 1640},
            8: {'name': 'Face Yaw',      'neutral': 1560, 'minright': 1300, 'maxleft': 1800},
            9: {'name': 'Head Tilt',     'neutral': 1500, 'minright': 1650, 'maxleft': 1360}
        }

    def _limit_pair(self, limits):
        # Support descriptive min/max pairs without forcing a single naming convention.
        if 'min' in limits and 'max' in limits:
            return limits['min'], limits['max']

        # Tolerate the existing typo without changing the stored value.
        if 'minstraghit' in limits and 'minstraight' not in limits:
            limits = dict(limits)
            limits['minstraight'] = limits['minstraghit']

        pairs = [
            ('minleft', 'maxright'),
            ('minright', 'maxleft'),
            ('mindown', 'maxup'),
            ('minup', 'maxdown'),
            ('minclosed', 'maxopen'),
            ('minstraight', 'maxup'),
        ]
        for min_key, max_key in pairs:
            if min_key in limits and max_key in limits:
                return limits[min_key], limits[max_key]

        min_keys = [k for k in limits if k.startswith('min')]
        max_keys = [k for k in limits if k.startswith('max')]
        if len(min_keys) == 1 and len(max_keys) == 1:
            return limits[min_keys[0]], limits[max_keys[0]]

        neutral = limits.get('neutral', 1500)
        return neutral, neutral

    def get_limits(self, channel):
        if channel not in self.servos:
            return (1500, 1500)
        return self._limit_pair(self.servos[channel])

    def get_neutral(self, channel, default=1500):
        return self.servos.get(channel, {}).get('neutral', default)

    def set_speed(self, channel, speed):
        """Sets the speed limit (0-255). 0 is unlimited."""
        if self.usb:
            lsb = speed & 0x7F
            msb = (speed >> 7) & 0x7F
            self.usb.write(bytes([0x87, channel, lsb, msb]))

    def set_accel(self, channel, accel):
        """Sets acceleration limit (0-255). 0 is unlimited."""
        if self.usb:
            lsb = accel & 0x7F
            msb = (accel >> 7) & 0x7F
            self.usb.write(bytes([0x89, channel, lsb, msb]))

    def set_target(self, channel, target_us):
        if self.usb is None: return
        if channel not in self.servos: return

        limits = self.servos[channel]
        raw_min, raw_max = self._limit_pair(limits)
        true_min = min(raw_min, raw_max)
        true_max = max(raw_min, raw_max)
        safe_target = max(true_min, min(target_us, true_max))

        val = int(safe_target * 4)
        lsb = val & 0x7F
        msb = (val >> 7) & 0x7F
        self.usb.write(bytes([0x84, channel, lsb, msb]))

    def reset_to_neutral(self):
        print("Resetting to neutral...")
        for ch, config in self.servos.items():
            self.set_target(ch, config['neutral'])

if __name__ == "__main__":
    controller = ServoController()
    controller.reset_to_neutral()
