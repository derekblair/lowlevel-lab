/* Same inputs on CPU 0 (P) and CPU 4 (E) inside one process; report which
   result/flag bits differ, per shift count. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define ST 0x8D5ULL
static void pin(int c){ cpu_set_t s; CPU_ZERO(&s); CPU_SET(c,&s); sched_setaffinity(0,sizeof s,&s); }
#define OP2(name, insn) static void name(uint64_t a, uint64_t b, uint64_t fin, uint64_t *r, uint64_t *f){ \
  uint64_t x=a, y=b, fl=fin; __asm__ volatile("push %[fl]\n\tpopfq\n\t" insn "\n\tpushfq\n\tpop %[fl]" \
  : "+a"(x), "+c"(y), [fl]"+r"(fl) : : "rdx","cc"); *r=x; *f=fl&ST; }
OP2(op_shl,"shl %%cl, %%rax") OP2(op_shr,"shr %%cl, %%rax") OP2(op_sar,"sar %%cl, %%rax")
OP2(op_shr8,"shr %%cl, %%al") OP2(op_shl8,"shl %%cl, %%al")
OP2(op_shld16,"shld %%cl, %%cx, %%ax") OP2(op_shrd16,"shrd %%cl, %%cx, %%ax")
OP2(op_shld64,"shld %%cl, %%rcx, %%rax")
OP2(op_rol,"rol %%cl, %%rax") OP2(op_ror,"ror %%cl, %%rax") OP2(op_rcl8,"rcl %%cl, %%al") OP2(op_rcr8,"rcr %%cl, %%al")
struct op { const char *n; void (*fn)(uint64_t,uint64_t,uint64_t,uint64_t*,uint64_t*); };
static const char *flagname(int bit){ switch(bit){case 0:return "CF";case 2:return "PF";case 4:return "AF";case 6:return "ZF";case 7:return "SF";case 11:return "OF";} return "?"; }
#define NV 64
int main(void){
  struct op ops[] = {{"shl",op_shl},{"shr",op_shr},{"sar",op_sar},{"shl8",op_shl8},{"shr8",op_shr8},{"shld16",op_shld16},
    {"shrd16",op_shrd16},{"shld64",op_shld64},{"rol",op_rol},{"ror",op_ror},{"rcl8",op_rcl8},{"rcr8",op_rcr8}};
  static uint64_t vals[NV]; uint64_t s=0x9E3779B97F4A7C15ULL;
  for (int i=0;i<NV;i++){ s^=s<<13; s^=s>>7; s^=s<<17; vals[i]=s; } vals[0]=0; vals[1]=~0ULL; vals[2]=1; vals[3]=0x8000000000000000ULL;
  static uint64_t R[2][NV][64][2], F[2][NV][64][2];
  for (unsigned o=0;o<sizeof ops/sizeof ops[0];o++){
    for (int core=0; core<2; core++){ pin(core?4:0);
      for (int v=0; v<NV; v++) for (int c=0;c<64;c++) for (int fi=0;fi<2;fi++)
        ops[o].fn(vals[v], (uint64_t)c | (vals[(v+7)%NV] & ~0xffULL), fi?(ST|2):2, &R[core][v][c][fi], &F[core][v][c][fi]); }
    uint64_t fdiff_by_count[64]={0}; int rdiff_by_count[64]={0}; int any=0;
    for (int v=0; v<NV; v++) for (int c=0;c<64;c++) for (int fi=0;fi<2;fi++){
      fdiff_by_count[c] |= F[0][v][c][fi]^F[1][v][c][fi]; if (R[0][v][c][fi]!=R[1][v][c][fi]) rdiff_by_count[c]++; }
    printf("%-7s:", ops[o].n);
    for (int c=0;c<64;c++) if (fdiff_by_count[c]||rdiff_by_count[c]){ any=1;
      printf(" c=%d[", c); for(int b=0;b<12;b++) if (fdiff_by_count[c]>>b&1) printf("%s ", flagname(b));
      if (rdiff_by_count[c]) printf("RESULTx%d", rdiff_by_count[c]); printf("]"); }
    if (!any) printf(" identical");
    printf("\n");
  }
  return 0; }
