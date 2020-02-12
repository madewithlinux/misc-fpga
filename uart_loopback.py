# uart_loopback.py
from nmigen import *
from nmigen.build import *
from nmigen_boards.tinyfpga_bx import *
from nmigen_boards.resources.interface import *
from nmigen_boards.resources.user import *
from nmigen_examples_uart import *


class UARTLoopback(Elaboratable):
    def __init__(self,
            uart_pins,
            led,
            odata):
        self.uart = UART(divisor=int(16e6//9600))
        # uart_pins = platform.request("uart")
        # led = platform.request("led", 0)
        # odata  = platform.request('outpins', 0)
        self.uart_pins = uart_pins
        self.led = led
        self.odata  = odata

    def elaborate(self, platform):
        m = Module()
        uart_pins = self.uart_pins
        led = self.led
        odata = self.odata

        uart = self.uart
        m.submodules += uart
        
        timer = Signal(20)
        empty = Signal(1, reset=1)
        data = Signal(8, reset=0xaa)

        m.d.sync += timer.eq(timer + 1)
        # m.d.comb += led.o.eq(timer[-1])

        m.d.comb += uart.rx_i.eq(uart_pins.rx)
        m.d.comb += uart_pins.tx.eq(uart.tx_o)

        m.d.comb += odata.o[0].eq(empty)
        m.d.comb += odata.o[1].eq(uart.tx_ack)
        m.d.comb += odata.o[2].eq(uart.tx_rdy)
        m.d.comb += odata.o[3].eq(uart.rx_ack)
        m.d.comb += odata.o[4].eq(uart.rx_rdy)

        with m.If(~empty):
            m.d.sync += uart.rx_ack.eq(0)
        with m.Elif(uart.rx_rdy & empty):
            m.d.sync += empty.eq(0)
            m.d.sync += data.eq(uart.rx_data)
            m.d.sync += uart.rx_ack.eq(1)

        # with m.If(uart.tx_ack):
        #     m.d.sync += empty.eq(1)
            # m.d.sync += uart.tx_rdy.eq(0)

        with m.If(uart.tx_rdy):
            m.d.sync += uart.tx_rdy.eq(0)
        with m.Elif((~empty) & uart.tx_ack):
            m.d.sync += uart.tx_rdy.eq(1)
            m.d.sync += uart.tx_data.eq(data)
            m.d.sync += empty.eq(1)


        # m.d.comb += [
        #     uart.tx_data.eq(0x61),
        #     uart.tx_rdy.eq(timer[-1])
        # ]

        m.d.comb += led.eq(uart.tx_ack)

        return m


# if __name__ == "__main__":
def synthesize():
    platform = TinyFPGABXPlatform()
    
    platform.add_resources([UARTResource("uart", 0,
        rx="A9", # 18
        tx="C9", # 17
    )])
    uart_pins = platform.request("uart")
    
    led = platform.request("led", 0)

    # outpins = [ Resource("outpins", 0, Pins("A2 A1 B1 C2 C1 D2 D1 E2 E1 G2 H1 J1 H2"), Attrs(IO_STANDARD="SB_LVCMOS")) ]
    outpins = [ Resource("outpins", 0, Pins("A2 A1 B1 C2 C1 D2 D1 E2 E1 G2 H1 J1 H2")) ]
    platform.add_resources(outpins)
    odata  = platform.request('outpins', 0)
    
    platform.build(UARTLoopback(uart_pins, led, odata), do_program=True)


if __name__ == "__main__":
    from nmigen.back.pysim import Simulator, Delay, Settle
    m = Module()
    uart_pins = signal()
    led = signal()
    odata = signal()
    m.submodules.uart_loopback = uart_loopback = UARTLoopback(uart_pins, led, odata)

    sim = Simulator(m)
    sim.add_clock(1e-6, domain="fast_clock")

    uart_tick = Delay(1/9600)
    def process():
        rx = uart_loopback.uart.rx_i
        yield x.eq(0)
        yield uart_tick
        for i in range(8):
            yield x.eq(i % 2 == 0)
            yield uart_tick
        yield x.eq(0)
        yield uart_tick
        yield uart_tick
        yield uart_tick

    sim.add_process(process) # or sim.add_sync_process(process), see below
    with sim.write_vcd("test.vcd", "test.gtkw", traces=[uart_loopback.uart.rx_i, uart_loopback.uart.tx_o]):
        sim.run()

