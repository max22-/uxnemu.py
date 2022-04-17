#!/usr/bin/env python3

import sys

class StackOverflow(Exception):
    pass

class StackUnderflow(Exception):
    pass

class Stack:
    def __init__(self):
        self.array = bytearray(0x100)
        self.view = memoryview(self.array)
        self.ptr = 0

    def push8(self, v):
        if self.ptr >= 0xff:
            raise StackOverflow()
        self.view[self.ptr] = v & 0xff
        self.ptr += 1

    def push16(self, v):
        if self.ptr >= 0xfe:
            raise StackOverflow()
        self.view[self.ptr] = (v & 0xff00) >> 8
        self.view[self.ptr+1] = v & 0xff
        self.ptr += 2

    def pop8(self):
        if self.ptr < 1:
            raise StackUnderflow()
        v = self.view[self.ptr]
        self.ptr -= 1
        return v

    def pop16(self):
        if self.ptr < 2:
            raise StackUnderflow()
        self.ptr -= 2
        v = self.view[self.ptr] << 8
        v |= self.view[self.ptr+1]
        return v

    def __repr__(self):
        return str([hex(self.array[i]) for i in range(self.ptr)])

class Uxn:
    page_program = 0x100
    def __init__(self):
        self.ram_array = bytearray(0x10000)
        self.ram = memoryview(self.ram_array)
        self.wst = Stack()
        self.rst = Stack()
        self.dev_array = [bytearray(0x10) for i in range(0x10)]
        self.dev = [memoryview(d) for d in self.dev_array]
        self.pc = 0
        self.halted = False
        self.s = False
        self.r = False
        self.k = False

    def load(self, rom):
        self.ram[Uxn.page_program:Uxn.page_program + len(rom)] = rom

    def eval(self, pc):
        self.halted = False
        self.pc = pc
        while not self.halted:
            self.step()

    def step(self):
        op = self.ram[self.pc]
        if self.pc == 0 or op == 0:
            self.halt()
            return
        opcode = op & 0x1f
        self.s = True if op & 0x20 else False
        self.r = True if op & 0x40 else False
        self.k = True if op & 0x80 else False

        if opcode == 0x00: # LIT
            if self.s:
                self.wst.push16(self.peek16(self.pc + 1))
                self.pc += 3
            else:
                self.wst.push8(self.peek8(self.pc + 1))
                self.pc += 2
        else:
            self.pc += 1

    def push(self, stack, v):
        pass

    def pop(self, stack):
        pass

    def peek8(self, addr):
        return self.ram[addr]

    def peek16(self, addr):
        return (self.ram[addr] << 8) | (self.ram[addr+1] & 0xff)

    def poke(self):
        pass

    def halt(self):
        print("Halted")
        self.halted = True

    def __repr__(self):
        return "wst: " + self.wst.__repr__() + "\nrst: " + self.rst.__repr__()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: uxnemu.py file.rom")

    with open(sys.argv[1], 'rb') as f:
        rom = f.read()

    print(f"{len(rom)} bytes")
    print(rom)

    uxn = Uxn()
    uxn.load(rom)
    uxn.eval(Uxn.page_program)
    print(uxn)
