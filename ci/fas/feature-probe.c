/* SPDX-License-Identifier: GPL-3.0-or-later
 * ARM64 static feature test for the FranBakaSU 5.4 ringbuf backport.
 * The 17-instruction frame program below is from shadow3aaa/frame-analyzer-ebpf,
 * extracted from the official fas-rs v4.9.1 release (see UPSTREAM.json).
 */
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <linux/elf.h>
#include <asm/unistd.h>

typedef unsigned long usize;
static long call6(long n, long a, long b, long c, long d, long e, long f)
{
 register long x8 __asm__("x8")=n, x0 __asm__("x0")=a, x1 __asm__("x1")=b;
 register long x2 __asm__("x2")=c, x3 __asm__("x3")=d, x4 __asm__("x4")=e, x5 __asm__("x5")=f;
 __asm__ volatile("svc #0" : "+r"(x0) : "r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5) : "memory","cc");
 return x0;
}
#define sc(n,a,b,c,d,e,f) call6(__NR_##n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
void *memset(void *p,int c,usize n) { unsigned char *s=p; for(usize i=0;i<n;i++)s[i]=c;return p; }
void *memcpy(void *p,const void *q,usize n) { unsigned char *d=p; const unsigned char *s=q;for(usize i=0;i<n;i++)d[i]=s[i];return p; }
static usize len(const char *s) { usize n=0;while(s[n])n++;return n; }
static void say(const char *s) { usize n=len(s);while(n){long r=sc(write,1,s,n,0,0,0);if(r<=0)return;s+=r;n-=r;} }
static void num(long x) { char b[32];int i=31;b[i]=0;unsigned long v=x<0?-x:x;do{b[--i]='0'+v%10;v/=10;}while(v);if(x<0)b[--i]='-';say(b+i); }
static int fail(const char *s,long e){say("FAIL: ");say(s);say(" (");num(e);say(")\n");return 1;}
static int contains(const char *s,const char *needle){for(;*s;s++){usize i=0;while(needle[i] && s[i]==needle[i])i++;if(!needle[i])return 1;}return 0;}
static int closefd(int fd){return sc(close,fd,0,0,0,0,0);}
static long bpf(int cmd,union bpf_attr *a){return sc(bpf,cmd,a,sizeof(*a),0,0,0);}
static char logbuf[32768];
#define I(c,d,s,o,v) ((struct bpf_insn){.code=c,.dst_reg=d,.src_reg=s,.off=o,.imm=v})
static struct bpf_insn frame[]={
 {0xbf,6,1,0,0},{0x18,1,1,0,0},{0,0,0,0,0},{0xb7,2,0,0,16},
 {0xb7,3,0,0,0},{0x85,0,0,0,131},{0xbf,7,0,0,0},{0x15,7,0,7,0},
 {0x85,0,0,0,5},{0x79,1,6,0,0},{0x7b,7,1,8,0},{0x7b,7,0,0,0},
 {0xbf,1,7,0,0},{0xb7,2,0,0,0},{0x85,0,0,0,132},{0xb7,0,0,0,0},{0x95,0,0,0,0}
};
static int load(struct bpf_insn *p,int n)
{
 union bpf_attr a={0};a.prog_type=BPF_PROG_TYPE_KPROBE;a.insn_cnt=n;
 a.insns=(usize)p;a.license=(usize)"GPL";a.log_buf=(usize)logbuf;a.log_size=sizeof(logbuf);a.log_level=1;
 logbuf[0]=0;return bpf(BPF_PROG_LOAD,&a);
}
static int rejected(int map,int mode,const char *name)
{
 struct bpf_insn p[40];int n=0,j;
 p[n++]=I(0x18,1,1,0,map);p[n++]=I(0,0,0,0,0);
 p[n++]=I(0xb7,2,0,0,16);p[n++]=I(0xb7,3,0,0,0);p[n++]=I(0x85,0,0,0,131);
 if(mode==5)p[n++]=I(0x07,0,0,0,8); /* arithmetic before null test */
 j=n;p[n++]=I(0x15,0,0,0,0);p[n++]=I(0xbf,7,0,0,0);
 if(mode==1)p[n++]=I(0x7a,7,0,16,1); /* out of bounds */
 if(mode==2)p[n++]=I(0x07,7,0,0,8); /* shifted release */
 if(mode!=0){
  p[n++]=I(0xbf,8,7,0,0);p[n++]=I(0x07,8,0,0,8);
  p[n++]=I(0xbf,1,7,0,0);p[n++]=I(0xb7,2,0,0,0);p[n++]=I(0x85,0,0,0,132);
 }
 if(mode==3){p[n++]=I(0xbf,1,7,0,0);p[n++]=I(0xb7,2,0,0,0);p[n++]=I(0x85,0,0,0,132);}
 if(mode==4)p[n++]=I(0x7a,8,0,0,1); /* use derived pointer after free */
 p[j].off=n-j-1;p[n++]=I(0xb7,0,0,0,0);p[n++]=I(0x95,0,0,0,0);
 int fd=load(p,n);if(fd>=0){closefd(fd);return fail(name,0);}if(fd!=-13 && fd!=-22){say(logbuf);return fail(name,fd);}
 const char *reason[]={"Unreleased reference","invalid access to memory","invalid allocated-memory release","expected=mem","invalid mem access","null-check it first"};
 if(!contains(logbuf,reason[mode])){say(logbuf);return fail("unexpected verifier rejection",mode);}
 say("PASS reject ");say(name);say("\n");return 0;
}
__attribute__((noinline,used)) static void measured_frame(unsigned long token){__asm__ volatile("" :: "r"(token) : "memory");}
static unsigned long frame_offset(void)
{
 unsigned char bytes[4096];long fd=sc(openat,-100,"/proc/self/exe",0,0,0,0);if(fd<0)return 0;
 long n=sc(read,fd,bytes,sizeof(bytes),0,0,0);closefd(fd);if(n<64)return 0;
 struct elf64_hdr *h=(void*)bytes;
 if(h->e_phoff+(usize)h->e_phnum*h->e_phentsize>(usize)n)return 0;
 for(int i=0;i<h->e_phnum;i++){
  struct elf64_phdr *p=(void*)(bytes+h->e_phoff+i*h->e_phentsize);usize a=(usize)measured_frame;
  if(p->p_type==PT_LOAD && a>=p->p_vaddr && a<p->p_vaddr+p->p_filesz)return a-p->p_vaddr+p->p_offset;
 }return 0;
}
static int test(void)
{
 struct {__u64 cur,max;} limit={~0ULL,~0ULL};
 long r=sc(prlimit64,0,8,&limit,0,0,0);if(r<0)return fail("RLIMIT_MEMLOCK",r);
 union bpf_attr a={0};a.map_type=BPF_MAP_TYPE_RINGBUF;a.max_entries=4096;
 int map=bpf(BPF_MAP_CREATE,&a);if(map<0)return fail("ringbuf map create",map);
 frame[1].imm=map;int prog=load(frame,sizeof(frame)/sizeof(frame[0]));
 if(prog<0){say(logbuf);closefd(map);return fail("official fas-rs program load",prog);}
 say("PASS official fas-rs v4.9.1 uprobe program load\n");
 struct bpf_insn spilled[19];memcpy(spilled,frame,7*sizeof(*frame));
 spilled[7]=I(0x7b,10,7,-8,0);spilled[8]=I(0x79,7,10,-8,0);
 memcpy(spilled+9,frame+7,10*sizeof(*frame));
 int spill=load(spilled,19);
 if(spill<0){say(logbuf);closefd(prog);closefd(map);return fail("nullable allocation spill/reload",spill);}
 closefd(spill);say("PASS nullable allocation spill/reload\n");
 int error=0;
 const char *names[]={"reservation leak","out of bounds","shifted release","double release","use after release","nullable arithmetic"};
 for(int i=0;i<6;i++)error|=rejected(map,i,names[i]);
 if(error){closefd(prog);closefd(map);return 1;}
 unsigned long *cons=(void*)sc(mmap,0,4096,3,1,map,0);
 if((long)cons<0){closefd(prog);closefd(map);return fail("consumer mmap",(long)cons);}
 unsigned long *prod=(void*)sc(mmap,0,12288,1,1,map,4096);
 if((long)prod<0){sc(munmap,cons,4096,0,0,0,0);closefd(prog);closefd(map);return fail("producer mmap",(long)prod);}
 long invalid=sc(mmap,0,4096,3,1,map,4096);
 if(invalid>=0){sc(munmap,invalid,4096,0,0,0,0);error=fail("writable producer mapping accepted",0);}else say("PASS reject writable producer mapping\n");
 char s[32];int typefd=sc(openat,-100,"/sys/bus/event_source/devices/uprobe/type",0,0,0,0);
 if(typefd<0)error=fail("uprobe PMU",typefd);
 int type=0;
 if(typefd>=0){r=sc(read,typefd,s,sizeof(s),0,0,0);closefd(typefd);if(r<=0)error=fail("read uprobe PMU",r);else for(long i=0;i<r && s[i]>='0' && s[i]<='9';i++)type=type*10+s[i]-'0';}
 struct perf_event_attr attr={0};attr.size=sizeof(attr);attr.type=type;attr.config1=(usize)"/proc/self/exe";attr.config2=frame_offset();attr.sample_period=1;attr.wakeup_events=1;
 int event=-1;
 if(!error && attr.config2){event=sc(perf_event_open,&attr,0,-1,-1,8,0);if(event<0)error=fail("perf uprobe attach",event);}else if(!error)error=fail("ELF function offset",0);
 if(event>=0){
  r=sc(ioctl,event,0x40042408,prog,0,0,0);if(r<0)error=fail("PERF_EVENT_IOC_SET_BPF",r);
  if(!error){r=sc(ioctl,event,0x2400,0,0,0,0);if(r<0)error=fail("PERF_EVENT_IOC_ENABLE",r);}
  unsigned char *data=(void*)((char*)prod+4096);
  for(unsigned long i=1;!error && i<=400;i++){
   measured_frame(i);
   struct {int fd;short events,revents;} pfd={map,1,0};struct {long sec,nsec;} timeout={1,0};
   r=sc(ppoll,&pfd,1,&timeout,0,8,0);
   unsigned long c=__atomic_load_n(cons,__ATOMIC_ACQUIRE),p=__atomic_load_n(prod,__ATOMIC_ACQUIRE);
   if(r!=1 || !(pfd.revents&1) || p-c!=24){error=fail("poll/record availability",r);break;}
   __u32 hdr=__atomic_load_n((__u32*)(data+(c&4095)),__ATOMIC_ACQUIRE);
   __u64 *v=(void*)(data+(c&4095)+8);
   if(hdr!=16 || !v[0] || v[1]!=i){error=fail("record timestamp/token",hdr);break;}
   __atomic_store_n(cons,c+24,__ATOMIC_RELEASE);
  }
  if(!error)say("PASS 400 real uprobes, mmap/poll roundtrip and ring wrap\n");
  closefd(event);
 }
 sc(munmap,prod,12288,0,0,0,0);sc(munmap,cons,4096,0,0,0,0);closefd(prog);closefd(map);
 if(!error)say("FAS_FEATURE_PROBE: PASS\n");return error;
}
void start_c(unsigned long *sp)
{
 (void)sp;int init=sc(getpid,0,0,0,0,0,0)==1;
 if(init){
  if(sc(mount,"proc","/proc","proc",0,0,0)<0 || sc(mount,"sysfs","/sys","sysfs",0,0,0)<0){fail("mount proc/sys",0);goto done;}
 }
 int result=test();
 if(!init)sc(exit_group,result,0,0,0,0,0);
 done: if(init)sc(reboot,0xfee1dead,672274793,0x4321fedc,0,0,0);
 for(;;)sc(exit_group,1,0,0,0,0,0);
}
__asm__(".global _start\n_start:\nmov x0, sp\nbl start_c\nb .\n");
