/*
 * smcobs — self-modifying-code observatory for hybrid x86 (benign, own-process)
 *
 * One measurement per invocation (no cross-point state bleed), printed as one
 * CSV row on stdout. A shell driver (run.sh) loops over cpu x placement x
 * store-offset x repeats; report.py aggregates into medians, an ANSI heatmap,
 * and machine-checkable verdicts.
 *
 * SUBCOMMANDS
 *   sweep   CPU CODE_OFF STORE_OFF EVENT
 *       Place a 6-byte function (mov eax,0 ; ret) at BASE+CODE_OFF in an RWX
 *       page, then N times: store one byte at BASE+STORE_OFF and call the
 *       function. Count EVENT on this core's PMU. This is the SMC
 *       self-modify-then-execute cost, as a function of the store's distance
 *       from the executing code. STORE_OFF must not overlap [CODE_OFF,CODE_OFF+6).
 *   xcore  WRITER_CPU EXEC_CPU EVENT
 *       Cross-modifying code: a writer thread pinned to WRITER_CPU rewrites a
 *       byte of a shared RWX code page; an executor thread pinned to EXEC_CPU
 *       runs that code in a loop. Count EVENT on the EXECUTOR. Reports clears
 *       per million executes. Benign: both are threads of THIS process; nothing
 *       is transmitted — we report machine-clear counts, not a channel.
 *   torn   WRITER_CPU EXEC_CPU
 *       Writer flips an instruction that straddles a 64-byte line boundary
 *       between two encodings that return 0 vs 1; executor records how many
 *       reads were neither (a torn fetch). Reports mismatch count. Observed
 *       behaviour on this part, not a guarantee.
 *
 * EVENT names resolve to (event,umask) per core class, from Intel perfmon
 * PTL @8da58930a226 (cross-checked against the local kernel pmu-events):
 *   Cougar Cove (P, cpu_core):  SMC=0xC3/0x04  COUNT=0xC3/0x01   (XMC: none)
 *   Darkmont (E/LP-E, cpu_atom): SMC=0xC3/0x01  XMC=0xC3/0x80  ANY=0xC3/0x00
 * Only own task is counted (exclude_kernel/hv), which perf_event_paranoid=2
 * permits. No RDPMC, no kernel counts, no other process is touched.
 */
#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <x86intrin.h>

#define PAGE 4096
#define MAPSZ (64 * 1024)
#define NITER 200000

static int pin(int cpu) {
    cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu, &s);
    return sched_setaffinity(0, sizeof s, &s);
}

/* P-cores are CPUs 0-3 on this part; everything else is Darkmont (cpu_atom). */
static const char *pmu_name(int cpu) { return cpu < 4 ? "cpu_core" : "cpu_atom"; }
static const char *core_class(int cpu) {
    if (cpu < 4) return "P";
    if (cpu < 12) return "E";
    return "LP-E";
}
static int pmu_type(const char *n) {
    char p[160]; int t = -1;
    snprintf(p, sizeof p, "/sys/bus/event_source/devices/%s/type", n);
    FILE *f = fopen(p, "r");
    if (f) { if (fscanf(f, "%d", &t) != 1) t = -1; fclose(f); }
    return t;
}
/* Returns config (event|umask<<8) for EVENT on the core's class, or ~0 if the
 * event does not exist on that class (e.g. XMC on a P-core). */
static uint64_t event_config(int cpu, const char *ev) {
    int p = cpu < 4;  /* P-core? */
    if (!strcmp(ev, "smc"))   return p ? 0x04c3 : 0x01c3;
    if (!strcmp(ev, "count")) return p ? 0x01c3 : 0x00c3; /* P COUNT / atom ANY */
    if (!strcmp(ev, "xmc"))   return p ? ~0ULL  : 0x80c3; /* XMC: Darkmont only */
    return ~0ULL;
}
static int open_counter(int cpu, const char *ev) {
    uint64_t cfg = event_config(cpu, ev);
    if (cfg == ~0ULL) return -2;  /* event absent on this class */
    struct perf_event_attr a; memset(&a, 0, sizeof a);
    a.size = sizeof a;
    a.type = pmu_type(pmu_name(cpu));
    a.config = cfg;
    a.exclude_kernel = 1; a.exclude_hv = 1; a.disabled = 1;
    return syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
}

static unsigned char *make_code_page(void) {
    unsigned char *p = mmap(0, MAPSZ, PROT_READ | PROT_WRITE | PROT_EXEC,
                            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); exit(1); }
    memset(p, 0xcc, MAPSZ);  /* int3 everywhere so a stray fetch traps */
    return p;
}
/* mov eax,0 ; ret  at p+off (6 bytes). */
static void emit_ret0(unsigned char *p, int off) {
    p[off] = 0xb8; memset(p + off + 1, 0, 4); p[off + 5] = 0xc3;
}

static int do_sweep(int cpu, int code_off, int store_off, const char *ev) {
    if (pin(cpu)) { perror("affinity"); return 1; }
    if (store_off >= code_off && store_off < code_off + 6) {
        fprintf(stderr, "store_off overlaps code\n"); return 2;
    }
    int fd = open_counter(cpu, ev);
    if (fd == -2) {  /* event not available on this class: emit NA row */
        printf("sweep,%d,%s,%s,%d,%d,%s,NA,NA,0\n",
               cpu, core_class(cpu), pmu_name(cpu), code_off, store_off, ev);
        return 0;
    }
    if (fd < 0) { perror("perf_event_open"); return 1; }
    unsigned char *p = make_code_page();
    emit_ret0(p, code_off);
    int (*fn)(void) = (int (*)(void))(p + code_off);
    volatile unsigned char *t = p + store_off;
    long sum = 0;
    ioctl(fd, PERF_EVENT_IOC_RESET, 0);
    ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    uint64_t t0 = __rdtsc();
    for (int i = 0; i < NITER; i++) { *t = 0xcc; sum += fn(); }
    uint64_t t1 = __rdtsc();
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    uint64_t c = 0;
    if (read(fd, &c, sizeof c) != sizeof c) { perror("read"); return 1; }
    printf("sweep,%d,%s,%s,%d,%d,%s,%.4f,%.1f,%ld\n",
           cpu, core_class(cpu), pmu_name(cpu), code_off, store_off, ev,
           (double)c / NITER, (double)(t1 - t0) / NITER, sum);
    munmap(p, MAPSZ); close(fd);
    return 0;
}

/* ---- cross-modifying-code experiment ---------------------------------- */
struct xcore_ctx {
    int writer_cpu, exec_cpu;
    unsigned char *code;
    _Atomic int stop;
    _Atomic unsigned long writes;
};
static void *xcore_writer(void *arg) {
    struct xcore_ctx *c = arg;
    if (pin(c->writer_cpu)) { perror("writer affinity"); }
    volatile unsigned char *imm = c->code + 1;  /* the imm32 of mov eax,imm */
    unsigned long w = 0;
    while (!atomic_load_explicit(&c->stop, memory_order_relaxed)) {
        *imm = (unsigned char)(w & 0xff);
        w++;
    }
    atomic_store(&c->writes, w);
    return 0;
}
static int do_xcore(int writer_cpu, int exec_cpu, const char *ev) {
    struct xcore_ctx c; memset(&c, 0, sizeof c);
    c.writer_cpu = writer_cpu; c.exec_cpu = exec_cpu;
    c.code = make_code_page();
    emit_ret0(c.code, 0);  /* mov eax,0 ; ret — writer scribbles the imm */
    if (pin(exec_cpu)) { perror("exec affinity"); return 1; }
    int fd = open_counter(exec_cpu, ev);
    int have = (fd >= 0);
    if (fd == -2)
        fprintf(stderr, "(event %s absent on executor class %s)\n", ev, core_class(exec_cpu));
    int (*fn)(void) = (int (*)(void))c.code;
    pthread_t wt;
    if (pthread_create(&wt, 0, xcore_writer, &c)) { perror("pthread"); return 1; }
    const long N = 5 * 1000 * 1000; long sum = 0;
    if (have) { ioctl(fd, PERF_EVENT_IOC_RESET, 0); ioctl(fd, PERF_EVENT_IOC_ENABLE, 0); }
    uint64_t t0 = __rdtsc();
    for (long i = 0; i < N; i++) sum += fn();
    uint64_t t1 = __rdtsc();
    if (have) ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    atomic_store(&c.stop, 1);
    pthread_join(wt, 0);
    uint64_t cc = 0;
    if (have && read(fd, &cc, sizeof cc) != sizeof cc) { perror("read"); return 1; }
    printf("xcore,%d,%s,%d,%s,%s,%.4f,%.1f,%lu\n",
           exec_cpu, core_class(exec_cpu), writer_cpu, core_class(writer_cpu), ev,
           have ? (double)cc * 1e6 / N : -1.0,       /* clears per million executes */
           (double)(t1 - t0) / N,                    /* tsc per execute */
           atomic_load(&c.writes));
    if (have) close(fd);
    munmap(c.code, MAPSZ);
    (void)sum;
    return 0;
}

/* ---- torn-fetch probe -------------------------------------------------- */
/*
 * A torn instruction fetch is one where the two cache lines that hold a single
 * instruction are fetched from DIFFERENT code versions, yielding bytes that were
 * never coherently in memory. To make that detectable, put `mov eax, imm32`
 * (B8 + 4 imm bytes) with the imm32 STRADDLING a 64-byte line: opcode at
 * off=61, imm32 at 62..65, so the low 16 bits (62,63) sit in line 0 and the
 * high 16 bits (64,65) sit in line 1.
 *   A = 0x11112222  (low16=0x2222 @62/63, high16=0x1111 @64/65)
 *   B = 0x33334444  (low16=0x4444,        high16=0x3333)
 * The writer updates each half with ONE aligned 2-byte store, and orders them so
 * memory only ever holds A, B or the intermediate 0x33332222 (A->B: high half
 * first; B->A: low half first). On x86-TSO stores are not reordered, so
 * 0x11114444 (high from A, low from B) is never written. An executor that reads
 * eax == 0x11114444 therefore fetched the two lines from different versions:
 * a genuine torn fetch. (On this Intel part the expected result is 0 — strong
 * I-fetch coherence — but the probe now HAS the power to detect a tear; see
 * README.) The ret (C3) lives safely in line 1 at off=66.
 */
#define TORN_A 0x11112222u
#define TORN_B 0x33334444u
#define TORN_TORN 0x11114444u   /* high(A) | low(B): never coherently in memory */
#define TORN_MID 0x33332222u    /* high(B) | low(A): the legitimate intermediate */
#define TORN_OFF 61
struct torn_ctx { int writer_cpu, exec_cpu; unsigned char *code; _Atomic int stop; };
static void *torn_writer(void *arg) {
    struct torn_ctx *c = arg;
    pin(c->writer_cpu);
    volatile uint16_t *lo = (uint16_t *)(c->code + TORN_OFF + 1);      /* imm bytes 62,63 */
    volatile uint16_t *hi = (uint16_t *)(c->code + TORN_OFF + 3);      /* imm bytes 64,65 */
    while (!atomic_load_explicit(&c->stop, memory_order_relaxed)) {
        /* A -> B: write high half first (A, 0x33332222, B) */
        *hi = (uint16_t)(TORN_B >> 16); *lo = (uint16_t)(TORN_B & 0xffff);
        /* B -> A: write low half first (B, 0x33332222, A) */
        *lo = (uint16_t)(TORN_A & 0xffff); *hi = (uint16_t)(TORN_A >> 16);
    }
    return 0;
}
static int do_torn(int writer_cpu, int exec_cpu) {
    struct torn_ctx c; memset(&c, 0, sizeof c);
    c.writer_cpu = writer_cpu; c.exec_cpu = exec_cpu; c.code = make_code_page();
    c.code[TORN_OFF] = 0xb8;                              /* mov eax, imm32 */
    *(uint32_t *)(c.code + TORN_OFF + 1) = TORN_A;        /* imm32 @62..65 */
    c.code[TORN_OFF + 5] = 0xc3;                          /* ret @66 (line 1) */
    pin(exec_cpu);
    unsigned (*fn)(void) = (unsigned (*)(void))(c.code + TORN_OFF);
    pthread_t wt;
    if (pthread_create(&wt, 0, torn_writer, &c)) { perror("pthread"); return 1; }
    const long N = 5 * 1000 * 1000;
    long torn = 0, legit = 0, other = 0;
    for (long i = 0; i < N; i++) {
        unsigned v = fn();
        if (v == TORN_A || v == TORN_B || v == TORN_MID) legit++;
        else if (v == TORN_TORN) torn++;
        else other++;  /* any other value is also a tear (half-store non-atomicity) */
    }
    atomic_store(&c.stop, 1); pthread_join(wt, 0);
    printf("torn,%d,%s,%d,%s,-,%ld,%ld,%ld\n",
           exec_cpu, core_class(exec_cpu), writer_cpu, core_class(writer_cpu),
           torn + other, legit, torn);  /* field7 = all torn (incl 'other'), field9 = exact 0x11114444 */
    munmap(c.code, MAPSZ);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: smcobs sweep|xcore|torn ...\n"); return 2; }
    if (!strcmp(argv[1], "sweep") && argc == 6)
        return do_sweep(atoi(argv[2]), atoi(argv[3]), atoi(argv[4]), argv[5]);
    if (!strcmp(argv[1], "xcore") && argc == 5)
        return do_xcore(atoi(argv[2]), atoi(argv[3]), argv[4]);
    if (!strcmp(argv[1], "torn") && argc == 4)
        return do_torn(atoi(argv[2]), atoi(argv[3]));
    fprintf(stderr, "bad args\n");
    return 2;
}
