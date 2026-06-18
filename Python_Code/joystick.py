import serial
import pydirectinput as game
import time

import sys


# Port Settings

port = 'COM5'
baud = 115200

game.PAUSE = 0
game.FAILSAFE = False


# Connect Arduino
try:
    arduino = serial.Serial(port, baud, timeout=0)
    time.sleep(1)
    arduino.flushInput()
    print("Controller Connected")
except Exception as e:
    print(f"Error: Could not connect to Arduino on {port}.")
    print(f"Details: {e}")
    print("Please make sure the Arduino is plugged in and using the correct COM port.")
    input("Press Enter to exit...")
    sys.exit()


# Key States

left = False
right = False
forward = False
backward = False

space_btn = False
shift_btn = False
f_btn = False
esc_btn = False

# Dead zone
low = 470
high = 560


# Main Loop

while True:
    try:
        if arduino.in_waiting:

            data = arduino.readline().decode(errors='ignore').strip()
            values = data.split(",")

            if len(values) >= 8:

                a0 = int(values[0])
                a1 = int(values[1])   # right joystick X
                a2 = int(values[2])   # left joystick X
                a3 = int(values[3])

                b1 = int(values[4])   # D3
                b2 = int(values[5])   # D4
                b3 = int(values[6])   # D5
                b4 = int(values[7])   # D6

                
                # Right joystick = Left / Right
                
                if a1 < low:
                    if not left:
                        game.keyDown("left")
                        left = True
                    if right:
                        game.keyUp("right")
                        right = False

                elif a1 > high:
                    if not right:
                        game.keyDown("right")
                        right = True
                    if left:
                        game.keyUp("left")
                        left = False

                else:
                    if left:
                        game.keyUp("left")
                        left = False
                    if right:
                        game.keyUp("right")
                        right = False

                
                # Left joystick = Forward / Backward
                
                if a2 > high:
                    if not forward:
                        game.keyDown("up")
                        forward = True
                    if backward:
                        game.keyUp("down")
                        backward = False

                elif a2 < low:
                    if not backward:
                        game.keyDown("down")
                        backward = True
                    if forward:
                        game.keyUp("up")
                        forward = False

                else:
                    if forward:
                        game.keyUp("up")
                        forward = False
                    if backward:
                        game.keyUp("down")
                        backward = False

                
                # Buttons
                

                # Button 1 = Space
                if b1 == 1:
                    if not space_btn:
                        game.keyDown("space")
                        space_btn = True
                else:
                    if space_btn:
                        game.keyUp("space")
                        space_btn = False

                # Button 2 = Shift
                if b2 == 1:
                    if not shift_btn:
                        game.keyDown("shift")
                        shift_btn = True
                else:
                    if shift_btn:
                        game.keyUp("shift")
                        shift_btn = False

                # Button 3 = F
                if b3 == 1:
                    if not f_btn:
                        game.keyDown("f")
                        f_btn = True
                else:
                    if f_btn:
                        game.keyUp("f")
                        f_btn = False

                # Button 4 = ESC
                if b4 == 1:
                    if not esc_btn:
                        game.press("esc")
                        esc_btn = True
                else:
                    esc_btn = False

    except:
        pass