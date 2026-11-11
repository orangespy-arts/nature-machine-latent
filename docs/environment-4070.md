# 4070 台式机环境检查

检查日期：2026-11-11。同日按用户确认安装 RAVE 训练环境，并用合成音频完成预处理、smoke 训练、恢复和导出验证（见下文）。尚未复制真实素材，未启动正式训练。
用途：项目全部训练、训练试跑、测速、恢复与导出验证均在本机进行。

## 实测结果

| 项目 | 结果 |
| --- | --- |
| 操作系统 | Windows 10 专业版，10.0.19045 |
| CPU | Intel Core i7-13700K |
| 系统内存 | 约 32 GB（可见 33,288,672 KB）；检查时可用约 20.5 GiB |
| GPU | NVIDIA GeForce RTX 4070，12,282 MiB 显存；桌面应用空闲时已占用约 1.1 GiB |
| NVIDIA 驱动 | 546.33；nvidia-smi 显示 CUDA 12.3（驱动支持上限，不代表已安装 Toolkit） |
| 磁盘剩余 | C: 约 38.7 GB · D: 约 28.1 GB · E: 约 218.2 GB（仓库位于 E:） |
| Python | `py` 启动器可见 3.12.6（默认，`C:\Python312`）与 3.11.9；`python` 命令指向 3.11.9 |
| PyTorch | 3.12 中有 `torch 2.6.0+cpu`（CPU 版，`cuda.is_available()` 为 False）；3.11 中无 torch |
| torchaudio、acids-rave、gin、pytorch_lightning | 两个 Python 中均未安装 |
| FFmpeg、Conda、uv、rave 命令 | PATH 中未找到 |
| WSL | 命令存在，但未安装 Linux 发行版 |
| Git | 可用；`gh` 在 Git Bash 中未找到 |
| 素材 | 本机仓库中无 `datasets/raw/`（音频被 Git 忽略，尚未从笔记本传过来） |

## RAVE 版本核对（2026-11-11）

- PyPI 最新为 [`acids-rave` 2.3.1](https://pypi.org/project/acids-rave/)，2023-12-18 发布，`Requires-Python >=3.9`。
- GitHub [master 相对 v2.3.1 tag 只有 README 改动](https://github.com/acids-ircam/RAVE/compare/v2.3.1...master)（最新提交 2025-04-26），代码与 2.3.1 相同。本项目固定使用 2.3.1。
- 2.3.1 依赖固定 `scipy==1.10.0` 与 `pytorch-lightning==1.9.0`；[scipy 1.10.0](https://pypi.org/project/scipy/1.10.0/) 要求 Python `<3.12`，只提供 cp38–cp311 wheel。**因此训练环境须用本机 Python 3.11，不能用默认的 3.12。**
- `torch`、`torchaudio` 不固定版本，[README](https://github.com/acids-ircam/RAVE) 建议先自行安装匹配本机的 CUDA 版 torch 再装 RAVE；预处理调用外部 `ffmpeg` 解码，须在 PATH 中。
- README 标注 v2_small 最低 8 GB 显存，v2 为 16 GB。本机 12 GB 可作为 v2_small 候选；**v2 不适合本机**。实际峰值显存待试跑实测。

## 已安装的环境（2026-11-11）

| 项目 | 位置／版本 |
| --- | --- |
| 数据根目录 | `E:\nature-machine-latent-data\`：`raw\machine`、`raw\nature`、`processed`、`checkpoints\exp-002`、`exports\exp-002`、`listening\exp-002`；路径写入仓库根目录本机 `.env`（不进 Git） |
| 虚拟环境 | `E:\envs\rave-2.3.1\`，Python 3.11.9（系统 3.12 环境未改动） |
| torch / torchaudio | 2.5.0+cu121，来自 PyTorch cu121 源；`cuda.is_available()` 为 True，识别 RTX 4070 |
| acids-rave | 2.3.1；`pip check` 无冲突。关键版本：numpy 1.26.4、scipy 1.10.0、pytorch-lightning 1.9.0、protobuf 7.36.2、lmdb 3.0.0 |
| FFmpeg | 9.0.2（[gyan.dev](https://www.gyan.dev/ffmpeg/builds/) essentials，SHA-256 与官网校验值一致）；仅复制 `ffmpeg.exe`、`ffprobe.exe` 到 `E:\envs\rave-2.3.1\Scripts\`，只在该环境 PATH 生效，未改系统 PATH |
| 完整依赖 | [`configs/requirements-4070-rave-2.3.1.txt`](../configs/requirements-4070-rave-2.3.1.txt)（pip freeze，文件头写有重建命令） |

选择 torch 2.5.0 的依据：RAVE 依赖的 [`nn-tilde` 1.6.0](https://pypi.org/project/nn-tilde/) 固定 `torch==2.5`、要求 Python ≥3.11；cu121 构建在驱动 546.33（CUDA 12.3）之内。torch 2.5 与 pytorch-lightning 1.9.0 不是官方同期组合，下列 smoke 验证通过，但长时训练中如出现异常需优先排查这一点。

使用环境（PowerShell）：

```powershell
$env:PATH = "E:\envs\rave-2.3.1\Scripts;$env:PATH"   # 或运行 E:\envs\rave-2.3.1\Scripts\Activate.ps1
```

## Windows 上的实测问题与对策

1. **官方预处理在 Windows 上不可用** → 用项目脚本 [`scripts/rave_preprocess_windows.py`](../scripts/rave_preprocess_windows.py)。
   - 实测 `rave preprocess`：默认 protobuf（upb）后端在第 3 个片段报 `EncodeError: Failed to serialize proto`；强制纯 Python 后端则在约 18 个片段后停滞。同样的数据在主进程串行写入完全正常，问题出在其 `multiprocessing.Pool` + `Manager().Queue` 并行读取。
   - 源码中 `search_for_audios` 同时匹配 `*.wav` 和 `*.WAV`；Windows 路径不分大小写，每个文件会被收录两次（重复片段会进入训练和内部验证）。
   - 包装脚本直接调用已安装 RAVE 的预处理函数，只把并行读取改为串行、按路径去重；数据库格式与 `metadata.yaml` 不变。合成数据：20 个 30 秒文件 → 100 条，无重复。
2. **LMDB 预处理后按 `--max_db_size` 占满磁盘**：forest-s105ck01-v001 用 `--max_db_size 3` 预处理后 `data.mdb` 为 3072 MB，实际数据仅 942 MB（LMDB `last_pgno` 统计）。smoke 数据库从 2048 MB 缩到 50.4 MB 发生在训练打开它之后（修改时间与恢复训练同时），推测训练端以只读方式打开时按实际大小截断，未逐项验证。结论：预处理时需要至少 `--max_db_size` 的空闲磁盘，之后文件可能保持满额。默认 100 GB 不可用；按数据量显式设置并留余量（每条约 0.5 MB / 5.9 秒，单声道 44.1 kHz）。
3. **GPU 自动选择失败**：[`rave.core.setup_gpu`](https://github.com/acids-ircam/RAVE/blob/v2.3.1/rave/core.py) 只选择显存占用低于 5% 的 GPU；本机桌面已占用约 9%，因此报 `Trainer(devices=[])`。训练时必须加 `--gpu 0`。
4. **第二阶段（对抗训练）一开始就崩溃** → 用 [`scripts/rave_train_windows.py`](../scripts/rave_train_windows.py)（或自动续训的 [`run_training_windows.ps1`](../scripts/run_training_windows.ps1)）代替 `rave train`。
   - 实测：`--override PHASE_1_DURATION=500` 时，第 500 步判别器反向传播报 `CUDA error: an illegal memory access`（rave/model.py:404），`CUDA_LAUNCH_BLOCKING=1` 下稳定复现。torch 2.5.0+cu121 内置 cuDNN 9.1.0。
   - 关闭 cuDNN 即可通过。第一阶段关闭 cuDNN 会从约 13.5 降到 10.6 步/秒，所以包装只在 `warmed_up` 后关闭；第二阶段约 5.1–5.6 步/秒。
   - 根因是 cuDNN 内核还是 torch／驱动组合，未进一步区分；升级 torch 受 nn-tilde 固定 `torch==2.5` 限制。
   - 默认 `PHASE_1_DURATION` 为 1,000,000，未用包装时正式训练会在约 20 小时后崩溃。
5. **检查点只在验证时保存**（每 `--val_every` 步，默认 10,000），不是每个 epoch；中断最多损失到上一次验证之后的进度。另每 `--save_every`（默认 500,000）步额外保留一个检查点。
6. [`train.py`](https://github.com/acids-ircam/RAVE/blob/v2.3.1/scripts/train.py) 在 Windows 上强制 `num_workers=0`，数据在主进程加载。正式测速时观察 GPU 利用率是否受限。
7. 默认 `--max_steps 6000000`、`--val_every 10000`、`--save_every 500000`；smoke 运行需显式限制步数。
8. 当日调试时留下的停滞预处理进程（PID 28920）已由用户结束。

## Smoke 验证（合成音频，非真实素材）

数据：`processed\smoke-synthetic\`，20 段 30 秒合成正弦＋噪声，共约 9 分 48 秒。仅用于验证流程，其输出没有任何听感意义。

| 检查 | 命令要点 | 结果 |
| --- | --- | --- |
| 预处理 | `rave_preprocess_windows.py --channels 1 --max_db_size 2` | 100 条，约 1 秒完成 |
| 训练 | `rave train --config v2_small --channels 1 --gpu 0 --batch 8 --max_steps 300 --val_every 100` | 正常结束；约 13 步/秒（phase 1，数据量极小，不代表正式速度）；14.6 M 参数；整卡显存峰值约 3.9 GiB（含桌面约 1.1 GiB） |
| 检查点 | `checkpoints\smoke\smoke-synth_d744cc98b7\` | 写入 `config.gin`、`best.ckpt`、按 epoch 的 ckpt、TensorBoard 日志 |
| 恢复训练 | 同上加 `--ckpt <run 目录>`，`--max_steps 400` | 从 global_step 288 恢复并继续至 384（按 epoch 保存），优化器状态已恢复 |
| 导出 | `rave export --run <run 目录> --streaming` | 生成 `*_streaming.ts`，日志称兼容 RAVE VST；`torch.jit.load` 后 encode/decode/forward 可用，65536 样本输入 → 潜在 `(1, 1, 128)`（潜在维数 1 是极短训练后的 PCA 裁剪结果，正式模型需重新核对） |

未验证：phase 2 对抗训练阶段的速度与显存、真实素材的预处理时长、长时间训练稳定性、导出模型在 5070 笔记本或 Max/PD 中的加载。

## 待完成

- [x] 安装环境并记录依赖版本。
- [x] smoke 训练、恢复、导出验证（合成音频）。
- [ ] 从 5070 笔记本传入选片结果与清单，放入 `raw\`，核对 SHA-256。
- [ ] 按 exp-002 用真实素材测速（含 phase 2），记录显存与每步耗时。
- [ ] smoke 产物（`processed\smoke-synthetic\`、`checkpoints\smoke\`）可在正式训练前删除。
