import tkinter as tk
import random

class RandomNumberGenerator:

    def register(self, controller, address):
        controller.vmem[address] = self

    def read(self, where):
        return random.randint(0, 0xff)

class BitmapDisplay:

    def __init__(self, width, height, pixel_size = 10):
        self.start_address = 0
        self.pixel_size = pixel_size
        self.width = width
        self.height = height
        self.last_key = 0

        self.top = tk.Tk()
        self.top.bind_all('<Key>', self.key_pressed)
        self.canvas = tk.Canvas(self.top, width=width * pixel_size, height=height * pixel_size, background="black")
        self.canvas.pack()

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

    def key_pressed(self, e):
        self.last_key = e.keycode

    def register(self, controller, start_address):
        self.start_address = start_address
        for a in range(start_address, start_address + self.width * self.height):
            controller.vmem[a] = self
        controller.vmem[0xff] = self

    def stay(self):
        self.top.mainloop()

    def write(self, what, where):
        offset = where - self.start_address
        x = offset % self.width
        y = int((offset - x) / self.width)
        xp = x * self.pixel_size
        yp = y * self.pixel_size

        self.canvas.create_rectangle(xp, yp, xp + self.pixel_size, yp + self.pixel_size,
                                     fill=self.colors[what % 0xf], width=0)
        self.top.update()

    def read(self, where):
        return self.last_key