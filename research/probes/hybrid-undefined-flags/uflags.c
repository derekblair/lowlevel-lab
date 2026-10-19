/* Probe: architecturally-undefined flag/result behaviour, P-core vs E-core.
   For each op, run N pseudo-random operand pairs from two initial RFLAGS
   states (all-0 / all-1 of the status flags) and print (result,flags) hash
   + first few raw samples. Pin with argv[1] = cpu number. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#define ST 0x8D5ULL /* CF PF AF ZF SF OF */
static uint64_t rng = 88172645463325252ULL;
static uint64_t xs(void){ rng ^= rng<<13; rng ^= rng>>7; rng ^= rng<<17; return rng; }
#define OP2(name, insn) static void name(uint64_t a, uint64_t b, uint64_t fin, uint64_t *r, uint64_t *f){ \
  uint64_t x=a, y=b, fl=fin; __asm__ volatile("push %[fl]\n\tpopfq\n\t" insn "\n\tpushfq\n\tpop %[fl]" \
  : "+a"(x), "+c"(y), [fl]"+r"(fl) : : "rdx","cc"); *r=x; *f=fl&ST; }
OP2(op_mul,   "mul %%rcx")                       /* SF ZF AF PF undefined */
OP2(op_imul,  "imul %%rcx, %%rax")               /* SF ZF AF PF undefined */
OP2(op_bsf,   "bsf %%rcx, %%rax")                /* src=0: dest+flags undef */
OP2(op_bsr,   "bsr %%rcx, %%rax")
OP2(op_shl,   "shl %%cl, %%rax")                 /* OF undef for cnt>1, AF undef */
OP2(op_shr8,  "shr %%cl, %%al")                  /* CF undef cnt>=8 */
OP2(op_shld16,"shld %%cl, %%cx, %%ax")           /* cnt>16: result+flags undef */
OP2(op_shrd16,"shrd %%cl, %%cx, %%ax")
OP2(op_rol,   "rol %%cl, %%rax")                 /* OF undef cnt>1 */
OP2(op_rcl8,  "rcl %%cl, %%al")
OP2(op_and,   "and %%rcx, %%rax")                /* AF undef */
OP2(op_bt,    "bt %%rcx, %%rax")                 /* OF SF AF PF undef */
OP2(op_tzcnt, "tzcnt %%rcx, %%rax")              /* OF SF PF AF undef */
OP2(op_lzcnt, "lzcnt %%rcx, %%rax")
OP2(op_bswap16,".byte 0x66, 0x0f, 0xc8")         /* bswap ax: result undefined */
static void op_div(uint64_t a, uint64_t b, uint64_t fin, uint64_t *r, uint64_t *f){
  uint64_t x=a, y=(b|1), fl=fin, d=0; __asm__ volatile("push %[fl]\n\tpopfq\n\tdiv %%rcx\n\tpushfq\n\tpop %[fl]"
  : "+a"(x), "+c"(y), "+d"(d), [fl]"+r"(fl) : : "cc"); *r=x^d; *f=fl&ST; }
struct op { const char *n; void (*fn)(uint64_t,uint64_t,uint64_t,uint64_t*,uint64_t*); int zero_b; };
int main(int argc, char **argv){
  int cpu = atoi(argv[1]); cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu,&s);
  if (sched_setaffinity(0,sizeof s,&s)) { perror("affinity"); return 1; }
  struct op ops[] = {{"mul",op_mul,0},{"imul",op_imul,0},{"bsf0",op_bsf,1},{"bsr0",op_bsr,1},{"shl",op_shl,0},
    {"shr8",op_shr8,0},{"shld16",op_shld16,0},{"shrd16",op_shrd16,0},{"rol",op_rol,0},{"rcl8",op_rcl8,0},{"and",op_and,0},
    {"bt",op_bt,0},{"tzcnt",op_tzcnt,0},{"lzcnt",op_lzcnt,0},{"bswap16",op_bswap16,0},{"div",op_div,0}};
  for (unsigned i=0;i<sizeof ops/sizeof ops[0];i++){
    rng = 88172645463325252ULL; uint64_t h = 1469598103934665603ULL;
    for (int k=0;k<200000;k++){
      uint64_t a=xs(), b=xs(); if (ops[i].zero_b) b=0;
      for (int fi=0; fi<2; fi++){ uint64_t r,f; ops[i].fn(a,b, fi?(ST|2):2, &r,&f);
        h = (h ^ r) * 1099511628211ULL; h = (h ^ f) * 1099511628211ULL; }
    }
    printf("%-8s %016llx\n", ops[i].n, (unsigned long long)h);
  }
  return 0; }
