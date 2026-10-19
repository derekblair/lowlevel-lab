#!/usr/bin/env python3
"""strace_audit.py LOG ROOT [ROOT ...] — audit an `strace -f -o LOG` capture.

Flags, per REVIEW-00 §2.2/§2.4:
  WRITE / FS-MUTATE   write-mode open or path mutation outside ROOTs, /tmp, /dev/{null,tty,pts,shm}
  REL-WRITE-OUT       relative-path write-mode open resolved (via tracked per-pid cwd) outside the roots
  (chdir itself is informational: shells walk /home/... and come straight back; v1 flagged
   that as CHDIR-OUT, a false positive found on BUILD-02's capture)
  NETWORK             AF_INET/AF_INET6 socket/connect/sendto/sendmsg/bind
  EXEC-PRIV/NET       exec of sudo/su/pkexec/doas/curl/wget/ssh/scp/nc/socat
  PTRACE-ATTACH       PTRACE_ATTACH / PTRACE_SEIZE (attaching to a non-child)
  FOREIGN-WRITE       process_vm_writev
Informational: UNIX-SOCKET (e.g. glibc NSS), counts of relative-path writes.
Exit status: 0 clean, 1 if any blocking class was found.
"""
import os
import re
import sys

BLOCKING = ("WRITE", "REL-WRITE-OUT", "FS-MUTATE", "NETWORK", "EXEC-PRIV/NET",
            "PTRACE-ATTACH", "FOREIGN-WRITE")
WRITE_FLAGS = re.compile(r"O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND")
MUTATORS = {"rename", "renameat", "renameat2", "unlink", "unlinkat", "mkdir",
            "mkdirat", "rmdir", "symlink", "symlinkat", "link", "linkat",
            "truncate", "chmod", "fchmodat"}
LINE = re.compile(r"^(\d+)\s+(\w+)\((.*)$")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    log = sys.argv[1]
    allowed = [os.path.realpath(r) for r in sys.argv[2:]]
    allowed += ["/tmp", "/dev/null", "/dev/tty", "/dev/pts", "/dev/shm",
                "/proc/self", "/proc/thread-self"]

    def inside(path):
        p = os.path.realpath(path)
        return any(p == a or p.startswith(a.rstrip("/") + "/") for a in allowed)

    found = {}
    relative_writes = 0
    cwd = {}  # pid -> tracked cwd (only for pids we saw chdir in)
    for ln in open(log, errors="replace"):
        m = LINE.match(ln)
        if not m:
            continue
        pid, call, rest = m.groups()
        failed = re.search(r"\)\s+=\s+-1\b", rest) is not None
        paths = re.findall(r'"([^"]*)"', rest)
        cls = None
        if call in ("open", "openat", "creat") and paths and not failed:
            if call == "creat" or WRITE_FLAGS.search(rest):
                if paths[0].startswith("/"):
                    cls = None if inside(paths[0]) else "WRITE"
                else:
                    relative_writes += 1
                    if pid in cwd and not inside(os.path.join(cwd[pid], paths[0])):
                        cls = "REL-WRITE-OUT"
        elif call in MUTATORS and not failed:
            if any(p.startswith("/") and not inside(p) for p in paths):
                cls = "FS-MUTATE"
        elif call == "chdir" and paths and not failed:
            new = paths[0] if paths[0].startswith("/") else os.path.join(cwd.get(pid, "/"), paths[0])
            cwd[pid] = os.path.normpath(new)
        elif call in ("connect", "sendto", "sendmsg", "bind", "socket"):
            if re.search(r"AF_INET6?\b|PF_INET6?\b", rest):
                cls = "NETWORK"
            elif "AF_UNIX" in rest or "AF_LOCAL" in rest or "PF_LOCAL" in rest:
                cls = "UNIX-SOCKET"
        elif call in ("execve", "execveat") and paths and not failed:
            if re.search(r"/(sudo|su|pkexec|doas|curl|wget|ssh|scp|nc|ncat|socat)$", paths[0]):
                cls = "EXEC-PRIV/NET"
        elif call == "ptrace" and not failed and re.search(r"PTRACE_(ATTACH|SEIZE)", rest):
            cls = "PTRACE-ATTACH"
        elif call == "process_vm_writev":
            cls = "FOREIGN-WRITE"
        if cls:
            found.setdefault(cls, []).append(ln.rstrip())

    print(f"strace audit of {log}")
    print(f"  allowed write roots: {', '.join(allowed)}")
    print(f"  relative-path write-mode opens (resolved against cwd): {relative_writes}")
    bad = False
    for cls in BLOCKING + ("UNIX-SOCKET",):
        lines = found.get(cls, [])
        tag = "BLOCKING" if cls in BLOCKING and lines else ("info" if lines else "none")
        print(f"  {cls:14s} {len(lines):5d}  [{tag}]")
        for ln in lines[:8]:
            print(f"      {ln[:220]}")
        bad |= cls in BLOCKING and bool(lines)
    print("  RESULT:", "FINDINGS (see above)" if bad else "CLEAN")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
