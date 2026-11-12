# Mac 环境检查

检查日期：2026-11-12。用途（用户 2026-11-12 确定）：
- 声音：素材准备、试听、Max／nn~ patch、潜在空间探索；
- Arduino 接在本机，传感器与 Max 的联调在本机进行；
- 不进行训练。

## 实测结果

| 项目 | 结果 |
| --- | --- |
| 操作系统 | macOS 14.4.1（23E224） |
| 芯片／内存 | Apple M1，8 GB |
| Max | 9.0.9（`/Applications/Max.app`），实测以原生 arm64 运行，未经 Rosetta |
| nn~ | v1.6.0（2025-05-22 发布，用 torch 2.5.1 构建），安装在 `~/Documents/Max 9/Packages/nn_tilde/`，共 738 MB |
| Arduino | Arduino IDE 已安装；检查时未连接开发板，型号待记录 |
| Python | 3.11.9（python.org 版）；没有 numpy、soundfile、scipy |
| 3D 软件 | 已安装 Autodesk Fusion。3D 建模由 5070 笔记本负责，本机不承担 |

## nn~ 安装（2026-11-12，经用户同意）

- **来源**：[nn_tilde releases](https://github.com/acids-ircam/nn_tilde/releases) 中的 `nn_max_msp_macos_ub.tar.gz`，大小与 GitHub 标注一致（301,838,118 字节；GitHub 未公布哈希值），本地 SHA-256 为 `15d9f486…b727ea14`。
- **安装方式**：解压到 Max 9 Packages。没有使用 sudo，没有修改签名，没有改动系统设置。
- **签名**：`nn~.mxo`、`mc.nn~.mxo` 和 `support/` 下的 15 个 dylib 均由 IRCAM 签名（Developer ID，Team 3BD2P55TR2），`codesign --verify` 全部通过。
- **公证与隔离**：`spctl` 显示“Unnotarized Developer ID”，即签了名但没经过 Apple 公证。所有文件都没有隔离标记（quarantine），Max 能正常载入。
- **架构**：`nn~` 与 `libtorch_cpu` 都是通用二进制（x86_64 + arm64）。

## 模型与数据

- **模型位置**：模型复制到 `nn_tilde/models/`，在 patch 中只写模型名就能载入。
  - exp-003 第一阶段：`exp003-forest-s105ck01-p1-step1000000_streaming.ts`，SHA-256 `b2b4e1fa…26fb7a2`，与 4070 导出的一致。
- **兼容性**：模型在 Windows 上用 torch 2.5.0 导出，nn~ 用 torch 2.5.1 构建。实测 `forward` 能载入并出声。
- **试听包**：从 4070 拷来，放在仓库内的 `datasets/mac-exp003-p1/`（已加入 `.gitignore`），88 个文件的 SHA-256 全部一致。
- **测试 patch**：见 [instrument/max/exp-003](../instrument/max/exp-003/README.md)。

## 注意

- 本机连着蓝牙音箱（JBL Flip 5）。测延迟或演奏时，请用有线耳机或内置输出，因为蓝牙会额外增加延迟。
- `scripts/` 中的素材处理脚本（如 `convert_audio.py`）需要 numpy、soundfile、soxr，本机还没有安装。安装前要先问用户，并决定装在哪个虚拟环境里。

## 未验证

- 在 Max 中的 CPU 占用、实际延迟（用 `scripts/measure_max_latency.py` 测）、长时间运行的稳定性。
- 8 GB 内存能同时运行几个 nn~ 实例。
- 演出用哪台设备，暂不决定。
