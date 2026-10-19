/*
 * verify_singlestep — INDEPENDENT ground-truth oracle for pt-truth (P2-4).
 *
 * Confirms, with NO Intel-PT in the loop, that the self-modified bytes of
 * version i really execute at step i. It single-steps its own execution with
 * the trap flag (TF) and a SIGTRAP handler (benign, own-process), and each time
 * the instruction pointer reaches the mutable region's `ret` it records EAX.
 * EAX there is whatever `mov eax, EXEC_TAG+i` loaded, i.e. the version that ran.
 * If the recorded EAX sequence is EXEC_TAG+0, +1, ... then the EXEC PTW payloads
 * that attribute.py scores against are trustworthy, established independently of
 * the PT decode path (perf is never opened here).
 *
 * usage: verify_singlestep VERSIONS  -> prints PASS/FAIL and exits 0/1
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <ucontext.h>

#define EXEC_TAG 0x5EC00000u
#define TF 0x100
#define MAPSZ 4096
#define RETOFF 9   /* ret is at code+9 (b8 imm32 | f3 0f ae e0 | c3) */

static unsigned char *code;
static volatile int stepping;
static unsigned results[4096];
static volatile int nres;

static void on_trap(int sig, siginfo_t *si, void *uc) {
    (void)sig; (void)si;
    greg_t *g = ((ucontext_t *)uc)->uc_mcontext.gregs;
    uintptr_t rip = (uintptr_t)g[REG_RIP];
    if (stepping && rip >= (uintptr_t)code && rip < (uintptr_t)code + MAPSZ) {
        if (rip == (uintptr_t)code + RETOFF && nres < (int)(sizeof results / sizeof results[0]))
            results[nres++] = (unsigned)g[REG_RAX];
        g[REG_EFL] |= TF;      /* keep stepping inside the region */
    } else {
        g[REG_EFL] &= ~TF;     /* stop stepping once we leave it */
    }
}

static const unsigned char PTWRITE_EAX[] = {0xf3, 0x0f, 0xae, 0xe0};

int main(int argc, char **argv) {
    int versions = argc > 1 ? atoi(argv[1]) : 24;
    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_trap; sa.sa_flags = SA_SIGINFO; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGTRAP, &sa, 0)) { perror("sigaction"); return 2; }

    code = mmap(0, MAPSZ, PROT_READ | PROT_WRITE | PROT_EXEC,
                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (code == MAP_FAILED) { perror("mmap"); return 2; }
    memset(code, 0xcc, MAPSZ);
    unsigned (*fn)(void) = (unsigned (*)(void))code;

    int ok = 1;
    for (int i = 0; i < versions; i++) {
        uint32_t payload = EXEC_TAG + (unsigned)i;
        code[0] = 0xb8; memcpy(code + 1, &payload, 4);
        memcpy(code + 5, PTWRITE_EAX, 4); code[RETOFF] = 0xc3;
        __asm__ volatile("mfence; lfence" ::: "memory");
        /* arm single-stepping: set TF, then call fn(); the handler steps through
         * the mutable region, records EAX at the ret, and disarms on exit. */
        stepping = 1;
        __asm__ volatile("pushfq\n\torl $0x100,(%%rsp)\n\tpopfq" ::: "cc", "memory");
        unsigned r = fn();
        stepping = 0;
        if (r != payload) { ok = 0; fprintf(stderr, "ver %d: fn()=%#x != %#x\n", i, r, payload); }
    }
    /* The single-stepped EAX-at-ret sequence must equal EXEC_TAG+0..versions-1. */
    if (nres != versions) { fprintf(stderr, "recorded %d results, expected %d\n", nres, versions); ok = 0; }
    for (int i = 0; i < nres && i < versions; i++)
        if (results[i] != EXEC_TAG + (unsigned)i) {
            fprintf(stderr, "step %d: EAX-at-ret=%#x != %#x\n", i, results[i], EXEC_TAG + i); ok = 0;
        }
    printf("verify_singlestep: %d versions, %d single-stepped ret-points, ground truth %s\n",
           versions, nres, ok ? "CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)" : "MISMATCH");
    return ok ? 0 : 1;
}
