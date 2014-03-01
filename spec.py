import unittest
from controller import Controller
from assembler import Assembler


class ControllerTest(unittest.TestCase):
    def test_load_memory(self):
        c = Controller(4, 0)
        c.load([42, 27], 1)
        self.assertEqual(c.mem, [0, 42, 27, 0])

    def test_load_then_store(self):
        c = Controller(11, 2)
        c.run([0xa9, 42, 0x8d, 0x00, 0x00, 0x8d, 0x01, 0x00, 0x00])
        self.assertEqual(42, c.a)
        self.assertEqual(c.mem[0:2], [42, 42])

    def test_capture_writes(self):
        class Listener:
            def write(self, what, where):
                self.what = what
                self.where = where

            def read(self, where):
                self.where = where

        listener = Listener()

        c = Controller(5, 2)
        c.vmem[0x0200] = listener
        c.a = 42
        c.run([0x8d, 0x00, 0x02])

        self.assertEqual(0x0200, listener.where)
        self.assertEqual(42, listener.what)


class OperationsTest(unittest.TestCase):
    def x(self, program, data=0, stack=0):
        asm = Assembler().assemble(program, data + stack)
        c = Controller(len(asm) + data + stack, data + stack, data)
        c.sp = stack - 1
        c.run(asm)
        return c

    def test_lda_im(self):
        c = self.x('  LDA    #$1a')
        self.assertEqual(c.a, 26)

    def test_sta_ab(self):
        c = self.x('LDA #$1b STA $0002', 3)
        self.assertEqual(c.mem[0:3], [0, 0, 27])

    def test_tax(self):
        c = self.x('LDA #$1c TAX')
        self.assertEqual(28, c.x)

    def test_inx(self):
        c = self.x('LDX #$1b INX')
        self.assertEqual(28, c.x)

    def test_adc(self):
        c = self.x('LDA #$02 TAX INX ADC #$c4 BRK')
        self.assertEqual(c.x, 0x03)
        self.assertEqual(c.a, 0x02 + 0xc4)

    def test_bne_back(self):
        c = self.x('LDX #$08 decrement: DEX STX $0000 CPX #$03 BNE decrement STX $0001 BRK', 2)
        self.assertEqual(c.mem[2:],
                         [0xa2, 0x08, 0xca, 0x8e, 0x00, 0x00, 0xe0, 0x03, 0xd0, 0xf8, 0x8e, 0x01, 0x00, 0x00])
        self.assertEqual(c.x, 3)
        self.assertEqual(c.mem[:2], [3, 3])

    def test_bne_forward(self):
        c = self.x('LDA #$01 CMP #$02 BNE notequal STA $01 notequal: TAX', 2)
        self.assertEqual(c.mem[0:2], [0, 0])
        self.assertEqual(c.mem[2:], [0xa9, 0x01, 0xc9, 0x02, 0xd0, 0x02, 0x85, 0x01, 0xaa])
        self.assertEqual(c.a, 1)
        self.assertEqual(c.x, 1)

    def test_addressing_zero_page(self):
        c = self.x('LDA #$1b STA $01', 2)
        self.assertEqual(c.mem[0:2], [0, 27])

    def test_addressing_zero_page_x(self):
        c = self.x('LDX #$01 LDA #$1b STA $01,X INX STA $01,X DEX STA $ff,X', 4)
        self.assertEqual(c.mem[0:4], [0, 27, 27, 27])

    def test_absolute_x_and_y(self):
        c = self.x('LDX #$01 LDY #$02 LDA #$1b STA $0001,X STA $0001,Y', 4)
        self.assertEqual(c.mem[0:4], [0, 0, 27, 27])

    def test_indexed_indirect(self):
        c = self.x('LDX #$01 LDA #$01 STA $02 LDA #$00 STA $03 LDA #$1b STA ($01,X)', 4)
        self.assertEqual(c.mem[0:4], [0, 27, 0x01, 0x00])

    def test_indirect_indexed(self):
        c = self.x('LDY #$01 LDA #$01 STA $03 LDA #$00 STA $04 LDA #$1b STA ($03),Y', 5)
        self.assertEqual(c.mem[0:5], [0, 0, 27, 0x01, 0x00])

    def test_jmp(self):
        c = self.x('LDA #$1b JMP there STA $00 there: STA $01', 2)
        self.assertEqual(c.mem[0:2], [0, 27])

    def test_stack(self):
        c = self.x('LDA #$01 PHA LDA #$02 PHA LDA #$00 PLA TAX PLA PHA', 0, 3)
        self.assertEqual(c.mem[3:], [0xa9, 0x01, 0x48, 0xa9, 0x02, 0x48, 0xa9, 0x00, 0x68, 0xaa, 0x68, 0x48])
        self.assertEqual(c.a, 1)
        self.assertEqual(c.x, 2)
        self.assertEqual(c.sp, 0x01)

    def test_subroutine(self):
        c = self.x('JSR there INX BRK there: LDX #$01 RTS', 0, 2)
        self.assertEqual(c.mem[2:], [0x20, 0x07, 0x00, 0xe8, 0x00, 0xa2, 0x01, 0x60])
        self.assertEqual(c.x, 2)

    def test_comments(self):
        c = self.x("LDA #$01 ; end of line comment \n ; full line comment LDA #$02 \n STA $00", 1)
        self.assertEqual(c.mem[0], 1)

    def test_decimal_immediate(self):
        c = self.x('LDX #2 LDA #27')
        self.assertEqual(c.x, 2)
        self.assertEqual(c.a, 27)

    def test_lsr(self):
        c = self.x('LDA #$03 LSR')
        self.assertEqual(c.a, 1)
        self.assertEqual(c.c, True)

    def test_inc(self):
        c = self.x('LDA #27 STA $00 INC $00', 1)
        self.assertEqual(c.mem[0], 28)


class Py65Test(unittest.TestCase):

    # ADC Absolute

    def test_adc_bcd_off_absolute_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0x00
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def test_adc_bcd_off_absolute_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.c = True
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0x00
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)

    def test_adc_bcd_off_absolute_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0xFE
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def test_adc_bcd_off_absolute_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0xFF
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def test_adc_bcd_off_absolute_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.a = 0x01
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0x01
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_absolute_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.a = 0x01
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0xff
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def test_adc_bcd_off_absolute_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.a = 0x7f
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0x01
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def test_adc_bcd_off_absolute_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.a = 0x80
        # $0000 ADC $C000
        mpu.mem[0xC000] = 0xff
        mpu.run((0x6D, 0x00, 0xC0))

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_absolute_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        # $0000 ADC $C000
        mpu.run((0x6D, 0x00, 0xC0))
        mpu.mem[0xC000] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Zero Page

    def _test_adc_bcd_off_zp_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_zp_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.p |= mpu.CARRY
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_zp_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_zp_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_zp_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_zp_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0xff

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_zp_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_zp_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0xff

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_zp_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.a = 0x40
        mpu.p &= ~(mpu.OVERFLOW)
        # $0000 ADC $00B0
        mpu.run((0x65, 0xB0))
        mpu.mem[0x00B0] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Immediate

    def _test_adc_bcd_off_immediate_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0
        # $0000 ADC #$00
        mpu.run((0x69, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_immediate_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.p |= mpu.CARRY
        # $0000 ADC #$00
        mpu.run((0x69, 0x00))

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_immediate_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        # $0000 ADC #$FE
        mpu.run((0x69, 0xFE))

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_immediate_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        # $0000 ADC #$FF
        mpu.run((0x69, 0xFF))

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_immediate_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC #$01
        self._write(mpu.mem, 0x000, (0x69, 0x01))

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_immediate_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC #$FF
        self._write(mpu.mem, 0x000, (0x69, 0xff))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_immediate_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        # $0000 ADC #$01
        self._write(mpu.mem, 0x000, (0x69, 0x01))

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_immediate_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        # $0000 ADC #$FF
        self._write(mpu.mem, 0x000, (0x69, 0xff))

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_immediate_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.a = 0x40
        # $0000 ADC #$40
        mpu.run((0x69, 0x40))

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_on_immediate_79_plus_00_carry_set(self):
        mpu = Controller()
        mpu.p |= mpu.DECIMAL
        mpu.p |= mpu.CARRY
        mpu.a = 0x79
        # $0000 ADC #$00
        mpu.run((0x69, 0x00))

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)

    def _test_adc_bcd_on_immediate_6f_plus_00_carry_set(self):
        mpu = Controller()
        mpu.p |= mpu.DECIMAL
        mpu.p |= mpu.CARRY
        mpu.a = 0x6f
        # $0000 ADC #$00
        mpu.run((0x69, 0x00))

        self.assertEqual(0x76, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)

    def _test_adc_bcd_on_immediate_9c_plus_9d(self):
        mpu = Controller()
        mpu.p |= mpu.DECIMAL
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x9c
        # $0000 ADC #$9d
        # $0002 ADC #$9d
        mpu.run((0x69, 0x9d))
        self._write(mpu.mem, 0x0002, (0x69, 0x9d))

        self.assertEqual(0x9f, mpu.a)
        self.assertEqual(True, mpu.c)

        self.assertEqual(0x93, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    # ADC Absolute, X-Indexed

    def _test_adc_bcd_off_abs_x_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_abs_x_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_abs_x_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_abs_x_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.x = 0x03
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_abs_x_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_abs_x_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0xff

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_abs_x_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_abs_x_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0xff

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_abs_x_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        mpu.x = 0x03
        # $0000 ADC $C000,X
        mpu.run((0x7D, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.x] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Absolute, Y-Indexed

    def _test_adc_bcd_off_abs_y_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_abs_y_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.y = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_abs_y_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        mpu.y = 0x03
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_abs_y_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.y = 0x03
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_abs_y_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_abs_y_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_abs_y_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_abs_y_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0xFF

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_abs_y_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        mpu.y = 0x03
        # $0000 ADC $C000,Y
        mpu.run((0x79, 0x00, 0xC0))
        mpu.mem[0xC000 + mpu.y] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Zero Page, X-Indexed

    def _test_adc_bcd_off_zp_x_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_zp_x_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_zp_x_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_zp_x_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_zp_x_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_zp_x_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_zp_x_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_zp_x_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xff

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_zp_x_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        mpu.x = 0x03
        # $0000 ADC $0010,X
        mpu.run((0x75, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Indirect, Indexed (X)

    def _test_adc_bcd_off_ind_indexed_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_ind_indexed_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_ind_indexed_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_ind_indexed_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_ind_indexed_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_ind_indexed_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_ind_indexed_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_ind_indexed_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_ind_indexed_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        mpu.x = 0x03
        # $0000 ADC ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x61, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # ADC Indexed, Indirect (Y)

    def _test_adc_bcd_off_indexed_ind_carry_clear_in_accumulator_zeroes(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.z)

    def _test_adc_bcd_off_indexed_ind_carry_set_in_accumulator_zero(self):
        mpu = Controller()
        mpu.a = 0
        mpu.y = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertNotEqual(True, mpu.c)

    def _test_adc_bcd_off_indexed_ind_carry_clear_in_no_carry_clear_out(self):
        mpu = Controller()
        mpu.a = 0x01
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFE

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_indexed_ind_carry_clear_in_carry_set_out(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_adc_bcd_off_indexed_ind_overflow_clr_no_carry_01_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.y = 0x03
        # $0000 $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x01

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_indexed_ind_overflow_clr_no_carry_01_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x01
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.v)

    def _test_adc_bcd_off_indexed_ind_overflow_set_no_carry_7f_plus_01(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x7f
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x01

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_indexed_ind_overflow_set_no_carry_80_plus_ff(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.a = 0x80
        mpu.y = 0x03
        # $0000 $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x7f, mpu.a)
        self.assertEqual(True, mpu.v)

    def _test_adc_bcd_off_indexed_ind_overflow_set_on_40_plus_40(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.a = 0x40
        mpu.y = 0x03
        # $0000 ADC ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x71, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x40

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(True, mpu.v)
        self.assertEqual(False, mpu.z)

    # AND (Absolute)

    def _test_and_absolute_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND $ABCD
        mpu.run((0x2D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_absolute_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND $ABCD
        mpu.run((0x2D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND (Absolute)

    def _test_and_zp_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND $0010
        mpu.run((0x25, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_zp_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND $0010
        mpu.run((0x25, 0x10))
        mpu.mem[0x0010] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND (Immediate)

    def _test_and_immediate_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND #$00
        mpu.run((0x29, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_immediate_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 AND #$AA
        mpu.run((0x29, 0xAA))

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND (Absolute, X-Indexed)

    def _test_and_abs_x_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND $ABCD,X
        mpu.run((0x3d, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_abs_x_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND $ABCD,X
        mpu.run((0x3d, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND (Absolute, Y-Indexed)

    def _test_and_abs_y_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 AND $ABCD,X
        mpu.run((0x39, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_abs_y_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 AND $ABCD,X
        mpu.run((0x39, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND Indirect, Indexed (X)

    def _test_and_ind_indexed_x_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x21, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_ind_indexed_x_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x21, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND Indexed, Indirect (Y)

    def _test_and_indexed_ind_y_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 AND ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x31, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_indexed_ind_y_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 AND ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x31, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # AND Zero Page, X-Indexed

    def _test_and_zp_x_all_zeros_setting_zero_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND $0010,X
        mpu.run((0x35, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_and_zp_x_all_zeros_and_ones_setting_negative_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 AND $0010,X
        mpu.run((0x35, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xAA

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ASL Accumulator

    def _test_asl_accumulator_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        # $0000 ASL A
        mpu.mem[0x0000] = 0x0A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_asl_accumulator_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x40
        # $0000 ASL A
        mpu.mem[0x0000] = 0x0A

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_asl_accumulator_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0x7F
        # $0000 ASL A
        mpu.mem[0x0000] = 0x0A

        self.assertEqual(0xFE, mpu.a)
        self.assertEqual(False, mpu.c)

    def _test_asl_accumulator_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 ASL A
        mpu.mem[0x0000] = 0x0A

        self.assertEqual(0xFE, mpu.a)
        self.assertEqual(True, mpu.c)

    def _test_asl_accumulator_80_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x80
        mpu.p &= ~(mpu.ZERO)
        # $0000 ASL A
        mpu.mem[0x0000] = 0x0A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    # ASL Absolute

    def _test_asl_absolute_sets_z_flag(self):
        mpu = Controller()
        # $0000 ASL $ABCD
        mpu.run((0x0E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_asl_absolute_sets_n_flag(self):
        mpu = Controller()
        # $0000 ASL $ABCD
        mpu.run((0x0E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x40

        self.assertEqual(0x80, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_asl_absolute_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0xAA
        # $0000 ASL $ABCD
        mpu.run((0x0E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x7F

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.c)

    def _test_asl_absolute_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0xAA
        # $0000 ASL $ABCD
        mpu.run((0x0E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.c)

    # ASL Zero Page

    def _test_asl_zp_sets_z_flag(self):
        mpu = Controller()
        # $0000 ASL $0010
        mpu.run((0x06, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_asl_zp_sets_n_flag(self):
        mpu = Controller()
        # $0000 ASL $0010
        mpu.run((0x06, 0x10))
        mpu.mem[0x0010] = 0x40

        self.assertEqual(0x80, mpu.mem[0x0010])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_asl_zp_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0xAA
        # $0000 ASL $0010
        mpu.run((0x06, 0x10))
        mpu.mem[0x0010] = 0x7F

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0x0010])
        self.assertEqual(False, mpu.c)

    def _test_asl_zp_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0xAA
        # $0000 ASL $0010
        mpu.run((0x06, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0x0010])
        self.assertEqual(True, mpu.c)

    # ASL Absolute, X-Indexed

    def _test_asl_abs_x_indexed_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        # $0000 ASL $ABCD,X
        mpu.run((0x1E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_asl_abs_x_indexed_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        # $0000 ASL $ABCD,X
        mpu.run((0x1E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x40

        self.assertEqual(0x80, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_asl_abs_x_indexed_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0xAA
        mpu.x = 0x03
        # $0000 ASL $ABCD,X
        mpu.run((0x1E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x7F

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_asl_abs_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0xAA
        mpu.x = 0x03
        # $0000 ASL $ABCD,X
        mpu.run((0x1E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.c)

    # ASL Zero Page, X-Indexed

    def _test_asl_zp_x_indexed_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        # $0000 ASL $0010,X
        mpu.run((0x16, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_asl_zp_x_indexed_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        # $0000 ASL $0010,X
        mpu.run((0x16, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x40

        self.assertEqual(0x80, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_asl_zp_x_indexed_shifts_out_zero(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.a = 0xAA
        # $0000 ASL $0010,X
        mpu.run((0x16, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x7F

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_asl_zp_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.a = 0xAA
        # $0000 ASL $0010,X
        mpu.run((0x16, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0xAA, mpu.a)
        self.assertEqual(0xFE, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.c)

    # BCC

    def _test_bcc_carry_clear_branches_relative_forward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 BCC +6
        mpu.run((0x90, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bcc_carry_clear_branches_relative_backward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.pc = 0x0050
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        # $0000 BCC -6
        self._write(mpu.mem, 0x0050, (0x90, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bcc_carry_set_does_not_branch(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 BCC +6
        mpu.run((0x90, 0x06))


    # BCS

    def _test_bcs_carry_set_branches_relative_forward(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 BCS +6
        mpu.run((0xB0, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bcs_carry_set_branches_relative_backward(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        mpu.pc = 0x0050
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        # $0000 BCS -6
        self._write(mpu.mem, 0x0050, (0xB0, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bcs_carry_clear_does_not_branch(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 BCS +6
        mpu.run((0xB0, 0x06))


    # BEQ

    def _test_beq_zero_set_branches_relative_forward(self):
        mpu = Controller()
        mpu.p |= mpu.ZERO
        # $0000 BEQ +6
        mpu.run((0xF0, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_beq_zero_set_branches_relative_backward(self):
        mpu = Controller()
        mpu.p |= mpu.ZERO
        mpu.pc = 0x0050
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        # $0000 BEQ -6
        self._write(mpu.mem, 0x0050, (0xF0, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_beq_zero_clear_does_not_branch(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        # $0000 BEQ +6
        mpu.run((0xF0, 0x06))


    # BIT (Absolute)

    def _test_bit_abs_copies_bit_7_of_memory_to_n_flag_when_0(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0xFF
        mpu.a = 0xFF

        self.assertEqual(True, mpu.n)

    def _test_bit_abs_copies_bit_7_of_memory_to_n_flag_when_1(self):
        mpu = Controller()
        mpu.p |= mpu.NEGATIVE
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0x00
        mpu.a = 0xFF

        self.assertEqual(False, mpu.n)

    def _test_bit_abs_copies_bit_6_of_memory_to_v_flag_when_0(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0xFF
        mpu.a = 0xFF

        self.assertEqual(True, mpu.v)

    def _test_bit_abs_copies_bit_6_of_memory_to_v_flag_when_1(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0x00
        mpu.a = 0xFF

        self.assertEqual(False, mpu.v)

    def _test_bit_abs_stores_result_of_and_in_z_preserves_a_when_1(self):
        mpu = Controller()
        mpu.p &= ~mpu.ZERO
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0x00
        mpu.a = 0x01

        self.assertEqual(True, mpu.z)
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x00, mpu.mem[0xFEED])

    def _test_bit_abs_stores_result_of_and_when_nonzero_in_z_preserves_a(self):
        mpu = Controller()
        mpu.p |= mpu.ZERO
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0x01
        mpu.a = 0x01

        self.assertEqual(False, mpu.z)  # result of AND is non-zero
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x01, mpu.mem[0xFEED])

    def _test_bit_abs_stores_result_of_and_when_zero_in_z_preserves_a(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        # $0000 BIT $FEED
        mpu.run((0x2C, 0xED, 0xFE))
        mpu.mem[0xFEED] = 0x00
        mpu.a = 0x01

        self.assertEqual(True, mpu.z)  # result of AND is zero
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x00, mpu.mem[0xFEED])

    # BIT (Zero Page)

    def _test_bit_zp_copies_bit_7_of_memory_to_n_flag_when_0(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0xFF
        mpu.a = 0xFF

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(True, mpu.n)

    def _test_bit_zp_copies_bit_7_of_memory_to_n_flag_when_1(self):
        mpu = Controller()
        mpu.p |= mpu.NEGATIVE
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0x00
        mpu.a = 0xFF

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(False, mpu.n)

    def _test_bit_zp_copies_bit_6_of_memory_to_v_flag_when_0(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0xFF
        mpu.a = 0xFF

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(True, mpu.v)

    def _test_bit_zp_copies_bit_6_of_memory_to_v_flag_when_1(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0x00
        mpu.a = 0xFF

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(False, mpu.v)

    def _test_bit_zp_stores_result_of_and_in_z_preserves_a_when_1(self):
        mpu = Controller()
        mpu.p &= ~mpu.ZERO
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0x00
        mpu.a = 0x01

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(True, mpu.z)
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x00, mpu.mem[0x0010])

    def _test_bit_zp_stores_result_of_and_when_nonzero_in_z_preserves_a(self):
        mpu = Controller()
        mpu.p |= mpu.ZERO
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0x01
        mpu.a = 0x01

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(False, mpu.z)  # result of AND is non-zero
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x01, mpu.mem[0x0010])

    def _test_bit_zp_stores_result_of_and_when_zero_in_z_preserves_a(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        # $0000 BIT $0010
        mpu.run((0x24, 0x10))
        mpu.mem[0x0010] = 0x00
        mpu.a = 0x01

        self.assertEqual(3, mpu.processorCycles)
        self.assertEqual(True, mpu.z)  # result of AND is zero
        self.assertEqual(0x01, mpu.a)
        self.assertEqual(0x00, mpu.mem[0x0010])

    # BMI

    def _test_bmi_negative_set_branches_relative_forward(self):
        mpu = Controller()
        mpu.p |= mpu.NEGATIVE
        # $0000 BMI +06
        mpu.run((0x30, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bmi_negative_set_branches_relative_backward(self):
        mpu = Controller()
        mpu.p |= mpu.NEGATIVE
        mpu.pc = 0x0050
        # $0000 BMI -6
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        self._write(mpu.mem, 0x0050, (0x30, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bmi_negative_clear_does_not_branch(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        # $0000 BEQ +6
        mpu.run((0x30, 0x06))


    # BNE

    def _test_bne_zero_clear_branches_relative_forward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        # $0000 BNE +6
        mpu.run((0xD0, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bne_zero_clear_branches_relative_backward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.pc = 0x0050
        # $0050 BNE -6
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        self._write(mpu.mem, 0x0050, (0xD0, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bne_zero_set_does_not_branch(self):
        mpu = Controller()
        mpu.p |= mpu.ZERO
        # $0000 BNE +6
        mpu.run((0xD0, 0x06))


    # BPL

    def _test_bpl_negative_clear_branches_relative_forward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        # $0000 BPL +06
        mpu.run((0x10, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bpl_negative_clear_branches_relative_backward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.pc = 0x0050
        # $0050 BPL -6
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        self._write(mpu.mem, 0x0050, (0x10, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bpl_negative_set_does_not_branch(self):
        mpu = Controller()
        mpu.p |= mpu.NEGATIVE
        # $0000 BPL +6
        mpu.run((0x10, 0x06))


    # BRK

    def _test_brk_pushes_pc_plus_2_and_status_then_sets_pc_to_irq_vector(self):
        mpu = Controller()
        mpu.p = mpu.UNUSED
        self._write(mpu.mem, 0xFFFE, (0xCD, 0xAB))
        # $C000 BRK
        mpu.mem[0xC000] = 0x00
        mpu.pc = 0xC000

        self.assertEqual(0xABCD, mpu.pc)

        self.assertEqual(0xC0, mpu.mem[0x1FF])  # PCH
        self.assertEqual(0x02, mpu.mem[0x1FE])  # PCL
        self.assertEqual(mpu.BREAK | mpu.UNUSED, mpu.mem[0x1FD])  # Status
        self.assertEqual(0xFC, mpu.sp)

        self.assertEqual(mpu.BREAK | mpu.UNUSED | mpu.INTERRUPT, mpu.p)

    # BVC

    def _test_bvc_overflow_clear_branches_relative_forward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        # $0000 BVC +6
        mpu.run((0x50, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bvc_overflow_clear_branches_relative_backward(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        mpu.pc = 0x0050
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        # $0050 BVC -6
        self._write(mpu.mem, 0x0050, (0x50, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bvc_overflow_set_does_not_branch(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        # $0000 BVC +6
        mpu.run((0x50, 0x06))


    # BVS

    def _test_bvs_overflow_set_branches_relative_forward(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        # $0000 BVS +6
        mpu.run((0x70, 0x06))

        self.assertEqual(0x0002 + 0x06, mpu.pc)

    def _test_bvs_overflow_set_branches_relative_backward(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        mpu.pc = 0x0050
        rel = (0x06 ^ 0xFF + 1)  # two's complement of 6
        # $0050 BVS -6
        self._write(mpu.mem, 0x0050, (0x70, rel))

        self.assertEqual(0x0052 + rel, mpu.pc)

    def _test_bvs_overflow_clear_does_not_branch(self):
        mpu = Controller()
        mpu.p &= ~(mpu.OVERFLOW)
        # $0000 BVS +6
        mpu.run((0x70, 0x06))


    # CLC

    def _test_clc_clears_carry_flag(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 CLC
        mpu.mem[0x0000] = 0x18

        self.assertEqual(False, mpu.c)

    # CLD

    def _test_cld_clears_decimal_flag(self):
        mpu = Controller()
        mpu.p |= mpu.DECIMAL
        # $0000 CLD
        mpu.mem[0x0000] = 0xD8

        self.assertEqual(False, mpu.d)

    # CLI

    def _test_cli_clears_interrupt_mask_flag(self):
        mpu = Controller()
        mpu.p |= mpu.INTERRUPT
        # $0000 CLI
        mpu.mem[0x0000] = 0x58

        self.assertEqual(False, mpu.i)

    # CLV

    def _test_clv_clears_overflow_flag(self):
        mpu = Controller()
        mpu.p |= mpu.OVERFLOW
        # $0000 CLV
        mpu.mem[0x0000] = 0xB8

        self.assertEqual(False, mpu.v)

    # DEC Absolute

    def _test_dec_abs_decrements_memory(self):
        mpu = Controller()
        # $0000 DEC 0xABCD
        mpu.run((0xCE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x10

        self.assertEqual(0x0F, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dec_abs_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        # $0000 DEC 0xABCD
        mpu.run((0xCE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_dec_abs_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        # $0000 DEC 0xABCD
        mpu.run((0xCE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x01

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # DEC Zero Page

    def _test_dec_zp_decrements_memory(self):
        mpu = Controller()
        # $0000 DEC 0x0010
        mpu.run((0xC6, 0x10))
        mpu.mem[0x0010] = 0x10

        self.assertEqual(0x0F, mpu.mem[0x0010])
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dec_zp_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        # $0000 DEC 0x0010
        mpu.run((0xC6, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_dec_zp_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        # $0000 DEC 0x0010
        mpu.run((0xC6, 0x10))
        mpu.mem[0x0010] = 0x01

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # DEC Absolute, X-Indexed

    def _test_dec_abs_x_decrements_memory(self):
        mpu = Controller()
        # $0000 DEC 0xABCD,X
        mpu.run((0xDE, 0xCD, 0xAB))
        mpu.x = 0x03
        mpu.mem[0xABCD + mpu.x] = 0x10

        self.assertEqual(0x0F, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dec_abs_x_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        # $0000 DEC 0xABCD,X
        mpu.run((0xDE, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_dec_abs_x_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        # $0000 DEC 0xABCD,X
        mpu.run((0xDE, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x01

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # DEC Zero Page, X-Indexed

    def _test_dec_zp_x_decrements_memory(self):
        mpu = Controller()
        # $0000 DEC 0x0010,X
        mpu.run((0xD6, 0x10))
        mpu.x = 0x03
        mpu.mem[0x0010 + mpu.x] = 0x10

        self.assertEqual(0x0F, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dec_zp_x_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        # $0000 DEC 0x0010,X
        mpu.run((0xD6, 0x10))
        mpu.x = 0x03
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_dec_zp_x_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        # $0000 DEC 0x0010,X
        mpu.run((0xD6, 0x10))
        mpu.x = 0x03
        mpu.mem[0x0010 + mpu.x] = 0x01

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # DEX

    def _test_dex_decrements_x(self):
        mpu = Controller()
        mpu.x = 0x10
        # $0000 DEX
        mpu.mem[0x0000] = 0xCA

        self.assertEqual(0x0F, mpu.x)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dex_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        # $0000 DEX
        mpu.mem[0x0000] = 0xCA

        self.assertEqual(0xFF, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dex_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        mpu.x = 0x01
        # $0000 DEX
        mpu.mem[0x0000] = 0xCA

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # DEY

    def _test_dey_decrements_y(self):
        mpu = Controller()
        mpu.y = 0x10
        # $0000 DEY
        mpu.mem[0x0000] = 0x88

        self.assertEqual(0x0F, mpu.y)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_dey_below_00_rolls_over_and_sets_negative_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        # $0000 DEY
        mpu.mem[0x0000] = 0x88

        self.assertEqual(0xFF, mpu.y)
        self.assertEqual(True, mpu.n)

    def _test_dey_sets_zero_flag_when_decrementing_to_zero(self):
        mpu = Controller()
        mpu.y = 0x01
        # $0000 DEY
        mpu.mem[0x0000] = 0x88

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)

    # EOR Absolute

    def _test_eor_absolute_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.run((0x4D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)

    def _test_eor_absolute_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.run((0x4D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Zero Page

    def _test_eor_zp_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.run((0x45, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)

    def _test_eor_zp_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.run((0x45, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Immediate

    def _test_eor_immediate_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.run((0x49, 0xFF))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_eor_immediate_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.run((0x49, 0xFF))

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Absolute, X-Indexed

    def _test_eor_abs_x_indexed_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        mpu.run((0x5D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)

    def _test_eor_abs_x_indexed_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        mpu.run((0x5D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Absolute, Y-Indexed

    def _test_eor_abs_y_indexed_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        mpu.run((0x59, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(True, mpu.z)

    def _test_eor_abs_y_indexed_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        mpu.run((0x59, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Indirect, Indexed (X)

    def _test_eor_ind_indexed_x_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        mpu.run((0x41, 0x10))  # => EOR ($0010,X)
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))  # => Vector to $ABCD
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)

    def _test_eor_ind_indexed_x_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        mpu.run((0x41, 0x10))  # => EOR ($0010,X)
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))  # => Vector to $ABCD
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Indexed, Indirect (Y)

    def _test_eor_indexed_ind_y_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        mpu.run((0x51, 0x10))  # => EOR ($0010),Y
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))  # => Vector to $ABCD
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(True, mpu.z)

    def _test_eor_indexed_ind_y_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        mpu.run((0x51, 0x10))  # => EOR ($0010),Y
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))  # => Vector to $ABCD
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # EOR Zero Page, X-Indexed

    def _test_eor_zp_x_indexed_flips_bits_over_setting_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        mpu.run((0x55, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)

    def _test_eor_zp_x_indexed_flips_bits_over_setting_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        mpu.run((0x55, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # INC Absolute

    def _test_inc_abs_increments_memory(self):
        mpu = Controller()
        mpu.run((0xEE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x09

        self.assertEqual(0x0A, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_abs_increments_memory_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.run((0xEE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_abs_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.run((0xEE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x7F

        self.assertEqual(0x80, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    # INC Zero Page

    def _test_inc_zp_increments_memory(self):
        mpu = Controller()
        mpu.run((0xE6, 0x10))
        mpu.mem[0x0010] = 0x09

        self.assertEqual(0x0A, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_zp_increments_memory_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.run((0xE6, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_zp_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.run((0xE6, 0x10))
        mpu.mem[0x0010] = 0x7F

        self.assertEqual(0x80, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    # INC Absolute, X-Indexed

    def _test_inc_abs_x_increments_memory(self):
        mpu = Controller()
        mpu.run((0xFE, 0xCD, 0xAB))
        mpu.x = 0x03
        mpu.mem[0xABCD + mpu.x] = 0x09

        self.assertEqual(0x0A, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_abs_x_increments_memory_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.run((0xFE, 0xCD, 0xAB))
        mpu.x = 0x03
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_abs_x_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.run((0xFE, 0xCD, 0xAB))
        mpu.x = 0x03
        mpu.mem[0xABCD + mpu.x] = 0x7F

        self.assertEqual(0x80, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    # INC Zero Page, X-Indexed

    def _test_inc_zp_x_increments_memory(self):
        mpu = Controller()
        mpu.run((0xF6, 0x10))
        mpu.x = 0x03
        mpu.mem[0x0010 + mpu.x] = 0x09

        self.assertEqual(0x0A, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_zp_x_increments_memory_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.run((0xF6, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inc_zp_x_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.run((0xF6, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x7F

        self.assertEqual(0x80, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    # INX

    def _test_inx_increments_x(self):
        mpu = Controller()
        mpu.x = 0x09
        mpu.mem[0x0000] = 0xE8  # => INX

        self.assertEqual(0x0A, mpu.x)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_inx_above_FF_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        mpu.mem[0x0000] = 0xE8  # => INX

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)

    def _test_inx_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.x = 0x7f
        mpu.mem[0x0000] = 0xE8  # => INX

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)

    # INY

    def _test_iny_increments_y(self):
        mpu = Controller()
        mpu.y = 0x09
        mpu.mem[0x0000] = 0xC8  # => INY

        self.assertEqual(0x0A, mpu.y)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_iny_above_FF_rolls_over_and_sets_zero_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        mpu.mem[0x0000] = 0xC8  # => INY

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)

    def _test_iny_sets_negative_flag_when_incrementing_above_7F(self):
        mpu = Controller()
        mpu.y = 0x7f
        mpu.mem[0x0000] = 0xC8  # => INY

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)

    # JMP Absolute

    def _test_jmp_abs_jumps_to_absolute_address(self):
        mpu = Controller()
        # $0000 JMP $ABCD
        mpu.run((0x4C, 0xCD, 0xAB))

        self.assertEqual(0xABCD, mpu.pc)

    # JMP Indirect

    def _test_jmp_ind_jumps_to_indirect_address(self):
        mpu = Controller()
        # $0000 JMP ($ABCD)
        mpu.run((0x6C, 0x00, 0x02))
        self._write(mpu.mem, 0x0200, (0xCD, 0xAB))

        self.assertEqual(0xABCD, mpu.pc)

    # JSR

    def _test_jsr_pushes_pc_plus_2_and_sets_pc(self):
        mpu = Controller()
        # $C000 JSR $FFD2
        self._write(mpu.mem, 0xC000, (0x20, 0xD2, 0xFF))
        mpu.pc = 0xC000

        self.assertEqual(0xFFD2, mpu.pc)
        self.assertEqual(0xFD, mpu.sp)
        self.assertEqual(0xC0, mpu.mem[0x01FF])  # PCH
        self.assertEqual(0x02, mpu.mem[0x01FE])  # PCL+2

    # LDA Absolute

    def _test_lda_absolute_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        # $0000 LDA $ABCD
        mpu.run((0xAD, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_absolute_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 LDA $ABCD
        mpu.run((0xAD, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDA Zero Page

    def _test_lda_zp_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        # $0000 LDA $0010
        mpu.run((0xA5, 0x10))
        mpu.mem[0x0010] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_zp_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 LDA $0010
        mpu.run((0xA5, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDA Immediate

    def _test_lda_immediate_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        # $0000 LDA #$80
        mpu.run((0xA9, 0x80))

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_immediate_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        # $0000 LDA #$00
        mpu.run((0xA9, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDA Absolute, X-Indexed

    def _test_lda_abs_x_indexed_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 LDA $ABCD,X
        mpu.run((0xBD, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_abs_x_indexed_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 LDA $ABCD,X
        mpu.run((0xBD, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_lda_abs_x_indexed_does_not_page_wrap(self):
        mpu = Controller()
        mpu.a = 0
        mpu.x = 0xFF
        # $0000 LDA $0080,X
        mpu.run((0xBD, 0x80, 0x00))
        mpu.mem[0x0080 + mpu.x] = 0x42

        self.assertEqual(0x42, mpu.a)

    # LDA Absolute, Y-Indexed

    def _test_lda_abs_y_indexed_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 LDA $ABCD,Y
        mpu.run((0xB9, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_abs_y_indexed_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 LDA $ABCD,Y
        mpu.run((0xB9, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_lda_abs_y_indexed_does_not_page_wrap(self):
        mpu = Controller()
        mpu.a = 0
        mpu.y = 0xFF
        # $0000 LDA $0080,X
        mpu.run((0xB9, 0x80, 0x00))
        mpu.mem[0x0080 + mpu.y] = 0x42

        self.assertEqual(0x42, mpu.a)

    # LDA Indirect, Indexed (X)

    def _test_lda_ind_indexed_x_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 LDA ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0xA1, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_ind_indexed_x_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 LDA ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0xA1, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDA Indexed, Indirect (Y)

    def _test_lda_indexed_ind_y_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 LDA ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0xB1, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_indexed_ind_y_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 LDA ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0xB1, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDA Zero Page, X-Indexed

    def _test_lda_zp_x_indexed_loads_a_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 LDA $10,X
        mpu.run((0xB5, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x80

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_lda_zp_x_indexed_loads_a_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 LDA $10,X
        mpu.run((0xB5, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDX Absolute

    def _test_ldx_absolute_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        # $0000 LDX $ABCD
        mpu.run((0xAE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x80

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldx_absolute_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        # $0000 LDX $ABCD
        mpu.run((0xAE, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDX Zero Page

    def _test_ldx_zp_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        # $0000 LDX $0010
        mpu.run((0xA6, 0x10))
        mpu.mem[0x0010] = 0x80

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldx_zp_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        # $0000 LDX $0010
        mpu.run((0xA6, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDX Immediate

    def _test_ldx_immediate_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        # $0000 LDX #$80
        mpu.run((0xA2, 0x80))

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldx_immediate_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        # $0000 LDX #$00
        mpu.run((0xA2, 0x00))

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDX Absolute, Y-Indexed

    def _test_ldx_abs_y_indexed_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        mpu.y = 0x03
        # $0000 LDX $ABCD,Y
        mpu.run((0xBE, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x80

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldx_abs_y_indexed_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        mpu.y = 0x03
        # $0000 LDX $ABCD,Y
        mpu.run((0xBE, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDX Zero Page, Y-Indexed

    def _test_ldx_zp_y_indexed_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x00
        mpu.y = 0x03
        # $0000 LDX $0010,Y
        mpu.run((0xB6, 0x10))
        mpu.mem[0x0010 + mpu.y] = 0x80

        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldx_zp_y_indexed_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0xFF
        mpu.y = 0x03
        # $0000 LDX $0010,Y
        mpu.run((0xB6, 0x10))
        mpu.mem[0x0010 + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDY Absolute

    def _test_ldy_absolute_loads_y_sets_n_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        # $0000 LDY $ABCD
        mpu.run((0xAC, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x80

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldy_absolute_loads_y_sets_z_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        # $0000 LDY $ABCD
        mpu.run((0xAC, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDY Zero Page

    def _test_ldy_zp_loads_y_sets_n_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        # $0000 LDY $0010
        mpu.run((0xA4, 0x10))
        mpu.mem[0x0010] = 0x80

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldy_zp_loads_y_sets_z_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        # $0000 LDY $0010
        mpu.run((0xA4, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDY Immediate

    def _test_ldy_immediate_loads_y_sets_n_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        # $0000 LDY #$80
        mpu.run((0xA0, 0x80))

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldy_immediate_loads_y_sets_z_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        # $0000 LDY #$00
        mpu.run((0xA0, 0x00))

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDY Absolute, X-Indexed

    def _test_ldy_abs_x_indexed_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        mpu.x = 0x03
        # $0000 LDY $ABCD,X
        mpu.run((0xBC, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x80

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldy_abs_x_indexed_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        mpu.x = 0x03
        # $0000 LDY $ABCD,X
        mpu.run((0xBC, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LDY Zero Page, X-Indexed

    def _test_ldy_zp_x_indexed_loads_x_sets_n_flag(self):
        mpu = Controller()
        mpu.y = 0x00
        mpu.x = 0x03
        # $0000 LDY $0010,X
        mpu.run((0xB4, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x80

        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_ldy_zp_x_indexed_loads_x_sets_z_flag(self):
        mpu = Controller()
        mpu.y = 0xFF
        mpu.x = 0x03
        # $0000 LDY $0010,X
        mpu.run((0xB4, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    # LSR Accumulator

    def _test_lsr_accumulator_rotates_in_zero_not_carry(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR A
        mpu.mem[0x0000] = (0x4A)
        mpu.a = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_accumulator_sets_carry_and_zero_flags_after_rotation(self):
        mpu = Controller()
        mpu.p &= ~mpu.CARRY
        # $0000 LSR A
        mpu.mem[0x0000] = (0x4A)
        mpu.a = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_accumulator_rotates_bits_right(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR A
        mpu.mem[0x0000] = (0x4A)
        mpu.a = 0x04

        self.assertEqual(0x02, mpu.a)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    # LSR Absolute

    def _test_lsr_absolute_rotates_in_zero_not_carry(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR $ABCD
        mpu.run((0x4E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_absolute_sets_carry_and_zero_flags_after_rotation(self):
        mpu = Controller()
        mpu.p &= ~mpu.CARRY
        # $0000 LSR $ABCD
        mpu.run((0x4E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x01

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_absolute_rotates_bits_right(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR $ABCD
        mpu.run((0x4E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x04

        self.assertEqual(0x02, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    # LSR Zero Page

    def _test_lsr_zp_rotates_in_zero_not_carry(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR $0010
        mpu.run((0x46, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_zp_sets_carry_and_zero_flags_after_rotation(self):
        mpu = Controller()
        mpu.p &= ~mpu.CARRY
        # $0000 LSR $0010
        mpu.run((0x46, 0x10))
        mpu.mem[0x0010] = 0x01

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_zp_rotates_bits_right(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR $0010
        mpu.run((0x46, 0x10))
        mpu.mem[0x0010] = 0x04

        self.assertEqual(0x02, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    # LSR Absolute, X-Indexed

    def _test_lsr_abs_x_indexed_rotates_in_zero_not_carry(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        mpu.x = 0x03
        # $0000 LSR $ABCD,X
        mpu.run((0x5E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_abs_x_indexed_sets_c_and_z_flags_after_rotation(self):
        mpu = Controller()
        mpu.p &= ~mpu.CARRY
        mpu.x = 0x03
        # $0000 LSR $ABCD,X
        mpu.run((0x5E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x01

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_abs_x_indexed_rotates_bits_right(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 LSR $ABCD,X
        mpu.run((0x5E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x04

        self.assertEqual(0x02, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    # LSR Zero Page, X-Indexed

    def _test_lsr_zp_x_indexed_rotates_in_zero_not_carry(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        mpu.x = 0x03
        # $0000 LSR $0010,X
        mpu.run((0x56, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_zp_x_indexed_sets_carry_and_zero_flags_after_rotation(self):
        mpu = Controller()
        mpu.p &= ~mpu.CARRY
        mpu.x = 0x03
        # $0000 LSR $0010,X
        mpu.run((0x56, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x01

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(True, mpu.c)
        self.assertEqual(False, mpu.n)

    def _test_lsr_zp_x_indexed_rotates_bits_right(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        mpu.x = 0x03
        # $0000 LSR $0010,X
        mpu.run((0x56, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x04

        self.assertEqual(0x02, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)
        self.assertEqual(False, mpu.n)

    # NOP

    def _test_nop_does_nothing(self):
        mpu = Controller()
        # $0000 NOP
        mpu.mem[0x0000] = 0xEA


    # ORA Absolute

    def _test_ora_absolute_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        # $0000 ORA $ABCD
        mpu.run((0x0D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_absolute_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        # $0000 ORA $ABCD
        mpu.run((0x0D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Zero Page

    def _test_ora_zp_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        # $0000 ORA $0010
        mpu.run((0x05, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_zp_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        # $0000 ORA $0010
        mpu.run((0x05, 0x10))
        mpu.mem[0x0010] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Immediate

    def _test_ora_immediate_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        # $0000 ORA #$00
        mpu.run((0x09, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_immediate_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        # $0000 ORA #$82
        mpu.run((0x09, 0x82))

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Absolute, X

    def _test_ora_abs_x_indexed_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ORA $ABCD,X
        mpu.run((0x1D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_abs_x_indexed_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        mpu.x = 0x03
        # $0000 ORA $ABCD,X
        mpu.run((0x1D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Absolute, Y

    def _test_ora_abs_y_indexed_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 ORA $ABCD,Y
        mpu.run((0x19, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_abs_y_indexed_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        mpu.y = 0x03
        # $0000 ORA $ABCD,Y
        mpu.run((0x19, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Indirect, Indexed (X)

    def _test_ora_ind_indexed_x_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ORA ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x01, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_ind_indexed_x_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        mpu.x = 0x03
        # $0000 ORA ($0010,X)
        # $0013 Vector to $ABCD
        mpu.run((0x01, 0x10))
        self._write(mpu.mem, 0x0013, (0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Indexed, Indirect (Y)

    def _test_ora_indexed_ind_y_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 ORA ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x11, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_indexed_ind_y_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        mpu.y = 0x03
        # $0000 ORA ($0010),Y
        # $0010 Vector to $ABCD
        mpu.run((0x11, 0x10))
        self._write(mpu.mem, 0x0010, (0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # ORA Zero Page, X

    def _test_ora_zp_x_indexed_zeroes_or_zeros_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 ORA $0010,X
        mpu.run((0x15, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)

    def _test_ora_zp_x_indexed_turns_bits_on_sets_n_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x03
        mpu.x = 0x03
        # $0000 ORA $0010,X
        mpu.run((0x15, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x82

        self.assertEqual(0x83, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    # PHA

    def _test_pha_pushes_a_and_updates_sp(self):
        mpu = Controller()
        mpu.a = 0xAB
        # $0000 PHA
        mpu.mem[0x0000] = 0x48

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xAB, mpu.mem[0x01FF])
        self.assertEqual(0xFE, mpu.sp)

    # PHP

    def _test_php_pushes_processor_status_and_updates_sp(self):
        for flags in range(0x100):
            mpu = Controller()
            mpu.p = flags | mpu.BREAK | mpu.UNUSED
            # $0000 PHP
            mpu.mem[0x0000] = 0x08

            self.assertEqual((flags | mpu.BREAK | mpu.UNUSED),
                             mpu.mem[0x1FF])
            self.assertEqual(0xFE, mpu.sp)

    # PLA

    def _test_pla_pulls_top_byte_from_stack_into_a_and_updates_sp(self):
        mpu = Controller()
        # $0000 PLA
        mpu.mem[0x0000] = 0x68
        mpu.mem[0x01FF] = 0xAB
        mpu.sp = 0xFE

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xFF, mpu.sp)

    # PLP

    def _test_plp_pulls_top_byte_from_stack_into_flags_and_updates_sp(self):
        mpu = Controller()
        # $0000 PLP
        mpu.mem[0x0000] = 0x28
        mpu.mem[0x01FF] = 0xBA  # must have BREAK and UNUSED set
        mpu.sp = 0xFE

        self.assertEqual(0xBA, mpu.p)
        self.assertEqual(0xFF, mpu.sp)

    # ROL Accumulator

    def _test_rol_accumulator_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_accumulator_80_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x80
        mpu.p &= ~(mpu.CARRY)
        mpu.p &= ~(mpu.ZERO)
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_accumulator_zero_and_carry_one_clears_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p |= mpu.CARRY
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0x01, mpu.a)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_accumulator_sets_n_flag(self):
        mpu = Controller()
        mpu.a = 0x40
        mpu.p |= mpu.CARRY
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0x81, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_rol_accumulator_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0x7F
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0xFE, mpu.a)
        self.assertEqual(False, mpu.c)

    def _test_rol_accumulator_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0xFF
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL A
        mpu.mem[0x0000] = 0x2A

        self.assertEqual(0xFE, mpu.a)
        self.assertEqual(True, mpu.c)

    # ROL Absolute

    def _test_rol_absolute_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_absolute_80_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.p &= ~(mpu.ZERO)
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x80

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_absolute_zero_and_carry_one_clears_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p |= mpu.CARRY
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x01, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_absolute_sets_n_flag(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x40

        self.assertEqual(0x81, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_rol_absolute_shifts_out_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x7F

        self.assertEqual(0xFE, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.c)

    def _test_rol_absolute_shifts_out_one(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $ABCD
        mpu.run((0x2E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0xFE, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.c)

    # ROL Zero Page

    def _test_rol_zp_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_80_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.p &= ~(mpu.ZERO)
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0x80

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_zero_and_carry_one_clears_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p |= mpu.CARRY
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x01, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_sets_n_flag(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0x40

        self.assertEqual(0x81, mpu.mem[0x0010])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_rol_zp_shifts_out_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0x7F

        self.assertEqual(0xFE, mpu.mem[0x0010])
        self.assertEqual(False, mpu.c)

    def _test_rol_zp_shifts_out_one(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $0010
        mpu.run((0x26, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0xFE, mpu.mem[0x0010])
        self.assertEqual(True, mpu.c)

    # ROL Absolute, X-Indexed

    def _test_rol_abs_x_indexed_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.x = 0x03
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_abs_x_indexed_80_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.p &= ~(mpu.ZERO)
        mpu.x = 0x03
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x80

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_abs_x_indexed_zero_and_carry_one_clears_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x01, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_abs_x_indexed_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x40

        self.assertEqual(0x81, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_rol_abs_x_indexed_shifts_out_zero(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x7F

        self.assertEqual(0xFE, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_rol_abs_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $ABCD,X
        mpu.run((0x3E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0xFE, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.c)

    # ROL Zero Page, X-Indexed

    def _test_rol_zp_x_indexed_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.x = 0x03
        mpu.run((0x36, 0x10))
        # $0000 ROL $0010,X
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_x_indexed_80_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        mpu.p &= ~(mpu.ZERO)
        mpu.x = 0x03
        mpu.run((0x36, 0x10))
        # $0000 ROL $0010,X
        mpu.mem[0x0010 + mpu.x] = 0x80

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_x_indexed_zero_and_carry_one_clears_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        mpu.run((0x36, 0x10))
        # $0000 ROL $0010,X
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x01, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_rol_zp_x_indexed_sets_n_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROL $0010,X
        mpu.run((0x36, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x40

        self.assertEqual(0x81, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.z)

    def _test_rol_zp_x_indexed_shifts_out_zero(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $0010,X
        mpu.run((0x36, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x7F

        self.assertEqual(0xFE, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_rol_zp_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROL $0010,X
        mpu.run((0x36, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0xFE, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.c)

    # ROR Accumulator

    def _test_ror_accumulator_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROR A
        mpu.mem[0x0000] = 0x6A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_ror_accumulator_zero_and_carry_one_rotates_in_sets_n_flags(self):
        mpu = Controller()
        mpu.a = 0x00
        mpu.p |= mpu.CARRY
        # $0000 ROR A
        mpu.mem[0x0000] = 0x6A

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_ror_accumulator_shifts_out_zero(self):
        mpu = Controller()
        mpu.a = 0x02
        mpu.p |= mpu.CARRY
        # $0000 ROR A
        mpu.mem[0x0000] = 0x6A

        self.assertEqual(0x81, mpu.a)
        self.assertEqual(False, mpu.c)

    def _test_ror_accumulator_shifts_out_one(self):
        mpu = Controller()
        mpu.a = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR A
        mpu.mem[0x0000] = 0x6A

        self.assertEqual(0x81, mpu.a)
        self.assertEqual(True, mpu.c)

    # ROR Absolute

    def _test_ror_absolute_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROR $ABCD
        mpu.run((0x6E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_ror_absolute_zero_and_carry_one_rotates_in_sets_n_flags(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD
        mpu.run((0x6E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0x80, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_ror_absolute_shifts_out_zero(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD
        mpu.run((0x6E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x02

        self.assertEqual(0x81, mpu.mem[0xABCD])
        self.assertEqual(False, mpu.c)

    def _test_ror_absolute_shifts_out_one(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD
        mpu.run((0x6E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x03

        self.assertEqual(0x81, mpu.mem[0xABCD])
        self.assertEqual(True, mpu.c)

    # ROR Zero Page

    def _test_ror_zp_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROR $0010
        mpu.run((0x66, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_ror_zp_zero_and_carry_one_rotates_in_sets_n_flags(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010
        mpu.run((0x66, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x80, mpu.mem[0x0010])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_ror_zp_zero_absolute_shifts_out_zero(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010
        mpu.run((0x66, 0x10))
        mpu.mem[0x0010] = 0x02

        self.assertEqual(0x81, mpu.mem[0x0010])
        self.assertEqual(False, mpu.c)

    def _test_ror_zp_shifts_out_one(self):
        mpu = Controller()
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010
        mpu.run((0x66, 0x10))
        mpu.mem[0x0010] = 0x03

        self.assertEqual(0x81, mpu.mem[0x0010])
        self.assertEqual(True, mpu.c)

    # ROR Absolute, X-Indexed

    def _test_ror_abs_x_indexed_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROR $ABCD,X
        mpu.run((0x7E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_ror_abs_x_indexed_z_and_c_1_rotates_in_sets_n_flags(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD,X
        mpu.run((0x7E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0x80, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_ror_abs_x_indexed_shifts_out_zero(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD,X
        mpu.run((0x7E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x02

        self.assertEqual(0x81, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_ror_abs_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $ABCD,X
        mpu.run((0x7E, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x03

        self.assertEqual(0x81, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(True, mpu.c)

    # ROR Zero Page, X-Indexed

    def _test_ror_zp_x_indexed_zero_and_carry_zero_sets_z_flag(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p &= ~(mpu.CARRY)
        # $0000 ROR $0010,X
        mpu.run((0x76, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.z)
        self.assertEqual(False, mpu.n)

    def _test_ror_zp_x_indexed_zero_and_carry_one_rotates_in_sets_n_flags(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010,X
        mpu.run((0x76, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0x80, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.n)

    def _test_ror_zp_x_indexed_zero_absolute_shifts_out_zero(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010,X
        mpu.run((0x76, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x02

        self.assertEqual(0x81, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(False, mpu.c)

    def _test_ror_zp_x_indexed_shifts_out_one(self):
        mpu = Controller()
        mpu.x = 0x03
        mpu.p |= mpu.CARRY
        # $0000 ROR $0010,X
        mpu.run((0x76, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x03

        self.assertEqual(0x81, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(True, mpu.c)

    # RTI

    def _test_rti_restores_status_and_pc_and_updates_sp(self):
        mpu = Controller()
        # $0000 RTI
        mpu.mem[0x0000] = 0x40
        self._write(mpu.mem, 0x01FD, (0xFC, 0x03, 0xC0))  # Status, PCL, PCH
        mpu.sp = 0xFC

        self.assertEqual(0xC003, mpu.pc)
        self.assertEqual(0xFC, mpu.p)
        self.assertEqual(0xFF, mpu.sp)

    def _test_rti_forces_break_and_unused_flags_high(self):
        mpu = Controller()
        # $0000 RTI
        mpu.mem[0x0000] = 0x40
        self._write(mpu.mem, 0x01FD, (0x00, 0x03, 0xC0))  # Status, PCL, PCH
        mpu.sp = 0xFC

        self.assertEqual(True, mpu.b)
        self.assertEqual(True, mpu.u)

    # RTS

    def _test_rts_restores_pc_and_increments_then_updates_sp(self):
        mpu = Controller()
        # $0000 RTS
        mpu.mem[0x0000] = 0x60
        self._write(mpu.mem, 0x01FE, (0x03, 0xC0))  # PCL, PCH
        mpu.pc = 0x0000
        mpu.sp = 0xFD

        self.assertEqual(0xC004, mpu.pc)
        self.assertEqual(0xFF, mpu.sp)

    def _test_rts_wraps_around_top_of_memory(self):
        mpu = Controller()
        # $1000 RTS
        mpu.mem[0x1000] = 0x60
        self._write(mpu.mem, 0x01FE, (0xFF, 0xFF))  # PCL, PCH
        mpu.pc = 0x1000
        mpu.sp = 0xFD

        self.assertEqual(0xFF, mpu.sp)

    # SBC Absolute

    def test_sbc_abs_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC $ABCD
        mpu.mem[0xABCD] = 0x00
        mpu.run((0xED, 0xCD, 0xAB))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_abs_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = True # borrow = 0
        mpu.a = 0x01
        # $0000 SBC $ABCD
        mpu.mem[0xABCD] = 0x01
        mpu.run((0xED, 0xCD, 0xAB))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_abs_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC $ABCD
        mpu.mem[0xABCD] = 0x00
        mpu.run((0xED, 0xCD, 0xAB))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_abs_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC $ABCD
        mpu.mem[0xABCD] = 0x02
        mpu.run((0xED, 0xCD, 0xAB))

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    # SBC Zero Page

    def test_sbc_zp_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC $10
        mpu.mem[0x0010] = 0x00
        mpu.run((0xE5, 0x10))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_zp_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC $10
        mpu.mem[0x0010] = 0x01
        mpu.run((0xE5, 0x10))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_zp_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x01
        # => SBC $10
        mpu.run((0xE5, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_zp_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x07
        # => SBC $10
        mpu.mem[0x0010] = 0x02
        mpu.run((0xE5, 0x10))

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    # SBC Immediate

    def test_sbc_imm_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC #$00
        mpu.run((0xE9, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_imm_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC #$01
        mpu.run((0xE9, 0x01))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_imm_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC #$00
        mpu.run((0xE9, 0x00))

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def test_sbc_imm_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.c = False  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC #$02
        mpu.run((0xE9, 0x02))

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    def test_sbc_bcd_on_immediate_0a_minus_00_carry_set(self):
        mpu = Controller()
        mpu.d = True
        mpu.c = True
        mpu.a = 0x0a
        # $0000 SBC #$00
        mpu.run((0xe9, 0x00))

        self.assertEqual(0x0a, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    def _test_sbc_bcd_on_immediate_9a_minus_00_carry_set(self):
        mpu = Controller()
        mpu.d = True
        mpu.c = True
        mpu.a = 0x9a
        #$0000 SBC #$00
        mpu.run((0xe9, 0x00))

        self.assertEqual(0x9a, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    def _test_sbc_bcd_on_immediate_00_minus_01_carry_set(self):
        mpu = Controller()
        mpu.d = True
        mpu.v = True
        mpu.z = True
        mpu.c = True
        mpu.a = 0x00
        # => $0000 SBC #$01
        mpu.run((0xe9, 0x01))

        self.assertEqual(0x99, mpu.a)
        self.assertEqual(True, mpu.n)
        self.assertEqual(False, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(False, mpu.c)

    def _test_sbc_bcd_on_immediate_20_minus_0a_carry_unset(self):
        mpu = Controller()
        mpu.d = True
        mpu.a = 0x20
        # $0000 SBC #$00
        mpu.run((0xe9, 0x0a))

        self.assertEqual(0x1f, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.v)
        self.assertEqual(False, mpu.z)
        self.assertEqual(True, mpu.c)

    # SBC Absolute, X-Indexed

    def _test_sbc_abs_x_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.c = True  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC $FEE0,X
        mpu.run((0xFD, 0xE0, 0xFE))
        mpu.x = 0x0D
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(True, mpu.c)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_x_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC $FEE0,X
        mpu.run((0xFD, 0xE0, 0xFE))
        mpu.x = 0x0D
        mpu.mem[0xFEED] = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_x_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC $FEE0,X
        mpu.run((0xFD, 0xE0, 0xFE))
        mpu.x = 0x0D
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_x_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC $FEE0,X
        mpu.run((0xFD, 0xE0, 0xFE))
        mpu.x = 0x0D
        mpu.mem[0xFEED] = 0x02

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(mpu.CARRY, mpu.CARRY)

    # SBC Absolute, Y-Indexed

    def _test_sbc_abs_y_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC $FEE0,Y
        mpu.run((0xF9, 0xE0, 0xFE))
        mpu.y = 0x0D
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_y_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC $FEE0,Y
        mpu.run((0xF9, 0xE0, 0xFE))
        mpu.y = 0x0D
        mpu.mem[0xFEED] = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_y_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC $FEE0,Y
        mpu.run((0xF9, 0xE0, 0xFE))
        mpu.y = 0x0D
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_abs_y_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC $FEE0,Y
        mpu.run((0xF9, 0xE0, 0xFE))
        mpu.y = 0x0D
        mpu.mem[0xFEED] = 0x02

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(mpu.CARRY, mpu.CARRY)

    # SBC Indirect, Indexed (X)

    def _test_sbc_ind_x_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC ($10,X)
        # $0013 Vector to $FEED
        mpu.run((0xE1, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.x = 0x03
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_x_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC ($10,X)
        # $0013 Vector to $FEED
        mpu.run((0xE1, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.x = 0x03
        mpu.mem[0xFEED] = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_x_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC ($10,X)
        # $0013 Vector to $FEED
        mpu.run((0xE1, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.x = 0x03
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_x_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC ($10,X)
        # $0013 Vector to $FEED
        mpu.run((0xE1, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.x = 0x03
        mpu.mem[0xFEED] = 0x02

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(mpu.CARRY, mpu.CARRY)

    # SBC Indexed, Indirect (Y)

    def _test_sbc_ind_y_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 SBC ($10),Y
        # $0010 Vector to $FEED
        mpu.run((0xF1, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_y_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC ($10),Y
        # $0010 Vector to $FEED
        mpu.run((0xF1, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_y_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC ($10),Y
        # $0010 Vector to $FEED
        mpu.run((0xF1, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_ind_y_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC ($10),Y
        # $0010 Vector to $FEED
        mpu.run((0xF1, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0x02

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(mpu.CARRY, mpu.CARRY)

    # SBC Zero Page, X-Indexed

    def _test_sbc_zp_x_all_zeros_and_no_borrow_is_zero(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x00
        # $0000 SBC $10,X
        mpu.run((0xF5, 0x10))
        mpu.x = 0x0D
        mpu.mem[0x001D] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_zp_x_downto_zero_no_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p |= mpu.CARRY  # borrow = 0
        mpu.a = 0x01
        # $0000 SBC $10,X
        mpu.run((0xF5, 0x10))
        mpu.x = 0x0D
        mpu.mem[0x001D] = 0x01

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_zp_x_downto_zero_with_borrow_sets_z_clears_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x01
        # $0000 SBC $10,X
        mpu.run((0xF5, 0x10))
        mpu.x = 0x0D
        mpu.mem[0x001D] = 0x00

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(mpu.CARRY, mpu.CARRY)
        self.assertEqual(True, mpu.z)

    def _test_sbc_zp_x_downto_four_with_borrow_clears_z_n(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        mpu.p &= ~(mpu.CARRY)  # borrow = 1
        mpu.a = 0x07
        # $0000 SBC $10,X
        mpu.run((0xF5, 0x10))
        mpu.x = 0x0D
        mpu.mem[0x001D] = 0x02

        self.assertEqual(0x04, mpu.a)
        self.assertEqual(False, mpu.n)
        self.assertEqual(False, mpu.z)
        self.assertEqual(mpu.CARRY, mpu.CARRY)

    # SEC

    def _test_sec_sets_carry_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.CARRY)
        # $0000 SEC
        mpu.mem[0x0000] = 0x038

        self.assertEqual(True, mpu.c)

    # SED

    def _test_sed_sets_decimal_mode_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.DECIMAL)
        # $0000 SED
        mpu.mem[0x0000] = 0xF8

        self.assertEqual(True, mpu.d)

    # SEI

    def _test_sei_sets_interrupt_disable_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.INTERRUPT)
        # $0000 SEI
        mpu.mem[0x0000] = 0x78

        self.assertEqual(True, mpu.i)

    # STA Absolute

    def _test_sta_absolute_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        # $0000 STA $ABCD
        mpu.run((0x8D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_absolute_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        # $0000 STA $ABCD
        mpu.run((0x8D, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Zero Page

    def _test_sta_zp_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        # $0000 STA $0010
        mpu.run((0x85, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_zp_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        # $0000 STA $0010
        mpu.run((0x85, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Absolute, X-Indexed

    def _test_sta_abs_x_indexed_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 STA $ABCD,X
        mpu.run((0x9D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_abs_x_indexed_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 STA $ABCD,X
        mpu.run((0x9D, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.x])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Absolute, Y-Indexed

    def _test_sta_abs_y_indexed_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 STA $ABCD,Y
        mpu.run((0x99, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_abs_y_indexed_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 STA $ABCD,Y
        mpu.run((0x99, 0xCD, 0xAB))
        mpu.mem[0xABCD + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD + mpu.y])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Indirect, Indexed (X)

    def _test_sta_ind_indexed_x_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 STA ($0010,X)
        # $0013 Vector to $FEED
        mpu.run((0x81, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.mem[0xFEED] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xFEED])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_ind_indexed_x_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 STA ($0010,X)
        # $0013 Vector to $FEED
        mpu.run((0x81, 0x10))
        self._write(mpu.mem, 0x0013, (0xED, 0xFE))
        mpu.mem[0xFEED] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xFEED])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Indexed, Indirect (Y)

    def _test_sta_indexed_ind_y_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        mpu.y = 0x03
        # $0000 STA ($0010),Y
        # $0010 Vector to $FEED
        mpu.run((0x91, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xFEED + mpu.y])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_indexed_ind_y_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.y = 0x03
        # $0000 STA ($0010),Y
        # $0010 Vector to $FEED
        mpu.run((0x91, 0x10))
        self._write(mpu.mem, 0x0010, (0xED, 0xFE))
        mpu.mem[0xFEED + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xFEED + mpu.y])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STA Zero Page, X-Indexed

    def _test_sta_zp_x_indexed_stores_a_leaves_a_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.a = 0xFF
        mpu.x = 0x03
        # $0000 STA $0010,X
        mpu.run((0x95, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(0xFF, mpu.a)
        self.assertEqual(flags, mpu.p)

    def _test_sta_zp_x_indexed_stores_a_leaves_a_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0x03
        # $0000 STA $0010,X
        mpu.run((0x95, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(flags, mpu.p)

    # STX Absolute

    def _test_stx_absolute_stores_x_leaves_x_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.x = 0xFF
        # $0000 STX $ABCD
        mpu.run((0x8E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(0xFF, mpu.x)
        self.assertEqual(flags, mpu.p)

    def _test_stx_absolute_stores_x_leaves_x_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.x = 0x00
        # $0000 STX $ABCD
        mpu.run((0x8E, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(flags, mpu.p)

    # STX Zero Page

    def _test_stx_zp_stores_x_leaves_x_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.x = 0xFF
        # $0000 STX $0010
        mpu.run((0x86, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(0xFF, mpu.x)
        self.assertEqual(flags, mpu.p)

    def _test_stx_zp_stores_x_leaves_x_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.x = 0x00
        # $0000 STX $0010
        mpu.run((0x86, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(flags, mpu.p)

    # STX Zero Page, Y-Indexed

    def _test_stx_zp_y_indexed_stores_x_leaves_x_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.x = 0xFF
        mpu.y = 0x03
        # $0000 STX $0010,Y
        mpu.run((0x96, 0x10))
        mpu.mem[0x0010 + mpu.y] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.y])
        self.assertEqual(0xFF, mpu.x)
        self.assertEqual(flags, mpu.p)

    def _test_stx_zp_y_indexed_stores_x_leaves_x_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.x = 0x00
        mpu.y = 0x03
        # $0000 STX $0010,Y
        mpu.run((0x96, 0x10))
        mpu.mem[0x0010 + mpu.y] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.y])
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(flags, mpu.p)

    # STY Absolute

    def _test_sty_absolute_stores_y_leaves_y_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.y = 0xFF
        # $0000 STY $ABCD
        mpu.run((0x8C, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0x00

        self.assertEqual(0xFF, mpu.mem[0xABCD])
        self.assertEqual(0xFF, mpu.y)
        self.assertEqual(flags, mpu.p)

    def _test_sty_absolute_stores_y_leaves_y_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.y = 0x00
        # $0000 STY $ABCD
        mpu.run((0x8C, 0xCD, 0xAB))
        mpu.mem[0xABCD] = 0xFF

        self.assertEqual(0x00, mpu.mem[0xABCD])
        self.assertEqual(0x00, mpu.y)
        self.assertEqual(flags, mpu.p)

    # STY Zero Page

    def _test_sty_zp_stores_y_leaves_y_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.y = 0xFF
        # $0000 STY $0010
        mpu.run((0x84, 0x10))
        mpu.mem[0x0010] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010])
        self.assertEqual(0xFF, mpu.y)
        self.assertEqual(flags, mpu.p)

    def _test_sty_zp_stores_y_leaves_y_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.y = 0x00
        # $0000 STY $0010
        mpu.run((0x84, 0x10))
        mpu.mem[0x0010] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010])
        self.assertEqual(0x00, mpu.y)
        self.assertEqual(flags, mpu.p)

    # STY Zero Page, X-Indexed

    def _test_sty_zp_x_indexed_stores_y_leaves_y_and_n_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.NEGATIVE)
        mpu.y = 0xFF
        mpu.x = 0x03
        # $0000 STY $0010,X
        mpu.run((0x94, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0x00

        self.assertEqual(0xFF, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(0xFF, mpu.y)
        self.assertEqual(flags, mpu.p)

    def _test_sty_zp_x_indexed_stores_y_leaves_y_and_z_flag_unchanged(self):
        mpu = Controller()
        mpu.p = flags = 0xFF & ~(mpu.ZERO)
        mpu.y = 0x00
        mpu.x = 0x03
        # $0000 STY $0010,X
        mpu.run((0x94, 0x10))
        mpu.mem[0x0010 + mpu.x] = 0xFF

        self.assertEqual(0x00, mpu.mem[0x0010 + mpu.x])
        self.assertEqual(0x00, mpu.y)
        self.assertEqual(flags, mpu.p)

    # TAX

    def _test_tax_transfers_accumulator_into_x(self):
        mpu = Controller()
        mpu.a = 0xAB
        mpu.x = 0x00
        # $0000 TAX
        mpu.mem[0x0000] = 0xAA

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xAB, mpu.x)

    def _test_tax_sets_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x80
        mpu.x = 0x00
        # $0000 TAX
        mpu.mem[0x0000] = 0xAA

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)

    def _test_tax_sets_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.x = 0xFF
        # $0000 TAX
        mpu.mem[0x0000] = 0xAA

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)

    # TAY

    def _test_tay_transfers_accumulator_into_y(self):
        mpu = Controller()
        mpu.a = 0xAB
        mpu.y = 0x00
        # $0000 TAY
        mpu.mem[0x0000] = 0xA8

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xAB, mpu.y)

    def _test_tay_sets_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.a = 0x80
        mpu.y = 0x00
        # $0000 TAY
        mpu.mem[0x0000] = 0xA8

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)

    def _test_tay_sets_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.a = 0x00
        mpu.y = 0xFF
        # $0000 TAY
        mpu.mem[0x0000] = 0xA8

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)

    # TSX

    def _test_tsx_transfers_stack_pointer_into_x(self):
        mpu = Controller()
        mpu.sp = 0xAB
        mpu.x = 0x00
        # $0000 TSX
        mpu.mem[0x0000] = 0xBA

        self.assertEqual(0xAB, mpu.sp)
        self.assertEqual(0xAB, mpu.x)

    def _test_tsx_sets_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.sp = 0x80
        mpu.x = 0x00
        # $0000 TSX
        mpu.mem[0x0000] = 0xBA

        self.assertEqual(0x80, mpu.sp)
        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)

    def _test_tsx_sets_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.sp = 0x00
        mpu.y = 0xFF
        # $0000 TSX
        mpu.mem[0x0000] = 0xBA

        self.assertEqual(0x00, mpu.sp)
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)

    # TXA

    def _test_txa_transfers_x_into_a(self):
        mpu = Controller()
        mpu.x = 0xAB
        mpu.a = 0x00
        # $0000 TXA
        mpu.mem[0x0000] = 0x8A

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xAB, mpu.x)

    def _test_txa_sets_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.x = 0x80
        mpu.a = 0x00
        # $0000 TXA
        mpu.mem[0x0000] = 0x8A

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(0x80, mpu.x)
        self.assertEqual(True, mpu.n)

    def _test_txa_sets_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.x = 0x00
        mpu.a = 0xFF
        # $0000 TXA
        mpu.mem[0x0000] = 0x8A

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(True, mpu.z)

    # TXS

    def _test_txs_transfers_x_into_stack_pointer(self):
        mpu = Controller()
        mpu.x = 0xAB
        # $0000 TXS
        mpu.mem[0x0000] = 0x9A

        self.assertEqual(0xAB, mpu.sp)
        self.assertEqual(0xAB, mpu.x)

    def _test_txs_does_not_set_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.x = 0x80
        # $0000 TXS
        mpu.mem[0x0000] = 0x9A

        self.assertEqual(0x80, mpu.sp)
        self.assertEqual(0x80, mpu.x)
        self.assertEqual(False, mpu.n)

    def _test_txs_does_not_set_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.x = 0x00
        # $0000 TXS
        mpu.mem[0x0000] = 0x9A

        self.assertEqual(0x00, mpu.sp)
        self.assertEqual(0x00, mpu.x)
        self.assertEqual(False, mpu.z)

    # TYA

    def _test_tya_transfers_y_into_a(self):
        mpu = Controller()
        mpu.y = 0xAB
        mpu.a = 0x00
        # $0000 TYA
        mpu.mem[0x0000] = 0x98

        self.assertEqual(0xAB, mpu.a)
        self.assertEqual(0xAB, mpu.y)

    def _test_tya_sets_negative_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.NEGATIVE)
        mpu.y = 0x80
        mpu.a = 0x00
        # $0000 TYA
        mpu.mem[0x0000] = 0x98

        self.assertEqual(0x80, mpu.a)
        self.assertEqual(0x80, mpu.y)
        self.assertEqual(True, mpu.n)

    def _test_tya_sets_zero_flag(self):
        mpu = Controller()
        mpu.p &= ~(mpu.ZERO)
        mpu.y = 0x00
        mpu.a = 0xFF
        # $0000 TYA
        mpu.mem[0x0000] = 0x98

        self.assertEqual(0x00, mpu.a)
        self.assertEqual(0x00, mpu.y)
        self.assertEqual(True, mpu.z)


if __name__ == '__main__':
    unittest.main()