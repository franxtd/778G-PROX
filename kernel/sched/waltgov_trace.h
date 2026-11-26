/* SPDX-License-Identifier: GPL-2.0-only */
#undef TRACE_SYSTEM
#define TRACE_SYSTEM waltgov
#if !defined(_WALTGOV_TRACE_H) || defined(TRACE_HEADER_MULTI_READ)
#define _WALTGOV_TRACE_H
#include <linux/tracepoint.h>
TRACE_EVENT(waltgov_util_update,
	    TP_PROTO(int cpu,
		     unsigned long util, unsigned long avg_cap,
		     unsigned long max_cap, unsigned long nl, unsigned long pl,
		     unsigned int rtgb, unsigned int flags),
	    TP_ARGS(cpu, util, avg_cap, max_cap, nl, pl, rtgb, flags),
	    TP_STRUCT__entry(
		    __field(int, cpu)
		    __field(unsigned long, util)
		    __field(unsigned long, avg_cap)
		    __field(unsigned long, max_cap)
		    __field(unsigned long, nl)
		    __field(unsigned long, pl)
		    __field(unsigned int, rtgb)
		    __field(unsigned int, flags)
	    ),
	    TP_fast_assign(
		    __entry->cpu = cpu;
		    __entry->util = util;
		    __entry->avg_cap = avg_cap;
		    __entry->max_cap = max_cap;
		    __entry->nl = nl;
		    __entry->pl = pl;
		    __entry->rtgb = rtgb;
		    __entry->flags = flags;
	    ),
	    TP_printk("cpu=%d util=%lu avg_cap=%lu max_cap=%lu nl=%lu pl=%lu rtgb=%u flags=0x%x",
		      __entry->cpu, __entry->util, __entry->avg_cap,
		      __entry->max_cap, __entry->nl,
		      __entry->pl, __entry->rtgb, __entry->flags)
);

TRACE_EVENT(waltgov_next_freq,
	    TP_PROTO(unsigned int cpu, unsigned long util, unsigned long max,
		     unsigned int freq),
	    TP_ARGS(cpu, util, max, freq),
	    TP_STRUCT__entry(
		    __field(unsigned int, cpu)
		    __field(unsigned long, util)
		    __field(unsigned long, max)
		    __field(unsigned int, freq)
	    ),
	    TP_fast_assign(
		    __entry->cpu = cpu;
		    __entry->util = util;
		    __entry->max = max;
		    __entry->freq = freq;
	    ),
	    TP_printk("cpu=%u util=%lu max=%lu freq=%u",
		      __entry->cpu,
		      __entry->util,
		      __entry->max,
		      __entry->freq)
);

#endif
#undef TRACE_INCLUDE_PATH
#define TRACE_INCLUDE_PATH ../../kernel/sched
#undef TRACE_INCLUDE_FILE
#define TRACE_INCLUDE_FILE waltgov_trace
#include <trace/define_trace.h>
