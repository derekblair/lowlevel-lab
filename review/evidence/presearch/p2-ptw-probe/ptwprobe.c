/* Reviewer feasibility probe for P2 (benign: traces only its own user-mode code).
 * Q: can an unprivileged process (perf_event_paranoid=2) enable Intel PT with
 * PTWEn (format ptw=config:12) on itself and find its own PTWRITE payload in
 * the AUX buffer? PTW packet: 0x02, then 0x32 (8-byte payload, no FUP) or
 * 0xB2 (8-byte payload, IP bit set) followed by the little-endian payload.
 * usage: ptwprobe [fup]   (fup -> also set fup_on_ptw=config:5) */
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
static long rd(const char *p) { FILE *f = fopen(p, "r"); long v = -1; if (f) { if (fscanf(f, "%ld", &v) != 1) v = -1; fclose(f); } return v; }
int main(int argc, char **argv) {
    int fup = argc > 1;
    struct perf_event_attr a; memset(&a, 0, sizeof a);
    a.size = sizeof a; a.type = (uint32_t)rd("/sys/bus/event_source/devices/intel_pt/type");
    a.config = (1ULL << 0) | (1ULL << 13) | (1ULL << 12) | (fup ? (1ULL << 5) : 0); /* pt, branch, ptw[, fup_on_ptw] */
    a.exclude_kernel = 1; a.exclude_hv = 1; a.disabled = 1;
    int fd = syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
    if (fd < 0) { perror("perf_event_open(intel_pt, ptw)"); return 1; }
    long pg = sysconf(_SC_PAGESIZE); size_t data = (1 + 8) * pg, aux = 64 * pg;
    struct perf_event_mmap_page *up = mmap(0, data, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (up == MAP_FAILED) { perror("mmap data"); return 1; }
    up->aux_offset = data; up->aux_size = aux;
    unsigned char *ab = mmap(0, aux, PROT_READ | PROT_WRITE, MAP_SHARED, fd, data);
    if (ab == MAP_FAILED) { perror("mmap aux"); return 1; }
    const uint64_t magic = 0x1122334455667788ULL;
    ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
    for (int i = 0; i < 4; i++) __asm__ volatile("ptwrite %0" :: "r"(magic + (uint64_t)i));
    ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
    uint64_t head = __atomic_load_n(&up->aux_head, __ATOMIC_ACQUIRE);
    int found = 0;
    for (uint64_t i = 0; i + 10 <= head && i + 10 <= aux; i++) {
        if (ab[i] == 0x02 && (ab[i + 1] & 0x7f) == 0x32) {
            uint64_t v; memcpy(&v, ab + i + 2, 8);
            if (v - magic < 4) { printf("PTW packet @aux+%llu hdr=%02x %02x payload=%016llx\n",
                                        (unsigned long long)i, ab[i], ab[i + 1], (unsigned long long)v); found++; }
        }
    }
    printf("fup_on_ptw=%d aux_head=%llu bytes, PTW packets with magic payload: %d/4 -> %s\n",
           fup, (unsigned long long)head, found, found == 4 ? "FEASIBLE" : "NOT SHOWN");
    return found == 4 ? 0 : 2;
}
