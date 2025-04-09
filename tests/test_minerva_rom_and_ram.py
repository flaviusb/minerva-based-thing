import unittest

from amaranth import *
from amaranth.sim import *

from minerva.isa import Funct3
from minerva.core import Minerva
from amaranth_soc import wishbone
from amaranth_soc.wishbone.sram import WishboneSRAM
from amaranth_soc.wishbone.bus import Arbiter
from amaranth.lib.wiring import connect

def test_image(data=[], cycles=0, checks=[]):
    def test(self):
        m = Module()
        m.submodules.cpu = cpu = Minerva()
        m.submodules.sram = sram = WishboneSRAM(size=4294967296, data_width=32, granularity=8, writable=True, init=data)
        m.submodules.arb = arb = Arbiter(addr_width=30, data_width=32, granularity=8)
        arb.add(cpu.ibus)
        arb.add(cpu.dbus)
        connect(m, arb.bus, sram.wb_bus)
        self.dut = m
        sim = Simulator(self.dut)

        async def testbench(ctx):
            for i in range(cycles):
                await ctx.tick()
            for i in range(len(checks)):
                pass

        sim.add_clock(1e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd(vcd_file="dump.vcd"):
            sim.run()

    return test


class MinervaRomAndRamTestCase(unittest.TestCase):
    def setUp(self):
        pass

    # Test cases:

    test_all_zeros = test_image([], 10, [])

