# HarnessVLA 固定策略与外层控制复现

**LIBERO-Pro 仿真研究 · Gary 的机器人工程实习项目**

这是 Gary 实习中的 HarnessVLA 仿真复现项目。项目在 LIBERO-Pro 上比较直接调用固定策略与加入 harness 的执行方式，并通过配对账本、失败分类和记忆消融检查结果来自哪里。

**研究问题：** 冻结同一个动作策略后，增加观察、验证、重试和记忆等外层控制，能否改善任务执行？

**已有结果：** 对保留账本按完整条件配对并排除基础设施失败，离线复算为 direct 15/40、harness 23/40；其中11对被挽回、3对出现回归。该统计来自既有记录，不是新增80次实验。 [查看原始分析与边界](docs/evidence/nov-m4/paired-analysis.json)。

## 演示与图像

[![LIBERO-Pro 仿真成功单例。画面用于理解任务，不替代配对统计，也不是 B601 实机演示。](docs/portfolio/assets/demo-poster.png)](docs/evidence/oct-m3/video/A_harness_success_spatial_task.mp4)

[播放原始演示片段](docs/evidence/oct-m3/video/A_harness_success_spatial_task.mp4)。LIBERO-Pro 仿真成功单例。画面用于理解任务，不替代配对统计，也不是 B601 实机演示。

## Gary 的实习工程工作

以下说明项目中的复现、实现、集成与分析工作。上游 ASPIRE／HarnessVLA 的论文方法不作为实习生原创方法；共享代码历史与本次文档整理不重复计为新增实现。

| 工作 | 具体内容 | 可检查入口 |
|---|---|---|
| 接通直接策略与 harness 执行 | 固定策略条件，比较外层规划、验证、重试和记忆。 | [代码或证据](track/launchers/run_harness.py) |
| 建立配对账本与失败分类 | 记录条件、种子、终止原因，避免混算无效或不配对记录。 | [代码或证据](track/analysis/build_ledger.py) |
| 进行对照与消融分析 | 报告整体改善与局部回归，保留记忆污染和审计边界。 | [代码或证据](track/analysis/compare.py) |
| 整理可复核视频与实验材料 | 为成功、回归、消融和时钟预算案例提供索引和来源。 | [代码或证据](docs/evidence/nov-m4/video-index.csv) |

这些材料可供评审检查机器人接口、状态机、实验设计、日志追踪与结果分析能力。实际实现提交见[代码与证据映射](docs/evidence/oct-m3/implementation-commits.csv)，不以证据整理提交替代实现贡献。

## 里程碑与当前状态

| 阶段 | 技术成果入口 | 如何理解完成范围 |
|---|---|---|
| 基础复现与接口准备 | 下方代码目录、[原技术说明](docs/history/readme-before-showcase-2026-11-14.md) | 按各项目区分仿真、软件验证和实体实验 |
| October／M3 集成 | [实现与验证索引](docs/evidence/oct-m3/README.md) | 有可复核实现和所列测试，不能推定所有合同条款已验收 |
| November／M4 比较 | [对照与演示索引](docs/evidence/nov-m4/README.md) | 既有结果与失败分析；无线比较和两项工业演示仍有缺口 |
| December／M5 准备 | [复现、归档与后续工程](docs/evidence/dec-m5/README.md) | 准备／部分证据；完整干净机器重建、最终演示和大文件取回尚未闭合 |

月份是交付组织标签，实验日期见原始记录。2026-11-14 的证据整理和无硬件测试不表示当日新增实机或仿真实验。完整说明见[评审阅读指南](docs/portfolio/README.md)。

## 结果限制与后续工作

这些是仿真结果，不能证明物理 B601、无线链路比较或工业部署。账本不同阶段的分母不同，早期5/20与11/20不能与扩展15/40与23/40混为同一次实验。

## 代码导航与复核

| 路径 | 内容 |
|---|---|
| `track/launchers/` | direct、harness、消融执行入口 |
| `track/analysis/` | 账本、统计和条件校验 |
| `track/registry/` | 进展、风险、记忆审计和冻结状态 |
| `docs/evidence/` | 账本快照、视频与复现边界 |

已有环境中的软件检查入口如下；准确依赖和平台条件按[复现说明](docs/evidence/dec-m5/reproduce.md)配置。本页面整理未重新运行完整实验，也不要求评审者驱动实体机械臂。

```sh
python3 -m pytest track/tests/ -q
```

## 四条项目轨道

| 项目 | 研究／验证环境 |
|---|---|
| [ASPIRE 技能积累复现](https://github.com/23garyd/aspire-sim-reproduction) | 仿真研究 |
| [ASPIRE 到 reBot B601 的机器人适配](https://github.com/23garyd/aspire-robot-B601) | 软件适配与假驱动验证 |
| [HarnessVLA 固定策略与外层控制复现](https://github.com/23garyd/harnessvla-sim-reproduction) | LIBERO-Pro 仿真研究 |
| [HarnessVLA 在 reBot B601 上的实机实验](https://github.com/23garyd/harnessvla-rebot-b601) | B601 实机研究与工程验证 |

四个仓库是相关但不同的复现和工程项目，结果不混算。原始论文与框架归属见仓库中的引用及许可说明。商业审批报告、发票和付款信息不属于本技术展示页。
