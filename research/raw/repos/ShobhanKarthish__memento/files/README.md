# Memento

> A tiny bytecode VM you can run forward and backward.

Memento is a small stack-based virtual machine written in Rust. Give it a text
file with simple maths instructions, then run it normally, watch a trace, or
move through it one instruction at a time.

It is intentionally small. The point is to make bytecode execution and
time-travel debugging easy to understand.

## Try it

You need the Rust toolchain.

```bash
git clone https://github.com/ShobhanKarthish/memento.git
cd memento
cargo run -- examples/math.mem
# result: 5
```

## The program format

Memento reads one instruction per line. Empty lines and everything after `#`
are ignored.

| Instruction | What it does |
| --- | --- |
| `push <number>` | Puts a number on the stack. |
| `add` | Removes two numbers and pushes their sum. |
| `subtract` | Removes two numbers and pushes left minus right. |
| `multiply` | Removes two numbers and pushes their product. |
| `halt` | Stops the program. |

For example, [`examples/math.mem`](examples/math.mem) calculates
`(2 + 3) * 4 - 15`:

```text
push 2
push 3
add
push 4
multiply
push 15
subtract
halt
```

## Run modes

### Normal mode

```bash
cargo run -- examples/math.mem
```

### Trace mode

Trace mode shows the next instruction and the stack before and after it.

```bash
cargo run -- examples/math.mem --trace
```

See a complete, reproducible [demo transcript](examples/demo-output.txt).

### Debug mode

Debug mode lets you run a single instruction at a time.

```bash
cargo run -- examples/math.mem --debug
```

| Key | What it does |
| --- | --- |
| `n` | Run the next instruction. |
| `b` | Restore the stack and instruction pointer from before the last instruction. |
| `q` | Quit the debugger. |

## Test it

```bash
cargo test
```

## How reverse stepping works

Before Memento runs an instruction, it saves a small snapshot containing the
stack and instruction pointer. Pressing `b` restores the most recent snapshot.
It is simple and not memory-efficient yet, but it makes the idea easy to see.
