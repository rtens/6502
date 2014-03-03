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
    ('bpl', ''): 0x10,
    ('bmi', ''): 0x30,
    ('bvc', ''): 0x50,
    ('bvs', ''): 0x70,
    ('bcc', ''): 0x90,
    ('bcs', ''): 0xB0,
    ('bne', ''): 0xD0,
    ('beq', ''): 0xF0,
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
    ('jmp', ''): 0x4C,
    ('jmp', 'in'): 0x6C,
    ('jsr', ''): 0x20,
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

    def set(self, reg, what):
        setattr(self.c, reg, self.result(what))

    def read_two_bytes(self, address):
        return self.join_bytes([self.c.mem_read(address), self.c.mem_read(address + 1)])

    def read_im(self):
        self.c.pc += 1
        return self.c.mem_read(self.c.pc - 1)

    def read_zp(self):
        return self.c.mem_read(self.read_im())

    def write_zp(self, what):
        self.c.mem_write(what, self.read_im())

    def read_zpx(self):
        return self.c.mem_read((self.read_im() + self.c.x) % 0xff)

    def write_zpx(self, what):
        self.c.mem_write(what, (self.read_im() + self.c.x) % 0xff)

    def read_double_arg(self):
        self.c.pc += 2
        return self.read_two_bytes(self.c.pc - 2)

    def read_ab(self):
        return self.c.mem_read(self.read_double_arg())

    def write_ab(self, what):
        self.c.mem_write(what, self.read_double_arg())

    def write_abx(self, what):
        self.c.mem_write(what, self.read_double_arg() + self.c.x)

    def write_aby(self, what):
        self.c.mem_write(what, self.read_double_arg() + self.c.y)

    def write_inx(self, what):
        self.c.mem_write(what, self.read_two_bytes(self.read_im() + self.c.x))

    def write_iny(self, what):
        self.c.mem_write(what, self.read_two_bytes(self.read_im()) + self.c.y)


class Operations:
    def __init__(self, controller):
        self.c = controller
        self.x = Addressing(controller)

    def branch(self, condition):
        if condition:
            self.c.pc += self.x.signed(self.x.read_im())
        self.c.pc += 1

    def adc(self, what):
        result = self.c.a + what + (1 if self.c.c else 0)
        self.c.c = result > 0xff
        self.x.set('a', result)

    # adc_im
    def op_69(self):
        self.adc(self.x.read_im())

    # adc_zp
    def op_65(self):
        self.adc(self.x.read_zp())

    def op_75(self):
        raise Exception("Not implemented") # adc_zpx

    # adc_ab
    def op_6d(self):
        self.adc(self.x.read_ab())

    def op_7d(self):
        raise Exception("Not implemented") # adc_abx

    def op_79(self):
        raise Exception("Not implemented") # adc_aby

    def op_61(self):
        raise Exception("Not implemented") # adc_inx

    def op_71(self):
        raise Exception("Not implemented") # adc_iny

    # and_im
    def op_29(self):
        self.c.a = self.c.a & self.x.read_im()

    def op_25(self):
        raise Exception("Not implemented") # and_zp

    def op_35(self):
        raise Exception("Not implemented") # and_zpx

    def op_2d(self):
        raise Exception("Not implemented") # and_ab

    def op_3d(self):
        raise Exception("Not implemented") # and_abx

    def op_39(self):
        raise Exception("Not implemented") # and_aby

    def op_21(self):
        raise Exception("Not implemented") # and_inx

    def op_31(self):
        raise Exception("Not implemented") # and_iny

    def op_0a(self):
        raise Exception("Not implemented") # asl

    def op_06(self):
        raise Exception("Not implemented") # asl_zp

    def op_16(self):
        raise Exception("Not implemented") # asl_zpx

    def op_0e(self):
        raise Exception("Not implemented") # asl_ab

    def op_1e(self):
        raise Exception("Not implemented") # asl_abx

    # bit_zp
    def op_24(self):
        val = self.x.read_zp()
        self.c.z = (val & self.c.a) == 0
        self.c.n = (val & 0x80) != 0
        self.c.v = (val & 0x40) != 0

    def op_2c(self):
        raise Exception("Not implemented") # bit_ab

    # bpl
    def op_10(self):
        if not self.c.n:
            self.c.pc += self.x.signed(self.x.read_im())
        self.c.pc += 1

    # bmi
    def op_30(self):
        if self.c.n:
            self.c.pc += self.x.signed(self.x.read_im())
        self.c.pc += 1

    def op_50(self):
        raise Exception("Not implemented") # bvc

    def op_70(self):
        raise Exception("Not implemented") # bvs

    # bcc
    def op_90(self):
        self.branch(not self.c.c)

    # bcs
    def op_b0(self):
        self.branch(self.c.c)

    # bne
    def op_d0(self):
        self.branch(not self.c.z)

    # beq
    def op_f0(self):
        self.branch(self.c.z)

    # cmp_im
    def op_c9(self):
        self.c.z = (self.c.a == self.x.read_im())

    # cmp_zp
    def op_c5(self):
        self.c.z = (self.c.a == self.x.read_zp())

    def op_d5(self):
        raise Exception("Not implemented") # cmp_zpx

    def op_cd(self):
        raise Exception("Not implemented") # cmp_ab

    def op_dd(self):
        raise Exception("Not implemented") # cmp_abx

    def op_d9(self):
        raise Exception("Not implemented") # cmp_aby

    def op_c1(self):
        raise Exception("Not implemented") # cmp_inx

    def op_d1(self):
        raise Exception("Not implemented") # cmp_iny

    # cpx_im
    def op_e0(self):
        self.c.z = (self.c.x == self.x.read_im())

    # cpx_zp
    def op_e4(self):
        self.c.z = (self.c.x == self.x.read_zp())

    def op_ec(self):
        raise Exception("Not implemented") # cpx_ab

    # cpy_im
    def op_c0(self):
        self.c.z = (self.c.y == self.x.read_im())

    # cpy_zp
    def op_c4(self):
        self.c.y = (self.c.y == self.x.read_zp())

    def op_cc(self):
        raise Exception("Not implemented") # cpy_ab

    # dec_zp
    def op_c6(self):
        address = self.x.read_im()
        self.c.mem_write(self.c.mem_read(address) - 1, address)

    def op_d6(self):
        raise Exception("Not implemented") # dec_zpx

    def op_ce(self):
        raise Exception("Not implemented") # dec_ab

    def op_de(self):
        raise Exception("Not implemented") # dec_abx

    def op_49(self):
        raise Exception("Not implemented") # eor_im

    def op_45(self):
        raise Exception("Not implemented") # eor_zp

    def op_55(self):
        raise Exception("Not implemented") # eor_zpx

    def op_4d(self):
        raise Exception("Not implemented") # eor_ab

    def op_5d(self):
        raise Exception("Not implemented") # eor_abx

    def op_59(self):
        raise Exception("Not implemented") # eor_aby

    def op_41(self):
        raise Exception("Not implemented") # eor_inx

    def op_51(self):
        raise Exception("Not implemented") # eor_iny

    # clc
    def op_18(self):
        self.c.c = False

    # sec
    def op_38(self):
        self.c.c = True

    def op_58(self):
        raise Exception("Not implemented") # cli

    def op_78(self):
        raise Exception("Not implemented") # sei

    def op_b8(self):
        raise Exception("Not implemented") # clv

    def op_d8(self):
        raise Exception("Not implemented") # cld

    def op_f8(self):
        raise Exception("Not implemented") # sed

    # inc_zp
    def op_e6(self):
        address = self.x.read_im()
        self.c.mem_write(self.x.result(self.c.mem_read(address) + 1), address)

    def op_f6(self):
        raise Exception("Not implemented") # inc_zpx

    def op_ee(self):
        raise Exception("Not implemented") # inc_ab

    def op_fe(self):
        raise Exception("Not implemented") # inc_abx

    # jmp
    def op_4c(self):
        self.c.pc = self.x.read_double_arg()

    def op_6c(self):
        raise Exception("Not implemented") # jmp_in

    # jsr
    def op_20(self):
        pc = self.x.split_bytes(self.c.pc + 2)
        self.x.push(pc[1])
        self.x.push(pc[0])
        self.c.pc = self.x.read_double_arg()

    # lda_im
    def op_a9(self):
        self.c.a = self.x.read_im()

    # lda_zp
    def op_a5(self):
        self.c.a = self.x.read_zp()

    # lda_zpx
    def op_b5(self):
        self.c.a = self.x.read_zpx()

    def op_ad(self):
        raise Exception("Not implemented") # lda_ab

    def op_bd(self):
        raise Exception("Not implemented") # lda_abx

    def op_b9(self):
        raise Exception("Not implemented") # lda_aby

    def op_a1(self):
        raise Exception("Not implemented") # lda_inx

    def op_b1(self):
        raise Exception("Not implemented") # lda_iny

    # ldx_im
    def op_a2(self):
        self.c.x = self.x.read_im()

    # ldx_zp
    def op_a6(self):
        self.c.x = self.x.read_zp()

    def op_b6(self):
        raise Exception("Not implemented") # ldx_zpy

    def op_ae(self):
        raise Exception("Not implemented") # ldx_ab

    def op_be(self):
        raise Exception("Not implemented") # ldx_aby

    # ldy_im
    def op_a0(self):
        self.c.y = self.x.read_im()

    # ldy_zp
    def op_a4(self):
        self.c.y = self.x.read_zp()

    def op_b4(self):
        raise Exception("Not implemented") # ldy_zpx

    def op_ac(self):
        raise Exception("Not implemented") # ldy_ab

    def op_bc(self):
        raise Exception("Not implemented") # ldy_abx

    # lsr
    def op_4a(self):
        self.c.c = self.c.a & 1 == 1
        self.c.a = self.c.a >> 1

    def op_46(self):
        raise Exception("Not implemented") # lsr_zp

    def op_56(self):
        raise Exception("Not implemented") # lsr_zpx

    def op_4e(self):
        raise Exception("Not implemented") # lsr_ab

    def op_5e(self):
        raise Exception("Not implemented") # lsr_abx

    # nop
    def op_ea(self):
        time.sleep(0.01)

    def op_09(self):
        raise Exception("Not implemented") # ora_im

    def op_05(self):
        raise Exception("Not implemented") # ora_zp

    def op_15(self):
        raise Exception("Not implemented") # ora_zpx

    def op_0d(self):
        raise Exception("Not implemented") # ora_ab

    def op_1d(self):
        raise Exception("Not implemented") # ora_abx

    def op_19(self):
        raise Exception("Not implemented") # ora_aby

    def op_01(self):
        raise Exception("Not implemented") # ora_inx

    def op_11(self):
        raise Exception("Not implemented") # ora_iny

    # tax
    def op_aa(self):
        self.c.x = self.c.a

    # txa
    def op_8a(self):
        self.c.a = self.c.x

    # dex
    def op_ca(self):
        self.c.x -= 1
        self.c.n = self.c.x < 0
        self.c.x &= 0xff
        self.c.z = self.c.x == 0

    # inx
    def op_e8(self):
        self.c.x += 1

    def op_a8(self):
        raise Exception("Not implemented") # tay

    # tya
    def op_98(self):
        self.c.a = self.c.y

    def op_88(self):
        raise Exception("Not implemented") # dey

    # iny
    def op_c8(self):
        self.x.set('y', self.c.y + 1)

    def op_2a(self):
        raise Exception("Not implemented") # rol

    def op_26(self):
        raise Exception("Not implemented") # rol_zp

    def op_36(self):
        raise Exception("Not implemented") # rol_zpx

    def op_2e(self):
        raise Exception("Not implemented") # rol_ab

    def op_3e(self):
        raise Exception("Not implemented") # rol_abx

    def op_6a(self):
        raise Exception("Not implemented") # ror

    def op_66(self):
        raise Exception("Not implemented") # ror_zp

    def op_76(self):
        raise Exception("Not implemented") # ror_zpx

    def op_6e(self):
        raise Exception("Not implemented") # ror_ab

    def op_7e(self):
        raise Exception("Not implemented") # ror_abx

    def op_40(self):
        raise Exception("Not implemented") # rti

    # rts
    def op_60(self):
        self.c.pc = self.x.read_two_bytes(self.c.stack_top + self.c.sp + 1)
        self.x.pull()
        self.x.pull()

    def sbc(self, what):
        result = self.c.a - what - (0 if self.c.c else 1)
        self.c.c = result >= 0
        self.x.set('a', result)

    # sbc_im
    def op_e9(self):
        self.sbc(self.x.read_im())

    # sbc_zp
    def op_e5(self):
        self.sbc(self.x.read_zp())

    def op_f5(self):
        raise Exception("Not implemented") # sbc_zpx

    # sbc_ab
    def op_ed(self):
        self.sbc(self.x.read_ab())

    def op_fd(self):
        raise Exception("Not implemented") # sbc_abx

    def op_f9(self):
        raise Exception("Not implemented") # sbc_aby

    def op_e1(self):
        raise Exception("Not implemented") # sbc_inx

    def op_f1(self):
        raise Exception("Not implemented") # sbc_iny

    # sta_zp
    def op_85(self):
        self.x.write_zp(self.c.a)

    # sta_zpx
    def op_95(self):
        self.x.write_zpx(self.c.a)

    # sta_ab
    def op_8d(self):
        self.x.write_ab(self.c.a)

    # sta_abx
    def op_9d(self):
        self.x.write_abx(self.c.a)

    # sta_aby
    def op_99(self):
        self.x.write_aby(self.c.a)

    # sta_inx
    def op_81(self):
        self.x.write_inx(self.c.a)

    # sta_iny
    def op_91(self):
        self.x.write_iny(self.c.a)

    def op_9a(self):
        raise Exception("Not implemented") # txs

    def op_ba(self):
        raise Exception("Not implemented") # tsx

    # pha
    def op_48(self):
        self.x.push(self.c.a)

    # pla
    def op_68(self):
        self.c.a = self.x.pull()

    def op_08(self):
        raise Exception("Not implemented") # php

    def op_28(self):
        raise Exception("Not implemented") # plp

    # stx_zp
    def op_86(self):
        self.x.write_zp(self.c.x)

    def op_96(self):
        raise Exception("Not implemented") # stx

    # stx_ab
    def op_8e(self):
        self.x.write_ab(self.c.x)

    # sty_zp
    def op_84(self):
        self.x.write_zp(self.c.y)

    def op_94(self):
        raise Exception("Not implemented") # sty_zpx

    def op_8c(self):
        raise Exception("Not implemented") # sty_ab
