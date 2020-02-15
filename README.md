# misc-fpga

This is a collection of miscellaneous fpga-related stuff I have written, and useful info/links/code snippets that I have found.

# compile and install yosys 0.9 (it was easy)
```bash
git clone https://github.com/cliffordwolf/yosys.git
cd yosys
make
make test
sudo make install
```

# install icestorm
```bash
sudo apt-get install build-essential clang bison flex libreadline-dev \
    gawk tcl-dev libffi-dev git mercurial graphviz \
    xdot pkg-config python python3 libftdi-dev \
    qt5-default python3-dev libboost-all-dev cmake
git clone https://github.com/cliffordwolf/icestorm.git icestorm
cd icestorm
make -j$(nproc)
sudo make install
```

# install nextpnr-ice40
```bash
sudo apt install cmake qtbase5-dev libeigen3-dev libboost-iostreams1.65-dev
# /\ or \/
sudo apt install cmake qtbase5-dev libeigen3-dev libboost-iostreams1.58-dev
sudo apt install python3-dev # maybe don't need this?
sudo apt install python3.6-dev # maybe don't need this?

git clone git@github.com:YosysHQ/nextpnr.git
cd nextpnr
cmake -DARCH=ice40 .
make -j$(nproc)
sudo make install
```

# setup nmigen
```bash
pipenv install git+https://github.com/m-labs/nmigen.git#egg=nmigen
pipenv install git+https://github.com/m-labs/nmigen-boards.git#egg=nmigen-boards
sudo apt install gtkwave
```
vscode seems to detect pipenv well enough

# useful links

https://github.com/enjoy-digital/litex

nmigen tutorial https://github.com/RobertBaruch/nmigen-tutorial

micropython on fpga https://fupy.github.io/

tinyfpga BX nmigen platform https://github.com/m-labs/nmigen-boards/blob/master/nmigen_boards/tinyfpga_bx.py

verilog tutorial
http://www.asic-world.com/verilog/veritut.html
http://www.asic-world.com/verilog/verilog_one_day4.html

uart
https://en.wikipedia.org/wiki/Universal_asynchronous_receiver-transmitter

