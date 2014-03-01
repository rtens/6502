import assembler, controller, sys, os, plugins

class Debugger(controller.Controller):

    break_line = None

    def exec(self, op_code):
        line = self.assembler.lines[self.pc - 1]

        if self.break_line == None or self.break_line == line:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(str(line + 1) + ': ' + self.program_lines[line])
            print("%02x"%self.pc + ': ' + ' '.join(['%02x'%i for i in self.mem[self.pc - 1:self.pc + 3]]) + ' ...')
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
                print('%04x'%i + ': ' + ' '.join(['%02x'%i for i in self.mem[i:i + 16]]))

            i = input('\n\n\n\nContinue?')
            self.break_line = int(i) - 1 if len(i) > 0 else None

        super().exec(op_code)

    def debug(self, program):
        self.program_lines = program.split('\n')
        self.assembler = assembler.Assembler()

        self.run(self.assembler.assemble(program))


if __name__ == '__main__':
    c = Debugger()


    d = plugins.BitmapDisplay(32, 32, 10)
    d.register(c, 0x0200)

    c.debug(open(sys.argv[1], 'r').read())