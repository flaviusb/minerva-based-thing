import unittest

from amaranth import *
from amaranth.sim import *

from minerva.isa import Funct3
from minerva.core import Minerva
from amaranth_soc import wishbone
from amaranth_soc.memory import MemoryMap, ResourceInfo
from amaranth_soc.wishbone.sram import WishboneSRAM
from amaranth_soc.wishbone.bus import Arbiter, Decoder
from amaranth.lib.wiring import connect

class MemChunk:
    def __init__(self, sram=True, size=1024, initial_data=[], starting_address=0):
        self._sram = sram
        self._size = size
        self._initial_data = initial_data
        self._starting_address = starting_address

def test_image(data=[MemChunk()], cycles=0, checks=[], vcd_output="dump.vcd"):
    def test(self):
        m = Module()
        m.submodules.cpu = cpu = Minerva()
        m.submodules.mem = mem = Decoder(addr_width=30, data_width=32, alignment=1, granularity=8)
        for i in range(len(data)):
            if data[i]._sram:
                m.submodules[f"ram_{i}"] = WishboneSRAM(size=data[i]._size, data_width=32, granularity=8, writable=True, init=data[i]._initial_data)
                mem.add(sub_bus=m.submodules[f"ram_{i}"].wb_bus, name=f"ram_{i}", addr=data[i]._starting_address)
            else:
                m.submodules[f"ram_{i}"] = WishboneSRAM(size=data[i]._size, data_width=32, granularity=8, writable=False, init=data[i]._initial_data) # 'Flash' memory
                mem.add(sub_bus=m.submodules[f"ram_{i}"].wb_bus, name=f"ram_{i}", addr=data[i]._starting_address)
        m.submodules.arb = arb = Arbiter(addr_width=30, data_width=32, granularity=8)
        arb.add(cpu.ibus)
        arb.add(cpu.dbus)
        connect(m, arb.bus, mem.bus)
        self.dut = m
        sim = Simulator(self.dut)

        async def testbench(ctx):
            for i in range(cycles):
                await ctx.tick()
            for i in range(len(checks)):
                pass

        sim.add_clock(1e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd(vcd_file=vcd_output):
            sim.run()

    return test


nop    = 0b00000000000000000000000000010011
custom = 0b00000000000000000000000000000010

class MinervaRomAndRamTestCase(unittest.TestCase):
    def setUp(self):
        pass

    # Test cases:

    test_many_nops = test_image(data=[MemChunk(initial_data=[nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop])],    cycles=28,  checks=[], vcd_output="test_nops.vcd")
    test_custom    = test_image(data=[MemChunk(initial_data=[custom,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,custom,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,custom,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,custom,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop,nop])], cycles=100, checks=[], vcd_output="test_custom.vcd")

