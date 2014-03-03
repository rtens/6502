import time
import ops


class Controller:
    def __init__(self, mem_size=0xFFFF, pc=0x0600, stack_top=0x0100):
        self.ops = ops.Operations(self)

        self.vmem = {}
        self.mem = [0 for i in range(0, mem_size)]

        self.stack_top = stack_top

        # Registers
        self.pc = pc # Programm Counter
        self.sp = 0xff # Stack Pointer
        self.a = 0 # Accumulator
        self.x = 0 # X
        self.y = 0 # Y

        # Flags
        self.n = False # Negative
        self.v = False # Overflow
        self.u = True # Unused
        self.b = False # Break
        self.d = False # Decimal Mode
        self.i = False # Interrupt Disable
        self.z = False # Zero
        self.c = False # Carry

    def load(self, words, address):
        for w in words:
            self.mem[address] = w
            address += 1

    def run(self, op_codes=None):
        if op_codes:
            self.load(op_codes, self.pc)

        while self.pc < len(self.mem):
            op_code = self.mem[self.pc]
            self.pc += 1

            if op_code == 0:
                break

            self.exec(op_code)

    def exec(self, op_code):
        self.ops.exec(op_code)

    def mem_write(self, what, where):
        if where in self.vmem:
            self.vmem[where].write(what, where)
        else:
            self.mem[where] = what

    def mem_read(self, where):
        if where in self.vmem:
            return self.vmem[where].read(where)
        else:
            return self.mem[where]
