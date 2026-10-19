/* Reviewer fidelity probe (benign, own-process): does qemu-aarch64 model a
 * stale I-cache when code is patched WITHOUT cache maintenance?
 * f() starts as "mov w0,#1; ret"; we call it (so it gets translated), then
 * overwrite word 0 with "mov w0,#2" and call again. On real ARM64 hardware
 * the second call is architecturally UNPREDICTABLE without DC CVAU/IC IVAU/
 * DSB/ISB; if qemu always returns 2, it is coherent and cannot demonstrate
 * the stale-instruction hazard. */
#include <stdio.h>
#include <stdint.h>
#include <sys/mman.h>
int main(int argc, char **argv) {
    int use_flush = argc > 1;
    uint32_t *code = mmap(0, 4096, PROT_READ|PROT_WRITE|PROT_EXEC,
                          MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    if (code == MAP_FAILED) { perror("mmap"); return 1; }
    int (*f)(void) = (int (*)(void))code;
    code[0] = 0x52800020u;            /* mov w0, #1 */
    code[1] = 0xd65f03c0u;            /* ret        */
    __builtin___clear_cache((char *)code, (char *)(code + 2));
    int a = f();
    code[0] = 0x52800040u;            /* mov w0, #2 */
    if (use_flush) __builtin___clear_cache((char *)code, (char *)(code + 2));
    int b = f();
    printf("flush=%s first=%d second=%d\n", use_flush ? "yes" : "NO ", a, b);
    return 0;
}
