# 复现与归档技术说明

整理日期：2026-11-14。此目录用于 December 技术交付准备，不表示 December 已验收或所有最终工作已完成。

已检出的源提交：`05ad169a0bea541b1c7a36fafe3b0012a4866bc3`。代码与既有附件的每个文件由 [archive-manifest.csv](archive-manifest.csv) 给出固定 GitHub 链接、字节数和 SHA-256。归档范围为该源提交全部已跟踪文件；不含本次新建的 dec-m5 自身，其完整性由 [manifest.csv](manifest.csv) 另行记录，避免循环哈希。

```bash
git clone https://github.com/23garyd/harnessvla-sim-reproduction.git
cd harnessvla-sim-reproduction
git checkout 05ad169a0bea541b1c7a36fafe3b0012a4866bc3
```

归档 CSV 的路径相对仓库根目录。下载/检出后逐项用 SHA-256 校验；文件字节受证据目录 Git 属性保护。仓库仍为 private，访问使用现有授权。

[已有环境中的测试命令与真实输出](../nov-m4/verification/2026-11-14-tests.txt) 只证明指定无硬件软件子集可运行。软件完整依赖、GPU、厂商 SDK、模型与原始数据按 [仓库说明](../../../README.md) 和原环境锁定文件另行准备。

此次已做的是从已有私有源检出代码、验证附件及软件子集；没有完成整套系统在干净机器上的重建，也没有验证第三方可独立启动真实试验。不要在未经测量/标定的机器上直接执行实体机器人入口；当前软件检查不需要给机械臂上电。

[setup.sh](../../../track/setup/setup.sh) 与 [pin_check.sh](../../../track/setup/pin_check.sh) 是原 GPU 环境入口。本次只运行无 GPU 软件检查；RPent、pi0.5 权重与完整 artifacts 目录属于外部依赖，不能由少量视频或账本替代。
