#!/usr/bin/python3



from collections import namedtuple
import re
import argparse

# Some helpful constant values that we'll be using.
Constants = namedtuple("Constants",["NUM_REGS", "MEM_SIZE", "REG_SIZE"])
constants = Constants(NUM_REGS = 8, 
                      MEM_SIZE = 2**13,
                      REG_SIZE = 2**16)

def load_machine_code(machine_code, mem):
    """
    Loads an E20 machine code file into the list
    provided by mem. We assume that mem is
    large enough to hold the values in the machine
    code file.
    sig: list(str) -> list(int) -> NoneType
    """
    machine_code_re = re.compile("^ram\[(\d+)\] = 16'b(\d+);.*$")
    expectedaddr = 0
    for line in machine_code:
        match = machine_code_re.match(line)
        if not match:
            raise ValueError("Can't parse line: %s" % line)
        addr, instr = match.groups()
        addr = int(addr,10)
        instr = int(instr,2)
        if addr != expectedaddr:
            raise ValueError("Memory addresses encountered out of sequence: %s" % addr)
        if addr >= len(mem):
            raise ValueError("Program too big for memory")
        expectedaddr += 1
        mem[addr] = instr

def print_state(pc, regs, memory, memquantity):
    """
    Prints the current state of the simulator, including
    the current program counter, the current register values,
    and the first memquantity elements of memory.
    sig: int -> list(int) -> list(int) - int -> NoneType
    """
    print("Final state:")
    print("\tpc="+format(pc,"5d"))
    for reg, regval in enumerate(regs):
        print(("\t$%s=" % reg)+format(regval,"5d"))
    line = ""
    for count in range(memquantity):
        line += format(memory[count], "04x")+ " "
        if count % 8 == 7:
            print(line)
            line = ""
    if line != "":
        print(line)


#simulater function. According to the opcode,
#split instruction into three possible functions to analyze
def simulation(pc, regs, memory):
    instruction = memory[pc % 8192]
    # Instructions with three register arguments
    if (instruction & 57344) >> 13 == 0b000:
        return instruction_3R(instruction, pc, regs, memory)
    # Instructions with no register arguments
    elif ((instruction & 57344) >> 13) == 0b010 or ((instruction & 57344) >> 13 == 0b011):
        return instruction_0R(instruction, pc, regs, memory)
    #Instructions with two register arguments
    else:
        return instruction_2R(instruction, pc, regs, memory)


#if the given instruction with three register arguments
def instruction_3R(instruction, pc, regs, memory):
    regSrcA = (instruction & 7168) >> 10
    regSrcB = (instruction & 896) >> 7
    regDst = (instruction & 112) >> 4
    opcode = (instruction & 15)

    if opcode == 0b1000: #jr
        pc = regs[regSrcA]
        return valid_pc(pc), regs, memory

    # if a program tries to change the value of $0, do nothing
    if regDst == 0b0:
        return valid_pc(pc + 1), regs, memory

    if opcode == 0b0000:
        regs[regDst] = keep_16bits(regs[regSrcA] + regs[regSrcB])
    elif opcode == 0b0001:
        regs[regDst] = keep_16bits(regs[regSrcA] - regs[regSrcB])
    elif opcode == 0b0010:
        regs[regDst] = keep_16bits(regs[regSrcA] | regs[regSrcB])
    elif opcode == 0b0011:
        regs[regDst] = keep_16bits(regs[regSrcA] & regs[regSrcB])
    elif opcode == 0b0100:
        if regs[regSrcA] < regs[regSrcB]:
            regs[regDst] = 0b1
        else:
            regs[regDst] = 0b0
    return valid_pc(pc + 1), regs, memory


#if given instruction with two register arguments
def instruction_2R(instruction, pc, regs, memory):
    opcode = (instruction & 57344) >> 13
    regSrc = (instruction & 7168) >> 10
    regDst = (instruction & 896) >> 7
    imm = instruction & 127

    # if a program tries to change the value of $0, do nothing
    if regDst == 0b000:
        if opcode == 0b111 or opcode == 0b100 or opcode == 0b001:
            return valid_pc(pc + 1), regs, memory

    if opcode == 0b111: #slti
        if regs[regSrc] < sign_extend_7(imm):
            regs[regDst] = 0b1
        else:
            regs[regDst] = 0b0
        return valid_pc(pc + 1), regs, memory
    elif opcode == 0b100: #lw
        val = (regs[regSrc] + sign_number_converter(imm, 7)) & 8191
        regs[regDst] = keep_16bits(memory[val])
        return valid_pc(pc + 1), regs, memory
    elif opcode == 0b101: #sw
        val = (regs[regSrc] + sign_number_converter(imm, 7)) & 8191
        memory[val] = regs[regDst]
        return valid_pc(pc + 1), regs, memory
    elif opcode == 0b110: # jeq
        if regs[regSrc] == regs[regDst]:
            pc = (pc + 1 + sign_number_converter(imm, 7))
            return valid_pc(pc), regs, memory
        else:
            return valid_pc(pc + 1), regs, memory
    elif opcode == 0b001: #addi
        regs[regDst] = keep_16bits(regs[regSrc] + sign_number_converter(imm, 7))
        return valid_pc(pc + 1), regs, memory


#given instruction with no register arguments
def instruction_0R(instruction, pc, regs, memory):
    opcode = (instruction & 57344) >> 13
    imm = instruction & 8191
    if opcode == 0b010:
        pc = imm
    elif opcode == 0b011:
        regs[7] = keep_16bits(pc + 1)
        pc = imm
    return valid_pc(pc), regs, memory


#given a 7 bit number, do the sign extend
def sign_extend_7(num):
    left_most_bit = (num & 64) >> 6
    if left_most_bit == 0b1:
        return 65408 | num
    else:
        return num


#produce sign number, which can be positive or negative
def sign_number_converter(num, bits):
    left_most_bit = (num & 64) >> 6
    if left_most_bit == 0b1:
        bitmask = (1 << bits) - 1
        return -((num ^ bitmask) + 1)
    else:
        return num


#keep the memory address to be valid
#make sure the address is inside the range of valid address
def valid_pc(pc):
    return pc % 65536


#keep the number to be 16 bits number
def keep_16bits(num):
    bitmask = (1 << 16) - 1
    return num & bitmask


def main():

    parser = argparse.ArgumentParser(description='Simulate E20 machine')
    parser.add_argument('filename', help='The file containing machine code, typically with .bin suffix')
    cmdline = parser.parse_args()

    #initialize program counter, value of registers, and value of all memory
    pc = 0
    regs = [0] * constants.NUM_REGS
    memory = [0] * constants.MEM_SIZE

    with open(cmdline.filename) as file:
        #pass # TODO: your code here. Load file and parse using load_machine_code
        load_machine_code(file, memory)


    # TODO: your code here. Do simulation.
    old_pc = pc
    while True:
        new_pc, new_regs, new_memory = simulation(old_pc, regs, memory)
        if new_pc == old_pc:
            if memory[old_pc % 8191] >> 13 == 0b010: #j indicate halt
                break
        #update pc, reg and memory
        old_pc = new_pc
        regs = new_regs
        memory = new_memory
    # TODO: your code here. print the final state of the simulator before ending, using print_state
    print_state(new_pc, new_regs, new_memory, 128)

if __name__ == "__main__":
    main()
