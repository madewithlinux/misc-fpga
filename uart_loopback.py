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

        m.d.comb += uart.rx_i.eq(self.uart_rx)
        m.d.comb += self.uart_tx.eq(uart.tx_o)

        data = Signal(8)
        with m.FSM() as fsm:
            with m.State("WAIT_RX_LOW"):
                with m.If(~uart.rx_rdy):
                    m.d.sync += uart.rx_ack.eq(0)
                    m.next = "WAIT_TO_RX"

            with m.State("WAIT_TO_RX"):
                with m.If(uart.rx_rdy):
                    m.d.sync += data.eq(uart.rx_data)
                    m.d.sync += uart.rx_ack.eq(1)
                    m.next = "DO_TX"

            with m.State("DO_TX"):
                m.d.comb += uart.tx_rdy.eq(1)
                m.d.comb += uart.tx_data.eq(data)
                m.next = "WAIT_FOR_TX_ACK"

            with m.State("WAIT_FOR_TX_ACK"):
                with m.If(uart.tx_ack):
                    m.next = "WAIT_RX_LOW"

        return m


def simulate():
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

    uart_tick = Delay(1/uart_baud)
    def process():
        rx = uart_rx
        yield rx.eq(1)
        yield uart_tick
        for i in range(4):
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
            for i in range(30):
                yield uart_tick

    sim.add_process(process) # or sim.add_sync_process(process), see below
    with sim.write_vcd("test.vcd", "test.gtkw", traces=[uart_tx, uart_rx]):
        sim.run()

def synthesize():
    platform = TinyFPGABXPlatform()
    platform.add_resources([UARTResource("uart", 0,
        rx="A9", # 18
        tx="C9", # 17
    )])
    platform.add_resources([UARTResource("uart", 1,
        rx="A2", # pin 1
        tx="A1", # pin 2
    )])

    class Top(Elaboratable):
        def elaborate(self, platform):
            uart_pins = platform.request("uart", 0)
            uart_pins2 = platform.request("uart", 1)
            m = Module()
            m.submodules.uart_loopback = uart_loopback = UARTLoopback(divisor=int(16e6/115200))
            m.d.comb += uart_pins.tx.eq(uart_loopback.uart_tx)
            m.d.comb += uart_pins2.tx.eq(uart_loopback.uart_tx)
            m.d.comb += uart_loopback.uart_rx.eq(uart_pins.rx & uart_pins2.rx)
            return m
    
    platform.build(Top(), do_program=True)

if __name__ == '__main__':
    # simulate()
    synthesize()

