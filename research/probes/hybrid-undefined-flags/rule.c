#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdint.h>
static void pin(int c){ cpu_set_t s; CPU_ZERO(&s); CPU_SET(c,&s); sched_setaffinity(0,sizeof s,&s); }
#define OP(name, insn) static uint64_t name(uint64_t a, uint64_t c, uint64_t fin, uint64_t *r){ \
  uint64_t x=a, y=c, fl=fin; __asm__ volatile("push %[fl]\n\tpopfq\n\t" insn "\n\tpushfq\n\tpop %[fl]" \
  : "+a"(x), "+c"(y), [fl]"+r"(fl) :: "cc"); *r=x; return fl; }
OP(shl,"shl %%cl, %%rax") OP(shr,"shr %%cl, %%rax") OP(rol,"rol %%cl, %%rax") OP(ror,"ror %%cl, %%rax")
#define MSB(v) ((v)>>63 & 1)
#define MSB2(v) ((v)>>62 & 1)
int main(void){
  const char *names[]={"shl","shr","rol","ror"}; uint64_t (*fns[])(uint64_t,uint64_t,uint64_t,uint64_t*)={shl,shr,rol,ror};
  const char *rules[]={"MSB(res)^CF (last-step rule)","MSB(src)^MSB(res) (sign-change)","first-step rule","OF preserved","OF=0","MSB(res)^MSB2(res) (ror-style)"};
  for (int core=0; core<2; core++){ pin(core?4:0); printf("== %s core (CPU %d)\n", core?"E":"P", core?4:0);
    for (int o=0;o<4;o++){ int ok[6]={1,1,1,1,1,1}; uint64_t s=0x243F6A8885A308D3ULL;
      for (int k=0;k<20000;k++){ s^=s<<13; s^=s>>7; s^=s<<17; uint64_t a=s; uint64_t c=2+(k%62);
        for (int fi=0;fi<2;fi++){ uint64_t fin = fi? (0x8D5|2):2, r; uint64_t fl=fns[o](a,c,fin,&r);
          int of=(fl>>11)&1, cf=fl&1; int inof=(fin>>11)&1; int cand[6];
          cand[0]=MSB(r)^cf; cand[1]=MSB(a)^MSB(r);
          if (o==0) cand[2]=MSB(a)^MSB(a<<1); else if(o==1) cand[2]=MSB(a); else if(o==2) cand[2]=MSB((a<<1)|(a>>63))^((a>>63)&1); else cand[2]=MSB((a>>1)|(a<<63))^MSB2((a>>1)|(a<<63));
          cand[3]=inof; cand[4]=0; cand[5]=MSB(r)^MSB2(r);
          for (int j=0;j<6;j++) if (cand[j]!=of) ok[j]=0; } }
      printf("  %-4s:", names[o]); int any=0; for (int j=0;j<6;j++) if (ok[j]) { printf(" [%s]", rules[j]); any=1; } if(!any) printf(" (no simple rule matched)"); printf("\n"); } }
  return 0; }
