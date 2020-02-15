# uart_loopback.py
from nmigen import *
from nmigen.build import *
from nmigen_boards.tinyfpga_bx import *
from nmigen_boards.resources.interface import *
from nmigen_boards.resources.user import *
from nmigen_examples_uart import *


class UARTCopy(Elaboratable):
    def __init__(self, uart_rx, uart_tx):
        self.rx_ack  = uart_rx.rx_ack
        self.rx_data = uart_rx.rx_data
        self.rx_rdy  = uart_rx.rx_rdy
        self.tx_ack  = uart_tx.tx_ack
        self.tx_data = uart_tx.tx_data
        self.tx_rdy  = uart_tx.tx_rdy

    def elaborate(self, platform):
        m = Module()

        rx_rdy_rising = Signal()
        last_rx_rdy = Signal()
        m.d.sync += last_rx_rdy.eq(self.rx_rdy)
        m.d.comb += rx_rdy_rising.eq((last_rx_rdy == False) & (self.rx_rdy == True))

        tx_ack_rising = Signal()
        last_tx_ack = Signal()
        m.d.sync += last_tx_ack.eq(self.tx_ack)
        m.d.comb += tx_ack_rising.eq((last_tx_ack == False) & (self.tx_ack == True))

        data = Signal(8)
        with m.FSM() as fsm:
            with m.State("WAIT_TO_RX"):
                with m.If(rx_rdy_rising):
                    m.d.sync += data.eq(self.rx_data)
                    m.d.sync += self.rx_ack.eq(1)
                    m.next = "DO_TX"

            with m.State("DO_TX"):
                m.d.comb += self.tx_data.eq(data)
                # m.next = "WAIT_FOR_TX_ACK"
                with m.If(tx_ack_rising):
                    m.next = "WAIT_TO_RX"
                with m.Else():
                    m.d.comb += self.tx_rdy.eq(1)

        return m


class UARTHighSpeedBridge(Elaboratable):
    def __init__(self, divisor=int(16e6//9600), fast_divisor=5):
        self.divisor = divisor
        self.fast_divisor = fast_divisor
        self.uart_tx = Signal()
        self.uart_rx = Signal()
        self.uart_high_tx = Signal()
        self.uart_high_rx = Signal()
        self.uart_low = UART(divisor=self.divisor)
        self.uart_high = UART(divisor=self.fast_divisor)

    def elaborate(self, platform):
        m = Module()

        uart_low = self.uart_low
        uart_high = self.uart_high

        m.submodules += uart_low
        m.submodules += uart_high

        m.d.comb += uart_low.rx_i.eq(self.uart_rx)
        m.d.comb += self.uart_tx.eq(uart_low.tx_o)
        m.d.comb += uart_high.rx_i.eq(self.uart_high_rx)
        m.d.comb += self.uart_high_tx.eq(uart_high.tx_o)

        copy_low_high = UARTCopy(uart_low, uart_high)
        copy_high_low = UARTCopy(uart_high, uart_low)
        m.submodules += copy_low_high
        m.submodules += copy_high_low

        return m

class LowHighSpeedLoopback(Elaboratable):
    def __init__(self, divisor=int(16e6//9600), fast_divisor=5):
        self.divisor = divisor
        self.fast_divisor = fast_divisor
        self.uart_tx = Signal()
        self.uart_rx = Signal()
        self.bridge = UARTHighSpeedBridge(divisor, fast_divisor)
        # self.uart_high_tx = self.bridge.uart_high_tx
        # self.uart_high_rx = self.bridge.uart_high_rx
        self.uart_high = UART(divisor=self.fast_divisor)
        self.fast_loopback = UARTCopy(self.uart_high, self.uart_high)

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.bridge
        m.submodules += self.uart_high
        m.submodules += self.fast_loopback

        m.d.comb += self.bridge.uart_rx.eq(self.uart_rx)
        m.d.comb += self.uart_tx.eq(self.bridge.uart_tx)

        m.d.comb += self.uart_high.rx_i.eq(self.bridge.uart_high_tx)
        m.d.comb += self.bridge.uart_high_rx.eq(self.uart_high.tx_o)

        return m

    def ports(self):
        return [
            self.uart_tx,
            self.uart_rx,
            self.uart_high.tx_o,
            self.uart_high.rx_i,
        ]


def synthesize():
    platform = TinyFPGABXPlatform()
    uart_baud = 115200
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

            m.submodules.uart_high_speed = uart_high_speed = UARTHighSpeedBridge(
                divisor=int(16e6/uart_baud),
                fast_divisor=16,
            )

            m.d.comb += uart_pins.tx.eq(uart_high_speed.uart_tx)
            m.d.comb += uart_high_speed.uart_rx.eq(uart_pins.rx)
            m.d.comb += uart_pins2.tx.eq(uart_high_speed.uart_high_tx)
            m.d.comb += uart_high_speed.uart_high_rx.eq(uart_pins2.rx)
            return m

    platform.build(Top(), do_program=True)



def simulate():
    from nmigen.back.pysim import Simulator, Delay, Settle
    uart_baud = 9600
    sim_clock_freq = uart_baud * 32

    m = Module()
    uart_tx = Signal()
    uart_rx = Signal()
    m.submodules.uart_high_speed = uart_high_speed = LowHighSpeedLoopback(divisor=int(sim_clock_freq/uart_baud))
    m.d.comb += uart_tx.eq(uart_high_speed.uart_tx)
    m.d.comb += uart_high_speed.uart_rx.eq(uart_rx)

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
    # with sim.write_vcd("test.vcd", "test.gtkw", traces=[uart_tx, uart_rx]):
    with sim.write_vcd("test.vcd", "test.gtkw", traces=uart_high_speed.ports()):
        sim.run()

if __name__ == '__main__':
    # simulate()
    synthesize()

