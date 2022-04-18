#!/usr/bin/env python3

import sys
import disassembler

class StackOverflow(Exception):
    pass

class StackUnderflow(Exception):
    pass

def signed(u8):
    if u8 & 0x80:
        return -(0x100 - u8)
    else:
        return u8

class Stack:
    def __init__(self):
        self.array = bytearray(0x100)
        self.view = memoryview(self.array)
        self.ptr = 0
        self.kptr = 0
        self.k = False

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
        if self.k:
            ptr = self.kptr
        else:
            ptr = self.ptr
        if ptr < 1:
            raise StackUnderflow()
        ptr -= 1
        v = self.view[ptr]
        if self.k:
            self.kptr = ptr
        else:
            self.ptr = ptr
        return v

    def pop16(self):
        if self.k:
            ptr = self.kptr
        else:
            ptr = self.ptr
        if self.ptr < 2:
            raise StackUnderflow()
        ptr -= 2
        v = self.view[ptr] << 8
        v |= self.view[ptr+1]
        if self.k:
            self.kptr = ptr
        else:
            self.ptr = ptr
        return v

    def keep(self, mode):
        self.k = mode
        self.kptr = self.ptr

    def __repr__(self):
        return str([hex(self.array[i]) for i in range(self.ptr)])

class Uxn:
    page_program = 0x100
    def __init__(self):
        self.ram_array = bytearray(0x10000)
        self.ram = memoryview(self.ram_array)
        self.wst = Stack()
        self.rst = Stack()
        self.dev_array = bytearray(0x100)
        self.dev = memoryview(self.dev_array)
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

    def set_pc(self, pc):
        self.pc = pc

    def step(self):
        if self.pc == 0:
            self.halt()
            return
        op = self.ram[self.pc]
        self.pc += 1
        if op == 0:
            self.halt()
            return
        opcode = op & 0x1f
        self.s = True if op & 0x20 else False
        if op & 0x40:
            self.r = True
            self.src = self.rst
            self.dst = self.wst
        else:
            self.r = False
            self.src = self.wst
            self.dst = self.rst
        self.k = True if op & 0x80 else False
        self.src.keep(self.k) # set keep mode and initialize kptr

        if opcode == 0x00:   # LIT
            self.push(self.src, self.peek(self.pc))
            self.pc += 2 if self.s else 1
        elif opcode == 0x01: # INC
            a = self.pop()
            a += 1
            self.push(self.src, a)
        elif opcode == 0x02: # POP
            self.pop()
        elif opcode == 0x03: # NIP
            b = self.pop()
            self.pop()
            self.push(self.src, b)
        elif opcode == 0x04: # SWP
            b = self.pop()
            a = self.pop()
            self.push(self.src, b)
            self.push(self.src, a)
        elif opcode == 0x05: # ROT
            c = self.pop()
            b = self.pop()
            a = self.pop()
            self.push(self.src, b)
            self.push(self.src, c)
            self.push(self.src, a)
        elif opcode == 0x06: # DUP
            a = self.pop()
            self.push(self.src, a)
            self.push(self.src, a)  
        elif opcode == 0x07: # OVR
            b = self.pop()
            a = self.pop()
            self.push(self.src, a)
            self.push(self.src, b)
            self.push(self.src, a)
        elif opcode == 0x08: # EQU
            b = self.pop()
            a = self.pop()
            if a == b:
                self.src.push8(0x01)
            else:
                self.src.push8(0x00)
        elif opcode == 0x09: # NEQ
            b = self.pop()
            a = self.pop()
            if a != b:
                self.src.push8(0x01)
            else:
                self.src.push8(0x00)
        elif opcode == 0x0a: # GTH:
            b = self.pop()
            a = self.pop()
            if a > b:
                self.src.push8(0x01)
            else:
                self.src.push8(0x00)
        elif opcode == 0x0b: # LTH
            b = self.pop()
            a = self.pop()
            if a < b:
                self.src.push8(0x01)
            else:
                self.src.push8(0x00)
        elif opcode == 0x0c: # JMP
            a = self.pop()
            self.jump(a)
        elif opcode == 0x0d: # JCN
            a = self.pop()
            flag = self.src.pop8()
            if flag != 0:
                self.jump(a)
        elif opcode == 0x0e: # JSR
            a = self.pop()
            self.dst.push16(self.pc)
            self.jump(a)
        elif opcode == 0x0f: # STH
            a = self.pop()
            self.push(self.dst, a)
        elif opcode == 0x10: # LDZ
            a = self.src.pop8()
            v = self.peek(a)
            self.push(self.src, v)
        elif opcode == 0x11: # STZ
            a = self.src.pop8()
            v = self.pop()
            self.poke(a, v)
        elif opcode == 0x12: # LDR
            a = signed(self.src.pop8())
            v = self.peek(self.pc + a)
            self.push(self.src, v)
        elif opcode == 0x13: # STR
            a = signed(self.src.pop8())
            v = self.pop()
            self.poke(self.pc + a, v)
        elif opcode == 0x14: # LDA
            a = self.src.pop16()
            v = self.peek(a)
            self.push(self.src, v)
        elif opcode == 0x15: # STA
            a = self.src.pop16()
            v = self.pop()
            self.poke(a, v)
        elif opcode == 0x16: # DEI
            a = self.src.pop8()
            self.push(self.src, self.devr(a))
        elif opcode == 0x17: # DEO
            a = self.src.pop8()
            v = self.pop()
            self.devw(a, v)
        elif opcode == 0x18: # ADD
            b = self.pop()
            a = self.pop()
            self.push(self.src, a + b)
        elif opcode == 0x19: # SUB
            b = self.pop()
            a = self.pop()
            self.push(self.src, a - b)
        elif opcode == 0x1a: # MUL
            b = self.pop()
            a = self.pop()
            self.push(self.src, a * b)
        elif opcode == 0x1b: # DIV
            b = self.pop()
            a = self.pop()
            self.push(self.src, a // b)
        elif opcode == 0x1c: # AND
            b = self.pop()
            a = self.pop()
            self.push(self.src, a & b)
        elif opcode == 0x1d: # ORA
            b = self.pop()
            a = self.pop()
            self.push(self.src, a | b)
        elif opcode == 0x1e: # EOR
            b = self.pop()
            a = self.pop()
            self.push(self.src, a ^ b)
        elif opcode == 0x1f: # SFT
            b = self.src.pop8()
            a = self.pop()
            left = (b & 0xf0) >> 4
            right = b & 0x0f
            self.push(self.src, a >> right << left)

    def push(self, stack, v):
        if self.s:
            stack.push16(v)
        else:
            stack.push8(v)

    def pop(self):
        if self.s:
            return self.src.pop16()
        else:
            return self.src.pop8()

    def peek8(self, addr):
        return self.ram[addr]

    def peek16(self, addr):
        return (self.ram[addr] << 8) | (self.ram[addr+1] & 0xff)

    def peek(self, addr):
        if self.s:
            return self.peek16(addr)
        else:
            return self.peek8(addr)

    def poke8(self, addr, v):
        self.ram[addr] = v

    def poke16(self, addr, v):
        self.ram[addr] = (v & 0xff00) >> 8
        self.ram[addr+1] = v & 0xff

    def poke(self, addr, v):
        if self.s:
            self.poke16(addr, v)
        else:
            self.poke8(addr, v)

    def jump(self, a):
        if self.s:
            self.pc = a
        else:
            self.pc += signed(a)

    def devr(self, a):
        v = self.dei(a)
        if self.s:
            v = v << 8 | self.dei((a+1) & 0xff)
        return v

    def devw(self, a, v):
        if self.s:
            self.deo(a, v >> 8)
            self.deo((a + 1) & 0xff, v & 0xff)
        else:
            self.deo(a, v & 0xff)

    def dei(self, a):
        return self.dev[a]

    def deo(self, a, v):
        self.dev[a] = v

    def get_vec(self, a):
        a = a & 0xf0
        return (self.dev[a] << 8) | self.dev[a+1]

    def halt(self):
        self.halted = True

    def __repr__(self):
        res = (f"wst: {self.wst}\n"
               f"rst: {self.rst}\n"
               f"pc: {hex(self.pc)}\n")
        if not self.halted:
            res += f"next instruction: {disassembler.disassemble(uxn.ram[uxn.pc:])}"
        return res
        
class Varvara(Uxn):
    def dei(self, a):
        return super().dei(a)

    def deo(self, a, v):
        super().deo(a, v)
        if a == 0x18:
            sys.stdout.write(chr(v))

    def getchar(self):
        c = sys.stdin.read(1)
        if len(c) == 0:
            return False
        self.dev_array[0x12] = ord(c)
        vec = self.get_vec(0x10)
        if vec != 0:
            uxn.eval(vec)
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: uxnemu.py file.rom")
        sys.exit(1)

    print(f"Loading {sys.argv[1]}...")
    with open(sys.argv[1], 'rb') as f:
        rom = f.read()

    print(f"{len(rom)} bytes")
    print()

    uxn = Varvara()
    uxn.load(rom)

    if len(sys.argv) == 3 and sys.argv[2] == "-d":
        # step debugging
        uxn.set_pc(Uxn.page_program)
        print(uxn)
        while not uxn.halted:
            input()
            uxn.step()
            print(uxn)
            print()
    else:
        uxn.eval(Uxn.page_program)
        print("")
        print(uxn)
        while uxn.getchar():
            pass
            
        sys.exit(0)



    

        
    
