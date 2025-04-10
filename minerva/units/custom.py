from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out


__all__ = ["Custom"]


class Custom(wiring.Component):
    custom:         In(1)
    pc:             In(30)
    result_value:   Out(32)
    result_addr:    Out(30)


    def elaborate(self, platform):
        m = Module()
        m.d.comb += [
                self.result_value.eq(self.pc),
                self.result_addr.eq(self.pc),
                ]
        return m

