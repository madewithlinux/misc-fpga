# uart loopback
Also with a low to high-speed bridge.
On my tinyfpga BX, the high speed bridge worked at the max frequency (16MHz/4=4MHz).

Proof on scope of high speed uart (but this time at only 1MHz)
![high speed uart](uart_high_speed_loopback_working.png)

Writing this was a good introduction to states and stuff in verilog/nMigen