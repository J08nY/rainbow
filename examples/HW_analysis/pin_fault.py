#!/usr/bin/env python3

import numpy as np
from rainbow.devices.stm32 import rainbow_stm32f215 as rainbow_stm32
from rainbow.utils.plot import viewer

# Pick any reference pin (STORED_PIN) and a different input pin
# Goal is to make 'storage_containsPin' function return a non-null
# value, which would mean the code executes as if the user PIN
# was correct although it was not

STORED_PIN = "1874"
INPUT_PIN = "0000"

print("Setting up emulator")

e = rainbow_stm32(sca_mode=True)
e.load("trezor.elf")
e.trace = 0

def result(u):
  """ Test whether execution was faulted """
  return u['r0'] != 0 and u['pc'] == 0xaaaaaaaa

# as in the side-channel example, this is the location of the reference
# pin in Flash
e[0x08008110 + 0x189] = bytes(STORED_PIN + "\x00", "ascii")

# Pick any address for the input pin...
e[0xcafecafe] = bytes(INPUT_PIN + "\x00", "ascii")

N = 57

total_faults = 0
total_crashes = 0
fault_trace = [0] * N
crash_trace = [0] * N

print("Loop on all possible skips")
print("r0 should be 0 at the end of the function if no fault occurred") 
for i in range(1, N):
    e.reset()

    ## The first fault might not actually work depending
    ## on the value of r5 when calling. Remove comment to observe
    # e['r5'] = 0x60000000  

    e['r0'] = 0xcafecafe 
    e['lr'] = 0xaaaaaaaa

    e.start(e.functions['storage_containsPin'], 0xaaaaaaaa, count=i)

    pc = e['pc']
    d = e.disassemble_single(pc, 4)
    e.print_asmline(pc, d[2], d[3])

    # instruction skip : resume execution at pc + current instruction size 
    ret = e.start(pc+d[1], 0xaaaaaaaa, count=100)

    if not ret:
      if result(e):
        total_faults += 1
        fault_trace[i] = 1
        print(" <-- r0 =", hex(e['r0']))
    else:
      total_crashes += 1
      crash_trace[i] = 1
      print("crashed")

print(f"\n=== {total_faults} faults found ===")
print(f"=== {total_crashes} crashes ===")

# get an 'original' side channel trace
e.reset()

e.trace = 1
e.trace_regs = 1
e.mem_trace = 0

e['r0'] = 0xcafecafe 
e['lr'] = 0xaaaaaaaa

e.start(e.functions['storage_containsPin'], 0xaaaaaaaa)

# list(map(print, e.sca_address_trace))

trace = np.array(e.sca_values_trace, dtype=np.uint8)
fault_trace = trace.max() - np.array(fault_trace, dtype=np.uint8)[:trace.shape[0]] * trace.max() 
# crash_trace = -trace.max() + np.array(crash_trace, dtype=np.uint8)[:trace.shape[0]] * trace.max()

# viewer(e.sca_address_trace, np.array([trace, fault_trace, crash_trace]))
viewer(e.sca_address_trace, np.array([trace, fault_trace]), highlight=1)
