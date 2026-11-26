/* SPDX-License-Identifier: GPL-2.0-only */
/* AArch32 ABI check: deliberately uses 32-bit iovec entries on ARM64. */
typedef unsigned long usize;
static long call6(long n,long a,long b,long c,long d,long e,long f)
{
 register long r7 __asm__("r7")=n,r0 __asm__("r0")=a,r1 __asm__("r1")=b;
 register long r2 __asm__("r2")=c,r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f;
 __asm__ volatile("svc #0":"+r"(r0):"r"(r7),"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5):"memory","cc");return r0;
}
#define sc(n,a,b,c,d,e,f) call6(n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
static void say(const char *s){usize n=0;while(s[n])n++;sc(4,1,s,n,0,0,0);}
static int check(int ok,const char *s){say(ok?"PASS compat32 ":"FAIL: compat32 ");say(s);say("\n");return !ok;}
void start_c(void)
{
 int e=0;long pid=sc(20,0,0,0,0,0,0),fd=sc(434,pid,0,0,0,0,0);
 e+=check(fd>=0,"pidfd_open");
 char *p=(void*)sc(192,0,8192,3,0x22,-1,0);
 e+=check((usize)p<(usize)-4095,"anonymous map");
 if(!e){
  p[0]=73;p[4096]=26;struct {void *base;usize size;} v[2]={{p,4096},{p+4096,4096}};
  e+=check(sc(440,fd,v,2,20,0,0)==8192,"MADV_COLD imports 32-bit vectors");
  e+=check(sc(440,fd,v,2,21,0,0)==8192,"MADV_PAGEOUT imports 32-bit vectors");
  e+=check(p[0]==73&&p[4096]==26,"data preserved");
  v[1].base=(void*)1;
  e+=check(sc(440,fd,v,2,20,0,0)==4096,"partial byte count");
  e+=check(sc(440,fd,v,1,20,1,0)==-22,"unknown flags rejected");
  sc(91,p,8192,0,0,0,0);sc(6,fd,0,0,0,0,0);
 }
 sc(248,e,0,0,0,0,0);for(;;){}
}
__asm__(".arm\n.global _start\n_start:\nbl start_c\nb .\n");
