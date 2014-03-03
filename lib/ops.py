import inspect
import time

op_codes = {
    ('adc', 'im'): 0x69,
    ('adc', 'zp'): 0x65,
    ('adc', 'zpx'): 0x75,
    ('adc', 'ab'): 0x6D,
    ('adc', 'abx'): 0x7D,
    ('adc', 'aby'): 0x79,
    ('adc', 'inx'): 0x61,
    ('adc', 'iny'): 0x71,
    ('and', 'im'): 0x29,
    ('and', 'zp'): 0x25,
    ('and', 'zpx'): 0x35,
    ('and', 'ab'): 0x2D,
    ('and', 'abx'): 0x3D,
    ('and', 'aby'): 0x39,
    ('and', 'inx'): 0x21,
    ('and', 'iny'): 0x31,
    ('asl', 'a'): 0x0A,
    ('asl', 'zp'): 0x06,
    ('asl', 'zpx'): 0x16,
    ('asl', 'ab'): 0x0E,
    ('asl', 'abx'): 0x1E,
    ('bit', 'zp'): 0x24,
    ('bit', 'ab'): 0x2C,
    ('bpl', 'im'): 0x10,
    ('bmi', 'im'): 0x30,
    ('bvc', 'im'): 0x50,
    ('bvs', 'im'): 0x70,
    ('bcc', 'im'): 0x90,
    ('bcs', 'im'): 0xB0,
    ('bne', 'im'): 0xD0,
    ('beq', 'im'): 0xF0,
    ('brk', None): 0x00,
    ('cmp', 'im'): 0xC9,
    ('cmp', 'zp'): 0xC5,
    ('cmp', 'zpx'): 0xD5,
    ('cmp', 'ab'): 0xCD,
    ('cmp', 'abx'): 0xDD,
    ('cmp', 'aby'): 0xD9,
    ('cmp', 'inx'): 0xC1,
    ('cmp', 'iny'): 0xD1,
    ('cpx', 'im'): 0xE0,
    ('cpx', 'zp'): 0xE4,
    ('cpx', 'ab'): 0xEC,
    ('cpy', 'im'): 0xC0,
    ('cpy', 'zp'): 0xC4,
    ('cpy', 'ab'): 0xCC,
    ('dec', 'zp'): 0xC6,
    ('dec', 'zpx'): 0xD6,
    ('dec', 'ab'): 0xCE,
    ('dec', 'abx'): 0xDE,
    ('eor', 'im'): 0x49,
    ('eor', 'zp'): 0x45,
    ('eor', 'zpx'): 0x55,
    ('eor', 'ab'): 0x4D,
    ('eor', 'abx'): 0x5D,
    ('eor', 'aby'): 0x59,
    ('eor', 'inx'): 0x41,
    ('eor', 'iny'): 0x51,
    ('clc', None): 0x18,
    ('sec', None): 0x38,
    ('cli', None): 0x58,
    ('sei', None): 0x78,
    ('clv', None): 0xB8,
    ('cld', None): 0xD8,
    ('sed', None): 0xF8,
    ('inc', 'zp'): 0xE6,
    ('inc', 'zpx'): 0xF6,
    ('inc', 'ab'): 0xEE,
    ('inc', 'abx'): 0xFE,
    ('jmp', 'ab'): 0x4C,
    ('jmp', 'in'): 0x6C,
    ('jsr', 'ab'): 0x20,
    ('lda', 'im'): 0xA9,
    ('lda', 'zp'): 0xA5,
    ('lda', 'zpx'): 0xB5,
    ('lda', 'ab'): 0xAD,
    ('lda', 'abx'): 0xBD,
    ('lda', 'aby'): 0xB9,
    ('lda', 'inx'): 0xA1,
    ('lda', 'iny'): 0xB1,
    ('ldx', 'im'): 0xA2,
    ('ldx', 'zp'): 0xA6,
    ('ldx', 'zpy'): 0xB6,
    ('ldx', 'ab'): 0xAE,
    ('ldx', 'aby'): 0xBE,
    ('ldy', 'im'): 0xA0,
    ('ldy', 'zp'): 0xA4,
    ('ldy', 'zpx'): 0xB4,
    ('ldy', 'ab'): 0xAC,
    ('ldy', 'abx'): 0xBC,
    ('lsr', 'a'): 0x4A,
    ('lsr', 'zp'): 0x46,
    ('lsr', 'zpx'): 0x56,
    ('lsr', 'ab'): 0x4E,
    ('lsr', 'abx'): 0x5E,
    ('nop', None): 0xEA,
    ('ora', 'im'): 0x09,
    ('ora', 'zp'): 0x05,
    ('ora', 'zpx'): 0x15,
    ('ora', 'ab'): 0x0D,
    ('ora', 'abx'): 0x1D,
    ('ora', 'aby'): 0x19,
    ('ora', 'inx'): 0x01,
    ('ora', 'iny'): 0x11,
    ('tax', None): 0xAA,
    ('txa', None): 0x8A,
    ('dex', None): 0xCA,
    ('inx', None): 0xE8,
    ('tay', None): 0xA8,
    ('tya', None): 0x98,
    ('dey', None): 0x88,
    ('iny', None): 0xC8,
    ('rol', 'a'): 0x2A,
    ('rol', 'zp'): 0x26,
    ('rol', 'zpx'): 0x36,
    ('rol', 'ab'): 0x2E,
    ('rol', 'abx'): 0x3E,
    ('ror', 'a'): 0x6A,
    ('ror', 'zp'): 0x66,
    ('ror', 'zpx'): 0x76,
    ('ror', 'ab'): 0x6E,
    ('ror', 'abx'): 0x7E,
    ('rti', None): 0x40,
    ('rts', None): 0x60,
    ('sbc', 'im'): 0xE9,
    ('sbc', 'zp'): 0xE5,
    ('sbc', 'zpx'): 0xF5,
    ('sbc', 'ab'): 0xED,
    ('sbc', 'abx'): 0xFD,
    ('sbc', 'aby'): 0xF9,
    ('sbc', 'inx'): 0xE1,
    ('sbc', 'iny'): 0xF1,
    ('sta', 'zp'): 0x85,
    ('sta', 'zpx'): 0x95,
    ('sta', 'ab'): 0x8D,
    ('sta', 'abx'): 0x9D,
    ('sta', 'aby'): 0x99,
    ('sta', 'inx'): 0x81,
    ('sta', 'iny'): 0x91,
    ('txs', None): 0x9A,
    ('tsx', None): 0xBA,
    ('pha', None): 0x48,
    ('pla', None): 0x68,
    ('php', None): 0x08,
    ('plp', None): 0x28,
    ('stx', 'zp'): 0x86,
    ('stx', 'zpy'): 0x96,
    ('stx', 'ab'): 0x8E,
    ('sty', 'zp'): 0x84,
    ('sty', 'zpx'): 0x94,
    ('sty', 'ab'): 0x8C,
}

instructions = dict([(op_codes[i], i) for i in op_codes])
mnemonics = [i for i, a in op_codes if a is None]


class Addressing:
    def __init__(self, controller):
        self.c = controller

    @staticmethod
    def split_bytes(value):
        return [value % 0x100, int(value / 0x100)]

    @staticmethod
    def join_bytes(two_bytes):
        return two_bytes[0] + two_bytes[1] * 0x100

    @staticmethod
    def signed(number):
        return number if number < 0x80 else number - 0xff - 1

    @staticmethod
    def bcd(number):
        return number if number >= 0 else 0xff - number + 1

    def push(self, what):
        self.c.mem_write(what, self.c.stack_top + self.c.sp)
        self.c.sp -= 1

    def pull(self):
        self.c.sp += 1
        return self.c.mem_read(self.c.stack_top + self.c.sp)

    def result(self, what):
        self.c.v = what >= 0x80
        what = self.bcd(what % 0x100)
        self.c.z = what == 0
        self.c.n = what > 0x80
        return what

    def read_two_bytes(self, address):
        return self.join_bytes([self.c.mem_read(address), self.c.mem_read(address + 1)])

    def read_im(self):
        self.c.pc += 1
        return self.c.mem_read(self.c.pc - 1)

    def read_double_im(self):
        self.c.pc += 2
        return self.read_two_bytes(self.c.pc - 2)

    def read_zp(self):
        return self.c.mem_read(self.read_im())

    def write_zp(self, what):
        self.c.mem_write(what, self.read_im())

    def read_zpx(self):
        return self.c.mem_read((self.read_im() + self.c.x) % 0xff)

    def write_zpx(self, what):
        self.c.mem_write(what, (self.read_im() + self.c.x) % 0xff)

    def read_ab(self):
        return self.c.mem_read(self.read_double_im())

    def write_ab(self, what):
        self.c.mem_write(what, self.read_double_im())

    def write_abx(self, what):
        self.c.mem_write(what, self.read_double_im() + self.c.x)

    def write_aby(self, what):
        self.c.mem_write(what, self.read_double_im() + self.c.y)

    def write_inx(self, what):
        self.c.mem_write(what, self.read_two_bytes(self.read_im() + self.c.x))

    def write_iny(self, what):
        self.c.mem_write(what, self.read_two_bytes(self.read_im()) + self.c.y)


class Operations:
    def __init__(self, controller):
        self.c = controller
        self.x = Addressing(controller)

    def exec(self, op_code):
        inst, mode = instructions[op_code]
        inst_method = getattr(self, 'inst_' + inst)
        args = inspect.getargspec(inst_method).args

        if mode is None or len(args) == 1:
            result = inst_method()
        else:
            arg = getattr(self.x, 'read_' + mode)()
            result = inst_method(arg)

        if result is not None:
            getattr(self.x, 'write_' + mode)(result)

    def inst_adc(self, arg):
        result = self.c.a + arg + (1 if self.c.c else 0)
        self.c.c = result > 0xff
        self.c.a = self.x.result(result)

    def inst_and(self, arg):
        self.c.a = self.c.a & arg

    def inst_asl(self):
        raise Exception('Not implemented')

    def branch(self, condition):
        if condition:
            self.c.pc += self.x.signed(self.x.read_im())
        self.c.pc += 1

    def inst_bcc(self):
        self.branch(not self.c.c)

    def inst_bcs(self):
        self.branch(self.c.c)

    def inst_beq(self):
        self.branch(self.c.z)

    def inst_bit(self, arg):
        self.c.z = (arg & self.c.a) == 0
        self.c.n = (arg & 0x80) != 0
        self.c.v = (arg & 0x40) != 0

    def inst_bmi(self):
        self.branch(self.c.n)

    def inst_bne(self):
        self.branch(not self.c.z)

    def inst_bpl(self):
        self.branch(not self.c.n)

    def inst_brk(self):
        pass

    def inst_bvc(self):
        raise Exception('Not implemented')

    def inst_bvs(self):
        raise Exception('Not implemented')

    def inst_clc(self):
        self.c.c = False

    def inst_cld(self):
        raise Exception('Not implemented')

    def inst_cli(self):
        raise Exception('Not implemented')

    def inst_clv(self):
        raise Exception('Not implemented')

    def inst_cmp(self, arg):
        self.c.z = self.c.a == arg

    def inst_cpx(self, arg):
        self.c.z = self.c.x == arg

    def inst_cpy(self):
        raise Exception('Not implemented')

    def inst_dec(self, arg):
        self.c.pc -= 1
        return self.x.result(arg - 1)

    def inst_dex(self):
        self.c.x = self.x.result(self.c.x - 1)

    def inst_dey(self):
        raise Exception('Not implemented')

    def inst_eor(self):
        raise Exception('Not implemented')

    def inst_inc(self, arg):
        self.c.pc -= 1
        return self.x.result(arg + 1)

    def inst_inx(self):
        self.c.x = self.x.result(self.c.x + 1)

    def inst_iny(self):
        self.c.y = self.x.result(self.c.y + 1)

    def inst_jmp(self):
        self.c.pc = self.x.read_double_im()

    def inst_jsr(self):
        pc = self.x.split_bytes(self.c.pc + 2)
        self.x.push(pc[1])
        self.x.push(pc[0])
        self.c.pc = self.x.read_double_im()

    def inst_lda(self, arg):
        self.c.a = arg

    def inst_ldx(self, arg):
        self.c.x = arg

    def inst_ldy(self, arg):
        self.c.y = arg

    def inst_lsr(self):
        self.c.c = self.c.a & 1 == 1
        self.c.a = self.c.a >> 1

    def inst_nop(self):
        time.sleep(0.01)

    def inst_ora(self):
        raise Exception('Not implemented')

    def inst_pha(self):
        self.x.push(self.c.a)

    def inst_php(self):
        raise Exception('Not implemented')

    def inst_pla(self):
        self.c.a = self.x.pull()

    def inst_plp(self):
        raise Exception('Not implemented')

    def inst_rol(self):
        raise Exception('Not implemented')

    def inst_ror(self):
        raise Exception('Not implemented')

    def inst_rti(self):
        raise Exception('Not implemented')

    def inst_rts(self):
        self.c.pc = self.x.read_two_bytes(self.c.stack_top + self.c.sp + 1)
        self.x.pull()
        self.x.pull()

    def inst_sbc(self, arg):
        result = self.c.a - arg - (0 if self.c.c else 1)
        self.c.c = result >= 0
        self.c.a = self.x.result(result)

    def inst_sec(self):
        self.c.c = True

    def inst_sed(self):
        raise Exception('Not implemented')

    def inst_sei(self):
        raise Exception('Not implemented')

    def inst_sta(self):
        return self.c.a

    def inst_stx(self):
        return self.c.x

    def inst_sty(self):
        return self.c.y

    def inst_tax(self):
        self.c.x = self.c.a

    def inst_tay(self):
        raise Exception('Not implemented')

    def inst_tsx(self):
        raise Exception('Not implemented')

    def inst_txa(self):
        self.c.a = self.c.x

    def inst_txs(self):
        raise Exception('Not implemented')

    def inst_tya(self):
        self.c.a = self.c.y

    def adc(self, what):
        result = self.c.a + what + (1 if self.c.c else 0)
        self.c.c = result > 0xff
        self.c.a = self.x.result(result)