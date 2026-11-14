# HarnessVLA 仿真实现与历史证据索引

整理日期：2026-11-14。实现基线：`cc653453f0bb6384a442007a1b0b411de827010b`。
本次整理已有仿真实验附件，不新增 rollouts，也不把仿真视频当作 B601 实机录像。

| 功能 | 实现 | 可复核附件 |
|---|---|---|
| 固定策略与 harness 对照执行 | [direct](../../../track/launchers/run_direct.py)、[harness](../../../track/launchers/run_harness.py) | [实验注册表快照](snapshot-2026-08-25/harnessvla_experiment_registry.md) |
| 配对账本与统计分析 | [账本构建](../../../track/analysis/build_ledger.py)、[比较分析](../../../track/analysis/compare.py) | [历史账本 CSV](snapshot-2026-08-25/harnessvla_ledger_80_rollouts.csv)、[技术进展记录](snapshot-2026-08-25/harnessvla_progress_log.md) |
| 仿真执行示例 | [harness 实现](../../../track/launchers/harness_lib.py) | [仿真视频](video/A_harness_success_spatial_task.mp4) |

`snapshot-2026-08-25/` 与既有技术证据包中的文件字节相同。视频原用于仿真空间任务演示，与其他月度材料重复使用不产生新增实验，也不证明物理 B601、安全拒绝或链路降级行为。

账本文件名含 `80_rollouts`，但内容含基础与扩展／消融记录。统计时须按注册表中的版本、条件、配对和终止原因过滤，不能按文件名推断全部记录属于同一组实验。原始每次 rollout 的大型目录不包含于此处，CSV 中的机器路径也不是外部可下载地址。

[2026-11-14 测试输出](verification/2026-11-14-tests.txt) 记录所列 36 项分析与 harness 单元测试通过，不是重新执行 GPU 仿真实验。

本仓库与 ASPIRE 仿真仓库分别引用、分别报告结果。

[manifest.csv](manifest.csv) 给出本目录全部附件的字节数、SHA-256 及来源。

[implementation-commits.csv](implementation-commits.csv) 将每项功能对应到实现文件、最后修改该文件的历史提交、完整基线中的代码链接和附件路径。历史实现提交与本次证据整理提交分别保留，避免把文档整理称作新增实现。
