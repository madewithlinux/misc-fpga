# uart_loopback.py
from nmigen import *
from nmigen.build import *
from nmigen_boards.tinyfpga_bx import *
from nmigen_boards.resources.interface import *
from nmigen_boards.resources.user import *
from nmigen_examples_uart import *


class UARTLoopback(Elaboratable):
    def __init__(self, divisor=int(16e6//9600)):
        self.uart = UART(divisor=divisor)
        self.uart_tx = Signal()
        self.uart_rx = Signal()

    def elaborate(self, platform):
        m = Module()

        uart = self.uart
        m.submodules += uart

        timer = Signal(20)
        empty = Signal(1, reset=1)
        data = Signal(8, reset=0xaa)

        m.d.sync += timer.eq(timer + 1)

        m.d.comb += uart.rx_i.eq(self.uart_rx)
        m.d.comb += self.uart_tx.eq(uart.tx_o)

        with m.If(~empty):
            m.d.sync += uart.rx_ack.eq(0)
        with m.Elif(uart.rx_rdy & empty):
            m.d.sync += empty.eq(0)
            m.d.sync += data.eq(uart.rx_data)
            m.d.sync += uart.rx_ack.eq(1)

        with m.If(uart.tx_rdy):
            m.d.sync += uart.tx_rdy.eq(0)
        with m.Elif((~empty) & uart.tx_ack):
            m.d.sync += uart.tx_rdy.eq(1)
            m.d.sync += uart.tx_data.eq(data)
            m.d.sync += empty.eq(1)

        return m


if __name__ == "__main__":
    uart_baud = 9600
    sim_clock_freq = uart_baud * 4
    from nmigen.back.pysim import Simulator, Delay, Settle
    m = Module()
    uart_tx = Signal()
    uart_rx = Signal()
    m.submodules.uart_loopback = uart_loopback = UARTLoopback(divisor=int(sim_clock_freq/uart_baud))
    m.d.comb += uart_tx.eq(uart_loopback.uart_tx)
    m.d.comb += uart_loopback.uart_rx.eq(uart_rx)

    sim = Simulator(m)
    sim.add_clock(1/sim_clock_freq, domain="sync")
    # sim.add_clock(1e-6, domain="fast_clock")

    uart_tick = Delay(1/uart_baud)
    def process():
        rx = uart_rx
        yield rx.eq(1)
        yield uart_tick
        for i in range(1):
            # start bit
            yield rx.eq(0)
            yield uart_tick
            # 8 data bits
            for i in range(1,9):
                yield rx.eq(i % 2 == 1)
                yield uart_tick
            # one stop bit
            yield rx.eq(1)
            yield uart_tick
            # pause
            for i in range(5):
                yield uart_tick
        for i in range(50):
            yield uart_tick

    sim.add_process(process) # or sim.add_sync_process(process), see below
    with sim.write_vcd("test.vcd", "test.gtkw", traces=[uart_tx, uart_rx]):
        sim.run()

