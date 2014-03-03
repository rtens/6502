import ops


class Assembler:

    def __init__(self):
        self.labels = {}
        self.relatives = []
        self.absolutes = []
        self.lines = {}

    def assemble(self, program, start_address = 0x0600):
        lexer = Lexer(program)
        dump = []
        while lexer.has_next():
            pc = start_address + len(dump)
            op = lexer.next()
            self.lines[pc] = lexer.line

            try:
                dump += self.get_op_codes(lexer, op, pc)
            except Exception:
                raise Exception('Error in line ' + str(lexer.line) + ' [' + op + ']')

        for pc in self.relatives:
            dump[pc - start_address] = self._signed(self.labels[dump[pc - start_address]] - pc - 1)
        for pc in self.absolutes:
            dump[pc - start_address] = self.labels[dump[pc - start_address]] % 0x100
            dump[pc - start_address + 1] = int(self.labels[dump[pc - start_address + 1]] / 0x100)
        return dump

    def get_op_codes(self, lexer, op, pc):
        if op[-1] == ':':
            self.labels[op[:-1]] = pc
            return []
        elif op in ops.mnemonics:
            return [ops.op_codes[(op, None)]]
        else:
            return self.op_with_arg(op, lexer.next(), pc)

    def op_with_arg(self, op, arg, pc):
        mode = None
        if arg[0] == '#':
            if arg[1] == '$':
                args = [int(arg[2:4], 16)]
            else:
                args = [int(arg[1:])]
            mode = 'im'
        elif arg[0] == "(":
            if 'x' in arg:
                mode = 'inx'
            elif 'y' in arg:
                mode = 'iny'
            else:
                mode += 'in'
            args = [int(arg[2:4], 16)]
        elif ',' in arg:
            if len(arg) == 5:
                mode = 'zp' + arg[-1]
                args = [int(arg[1:3], 16)]
            else:
                mode = 'ab' + arg[-1]
                args = [int(arg[3:5], 16), int(arg[1:3], 16)]
        elif arg[0] == '$':
            if len(arg) == 5:
                args = [int(arg[3:5], 16), int(arg[1:3], 16)]
                mode = 'ab'
            else:
                args = [int(arg[1:3], 16)]
                mode = 'zp'
        elif arg == 'a':
            args = []
            mode = 'a'
        else:
            mode = ''
            if op in ['jmp', 'jsr']:
                self.absolutes.append(pc + 1)
                args = [arg, arg]
            else:
                self.relatives.append(pc + 1)
                args = [arg]

        return [ops.op_codes[(op, mode)]] + args

    @staticmethod
    def _signed(a):
        return a if a > 0 else 0xff + a + 1


class Lexer:

    def __init__(self, program):
        self.program = program.strip().lower()
        self.position = 0
        self.line = 0
        self.buffer = None

    def has_next(self):
        if not self.buffer:
            self.buffer = self._parse_next_token()
        return not not self.buffer

    def next(self):
        if not self.buffer:
            self.buffer = self._parse_next_token()

        token = self.buffer
        self.buffer = None
        return token

    def _parse_next_token(self):
        white_space = ' \t\n'

        while self.position < len(self.program):
            c = self.program[self.position]
            if c == ';':
                self._until('\n')
                self.line += 1
            elif c not in white_space:
                return self._until(white_space)
            if c == "\n":
                self.line += 1
            self.position += 1

    def _until(self, chars):
        token = ''
        while self.position < len(self.program) and self.program[self.position] not in chars:
            token += self.program[self.position]
            self.position += 1
        return token