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
struct torn_ctx { int writer_cpu, exec_cpu; unsigned char *code; int straddle; _Atomic int stop; };
static void *torn_writer(void *arg) {
    struct torn_ctx *c = arg;
    pin(c->writer_cpu);
    volatile unsigned char *imm = c->code + c->straddle + 1; /* imm8 of mov al,imm */
    while (!atomic_load_explicit(&c->stop, memory_order_relaxed)) {
        *imm = 0; *imm = 1;
    }
    return 0;
}
static int do_torn(int writer_cpu, int exec_cpu) {
    struct torn_ctx c; memset(&c, 0, sizeof c);
    c.writer_cpu = writer_cpu; c.exec_cpu = exec_cpu; c.code = make_code_page();
    /* Place "mov al,imm8 ; ret" so the 2-byte mov straddles a 64B boundary. */
    c.straddle = 64 - 1;
    c.code[c.straddle] = 0xb0;     /* mov al, imm8 */
    c.code[c.straddle + 1] = 0x00; /* imm8 (written 0/1 by the other core) */
    c.code[c.straddle + 2] = 0xc3; /* ret */
    pin(exec_cpu);
    int (*fn)(void) = (int (*)(void))(c.code + c.straddle);
    pthread_t wt; pthread_create(&wt, 0, torn_writer, &c);
    const long N = 5 * 1000 * 1000; long torn = 0, ones = 0, zeros = 0;
    for (long i = 0; i < N; i++) { int v = fn() & 0xff; if (v == 0) zeros++; else if (v == 1) ones++; else torn++; }
    atomic_store(&c.stop, 1); pthread_join(wt, 0);
    printf("torn,%d,%s,%d,%s,-,%ld,%ld,%ld\n",
           exec_cpu, core_class(exec_cpu), writer_cpu, core_class(writer_cpu),
           torn, zeros, ones);
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
