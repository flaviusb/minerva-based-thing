from functools import reduce
from itertools import starmap
from operator import or_

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from ..isa import Prefix, Opcode, Funct3, Funct7, Funct12


__all__ = ["InstructionDecoder"]


class Type:
    R = 0
    I = 1
    S = 2
    B = 3
    U = 4
    J = 5


class InstructionDecoder(wiring.Component):
    instruction: In(32)
    rd:          Out(5)
    rd_we:       Out(1)
    rs1:         Out(5)
    rs1_re:      Out(1)
    rs2:         Out(5)
    rs2_re:      Out(1)
    immediate:   Out(signed(32))
    bypass_x:    Out(1)
    bypass_m:    Out(1)
    load:        Out(1)
    store:       Out(1)
    fence_i:     Out(1)
    fence:       Out(1)
    adder:       Out(1)
    adder_sub:   Out(1)
    logic:       Out(1)
    multiply:    Out(1)
    divide:      Out(1)
    shift:       Out(1)
    direction:   Out(1)
    sext:        Out(1)
    lui:         Out(1)
    auipc:       Out(1)
    jump:        Out(1)
    branch:      Out(1)
    compare:     Out(1)
    csr:         Out(1)
    csr_we:      Out(1)
    csr_fmt_i:   Out(1)
    csr_set:     Out(1)
    csr_clear:   Out(1)
    privileged:  Out(1)
    ecall:       Out(1)
    ebreak:      Out(1)
    mret:        Out(1)
    wfi:         Out(1)
    funct3:      Out(3)
    illegal:     Out(1)
    custom:      Out(1)

    def __init__(self, with_muldiv):
        self._with_muldiv = with_muldiv
        super().__init__()

    def elaborate(self, platform):
        m = Module()

        prefix = Signal(2)
        opcode = Signal(5)
        funct3 = Signal(3)
        funct7 = Signal(7)
        funct12 = Signal(12)

        iimm12 = Signal(signed(12))
        simm12 = Signal(signed(12))
        bimm12 = Signal(signed(13))
        uimm20 = Signal(20)
        jimm20 = Signal(signed(21))

        insn = self.instruction
        fmt = Signal(range(Type.J + 1))

        m.d.comb += [
            prefix.eq(insn[0:2]),
            opcode.eq(insn[2:7]),
            funct3.eq(insn[12:15]),
            funct7.eq(insn[25:32]),
            funct12.eq(insn[20:32]),

            iimm12.eq(insn[20:32]),
            simm12.eq(Cat(insn[7:12], insn[25:32])),
            bimm12.eq(Cat(0, insn[8:12], insn[25:31], insn[7], insn[31])),
            uimm20.eq(insn[12:32]),
            jimm20.eq(Cat(0, insn[21:31], insn[20], insn[12:20], insn[31])),
        ]

        with m.Switch(prefix):
            with m.Case(Prefix.U32):
                m.d.comb += self.custom.eq(0b0)
                with m.Switch(opcode):
                    with m.Case(Opcode.LUI):
                        m.d.comb += fmt.eq(Type.U)
                    with m.Case(Opcode.AUIPC):
                        m.d.comb += fmt.eq(Type.U)
                    with m.Case(Opcode.JAL):
                        m.d.comb += fmt.eq(Type.J)
                    with m.Case(Opcode.JALR):
                        m.d.comb += fmt.eq(Type.I)
                    with m.Case(Opcode.BRANCH):
                        m.d.comb += fmt.eq(Type.B)
                    with m.Case(Opcode.LOAD):
                        m.d.comb += fmt.eq(Type.I)
                    with m.Case(Opcode.STORE):
                        m.d.comb += fmt.eq(Type.S)
                    with m.Case(Opcode.OP_IMM_32):
                        m.d.comb += fmt.eq(Type.I)
                    with m.Case(Opcode.OP_32):
                        m.d.comb += fmt.eq(Type.R)
                    with m.Case(Opcode.MISC_MEM):
                        m.d.comb += fmt.eq(Type.I)
                    with m.Case(Opcode.SYSTEM):
                        m.d.comb += fmt.eq(Type.I)
            with m.Case(Prefix.CUSTOM):
                m.d.comb += self.custom.eq(0b1)

        with m.Switch(fmt):
            with m.Case(Type.I):
                m.d.comb += self.immediate.eq(iimm12)
            with m.Case(Type.S):
                m.d.comb += self.immediate.eq(simm12)
            with m.Case(Type.B):
                m.d.comb += self.immediate.eq(bimm12)
            with m.Case(Type.U):
                m.d.comb += self.immediate.eq(uimm20 << 12)
            with m.Case(Type.J):
                m.d.comb += self.immediate.eq(jimm20)

        m.d.comb += [
            self.rd.eq(insn[7:12]),
            self.rs1.eq(insn[15:20]),
            self.rs2.eq(insn[20:25]),

            self.rd_we.eq(reduce(or_, (fmt == T for T in (Type.R, Type.I, Type.U, Type.J))) &
                          ~(self.fence_i | self.fence)),
            self.rs1_re.eq(reduce(or_, (fmt == T for T in (Type.R, Type.I, Type.S, Type.B)))),
            self.rs2_re.eq(reduce(or_, (fmt == T for T in (Type.R, Type.S, Type.B)))),

            self.funct3.eq(funct3)
        ]

        def matcher(encodings):
            return reduce(or_, starmap(
                lambda opc, f3=None, f7=None, f12=None:
                    (prefix  == Prefix.U32)                    \
                  & (opcode  == opc if opc is not None else 1) \
                  & (funct3  == f3  if f3  is not None else 1) \
                  & (funct7  == f7  if f7  is not None else 1) \
                  & (funct12 == f12 if f12 is not None else 1),
                encodings))

        m.d.comb += [
            self.compare.eq(matcher([
                (Opcode.OP_IMM_32, Funct3.SLT,  None), # slti
                (Opcode.OP_IMM_32, Funct3.SLTU, None), # sltiu
                (Opcode.OP_32,     Funct3.SLT,  0),    # slt
                (Opcode.OP_32,     Funct3.SLTU, 0)     # sltu
            ])),
            self.branch.eq(matcher([
                (Opcode.BRANCH, Funct3.BEQ,  None), # beq
                (Opcode.BRANCH, Funct3.BNE,  None), # bne
                (Opcode.BRANCH, Funct3.BLT,  None), # blt
                (Opcode.BRANCH, Funct3.BGE,  None), # bge
                (Opcode.BRANCH, Funct3.BLTU, None), # bltu
                (Opcode.BRANCH, Funct3.BGEU, None)  # bgeu
            ])),

            self.adder.eq(matcher([
                (Opcode.OP_IMM_32, Funct3.ADD, None),       # addi
                (Opcode.OP_32,     Funct3.ADD, Funct7.ADD), # add
                (Opcode.OP_32,     Funct3.ADD, Funct7.SUB)  # sub
            ])),
            self.adder_sub.eq(self.rs2_re & (funct7 == Funct7.SUB)),

            self.logic.eq(matcher([
                (Opcode.OP_IMM_32, Funct3.XOR, None), # xori
                (Opcode.OP_IMM_32, Funct3.OR,  None), # ori
                (Opcode.OP_IMM_32, Funct3.AND, None), # andi
                (Opcode.OP_32,     Funct3.XOR, 0),    # xor
                (Opcode.OP_32,     Funct3.OR,  0),    # or
                (Opcode.OP_32,     Funct3.AND, 0)     # and
            ])),
        ]

        if self._with_muldiv:
            m.d.comb += [
                self.multiply.eq(matcher([
                    (Opcode.OP_32, Funct3.MUL,    Funct7.MULDIV), # mul
                    (Opcode.OP_32, Funct3.MULH,   Funct7.MULDIV), # mulh
                    (Opcode.OP_32, Funct3.MULHSU, Funct7.MULDIV), # mulhsu
                    (Opcode.OP_32, Funct3.MULHU,  Funct7.MULDIV), # mulhu
                ])),

                self.divide.eq(matcher([
                    (Opcode.OP_32, Funct3.DIV,  Funct7.MULDIV), # div
                    (Opcode.OP_32, Funct3.DIVU, Funct7.MULDIV), # divu
                    (Opcode.OP_32, Funct3.REM,  Funct7.MULDIV), # rem
                    (Opcode.OP_32, Funct3.REMU, Funct7.MULDIV)  # remu
                ])),
            ]

        m.d.comb += [
            self.shift.eq(matcher([
                (Opcode.OP_IMM_32, Funct3.SLL, 0),          # slli
                (Opcode.OP_IMM_32, Funct3.SR,  Funct7.SRL), # srli
                (Opcode.OP_IMM_32, Funct3.SR,  Funct7.SRA), # srai
                (Opcode.OP_32,     Funct3.SLL, 0),          # sll
                (Opcode.OP_32,     Funct3.SR,  Funct7.SRL), # srl
                (Opcode.OP_32,     Funct3.SR,  Funct7.SRA)  # sra
            ])),
            self.direction.eq(funct3 == Funct3.SR),
            self.sext.eq(funct7 == Funct7.SRA),

            self.lui.eq(opcode == Opcode.LUI),
            self.auipc.eq(opcode == Opcode.AUIPC),

            self.jump.eq(matcher([
                (Opcode.JAL,  None), # jal
                (Opcode.JALR, 0)     # jalr
            ])),

            self.load.eq(matcher([
                (Opcode.LOAD, Funct3.B),  # lb
                (Opcode.LOAD, Funct3.BU), # lbu
                (Opcode.LOAD, Funct3.H),  # lh
                (Opcode.LOAD, Funct3.HU), # lhu
                (Opcode.LOAD, Funct3.W)   # lw
            ])),
            self.store.eq(matcher([
                (Opcode.STORE, Funct3.B), # sb
                (Opcode.STORE, Funct3.H), # sh
                (Opcode.STORE, Funct3.W)  # sw
            ])),

            self.fence_i.eq(matcher([
                (Opcode.MISC_MEM, Funct3.FENCEI) # fence.i
            ])),
            self.fence.eq(matcher([
                (Opcode.MISC_MEM, Funct3.FENCE)  # fence
            ])),

            self.csr.eq(matcher([
                (Opcode.SYSTEM, Funct3.CSRRW),  # csrrw
                (Opcode.SYSTEM, Funct3.CSRRS),  # csrrs
                (Opcode.SYSTEM, Funct3.CSRRC),  # csrrc
                (Opcode.SYSTEM, Funct3.CSRRWI), # csrrwi
                (Opcode.SYSTEM, Funct3.CSRRSI), # csrrsi
                (Opcode.SYSTEM, Funct3.CSRRCI)  # csrrci
            ])),
            self.csr_we.eq(~funct3[1] | (self.rs1 != 0)),
            self.csr_fmt_i.eq(funct3[2]),
            self.csr_set.eq(~funct3[0] & funct3[1]),
            self.csr_clear.eq(funct3[0] & funct3[1]),

            self.privileged.eq((opcode == Opcode.SYSTEM) & (funct3 == Funct3.PRIV)),
            self.ecall.eq(self.privileged & (funct12 == Funct12.ECALL)),
            self.ebreak.eq(self.privileged & (funct12 == Funct12.EBREAK)),
            self.mret.eq(self.privileged & (funct12 == Funct12.MRET)),
            self.wfi.eq(self.privileged & (funct12 == Funct12.WFI)),

            self.bypass_x.eq(self.adder | self.logic | self.lui | self.auipc | self.csr),
            self.bypass_m.eq(self.compare | self.divide | self.shift),

            self.illegal.eq((self.instruction[1:2] != 0b1) | ~reduce(or_, (
                self.compare, self.branch, self.adder, self.logic, self.multiply, self.divide, self.shift,
                self.lui, self.auipc, self.jump, self.load, self.store,
                self.csr, self.ecall, self.ebreak, self.mret, self.wfi, self.fence_i, self.fence, self.custom
            )))
        ]

        return m
