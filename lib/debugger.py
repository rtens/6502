import threading
import time
import os
import msvcrt

from lib import assembler, controller


class Debugger(controller.Controller):
    def __init__(self, mem_size=0xFFFF, pc=0x0600, stack_top=0x0100):
        super().__init__(mem_size, pc, stack_top)
        self.break_line = None

        self.running = True
        self.thread = threading.Thread(target=self.keep_running)
        self.thread.start()

        self.timer = time.time()
        self.instruction_count = 0

    def keep_running(self):
        while self.running:
            while self.break_line != -1:
                time.sleep(0.1)

            frequency = self.instruction_count / (time.time() - self.timer)
            self.timer = time.time()
            self.instruction_count = 0

            os.system('cls' if os.name == 'nt' else 'clear')
            print('Running with %.2f Hz' % frequency)
            print('(hit any key to break)')
            time.sleep(1)

            if msvcrt.kbhit():
                self.break_line = None


    def exec(self, op_code):
        self.instruction_count += 1
        line = self.assembler.lines[self.pc - 1]

        if self.break_line is None or self.break_line == line:
            self.print_info()
            i = input('\n\n\n\nContinue (to line)? ')
            self.break_line = int(i) - 1 if len(i) > 0 else None

        try:
            super().exec(op_code)
        except Exception as e:
            self.print_info()
            self.running = False
            raise e

    def print_info(self):
        os.system('cls' if os.name == 'nt' else 'clear')

        line = self.assembler.lines[self.pc - 1]
        print(str(line + 1) + ': ' + self.program_lines[line])

        print("%02x" % self.pc + ': ' + ' '.join(['%02x' % i for i in self.mem[self.pc - 1:self.pc + 3]]) + ' ...')

        print([
            "SP: %02x" % self.sp,
            "A: %02x" % self.a,
            "X: %02x" % self.x,
            "Y: %02x" % self.y])

        print({
            "N": 1 if self.n else 0,
            "V": 1 if self.v else 0,
            "B": 1 if self.b else 0,
            "D": 1 if self.d else 0,
            "I": 1 if self.i else 0,
            "Z": 1 if self.z else 0,
            "C": 1 if self.c else 0
        })

        print("")
        for i in range(0, 0x100, 16):
            print('%04x' % i + ': ' + ' '.join(['%02x' % i for i in self.mem[i:i + 16]]))

    def debug(self, program):
        self.program_lines = program.split('\n')
        self.assembler = assembler.Assembler()

        self.run(self.assembler.assemble(program))