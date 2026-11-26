#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile the real governor functions in a deterministic mocked rq environment."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
path='kernel/sched/cpufreq_schedutil.c'
current=(root/path).read_text()
baseline=(root/'ci/uclamp/sugov-baseline.c').read_text()
def function(source,name):
    # Locate the declaration preceding this function, not an earlier call.
    import re
    m=re.search(r'static (?:unsigned long|unsigned int|void) '+name+r'\(',source)
    assert m,name
    start=m.start();a=source.index('{',m.end());depth=1;i=a+1
    while depth:
        depth+=(source[i]=='{')-(source[i]=='}');i+=1
    return source[start:i]
pre=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <stddef.h>
typedef uint64_t u64;typedef int64_t s64;
#define max(a,b) ((a)>(b)?(a):(b))
#define min(a,b) ((a)<(b)?(a):(b))
#define mult_frac(x,n,d) ((x)*(n)/(d))
#define NL_RATIO 75
#define TARGET_LOAD 80
#define SCHED_CPUFREQ_INTERCLUSTER_MIG 1
struct sugov_tunables {unsigned int hispeed_load;bool pl;};
struct cpufreq_policy {unsigned int cpus;};
struct sugov_policy {struct cpufreq_policy *policy;struct sugov_tunables *tunables;unsigned long rtg_boost_util,hispeed_util,avg_cap;u64 last_freq_update_time;};
struct sugov_cpu {int cpu;struct sugov_policy *sg_policy;unsigned int flags;unsigned long util,max,iowait_boost;u64 last_update;struct {bool rtgb_active;unsigned long nl,pl;} walt_load;};
struct rq {unsigned long lo,hi;};
static struct sugov_cpu sugov_cpu[2];static struct rq runqueues[2];static bool enabled=true,pelt;
static s64 stale_ns=1000;
#define per_cpu(array,j) array[j]
#define for_each_cpu(j,mask) for((j)=0;(j)<2;(j)++) if((mask)&(1U<<(j)))
static struct rq *cpu_rq(unsigned int i){return &runqueues[i];}
static bool use_pelt(void){return pelt;}
static bool conservative_pl(void){return false;}
static unsigned long uclamp_rq_util_with(struct rq *rq,unsigned long u,void *unused){(void)unused;if(!enabled)return u;if(rq->lo>=rq->hi)return rq->lo;return min(max(u,rq->lo),rq->hi);}
static unsigned long sugov_iowait_apply(struct sugov_cpu *c,u64 t,unsigned long u,unsigned long cap){(void)t;(void)cap;return max(u,c->iowait_boost);}
static bool sugov_iowait_reset(struct sugov_cpu *c,u64 t,bool set){(void)t;(void)set;c->iowait_boost=0;return true;}
static unsigned int get_next_freq(struct sugov_policy *p,unsigned long u,unsigned long cap){(void)p;return u*1000/cap;}
'''
post=r'''
static void init(struct sugov_policy *p){for(int i=0;i<2;i++){sugov_cpu[i]=(struct sugov_cpu){.cpu=i,.sg_policy=p,.max=1024,.last_update=100};runqueues[i]=(struct rq){0,1024};}enabled=true;pelt=false;}
int main(void){
 struct cpufreq_policy cp={3};struct sugov_tunables tune={.hispeed_load=90};struct sugov_policy p={.policy=&cp,.tunables=&tune,.avg_cap=1024,.last_freq_update_time=100};
 int regressions=0;unsigned long cap;
 init(&p);sugov_cpu[0].util=100;sugov_cpu[0].iowait_boost=1024;runqueues[0].hi=128;runqueues[1].hi=128;
 if(sugov_next_freq_shared(&sugov_cpu[0],100)!=125)regressions++;
 init(&p);sugov_cpu[0].util=100;sugov_cpu[0].iowait_boost=1024;runqueues[0].hi=128;sugov_cpu[1].util=600;runqueues[1].hi=768;
 if(sugov_next_freq_shared(&sugov_cpu[0],100)!=585)regressions++;
 init(&p);sugov_cpu[0].util=100;runqueues[0].hi=128;sugov_cpu[1].util=900;
 assert(sugov_next_freq_shared(&sugov_cpu[0],100)==878);
 init(&p);sugov_cpu[0].last_update=0;p.last_freq_update_time=2000;sugov_cpu[0].iowait_boost=1024;sugov_cpu[1].last_update=2000;sugov_cpu[1].util=512;
 assert(sugov_next_freq_shared(&sugov_cpu[0],2000)==500);p.last_freq_update_time=100;
#ifdef FINAL_CLAMP
 assert(regressions==0);
 init(&p);runqueues[0]=(struct rq){256,512};cap=1024;
 assert(sugov_effective_util(&sugov_cpu[0],100,10,&cap)==256);
 sugov_cpu[0].iowait_boost=1024;assert(sugov_effective_util(&sugov_cpu[0],100,10,&cap)==512);
 sugov_cpu[0].iowait_boost=0;tune.pl=true;sugov_cpu[0].walt_load.pl=1024;
 assert(sugov_effective_util(&sugov_cpu[0],100,10,&cap)==512);tune.pl=false;
 sugov_cpu[0].walt_load.rtgb_active=true;p.rtg_boost_util=1024;
 assert(sugov_effective_util(&sugov_cpu[0],100,10,&cap)==512);
 init(&p);runqueues[0].lo=512;sugov_cpu[0].util=100;p.avg_cap=400;p.hispeed_util=1024;
 assert(sugov_effective_util(&sugov_cpu[0],100,100,&cap)==512);
 pelt=true;sugov_cpu[0].iowait_boost=1024;runqueues[0].hi=768;
 assert(sugov_effective_util(&sugov_cpu[0],100,100,&cap)==768);
 pelt=false;enabled=false;sugov_cpu[0].iowait_boost=0;sugov_cpu[0].util=800;
 assert(sugov_effective_util(&sugov_cpu[0],100,800,&cap)==1024);
 puts("PASS final WALT/IO clamps, minimum floor, raw-load threshold, shared policy and stale CPU");
#else
 (void)cap;assert(regressions==2);puts("PASS both clamp regressions reproduced in the original governor");
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    for title,src in [('baseline',baseline),('current',current)]:
        code=pre+'\n'+function(src,'sugov_walt_adjust')+'\n'
        if title=='current':code+='#define FINAL_CLAMP 1\n'+function(src,'sugov_effective_util')+'\n'
        code+=function(src,'sugov_next_freq_shared')+'\n'+post
        p=Path(td)/title;p.with_suffix('.c').write_text(code)
        subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',str(p.with_suffix('.c')),'-o',str(p)],check=True)
        subprocess.run([str(p)],check=True)
