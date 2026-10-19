/* Reviewer check of a BUILD-01 explanatory claim (benign, own-process):
 * is the small shortfall below 2/iter (P) and 1/iter (E) a "fixed ~2-count
 * ENABLE/DISABLE boundary loss" (README Precision note, report.py:139-143), or
 * the cold first iteration(s)? Same pattern as smcobs sweep code@0 store@8.
 * usage: deficit_probe CPU N WARMUP   (WARMUP = calls to fn before counting) */
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
static int pmu_type(const char *n) { char p[128]; int t = -1; snprintf(p, sizeof p, "/sys/bus/event_source/devices/%s/type", n);
    FILE *f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &t) != 1) t = -1; fclose(f); } return t; }
int main(int argc, char **argv) {
    int cpu = atoi(argv[1]); long N = atol(argv[2]); int warm = atoi(argv[3]);
    cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu, &s); if (sched_setaffinity(0, sizeof s, &s)) return 1;
    struct perf_event_attr a; memset(&a, 0, sizeof a); a.size = sizeof a;
    a.type = pmu_type(cpu < 4 ? "cpu_core" : "cpu_atom"); a.config = cpu < 4 ? 0x04c3 : 0x01c3;
    a.exclude_kernel = 1; a.exclude_hv = 1; a.disabled = 1;
    int fd = syscall(SYS_perf_event_open, &a, 0, -1, -1, 0); if (fd < 0) { perror("pe"); return 1; }
    unsigned char *p = mmap(0, 65536, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memset(p, 0xcc, 65536); p[0] = 0xb8; memset(p + 1, 0, 4); p[5] = 0xc3;
    int (*fn)(void) = (int (*)(void))p; volatile unsigned char *t = p + 8; long sum = 0;
    for (int i = 0; i < warm; i++) { *t = 0xcc; sum += fn(); }
    ioctl(fd, PERF_EVENT_IOC_RESET, 0); ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    for (long i = 0; i < N; i++) { *t = 0xcc; sum += fn(); }
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    uint64_t c = 0; if (read(fd, &c, sizeof c) != sizeof c) return 1;
    long per = cpu < 4 ? 2 : 1;
    printf("cpu=%-2d N=%-7ld warmup=%d clears=%llu expected=%ld deficit=%lld\n", cpu, N, warm,
           (unsigned long long)c, per * N, (long long)(per * N) - (long long)c);
    return (int)(sum & 0);
}
