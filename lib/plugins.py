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
    def __init__(self, width, height, pixel_size=10):
        self.start_address = 0
        self.flush_trigger = 0
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
        self.running = True
        self.thread = threading.Thread(target=self.update)

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

    def flush(self):
        while self.running and len(self.buffer) != 0:
            what, where = self.buffer.pop()
            self.canvas.itemconfig(self.pixels[where], fill=self.colors[what % 0x10])

        self.top.update()

    def stop(self):
        self.running = False
        self.top.destroy()

    def key_pressed(self, e):
        self.last_key = e.keycode

    def register(self, controller, start_address, key_reader=None, flush_trigger=None):
        self.start_address = start_address
        self.flush_trigger = flush_trigger

        for a in range(start_address, start_address + self.width * self.height):
            controller.vmem[a] = self
        if key_reader is not None:
            controller.vmem[key_reader] = self
        if flush_trigger is not None:
            controller.vmem[flush_trigger] = self

        for offset in range(0, self.width * self.height):
            x = offset % self.width
            y = int((offset - x) / self.width)
            xp = x * self.pixel_size
            yp = y * self.pixel_size

            pixel = self.canvas.create_rectangle(xp, yp, xp + self.pixel_size, yp + self.pixel_size,
                                                 fill='black', width=0)
            self.pixels[self.start_address + offset] = pixel

        self.thread.start()


    def write(self, what, where):
        if not self.running:
            return

        if where == self.flush_trigger:
            self.flush()
        else:
            self.buffer.insert(0, (what, where))

        if not self.flush_trigger and len(self.buffer) > self.width:
            self.flush()
            self.top.update()

    def read(self, where):
        return self.last_key