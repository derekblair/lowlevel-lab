#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
typedef int (*fn)(void);
/* v1: mov eax,1 ; jmp +2 ; (2 junk bytes: 0x0f 0x0b = ud2, skipped) ; ret
   v2: mov eax,2 ; nop ; nop ; xor eax,eax... keep same length: mov eax,2; 2x nop; 2x nop; ret */
static unsigned char v1[] = {0xb8,1,0,0,0, 0xeb,0x02, 0x0f,0x0b, 0xc3};
static unsigned char v2[] = {0xb8,2,0,0,0, 0x90,0x90, 0x90,0x90, 0xc3};
__attribute__((noinline)) void marker(int a, int b){ printf("v1 returned %d, v2 returned %d\n", a, b); }
int main(void){
  unsigned char *p = mmap(0,4096,PROT_READ|PROT_WRITE|PROT_EXEC,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  memcpy(p, v1, sizeof v1); int a = ((fn)p)();
  memcpy(p, v2, sizeof v2); int b = ((fn)p)();
  marker(a,b); return 0; }
