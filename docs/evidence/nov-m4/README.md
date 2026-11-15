# HarnessVLA 仿真对照与消融附件

整理日期：2026-11-14。账本和视频均来自原有仿真实验，本次仅做无 GPU 离线统计与技术整理。

| 工作 | 实现 | 附件 |
|---|---|---|
| 配对条件与终止原因统计 | [比较程序](../../../track/analysis/compare.py)、[账本构建](../../../track/analysis/build_ledger.py) | [既有账本](../oct-m3/snapshot-2026-08-25/harnessvla_ledger_80_rollouts.csv)、[本次离线分析](paired-analysis.json) |
| 固定策略与 harness 执行 | [harness](../../../track/launchers/harness_lib.py) | [视频目录](video/)、[视频索引与哈希](video-index.csv) |
| 隐藏记忆消融及失败边界 | [消融入口](../../../track/launchers/run_ablation_hiddenmem.sh) | [既有机制记录](../../../track/registry/day8_mechanism.md)、[记忆审计](../../../track/registry/memory_audit.md) |
| 分析与环境门禁检查 | [测试](../../../track/tests/) | [53 项测试输出](verification/2026-11-14-tests.txt) |

按原比较程序仅取完整条件配对、排除基础设施失败，已恢复账本重新算得 direct 15/40、harness 23/40。这是当前保留账本的离线复算，不是新 rollout；条件定义、终止原因、消融污染与隔离行仍按原注册表和审计记录解释。

四段视频分别说明回归、隐藏记忆消融、无记忆超时及增加时钟预算的个案。它们均是仿真视频，不能充当 B601 实机、无线通信比较或两个工业应用场景均已完成的证据。局部案例也不能代替完整配对统计。

[implementation-commits.csv](implementation-commits.csv) 映射代码提交，[manifest.csv](manifest.csv) 保留所有附件哈希。
