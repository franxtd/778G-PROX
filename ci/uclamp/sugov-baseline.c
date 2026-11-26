/* SPDX-License-Identifier: GPL-2.0-only */
/* Test fixture copied verbatim from 00cf9162657ed37fc3a460523ec84b3aa6bed9a2. */
static void sugov_walt_adjust(struct sugov_cpu *sg_cpu, unsigned long *util,
			      unsigned long *max)
{
	struct sugov_policy *sg_policy = sg_cpu->sg_policy;
	bool is_migration = sg_cpu->flags & SCHED_CPUFREQ_INTERCLUSTER_MIG;
	bool is_rtg_boost = sg_cpu->walt_load.rtgb_active;
	unsigned long nl = sg_cpu->walt_load.nl;
	unsigned long cpu_util = sg_cpu->util;
	bool is_hiload;
	unsigned long pl = sg_cpu->walt_load.pl;

	if (use_pelt())
		return;

	if (is_rtg_boost)
		*util = max(*util, sg_policy->rtg_boost_util);

	is_hiload = (cpu_util >= mult_frac(sg_policy->avg_cap,
					   sg_policy->tunables->hispeed_load,
					   100));

	if (is_hiload && !is_migration)
		*util = max(*util, sg_policy->hispeed_util);

	if (is_hiload && nl >= mult_frac(cpu_util, NL_RATIO, 100))
		*util = *max;

	if (sg_policy->tunables->pl) {
		if (conservative_pl())
			pl = mult_frac(pl, TARGET_LOAD, 100);
		*util = max(*util, pl);
	}
}

static unsigned int sugov_next_freq_shared(struct sugov_cpu *sg_cpu, u64 time)
{
	struct sugov_policy *sg_policy = sg_cpu->sg_policy;
	struct cpufreq_policy *policy = sg_policy->policy;
	u64 last_freq_update_time = sg_policy->last_freq_update_time;
	unsigned long util = 0, max = 1;
	unsigned int j;

	for_each_cpu(j, policy->cpus) {
		struct sugov_cpu *j_sg_cpu = &per_cpu(sugov_cpu, j);
		unsigned long j_util, j_max;
		s64 delta_ns;

		/*
		 * If the CPU utilization was last updated before the previous
		 * frequency update and the time elapsed between the last update
		 * of the CPU utilization and the last frequency update is long
		 * enough, don't take the CPU into account as it probably is
		 * idle now (and clear iowait_boost for it).
		 */
		delta_ns = last_freq_update_time - j_sg_cpu->last_update;
		if (delta_ns > stale_ns) {
			sugov_iowait_reset(j_sg_cpu, last_freq_update_time,
					   false);
			continue;
		}

		/*
		 * If the util value for all CPUs in a policy is 0, just using >
		 * will result in a max value of 1. WALT stats can later update
		 * the aggregated util value, causing get_next_freq() to compute
		 * freq = max_freq * 1.25 * (util / max) for nonzero util,
		 * leading to spurious jumps to fmax.
		 */
		j_util = j_sg_cpu->util;
		j_max = j_sg_cpu->max;
		j_util = sugov_iowait_apply(j_sg_cpu, time, j_util, j_max);

		if (j_util * max >= j_max * util) {
			util = j_util;
			max = j_max;
		}

		sugov_walt_adjust(j_sg_cpu, &util, &max);
	}

	return get_next_freq(sg_policy, util, max);
}
