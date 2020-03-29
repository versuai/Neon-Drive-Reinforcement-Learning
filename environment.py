''' Modules for installation -> numpy, keyboard, cv2, mss. Use pip3 install 'module'.
'''
import torchvision.transforms as T
from PIL import Image
import numpy as np
import threading
import keyboard
import torch
import cv2
import time
import mss

# define the codec
fourcc = cv2.VideoWriter_fourcc('H','2','6','4')
# create the video write object
out = cv2.VideoWriter('output.mkv', fourcc, 60, (320, 180), True)

resize = T.Compose([T.ToPILImage(),
                    T.Resize(40, interpolation=Image.CUBIC),
                    T.ToTensor()])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def histogram(image):
    ''' Histogram generate function
    '''
    hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8],[0, 256, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist

class env():
    ''' Class for environment management
    '''
    def __init__(self, resolution):
        self.w, self.h = resolution
        self.movements = ["a","d","w"]
        self.epochs_divisor = 10
        self.multiplicator = 0

        img = cv2.imread('gameover.jpg')
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.hist_restart = histogram(img)

        imageCapture = threading.Thread(name = 'imageCapture', target = self.imageCapture)
        imageCapture.setDaemon(True)
        imageCapture.start()

    def imageCapture(self):
        monitor = {'left': 0, 'top': 0, 'width': self.w, 'height': self.h}
        start_recording = time.time()
        with mss.mss() as sct:
            while True:
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                rgb_frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
                self.rgb_frame = rgb_frame
                gray_frame = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                (_, bw_frame) = cv2.threshold(gray_frame, 128, 255, cv2.THRESH_BINARY)
                bw_frame = bw_frame[int(self.h/2):int(self.h-(self.h/5)), int(self.w/5):int(self.w-(self.w/5))]
                bw_frame = cv2.resize(bw_frame,(int(320),int(180))) 
                self.bw_frame = cv2.bitwise_not(bw_frame)
                cv2.imshow('frame', self.bw_frame)
                stop_recording = time.time() - start_recording
                if stop_recording > 1000:
                    out.release()
                else:
                    out.write(cv2.cvtColor(self.bw_frame, cv2.COLOR_GRAY2BGR))
                _ = cv2.waitKey(1)

    def reset(self):
        time.sleep(0.4)
        keyboard.send("enter")
        time.sleep(2)
        self.initial_time = time.time()

    def step(self, action):
        done = False
        keyboard.send(self.movements[action])
        time.sleep(0.3)
        hist = histogram(self.rgb_frame)
        comparation = cv2.compareHist(self.hist_restart, hist, cv2.HISTCMP_BHATTACHARYYA)
        if comparation > 0.15:
            self.multiplicator = time.time() - self.initial_time
            rew = int(4 * self.multiplicator)
        else:
            if(self.multiplicator >= self.epochs_divisor):
                self.epochs_divisor = self.epochs_divisor + 10
                done = True
            else:
                rew = -100
                self.reset()
        print(rew)
        return [], rew, done, []

    def get_screen(self):
        return resize(self.bw_frame).unsqueeze(0).to(device)