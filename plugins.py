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
    def __init__(self):
        self.buffer = []
        threading.Thread(target=self.print).start()

    def register(self, controller, where):
        controller.vmem[where] = self

    def read(self, where):
        return 0

    def write(self, what, where):
        self.buffer.insert(0, what)

    def print(self):
        while True:
            while len(self.buffer) != 0:
                print(self.buffer.pop())
            time.sleep(0.01)


class BitmapDisplay:
    def __init__(self, width, height, pixel_size=10, triggered=False):
        self.start_address = 0
        self.pixel_size = pixel_size
        self.width = width
        self.height = height
        self.last_key = 0

        self.top = tk.Tk()
        self.top.protocol("WM_DELETE_WINDOW", self.stop)
        self.top.bind_all('<Key>', self.key_pressed)
        self.canvas = tk.Canvas(self.top, width=self.width * self.pixel_size, height=self.height * self.pixel_size,
                                background="black")
        self.canvas.pack()
        self.pixels = {}

        self.buffer = []
        self.running = not triggered
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
        while self.running:
            self.flush()
            time.sleep(0.01)

    def flush(self):
        start = time.time()
        size = len(self.buffer)
        while len(self.buffer) != 0:
            what, where = self.buffer.pop()
            self.canvas.itemconfig(self.pixels[where], fill=self.colors[what % 0x10])

        self.top.update()

    def stop(self):
        self.running = False

    def key_pressed(self, e):
        self.last_key = e.keycode

    def register(self, controller, start_address):
        self.start_address = start_address
        for a in range(start_address, start_address + self.width * self.height):
            controller.vmem[a] = self
        controller.vmem[0xff] = self
        if not self.running:
            controller.vmem[start_address - 1] = self

        for offset in range(0, self.width * self.height):
            x = offset % self.width
            y = int((offset - x) / self.width)
            xp = x * self.pixel_size
            yp = y * self.pixel_size

            pixel = self.canvas.create_rectangle(xp, yp, xp + self.pixel_size, yp + self.pixel_size,
                                                 fill='black', width=0)
            self.pixels[self.start_address + offset] = pixel


    def write(self, what, where):
        if where == self.start_address - 1:
            self.flush()
        else:
            self.buffer.insert(0, (what, where))

        if self.running and len(self.buffer) > self.width:
            self.flush()
            self.top.update()

    def read(self, where):
        return self.last_key