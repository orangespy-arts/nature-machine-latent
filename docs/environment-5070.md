# 5070 笔记本环境检查

检查日期：2026-10-30。仅检查与记录，未安装软件或启动训练。

## 实测结果

| 项目 | 结果 |
| --- | --- |
| 操作系统 | Windows 11 家庭版 中文版，10.0.26200 |
| CPU | Intel Core Ultra 9 275HX |
| 系统内存 | 约 32 GB（系统报告可见容量约 31.4 GiB） |
| 当时可用内存 | 约 12.9 GiB，随应用运行变化 |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU |
| 显存 | 8151 MiB，约 8 GB |
| NVIDIA 驱动 | 592.01 |
| nvidia-smi 显示的 CUDA 版本 | 13.1；这是驱动支持信息，不代表已安装 CUDA Toolkit 或 PyTorch |
| C 盘剩余空间 | 约 310 GiB |
| D 盘剩余空间 | 约 93 GiB |
| Python | 已发现 3.11、3.12、3.14；python 命令为 3.12.10，py 默认选择 3.14 |
| PyTorch、torchaudio、acids-rave | 在上述三个 Python 环境中均未查到；不排除其他未登记的环境 |
| FFmpeg、Conda、rave 命令 | 当前 PATH 未找到，不代表整个磁盘没有相关文件 |
| WSL | 命令存在，但查询返回安装提示及非零退出码，未确认有可用 Linux 环境 |
| Git | 可用，项目已建立仓库 |

## 用途与边界

用户已明确：这台 5070 笔记本不进行任何训练，包括短训练或训练试跑。
所有模型训练、恢复训练和训练性能验证均在 4070 台式机完成。
~~笔记本用于素材整理、音频检查、试听、项目管理，以及后续加载已训练模型进行演奏和装置调试。~~
2026-11-12 起：笔记本改为负责 3D 建模、切片并连接 3D 打印机；素材准备、试听与 Max／Arduino 调试改到 Mac（见 [Mac 环境](environment-mac.md)）。下方“待完成”中与素材、演奏相关的条目随之转到 Mac。
无需为训练安装 PyTorch、torchaudio、RAVE 或 WSL。后续演奏运行环境按所选宿主与模型格式另行确定。

## 声画联动（reveal）环境（2026-11-21）

2026-11-21 用户决定 5070 也要能运行声画联动（仍不训练）。

| 项目 | 结果 |
| --- | --- |
| 画面 Python 环境 | `C:\AI\sdtest`（2026-06 为本机装的）：Python 3.11.9，torch 2.11.0+cu128，capability (12, 0) 可用；streamdiffusion 0.1.1（pip，无 `utils/wrapper.py`），diffusers 0.24.0；无 xformers |
| python-osc | 1.10.3，经用户同意 `pip install --no-deps` 装入 `C:\AI\sdtest` |
| 模型缓存 | `%USERPROFILE%\.cache\huggingface\hub`（未设 `HF_HOME`）：sd-turbo、taesd 已在 |
| 画面运行 | `visual/sdgen.py` 自动改用 `CoreWrapper`；`SD_ACCELERATION=none`。demo：显示 20.5／生成 10.0 fps（无 OSC），18.3／10.5 fps（开 OSC），显存约 3.0 GB |
| 交接包 | U 盘拷自 4070，放在 `D:\nature-machine-latent-5070-reveal\`，31 个文件 SHA256 全部一致。其中 `nature-machine-latent\` 是旧副本，画面程序用本仓库 |
| Max | 9.0.8，`C:\Program Files\Max 9\Max.exe`（用户安装） |
| nn~ | v1.6.0 `nn_max_msp_windows_x64.tar.gz`（经用户同意下载，332,296,372 字节，SHA-256 `aced3dfb…e48d8b92`，与 4070 相同），装在 `C:\Users\wangz\Documents\Max 9\Packages\nn_tilde\`，约 1.2 GB |
| RAVE 模型 | `nn_tilde\models\exp003-forest-s105ck01-final-step1500000_streaming.ts`，SHA-256 `C902955F…B8799C` |

完整启动步骤见 [5070 启动指南](guide-run-reveal-5070.md)。

运行画面（在本仓库根目录）：

```powershell
$env:SD_ACCELERATION = "none"; $env:HF_HUB_OFFLINE = "1"; C:\AI\sdtest\Scripts\python.exe visual\reveal.py --input demo --windowed --debug
```

打开声音：

```powershell
Start-Process "C:\Program Files\Max 9\Max.exe" "D:\nature-machine-latent-5070-reveal\max\reveal-sound-5070.maxpat"
```

2026-11-21 实测（demo 输入）：patch 自动开音频，sr 44100；声画联动时 a 0–0.77、env 0–1、输出电平最高 0.42，nn~ 载入模型并出声。`adstatus cpu` 读数只在 0／1／100 间跳，不能作参考。

鼠标输入下按住时声音卡顿：画面生成占约 20／24 核，与 nn~（CPU 推理）抢 CPU。`visual/reveal.py` 现默认把 CPU 线程限制为 4（`VISUAL_CPU_THREADS`），生成时约 4.9 核，用户确认不再卡；当时 Max 另设为 High 优先级。这台的 nn~ 不能用 GPU（官方 Windows 包只有 CPU libtorch），见 [log](log.md) 2026-11-21。

未测：音频驱动与 vector size、摄像头输入、声画延迟差、不调优先级时是否仍流畅。

## 待完成

- [ ] 建立素材目录与独立备份。
- [ ] 根据素材检查需求安装并验证 FFmpeg 等音频工具。
- [ ] 登记素材来源、许可、音频属性与文件校验值。
- [ ] 试听筛选、检查重复与损坏文件，保留原始录音。
- [ ] 按录音场次划分数据集，准备交给台式机的素材、清单与处理记录。
- [ ] 选择演奏宿主，后续加载台式机导出的模型并测试声卡、缓冲与稳定性。
