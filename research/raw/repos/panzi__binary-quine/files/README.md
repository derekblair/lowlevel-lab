Binary Quine
============

A Python script that generates a binary quine for x86\_64 Linux.
This quine writes itself to stdout without reading its own code.

Generate and test `build/quine` (and `build/quine.out`, which should be binary identical):

```
$ make
./mkasm.py
output is the same!
```
