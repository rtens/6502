import threading
import tkinter as tk
import random
import time


class RandomNumberGenerator:

    def register(self, controller, address):
        controller.vmem[address] = self

    def read(self, where):
        return random.randint(0, 0xff)

class Out:

    def register(self, controller, where):
        controller.vmem[where] = self

    def read(self, where):
        return 0

    def write(self, what, where):
        print(what)

class BitmapDisplay:

    def __init__(self, width, height, pixel_size = 10):
        self.start_address = 0
        self.pixel_size = pixel_size
        self.width = width
        self.height = height
        self.last_key = 0

        self.buffer = []
        self.running = True
        self.thread = threading.Thread(target=self.update)
        self.thread.start()

        self.colors = [
            "black",
            "white",
            "red",
            "cyan",
            "purple",
            "green",
            "blue",
            "yellow",
            "orange",
            "brown",
            "indian red",
            "dark gray",
            "gray",
            "light green",
            "light blue",
            "light gray"
        ]

    def update(self):
        top = tk.Tk()
        top.protocol("WM_DELETE_WINDOW", self.stop)
        top.bind_all('<Key>', self.key_pressed)
        canvas = tk.Canvas(top, width=self.width * self.pixel_size, height=self.height * self.pixel_size, background="black")
        canvas.pack()

        while self.running:
            while len(self.buffer) != 0:
                what, where = self.buffer.pop()

                offset = where - self.start_address
                x = offset % self.width
                y = int((offset - x) / self.width)
                xp = x * self.pixel_size
                yp = y * self.pixel_size

                canvas.create_rectangle(xp, yp, xp + self.pixel_size, yp + self.pixel_size,
                                             fill=self.colors[what % 0xf], width=0)

            top.update()
            time.sleep(0.01)

    def stop(self):
        self.running = False

    def key_pressed(self, e):
        self.last_key = e.keycode

    def register(self, controller, start_address):
        self.start_address = start_address
        for a in range(start_address, start_address + self.width * self.height):
            controller.vmem[a] = self
        controller.vmem[0xff] = self

    def write(self, what, where):
        self.buffer.insert(0, (what, where))

    def read(self, where):
        return self.last_key