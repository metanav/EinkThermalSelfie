import time
import os
import io
import colorsys
import numpy as np
from PIL import Image
import subprocess
import logging
import RPi.GPIO as GPIO
import MLX90640 as mlx90640
from threading import Thread, Condition
from inky.inky_uc8159 import Inky

class ThermalCamera:
    def __init__(self, fps):
        self.condition = Condition()
        self.fps       = fps
        self.frame     = None

        mlx90640.setup(self.fps)
        
    def capture(self):
        logging.warning("Started Capture")
        while True:
            with self.condition:
                self.frame = mlx90640.get_frame()
                self.condition.notify_all()

            time.sleep(1.0 / self.fps)

    def start_recording(self):
        thread = Thread(target=self.capture)
        thread.start()
    
    def stop_recording(self):
        mlx90640.cleanup()


    def temperature_to_color(self, val, vmin, vmax):
        color = ((0,0,1), (0,1,1), (0,1,0), (1,1,0), (1,0,0), (1,0,1), (1,1,1))
        fractBetween = 0.0;
        vmin = vmin - 0.5
        vmax = vmax + 0.5 
        vrange = vmax - vmin
    
        val = (val - vmin) / vrange;
        if np.isnan(val):
            val = 0.0
    
        if val <= 0:
            idx1 = 0
            idx2 = 0
        elif val >= 1:
            idx1 = len(color) - 1
            idx2 = len(color) - 1
        else:
            val = val * (len(color) -1)
            idx1 = int(val);
            idx2 = idx1 + 1;
            fractBetween = val - idx1;
    
        r = int((((color[idx2][0] - color[idx1][0]) * fractBetween) + color[idx1][0]) * 255.0)
        g = int((((color[idx2][1] - color[idx1][1]) * fractBetween) + color[idx1][1]) * 255.0)
        b = int((((color[idx2][2] - color[idx1][2]) * fractBetween) + color[idx1][2]) * 255.0)
    
        return r, g, b

if __name__ == '__main__':
    capture = False
    #Setup button 'A' on the inky
    pin = 5
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    def btn_A_handler(pin):
        global capture
        capture = True

    GPIO.add_event_detect(pin, GPIO.FALLING, btn_A_handler, bouncetime=250)

    fps = 8
    thermal_camera = ThermalCamera(fps)
    print("Started recording")
    thermal_camera.start_recording()
    inky = Inky()
    try:
        while True:
            with thermal_camera.condition:
                thermal_camera.condition.wait()
                if capture == True:
                    print('Capture image')
                    time.sleep(5)
                    print('Ready')

                    capture = False
                    frame = thermal_camera.frame
                    vmin = min(frame)
                    vmax = max(frame)
                    img   = Image.new('RGB', (32, 24), 'black')
                
                    for y in range(24):
                        for x in range(32):
                            val = frame[32 * (23-y) + x]
                            rgb = thermal_camera.temperature_to_color(val, vmin, vmax)
                            img.putpixel((x, y), rgb)
                    
                    #img = img.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
                    img = img.resize((600, 448), Image.BICUBIC)
                    inky.set_image(img, saturation=0.5)
                    inky.show()

                    print('Done')

    except:
        print('Error')
    finally:
        thermal_camera.stop_recording()

