/* Reviewer power check for BUILD-01 fix-round torn probe (benign, own-process,
 * two threads). Replicates smcobs.c@271bd3e do_torn/torn_writer exactly
 * (mov eax,imm32 @61, imm32 @62..65 straddling the 64-B line, ret @66; writer
 * A->B high-first, B->A low-first with aligned 2-byte stores) but counts each
 * observed value separately. MID (0x33332222) exists in memory only mid-
 * transition, so its frequency shows how often the executor samples the windows
 * in which a tear (0x11114444) could appear = the probe's demonstrated power.
 * usage: torn_power WRITER_CPU EXEC_CPU N */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#define A 0x11112222u
#define B 0x33334444u
#define MID 0x33332222u
#define TORN 0x11114444u
static unsigned char *code; static _Atomic int stop; static int wcpu;
static void pin(int c) { cpu_set_t s; CPU_ZERO(&s); CPU_SET(c, &s); sched_setaffinity(0, sizeof s, &s); }
static void *writer(void *x) {
    (void)x; pin(wcpu);
    volatile uint16_t *lo = (uint16_t *)(code + 62), *hi = (uint16_t *)(code + 64);
    while (!atomic_load_explicit(&stop, memory_order_relaxed)) {
        *hi = (uint16_t)(B >> 16); *lo = (uint16_t)(B & 0xffff);
        *lo = (uint16_t)(A & 0xffff); *hi = (uint16_t)(A >> 16);
    }
    return 0;
}
int main(int argc, char **argv) {
    wcpu = atoi(argv[1]); int ecpu = atoi(argv[2]); long N = atol(argv[3]);
    code = mmap(0, 65536, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memset(code, 0xcc, 65536); code[61] = 0xb8; *(uint32_t *)(code + 62) = A; code[66] = 0xc3;
    pin(ecpu); unsigned (*fn)(void) = (unsigned (*)(void))(code + 61);
    pthread_t t; if (pthread_create(&t, 0, writer, 0)) return 1;
    long na = 0, nb = 0, nm = 0, nt = 0, no = 0;
    for (long i = 0; i < N; i++) { unsigned v = fn(); if (v == A) na++; else if (v == B) nb++; else if (v == MID) nm++; else if (v == TORN) nt++; else no++; }
    atomic_store(&stop, 1); pthread_join(t, 0);
    printf("writer=%d exec=%d N=%ld A=%ld B=%ld MID=%ld (%.2f%%) TORN=%ld other=%ld\n", wcpu, ecpu, N, na, nb, nm, 100.0 * nm / N, nt, no);
    return 0;
}
