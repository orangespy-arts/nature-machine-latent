# exp-003 训练流程：步骤与进度（4070）

更新：2026-11-17。共 **12 步**：第 1–11 步已完成，第 12 步（评价）进行中：重建试听在 Mac 上进行，插值与交叉淡化对照文件在 4070 上生成。

| # | 步骤 | 状态 | 位置／产物 |
| --- | --- | --- | --- |
| 1 | 安装 RAVE 训练环境并用合成音频验证 | ✅ 完成 | `E:\envs\rave-2.3.1\`；`docs/environment-4070.md` |
| 2 | 素材到位并核对哈希 | ✅ 完成 | `raw\dataset1\`，234 个文件与处理报告一致 |
| 3 | 按录音组划分训练／留出 | ✅ 完成 | `datasets/manifests/forest-s105ck01-v001-split.csv`；训练块数机械 934、自然 936（模型实际听到的量各一半） |
| 4 | 复制文件并预处理训练集 | ✅ 完成 | `processed\forest-s105ck01-v001\{train,heldout,db}`，1870 条，约 3 小时 5 分 |
| 5 | 测速 | ✅ 完成 | 阶段一约 13.5 步/秒，显存约 3.9 GB；阶段二切换时崩溃（见第 6 步） |
| 6 | 修复阶段二崩溃 | ✅ 完成 | `scripts/rave_train_windows.py`：进入对抗训练后关闭 cuDNN；跨切换测试通过（阶段二约 5.1–5.6 步/秒）；从阶段二检查点恢复、`scripts/run_training_windows.ps1` 自动续训均已验证 |
| 7 | 启动正式训练 | ✅ 完成 | 11-11 20:27 启动，`checkpoints\exp-003\exp003-forest-s105ck01_d744cc98b7\`；P 核亲和性见 `docs/environment-4070.md` 第 6 条 |
| 8 | 训练中监控，崩溃后从检查点恢复 | ✅ 完成（全程未崩溃、未重启） | 检查点只在验证时保存（每 10,000 步），中断最多损失约 12 分钟（阶段一）／31 分钟（阶段二）；`run_training_windows.ps1` 崩溃后自动续训，最多 5 次 |
| 9 | 阶段一结束（100 万步）后试听重建 | ✅ 已导出并生成试听文件 | 11-12 17:01；`exports\exp-003\…-p1-step1000000_streaming.ts`，`listening\exp-003\p1-step1000000\`；Mac 上 nn~ 可载入出声，逐个试听未记录 |
| 10 | 阶段二对抗训练，定期试听比较检查点 | ✅ 完成 | 11-13 18:29 到 1,500,000 步正常结束；约 5.3–5.4 步/秒；`best.ckpt` 停在阶段一，不代表最终模型 |
| 11 | 选定检查点，streaming 导出 | ✅ 完成 | `epoch_1500000.ckpt` → `exports\exp-003\exp003-forest-s105ck01-final-step1500000_streaming.ts`（SHA-256 c902955f…b8799c）；拷贝包 `handoff\mac-exp003-final\` |
| 12 | 用留出素材评价：重建、自然↔机械插值、与交叉淡化对照 | 🔄 进行中 | `listening\`；结论写入 exp-003 |

## 训练命令（第 7 步）

```powershell
$env:PATH = "E:\envs\rave-2.3.1\Scripts;$env:PATH"
python scripts/rave_train_windows.py --config v2_small `
  --db_path E:\nature-machine-latent-data\processed\forest-s105ck01-v001\db `
  --out_path E:\nature-machine-latent-data\checkpoints\exp-003 --name exp003 `
  --channels 1 --gpu 0 --batch 8
```

恢复训练：同一命令加 `--ckpt <checkpoints\exp-003\exp003_xxxxxxxxxx 目录>`。

## 待注意

- 测速试跑产物在 `checkpoints\exp-003-speedtest\`，正式训练前可删（需用户确认）。
