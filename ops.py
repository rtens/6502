import time

mnemonics = [
    'brk',
    'clc',
    'sec',
    'cli',
    'sei',
    'clv',
    'cld',
    'sed',
    'tax',
    'txa',
    'dex',
    'inx',
    'tay',
    'tya',
    'dey',
    'iny',
    'txs',
    'tsx',
    'pha',
    'pla',
    'php',
    'plp',
    'rts',
    'lsr',
    'asl',
    'nop',
]

op_codes = {
    'adc_im': 0x69,
    'adc_zp': 0x65,
    'adc_zpx': 0x75,
    'adc_ab': 0x6D,
    'adc_abx': 0x7D,
    'adc_aby': 0x79,
    'adc_inx': 0x61,
    'adc_iny': 0x71,
    'and_im': 0x29,
    'and_zp': 0x25,
    'and_zpx': 0x35,
    'and_ab': 0x2D,
    'and_abx': 0x3D,
    'and_aby': 0x39,
    'and_inx': 0x21,
    'and_iny': 0x31,
    'asl': 0x0A,
    'asl_zp': 0x06,
    'asl_zpx': 0x16,
    'asl_ab': 0x0E,
    'asl_abx': 0x1E,
    'bit_zp': 0x24,
    'bit_ab': 0x2C,
    'bpl': 0x10,
    'bmi': 0x30,
    'bvc': 0x50,
    'bvs': 0x70,
    'bcc': 0x90,
    'bcs': 0xB0,
    'bne': 0xD0,
    'beq': 0xF0,
    'brk': 0x00,
    'cmp_im': 0xC9,
    'cmp_zp': 0xC5,
    'cmp_zpx': 0xD5,
    'cmp_ab': 0xCD,
    'cmp_abx': 0xDD,
    'cmp_aby': 0xD9,
    'cmp_inx': 0xC1,
    'cmp_iny': 0xD1,
    'cpx_im': 0xE0,
    'cpx_zp': 0xE4,
    'cpx_ab': 0xEC,
    'cpy_im': 0xC0,
    'cpy_zp': 0xC4,
    'cpy_ab': 0xCC,
    'dec_zp': 0xC6,
    'dec_zpx': 0xD6,
    'dec_ab': 0xCE,
    'dec_abx': 0xDE,
    'eor_im': 0x49,
    'eor_zp': 0x45,
    'eor_zpx': 0x55,
    'eor_ab': 0x4D,
    'eor_abx': 0x5D,
    'eor_aby': 0x59,
    'eor_inx': 0x41,
    'eor_iny': 0x51,
    'clc': 0x18,
    'sec': 0x38,
    'cli': 0x58,
    'sei': 0x78,
    'clv': 0xB8,
    'cld': 0xD8,
    'sed': 0xF8,
    'inc_zp': 0xE6,
    'inc_zpx': 0xF6,
    'inc_ab': 0xEE,
    'inc_abx': 0xFE,
    'jmp': 0x4C,
    'jmp_in': 0x6C,
    'jsr': 0x20,
    'lda_im': 0xA9,
    'lda_zp': 0xA5,
    'lda_zpx': 0xB5,
    'lda_ab': 0xAD,
    'lda_abx': 0xBD,
    'lda_aby': 0xB9,
    'lda_inx': 0xA1,
    'lda_iny': 0xB1,
    'ldx_im': 0xA2,
    'ldx_zp': 0xA6,
    'ldx': 0xB6,
    'ldx_ab': 0xAE,
    'ldx_aby': 0xBE,
    'ldy_im': 0xA0,
    'ldy_zp': 0xA4,
    'ldy_zpx': 0xB4,
    'ldy_ab': 0xAC,
    'ldy_abx': 0xBC,
    'lsr': 0x4A,
    'lsr_zp': 0x46,
    'lsr_zpx': 0x56,
    'lsr_ab': 0x4E,
    'lsr_abx': 0x5E,
    'nop': 0xEA,
    'ora_im': 0x09,
    'ora_zp': 0x05,
    'ora_zpx': 0x15,
    'ora_ab': 0x0D,
    'ora_abx': 0x1D,
    'ora_aby': 0x19,
    'ora_inx': 0x01,
    'ora_iny': 0x11,
    'tax': 0xAA,
    'txa': 0x8A,
    'dex': 0xCA,
    'inx': 0xE8,
    'tay': 0xA8,
    'tya': 0x98,
    'dey': 0x88,
    'iny': 0xC8,
    'rol': 0x2A,
    'rol_zp': 0x26,
    'rol_zpx': 0x36,
    'rol_ab': 0x2E,
    'rol_abx': 0x3E,
    'ror': 0x6A,
    'ror_zp': 0x66,
    'ror_zpx': 0x76,
    'ror_ab': 0x6E,
    'ror_abx': 0x7E,
    'rti': 0x40,
    'rts': 0x60,
    'sbc_im': 0xE9,
    'sbc_zp': 0xE5,
    'sbc_zpx': 0xF5,
    'sbc_ab': 0xED,
    'sbc_abx': 0xFD,
    'sbc_aby': 0xF9,
    'sbc_inx': 0xE1,
    'sbc_iny': 0xF1,
    'sta_zp': 0x85,
    'sta_zpx': 0x95,
    'sta_ab': 0x8D,
    'sta_abx': 0x9D,
    'sta_aby': 0x99,
    'sta_inx': 0x81,
    'sta_iny': 0x91,
    'txs': 0x9A,
    'tsx': 0xBA,
    'pha': 0x48,
    'pla': 0x68,
    'php': 0x08,
    'plp': 0x28,
    'stx_zp': 0x86,
    'stx': 0x96,
    'stx_ab': 0x8E,
    'sty_zp': 0x84,
    'sty_zpx': 0x94,
    'sty_ab': 0x8C,
}


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
