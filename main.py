from machine import Pin, SoftI2C
from adxl345 import ADXL345
import time

# --- CONFIGURATION & CONSTANTS ---
# Movement sensitivity threshold
DELTA = 25
# Inactivity timeout in seconds before lifting
IDLE_TIMEOUT = 5
# Number of steps for the elevation mechanism
STEPS_TO_MOVE = 130
# Stepper Motor 1 Pins
motor1_pins = [Pin(4, Pin.OUT), Pin(16, Pin.OUT), Pin(17, Pin.OUT), Pin(18, Pin.OUT)]
# Stepper Motor 2 Pins
motor2_pins = [Pin(27, Pin.OUT), Pin(26, Pin.OUT), Pin(25, Pin.OUT), Pin(33, Pin.OUT)]

# I2C and Status LED Initialization
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
status_led = Pin(13, Pin.OUT)
accel = ADXL345(i2c)

# Full-step sequence for motors
sequence = [
    [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]
]


def disable_motors():
    """Powers down motor coils to prevent overheating and save energy."""
    for pin in motor1_pins + motor2_pins:
        pin.value(0)


def elevate_iron():
    """Lifts the iron to safety position."""
    print("ACTION: Elevating iron to safety position...")
    time.sleep(1)

    x = 0
    while x < STEPS_TO_MOVE:
        for i in range(4):
            step_m1 = sequence[i]
            step_m2 = sequence[3 - i]  # Reverse direction for the second motor

            for pin in range(4):
                motor1_pins[pin].value(step_m2[pin])
                motor2_pins[pin].value(step_m1[pin])

            time.sleep(0.005)
        x += 1

    disable_motors()
    print("STATUS: Elevation complete.")


def put_iron_down():
    """Lowers the iron back to working position."""
    print("ACTION: Lowering iron to active position...")
    time.sleep(1)

    x = 0
    while x < STEPS_TO_MOVE:
        for i in range(4):
            step_m1 = sequence[i]
            step_m2 = sequence[3 - i]  # Reverse direction for the second motor

            for pin in range(4):
                motor1_pins[pin].value(step_m1[pin])
                motor2_pins[pin].value(step_m2[pin])

            time.sleep(0.005)
        x += 1

    disable_motors()
    print("STATUS: Iron is now in active position.")


def convert_to_signed(val):
    """Converts raw 16-bit values from ADXL345 to signed integers."""
    if val > 32767:
        return val - 65536
    return val


def get_accel_data():
    """Reads and converts current accelerometer data."""
    raw_x, raw_y, raw_z = accel.read()
    return convert_to_signed(raw_x), convert_to_signed(raw_y), convert_to_signed(raw_z)


# --- MAIN CONTROL LOOP ---
status_led.value(1)
print('System Initialized: Monitoring iron movement...')

# Initial baseline calibration
last_x, last_y, last_z = get_accel_data()
start_time = time.time()
is_elevated = False

while True:
    curr_x, curr_y, curr_z = get_accel_data()

    # Calculate absolute movement change
    moved = (abs(curr_x - last_x) > DELTA or
             abs(curr_y - last_y) > DELTA or
             abs(curr_z - last_z) > DELTA)

    if moved:
        status_led.value(1)

        if is_elevated:
            put_iron_down()
            is_elevated = False
            # Wait for vibrations to settle and refresh baseline
            time.sleep(0.5)
            raw_x, raw_y, raw_z = accel.read()
            curr_x, curr_y, curr_z = get_accel_data()

        last_x = curr_x
        last_y = curr_y
        last_z = curr_z

        start_time = time.time()  # Reset inactivity timer

    elapsed_time = time.time() - start_time

# Trigger safety elevation after inactivity timeout
    if elapsed_time > IDLE_TIMEOUT and not is_elevated:
        status_led.value(0)
        elevate_iron()
        is_elevated = True
        # Reset timer after mechanical movement finishes
        start_time = time.time()
        last_x, last_y, last_z = get_accel_data()
