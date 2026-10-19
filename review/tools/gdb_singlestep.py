# gdb_singlestep.py — reviewer's independent single-step ground truth (gdb's own
# ptrace stepping; shares no code with any author tracer).
#
# usage:
#   START=<symbol> [END=<symbol>] [MAX=<steps>] [OUT=<file>] [NBYTES=<n>] \
#     gdb -q -batch -nx -x review/tools/gdb_singlestep.py --args ./target [args...]
#
# Breaks at START, then `stepi`s until PC == END's address (or MAX steps, or the
# inferior exits), logging one line per executed instruction:
#     <step> <pc-hex> <bytes-hex as in memory at that moment> <disassembly>
# Bytes are read immediately before each instruction executes, so for
# self-modifying code they are the bytes that actually ran. Without END, stepping
# stops when control returns past START's caller frame (finish-equivalent).
# Known gdb quirk: the instruction after a `syscall` can be logged twice (same
# PC on consecutive steps) — dedupe consecutive identical PCs after a syscall
# when comparing against a PT-decoded instruction stream.
import os

import gdb

start = os.environ["START"]
end = os.environ.get("END")
maxsteps = int(os.environ.get("MAX", "1000000"))
nbytes = int(os.environ.get("NBYTES", "16"))
out = open(os.environ.get("OUT", "/dev/stdout"), "w")

gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("set disassembly-flavor att")
gdb.execute(f"break {start}")
gdb.execute("run")
inf = gdb.selected_inferior()
end_addr = int(gdb.parse_and_eval(f"(long)&{end}")) if end else None
frame0 = gdb.selected_frame()
caller_sp = int(frame0.older().read_register("rsp")) if (not end and frame0.older()) else None

arch = frame0.architecture()
n = 0
while n < maxsteps:
    try:
        f = gdb.selected_frame()
    except gdb.error:
        break
    pc = int(f.pc())
    if end_addr is not None and pc == end_addr:
        break
    if caller_sp is not None and int(f.read_register("rsp")) > caller_sp:
        break
    raw = bytes(inf.read_memory(pc, nbytes))
    ins = arch.disassemble(pc)[0]
    length = ins["length"]
    out.write(f"{n} {pc:#x} {raw[:length].hex()} {ins['asm']}\n")
    n += 1
    try:
        gdb.execute("stepi", to_string=True)
    except gdb.error:
        break
out.write(f"# steps={n}\n")
out.close()
gdb.execute("kill")
