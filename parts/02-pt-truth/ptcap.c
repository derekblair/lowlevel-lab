/*
 * ptcap — capture an Intel-PT trace of a self-modifying target, for the
 * version-attribution head-to-head (REVIEW-01-build P2-3). Benign: traces only
 * this process's own user-mode code (perf_event_paranoid=2, exclude_kernel/hv).
 *
 * The target holds a mutable 1-instruction region in an RWX page. "Version i"
 * writes `mov eax, EXEC_TAG+i ; ptwrite eax ; ret` there; executing it emits an
 * EXEC PTWRITE whose payload = EXEC_TAG+i. That payload is GROUND TRUTH: it was
 * produced by executing the self-modified bytes, so it says which version really
 * ran. Separately, a cooperative in-band FENCE `ptwrite FENCE_TAG+i` is emitted
 * right before the patch+exec (what a PTWRITE-aware JIT would emit). An external
 * patch log records (i, rdtsc) at each patch, for the time-keyed decoder.
 *
 * A tunable spin of DELAY cycles sits between the recorded patch tsc and the
 * execution, so the patch->execute interval can be swept: small DELAY makes the
 * exec and the next patch fall within one timing-packet bucket, where a
 * time-keyed decoder cannot tell which side of the patch the exec was on.
 *
 * Outputs (paths from argv): <trace.pt> raw AUX bytes; <sideband> the
 * perf_event_mmap_page time params + DATA records; <patchlog> CSV of
 * (version,tsc_at_patch); <truth> CSV of (exec_seq,version) ground truth.
 *
 * usage: ptcap VERSIONS DELAY TIMING(coarse|fine) OUTDIR
 */
#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <x86intrin.h>
#include <cpuid.h>

#define EXEC_TAG  0x5EC00000ULL
#define FENCE_TAG 0xFE0C0000ULL
#define MAPSZ 4096

static long rd(const char *p) {
    FILE *f = fopen(p, "r"); long v = -1;
    if (f) { if (fscanf(f, "%ld", &v) != 1) v = -1; fclose(f); }
    return v;
}

int main(int argc, char **argv) {
    if (argc != 5) { fprintf(stderr, "usage: ptcap VERSIONS DELAY coarse|fine OUTDIR\n"); return 2; }
    int versions = atoi(argv[1]);
    uint64_t delay = strtoull(argv[2], 0, 0);
    int fine = !strcmp(argv[3], "fine");
    const char *outdir = argv[4];

    /* config: pt | ptw | tsc | mtc [| cyc]. We deliberately do NOT set `branch`
     * (bit 13): this experiment reads only PTW + timing packets, never control
     * flow, so disabling branch tracing keeps the tunable spin-delay loop from
     * flooding the AUX ring with TNT packets (which caused OVF / dropped FENCEs).
     * coarse = MTC period 3, no CYC; fine = densest MTC + CYC. */
    uint64_t cfg = (1ULL << 0) | (1ULL << 12) | (1ULL << 10) | (1ULL << 9);
    /* mtc_period is a period index validated against caps/mtc_periods; this
     * kernel accepts 3 and 0 but not 5 (checked empirically). fine = smallest
     * period (densest MTC) + CYC cycle-accurate deltas; coarse = period 3, no
     * CYC, so timing resolution is deliberately low. */
    if (fine) {
        cfg |= (1ULL << 1);                 /* cyc */
        cfg |= ((uint64_t)0 << 14);         /* mtc_period = 0 (densest) */
        cfg |= ((uint64_t)1 << 19);         /* cyc_thresh = 1 */
    } else {
        cfg |= ((uint64_t)3 << 14);         /* mtc_period = 3 (coarser), no CYC */
    }
    struct perf_event_attr a; memset(&a, 0, sizeof a);
    a.size = sizeof a;
    a.type = (uint32_t)rd("/sys/bus/event_source/devices/intel_pt/type");
    a.config = cfg;
    a.exclude_kernel = 1; a.exclude_hv = 1; a.disabled = 1;
    int fd = syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
    if (fd < 0) { perror("perf_event_open(intel_pt)"); return 1; }

    long pg = sysconf(_SC_PAGESIZE);
    size_t data = (1 + 8) * pg, aux = 1024 * pg;  /* 4 MiB AUX ring: headroom vs OVF */
    struct perf_event_mmap_page *up = mmap(0, data, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (up == MAP_FAILED) { perror("mmap data"); return 1; }
    up->aux_offset = data; up->aux_size = aux;
    unsigned char *ab = mmap(0, aux, PROT_READ | PROT_WRITE, MAP_SHARED, fd, data);
    if (ab == MAP_FAILED) { perror("mmap aux"); return 1; }

    unsigned char *code = mmap(0, MAPSZ, PROT_READ | PROT_WRITE | PROT_EXEC,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (code == MAP_FAILED) { perror("mmap code"); return 1; }
    memset(code, 0xcc, MAPSZ);

    char path[512];
    snprintf(path, sizeof path, "%s/patchlog.csv", outdir);
    FILE *pl = fopen(path, "w"); fprintf(pl, "version,tsc_at_patch\n");
    snprintf(path, sizeof path, "%s/truth.csv", outdir);
    FILE *tr = fopen(path, "w"); fprintf(tr, "exec_seq,version\n");

    /* mutable region layout, 12 bytes at code+0:
     *   b8 <imm32>        mov eax, EXEC_TAG+i
     *   0f 01 f9/?? -> we need PTWRITE eax. PTWRITE r32 = F3 0F AE E0 (/4, modrm e0=eax).
     *   c3                ret
     * ptwrite eax encoding: F3 0F AE E0. */
    static const unsigned char PTWRITE_EAX[] = {0xf3, 0x0f, 0xae, 0xe0};
    unsigned (*fn)(void) = (unsigned (*)(void))code;

    ioctl(fd, PERF_EVENT_IOC_RESET, 0);
    ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    /* Warm-up: PT needs a few packets after ENABLE before the first PSB/TSC
     * settle, which can clip the very first FENCE at the ring start. Emit a few
     * throwaway FENCE PTWs (version 0xFFFF, ignored by the decoder) so every
     * MEASURED version's fence is captured. */
    for (int w = 0; w < 4; w++)
        __asm__ volatile("ptwrite %0" :: "r"((uint64_t)(FENCE_TAG + 0xFFFFu)));
    for (int i = 0; i < versions; i++) {
        /* patch version i into the mutable region */
        uint32_t payload = (uint32_t)(EXEC_TAG + (unsigned)i);
        uint64_t tsc = __rdtsc();
        fprintf(pl, "%d,%llu\n", i, (unsigned long long)tsc);
        code[0] = 0xb8;                                 /* mov eax, imm32 */
        memcpy(code + 1, &payload, 4);
        memcpy(code + 5, PTWRITE_EAX, 4);               /* ptwrite eax */
        code[9] = 0xc3;                                 /* ret */
        /* serialize so the new code is what executes (benign own-process SMC) */
        __asm__ volatile("mfence; lfence" ::: "memory");
        /* in-band cooperative FENCE: a PTWRITE-aware JIT would emit this */
        uint64_t fence = FENCE_TAG + (unsigned)i;
        __asm__ volatile("ptwrite %0" :: "r"(fence));
        /* tunable patch->execute interval */
        for (volatile uint64_t d = 0; d < delay; d++) { }
        /* execute version i: emits EXEC PTW with payload = EXEC_TAG+i (truth) */
        fn();
        fprintf(tr, "%d,%u\n", i, (unsigned)i);
    }
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    fclose(pl); fclose(tr);

    uint64_t head = __atomic_load_n(&up->aux_head, __ATOMIC_ACQUIRE);
    snprintf(path, sizeof path, "%s/trace.pt", outdir);
    FILE *tf = fopen(path, "wb");
    uint64_t n = head < aux ? head : aux;
    fwrite(ab, 1, n, tf); fclose(tf);

    snprintf(path, sizeof path, "%s/sideband.txt", outdir);
    FILE *sb = fopen(path, "w");
    fprintf(sb, "aux_head=%llu timing=%s versions=%d delay=%llu\n",
            (unsigned long long)head, fine ? "fine" : "coarse", versions,
            (unsigned long long)delay);
    fprintf(sb, "time_shift=%u time_mult=%u time_zero=%llu\n",
            up->time_shift, up->time_mult, (unsigned long long)up->time_zero);
    fprintf(sb, "cap_user_time=%u cap_user_time_zero=%u\n",
            up->cap_user_time, up->cap_user_time_zero);
    /* CPUID.15H: TSC = CTC * ebx/eax (crystal-clock ratio). MTC fires every
     * 2^mtc_period CTC ticks, so one MTC = 2^mtc_period * ebx/eax TSC ticks.
     * This lets the time-keyed decoder refine between sparse TSC packets. */
    unsigned ea = 0, eb = 0, ec = 0, ed = 0;
    __get_cpuid(0x15, &ea, &eb, &ec, &ed);
    fprintf(sb, "cpuid15_eax_denom=%u cpuid15_ebx_numer=%u cpuid15_ecx_crystal_hz=%u\n", ea, eb, ec);
    fprintf(sb, "mtc_period=%d\n", fine ? 0 : 3);
    fclose(sb);

    fprintf(stderr, "ptcap: wrote %llu AUX bytes, %d versions, delay=%llu, %s timing\n",
            (unsigned long long)n, versions, (unsigned long long)delay, fine ? "fine" : "coarse");
    return 0;
}
