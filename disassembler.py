OPS = {
    0x00: "BRK",
    0x01: "INC",
    0x02: "POP",
    0x03: "DUP",
    0x04: "NIP",
    0x05: "SWP",
    0x06: "OVR",
    0x07: "ROT",
    0x08: "EQU",
    0x09: "NEQ",
    0x0a: "GTH",
    0x0b: "LTH",
    0x0c: "JMP",
    0x0d: "JCN",
    0x0e: "JSR",
    0x0f: "STH",
    0x10: "LDZ",
    0x11: "STZ",
    0x12: "LDR",
    0x13: "STR",
    0x14: "LDA",
    0x15: "STA",
    0x16: "DEI",
    0x17: "DEO",
    0x18: "ADD",
    0x19: "SUB",
    0x1a: "MUL",
    0x1b: "DIV",
    0x1c: "AND",
    0x1d: "ORA",
    0x1e: "EOR",
    0x1f: "SFT"
}

def disassemble(mem):
    op = mem[0]
    opcode = op & 0x1f
    s = (op & 0x20) != 0
    r = (op & 0x40) != 0
    k = (op & 0x80) != 0
    if opcode == 0x00 and k:
        print(f"#{mem[1]:02x}", end='')
        if s:
            print(f"{mem[2]:02x}", end='')
    else:
        print(OPS[opcode], end='')
        if s != 0:
            print('2', end='')
        if k != 0:
            print('k', end='')
        if r != 0:
            print('r', end='')
    print()