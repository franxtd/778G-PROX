// SPDX-License-Identifier: GPL-2.0-only
/* CI-only synthetic cpufreq hardware, refuses physical phone platforms. */
#include <linux/module.h>
#include <linux/cpufreq.h>
#include <linux/of.h>

static unsigned int current_khz = 800000;
static struct cpufreq_frequency_table rates[] = {
	{ .frequency = 800000 }, { .frequency = 1200000 },
	{ .frequency = 2000000 }, { .frequency = CPUFREQ_TABLE_END },
};
static unsigned int get(unsigned int cpu)
{
	return READ_ONCE(current_khz);
}
static int target(struct cpufreq_policy *policy, unsigned int index)
{
	WRITE_ONCE(current_khz, rates[index].frequency);
	return 0;
}
static unsigned int fast(struct cpufreq_policy *policy, unsigned int freq)
{
	WRITE_ONCE(current_khz, freq);
	return freq;
}
static bool slow;
module_param(slow, bool, 0400);
static int init_policy(struct cpufreq_policy *policy)
{
	cpufreq_generic_init(policy, rates, 100000);
	policy->fast_switch_possible = !slow;
	policy->cur = get(policy->cpu);
	return 0;
}
static struct cpufreq_driver test_driver = {
	.name = "fran-qemu",
	.flags = CPUFREQ_HAVE_GOVERNOR_PER_POLICY | CPUFREQ_STICKY,
	.verify = cpufreq_generic_frequency_table_verify,
	.target_index = target,
	.fast_switch = fast,
	.get = get,
	.init = init_policy,
	.attr = cpufreq_generic_attr,
};
static int __init test_init(void)
{
	if (!of_machine_is_compatible("linux,dummy-virt"))
		return -ENODEV;
	return cpufreq_register_driver(&test_driver);
}
static void __exit test_exit(void)
{
	cpufreq_unregister_driver(&test_driver);
}
module_init(test_init);
module_exit(test_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("CI-only virtual cpufreq hardware for WALT lifecycle testing");
