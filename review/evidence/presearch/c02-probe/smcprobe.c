/* Reviewer feasibility probe for C02 (benign, own-process): can an unprivileged
 * process (perf_event_paranoid=2) count MACHINE_CLEARS.SMC on both hybrid PMUs,
 * and does the count depend on store distance from executing code?
 * usage: smcprobe CPU DIST   — stores to (code_end + DIST) while calling the code.
 * Event encodings from intel/perfmon PTL @8da58930a226: Cougar Cove SMC 0xC3/0x04,
 * Darkmont SMC 0xC3/0x01. */
#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <x86intrin.h>
static int pmu_type(const char *n) {
    char p[128]; int t = -1; snprintf(p, sizeof p, "/sys/bus/event_source/devices/%s/type", n);
    FILE *f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &t) != 1) t = -1; fclose(f); } return t;
}
int main(int argc, char **argv) {
    if (argc < 3) return 2;
    int cpu = atoi(argv[1]), dist = atoi(argv[2]);
    cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu, &s);
    if (sched_setaffinity(0, sizeof s, &s)) { perror("affinity"); return 1; }
    const char *pmu = cpu < 4 ? "cpu_core" : "cpu_atom";
    struct perf_event_attr a; memset(&a, 0, sizeof a);
    a.size = sizeof a; a.type = pmu_type(pmu); a.config = cpu < 4 ? 0x04c3 : 0x01c3;
    a.exclude_kernel = 1; a.exclude_hv = 1; a.disabled = 1;
    int fd = syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
    if (fd < 0) { perror("perf_event_open"); return 1; }
    unsigned char *p = mmap(0, 16384, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    memset(p, 0xcc, 16384);
    p[0] = 0xb8; memset(p + 1, 0, 4); p[5] = 0xc3;          /* mov eax,0 ; ret */
    int (*fn)(void) = (int (*)(void))p;
    volatile unsigned char *t = p + 6 + dist;
    const int N = 200000; long sum = 0;
    ioctl(fd, PERF_EVENT_IOC_RESET, 0); ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    uint64_t t0 = __rdtsc();
    for (int i = 0; i < N; i++) { *t = 0xcc; sum += fn(); }
    uint64_t t1 = __rdtsc();
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    uint64_t c = 0; if (read(fd, &c, sizeof c) != sizeof c) return 1;
    printf("cpu=%-2d pmu=%-8s dist=%-5d smc_clears/iter=%.3f tsc/iter=%.1f (sum=%ld)\n",
           cpu, pmu, dist, (double)c / N, (double)(t1 - t0) / N, sum);
    return 0;
}
