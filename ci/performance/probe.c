/* SPDX-License-Identifier: GPL-2.0-only */
#include <asm/unistd.h>
#include <linux/uio.h>
#include <linux/capability.h>
typedef unsigned long usize;
static long call6(long n,long a,long b,long c,long d,long e,long f)
{
 register long x8 __asm__("x8")=n,x0 __asm__("x0")=a,x1 __asm__("x1")=b;
 register long x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5):"memory","cc");return x0;
}
#define sc(n,a,b,c,d,e,f) call6(__NR_##n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
void *memset(void *p,int c,usize n){unsigned char *s=p;for(usize i=0;i<n;i++)s[i]=c;return p;}
void *memcpy(void *p,const void *q,usize n){unsigned char *d=p;const unsigned char *s=q;for(usize i=0;i<n;i++)d[i]=s[i];return p;}
static usize len(const char *s){usize i=0;while(s[i])i++;return i;}
static void say(const char *s){sc(write,1,s,len(s),0,0,0);}
static int check(int ok,const char *name){say(ok?"PASS ":"FAIL: ");say(name);say("\n");return !ok;}
static int put(const char *path,const char *value){long fd=sc(openat,-100,path,1,0,0,0);if(fd<0)return -1;long r=sc(write,fd,value,len(value),0,0,0);sc(close,fd,0,0,0,0,0);return r==(long)len(value)?0:-1;}
static int readtext(const char *path,char *s,int n){long fd=sc(openat,-100,path,0,0,0,0);if(fd<0)return -1;long r=sc(read,fd,s,n-1,0,0,0);sc(close,fd,0,0,0,0,0);if(r<0)return -1;s[r]=0;return r;}
static int contains(const char *s,const char *n){for(;*s;s++){usize i=0;while(n[i]&&s[i]==n[i])i++;if(!n[i])return 1;}return 0;}
#define P "/sys/devices/system/cpu/cpufreq/policy0/"
static int memory_test(void)
{
 int e=0;long pid=sc(getpid,0,0,0,0,0,0),fd=sc(pidfd_open,pid,0,0,0,0,0);
 e+=check(fd>=0,"pidfd_open for standard compaction ABI");if(fd<0)return e;
 char *p=(void*)sc(mmap,0,8192,3,0x22,-1,0);if((long)p<0)return e+check(0,"anonymous memory map");
 p[0]=42;p[4096]=17;struct iovec v[2]={{p,4096},{p+4096,4096}};
 e+=check(sc(process_madvise,fd,v,2,20,0,0)==8192,"5-argument process_madvise MADV_COLD byte count");
 e+=check(sc(process_madvise,fd,v,2,21,0,0)==8192,"MADV_PAGEOUT byte count");
 e+=check(p[0]==42&&p[4096]==17,"compaction preserves anonymous data");
 v[1].iov_base=(void*)1;
 e+=check(sc(process_madvise,fd,v,2,20,0,0)==4096,"partial completion survives later invalid vector");
 e+=check(sc(process_madvise,fd,v+1,1,20,0,0)==-22,"unaligned vector rejected");
 e+=check(sc(process_madvise,fd,v,1,20,1,0)==-22,"unknown flags rejected");
 e+=check(sc(process_madvise,fd,v,1,4,0,0)==-22,"destructive DONTNEED advice rejected");
 e+=check(sc(process_madvise,-1,v,1,20,0,0)==-9,"invalid pidfd rejected");
 e+=check(sc(process_madvise,fd,v,1025,20,0,0)==-22,"oversized vector count rejected");
 e+=check(sc(process_madvise,fd,0,0,20,0,0)==0,"empty vector succeeds");
 struct __user_cap_header_struct hdr={_LINUX_CAPABILITY_VERSION_3,0};
 struct __user_cap_data_struct caps[2]={{0}};
 long r=sc(capget,&hdr,caps,0,0,0,0);unsigned int old=caps[0].effective;
 caps[0].effective &= ~(1U<<CAP_SYS_NICE);
 if(r==0)r=sc(capset,&hdr,caps,0,0,0,0);
 e+=check(r==0&&sc(process_madvise,fd,v,1,20,0,0)==-1,"CAP_SYS_NICE required for remote reclaim");
 caps[0].effective=old;e+=check(sc(capset,&hdr,caps,0,0,0,0)==0,"restore test capability");
 sc(munmap,p,8192,0,0,0,0);sc(close,fd,0,0,0,0,0);return e;
}
static int governor_test(const char *options)
{
 int e=0;char buf[1024];long fd=sc(openat,-100,"/fran_qemu_cpufreq.ko",0,0,0,0);
 if(fd<0)return check(0,"open CI-only cpufreq test module");
 long r=sc(finit_module,fd,options,0,0,0,0);sc(close,fd,0,0,0,0,0);
 e+=check(r==0,"load CI-only virtual cpufreq driver");if(r<0)return e;
 e+=check(readtext(P "scaling_available_governors",buf,sizeof(buf))>0&&contains(buf,"walt"),"real WALT governor registered");
 for(int i=0;i<4;i++){
  e+=check(put(P "scaling_governor","walt")==0,"select WALT and initialize tunables");
  e+=check(readtext(P "walt/hispeed_load",buf,sizeof(buf))>0,"WALT sysfs tunables exposed");
  e+=check(put(P "walt/up_rate_limit_us","500000")==0&&put(P "walt/down_rate_limit_us","500000")==0,"set long rate limits to test forced policy update");
  e+=check(put(P "scaling_min_freq","2000000")==0,"raise policy floor");
  for(volatile unsigned long j=0;j<10000000;j++){}
  e+=check(readtext(P "scaling_cur_freq",buf,sizeof(buf))>0&&contains(buf,"2000000"),"minimum enforced despite governor rate limit");
  e+=check(put(P "scaling_min_freq","800000")==0&&put(P "scaling_max_freq","800000")==0,"lower policy ceiling");
  for(volatile unsigned long j=0;j<10000000;j++){}
  e+=check(readtext(P "scaling_cur_freq",buf,sizeof(buf))>0&&contains(buf,"800000"),"maximum enforced despite governor rate limit");
  e+=check(put(P "scaling_max_freq","2000000")==0&&put(P "scaling_governor","schedutil")==0,"switch back to original schedutil");
 }
 e+=check(sc(delete_module,"fran_qemu_cpufreq",0,0,0,0,0)==0,"unload virtual driver and governor cleanly");return e;
}
static int compat_test(void)
{
 long child=sc(clone,17,0,0,0,0,0);
 if(!child){
  const char *args[]={"/compat-probe",0};
  sc(execve,args[0],args,0,0,0,0);
  sc(exit_group,127,0,0,0,0,0);
  for(;;){}
 }
 int status=-1;
 return check(child>0&&sc(wait4,child,&status,0,0,0,0)==child&&status==0,
              "AArch32 process_madvise compat ABI");
}
void start_c(void)
{
 int e=0;e+=check(sc(mount,"proc","/proc","proc",0,0,0)==0&&sc(mount,"sysfs","/sys","sysfs",0,0,0)==0,"mount test interfaces");
 if(!e){e+=memory_test();e+=compat_test();say("Testing fast switching\n");e+=governor_test("");say("Testing deferred switching\n");e+=governor_test("slow=1");}
 say(e?"PERFORMANCE_PROBE: FAIL\n":"PERFORMANCE_PROBE: PASS\n");
 sc(reboot,0xfee1dead,672274793,0x4321fedc,0,0,0);for(;;)sc(exit_group,1,0,0,0,0,0);
}
__asm__(".global _start\n_start:\nbl start_c\nb .\n");
