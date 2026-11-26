/* SPDX-License-Identifier: GPL-3.0-or-later */
/* QEMU-only test extension; never packaged in the Android runtime module. */
#include <linux/sched.h>
#include <linux/sched/types.h>
static int put_file(const char *path,const char *value)
{
 int fd=sc(openat,-100,path,1,0,0,0);if(fd<0)return fd;
 long r=sc(write,fd,value,len(value),0,0,0);int c=closefd(fd);
 return r==(long)len(value)?c:(r<0?r:-5);
}
static int get_file(const char *path,char *buf,unsigned long cap)
{
 int fd=sc(openat,-100,path,0,0,0,0);if(fd<0)return fd;
 long r=sc(read,fd,buf,cap-1,0,0,0);closefd(fd);if(r<0)return r;
 buf[r]=0;return 0;
}
static int effective_is(const char *key,unsigned long expected)
{
 static char text[16384];if(get_file("/proc/self/sched",text,sizeof(text)))return 0;
 for(char *s=text;*s;s++){
  unsigned long i=0;while(key[i] && s[i]==key[i])i++;
  if(key[i])continue;
  while(s[i] && s[i]!=':' && s[i]!='\n')i++;
  if(s[i++]!=':')continue;
  while(s[i]==' ' || s[i]=='\t')i++;
  unsigned long n=0;int digits=0;while(s[i]>='0' && s[i]<='9'){n=n*10+s[i++]-'0';digits++;}
  return digits && n==expected;
 }return 0;
}
static int test_uclamp(void)
{
 struct sched_attr saved={0},a={0},got={0};int error=0,mounted=0,joined=0;
 long r=sc(sched_getattr,0,&saved,sizeof(saved),0,0,0);
 if(r<0)return fail("sched_getattr",r);
 a=saved;a.size=sizeof(a);a.sched_flags|=SCHED_FLAG_UTIL_CLAMP_MIN|SCHED_FLAG_UTIL_CLAMP_MAX;
 a.sched_util_min=384;a.sched_util_max=1024;
 r=sc(sched_setattr,0,&a,0,0,0,0);if(r<0)return fail("task uclamp set",r);
 r=sc(sched_getattr,0,&got,sizeof(got),0,0,0);
 if(r<0 || got.sched_util_min!=384 || got.sched_util_max!=1024){error=fail("task uclamp readback",r);goto restore_task;}
 a.sched_util_min=1025;r=sc(sched_setattr,0,&a,0,0,0,0);
 if(r!=-22){error=fail("uclamp min > 1024 accepted",r);goto restore_task;}
 a.sched_util_min=512;a.sched_util_max=256;r=sc(sched_setattr,0,&a,0,0,0,0);
 if(r!=-22){error=fail("inverted task clamp accepted",r);goto restore_task;}
 a.sched_util_min=0;a.sched_util_max=1024;
 if((r=sc(sched_setattr,0,&a,0,0,0,0))<0){error=fail("reset test task hints",r);goto restore_task;}
 say("PASS per-task uclamp set/get and invalid bounds rejection\n");
 r=sc(mkdirat,-100,"/cg",0755,0,0,0);if(r<0){error=fail("mkdir cgroup mount",r);goto restore_task;}
 r=sc(mount,"cgroup","/cg","cgroup",0,"cpu",0);if(r<0){error=fail("mount CPU cgroup",r);goto restore_task;}mounted=1;
 r=sc(mkdirat,-100,"/cg/fran-test",0755,0,0,0);if(r<0){error=fail("create test cgroup",r);goto cleanup;}
 if(put_file("/cg/fran-test/cpu.uclamp.min","25.00") || put_file("/cg/fran-test/cpu.uclamp.max","75.00") ||
    put_file("/cg/fran-test/cpu.uclamp.latency_sensitive","1")){error=fail("cgroup uclamp writes",0);goto cleanup;}
 char v[64];
 if(get_file("/cg/fran-test/cpu.uclamp.latency_sensitive",v,sizeof(v)) || v[0]!='1'){error=fail("latency hint readback",0);goto cleanup;}
 if(put_file("/cg/fran-test/cpu.uclamp.latency_sensitive","2")!=-22 ||
    put_file("/cg/fran-test/cpu.uclamp.min","100.01")>=0){error=fail("invalid group hints accepted",0);goto cleanup;}
 if(put_file("/cg/fran-test/cgroup.procs","1")){error=fail("attach init to test group",0);goto cleanup;}joined=1;
 if(!effective_is("effective uclamp.min",256) || !effective_is("effective uclamp.max",768)){
  error=fail("effective cgroup clamps",0);goto cleanup;
 }
 if(put_file("/cg/fran-test/cpu.uclamp.min","50.00") || !effective_is("effective uclamp.min",512)){
  error=fail("live runnable-task clamp update",0);goto cleanup;
 }
 say("PASS CPU cgroup profile, latency hint, effective bounds and live update\n");
cleanup:
 if(joined && (r=put_file("/cg/cgroup.procs","1"))<0)error=fail("restore root cgroup",r);
 if((r=sc(unlinkat,-100,"/cg/fran-test",0x200,0,0,0))<0)error=fail("remove test cgroup",r);
 if(mounted && (r=sc(umount2,"/cg",0,0,0,0,0))<0)error=fail("unmount test controller",r);
restore_task:
 saved.sched_flags|=SCHED_FLAG_UTIL_CLAMP_MIN|SCHED_FLAG_UTIL_CLAMP_MAX;
 if((r=sc(sched_setattr,0,&saved,0,0,0,0))<0)error=fail("restore task attributes",r);
 if(!error)say("UCLAMP_FEATURE_PROBE: PASS\n");return error;
}
