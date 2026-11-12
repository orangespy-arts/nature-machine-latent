# exp-003 第一阶段模型 · Max 测试 patch

用于在 Mac 上测试 exp-003 第一阶段模型能否在 Max 中实时运行，并初步试探 4 个潜在维度。这里只有测试 patch，还不是演奏乐器。

| 文件 | 信号链 |
| --- | --- |
| `exp003-p1-forward-test.maxpat` | `sfplay~` → `nn~ … forward 2048` → 监听切换（原声／重建）→ 音量 → `ezdac~` |
| `exp003-p1-latent-test.maxpat` | `sfplay~` → `nn~ … encode 2048` → 每维 `z × 缩放 + 偏移` → `nn~ … decode 2048` → 音量 → `ezdac~` |

两个 patch 都带有：
- 双声道录音（`sfrecord~ 2`，左声道录原声、右声道录模型输出），用来测延迟；
- 读数 `adstatus cpu`：Max DSP 的 CPU 占用，每 250 ms 刷新一次。

## 环境

- **模型**：`exp003-forest-s105ck01-p1-step1000000_streaming.ts`，SHA-256 `b2b4e1fa…26fb7a2`。patch 只写模型名，要求模型位于 `~/Documents/Max 9/Packages/nn_tilde/models/`。模型和音频都不进 Git。
- **已确认（2026-11-12）**：Mac 配置为 macOS 14.4.1、Apple M1、8 GB 内存，Max 9.0.9 以原生 arm64 运行，没有经过 Rosetta。在这台 Mac 上，nn~ v1.6.0 能载入该模型的 `forward` 方法。
- **试听音频**：用 heldout 的 `__orig.wav`，目录在数据根目录下的 `listening/exp-003/p1-step1000000/level-matched/`。

## nn~ 参数（依据）

- 对象写法是 `nn~ <模型> <方法> <缓冲>`，缓冲默认 2048。缓冲越大，延迟越高、CPU 负担越低；缓冲大小只能在建对象时设定。设为 0 时，音频线程会等待模型输出，CPU 负担很重。以上来自 nn~ v1.6.0 自带的帮助 patch（`nn~.maxhelp` 的 buffer_size 页）和 [nn_tilde README](https://github.com/acids-ircam/nn_tilde)。
- encode 输出的潜在信号比音频速率慢，由 nn~ 在内部降采样后再输出（同一帮助 patch 的 overview 页）。
- 每一维做缩放和偏移的用法，来自 nn~ 自带 `rave_help.maxpat` 的示例：“We can mess up the scale and bias of each dimension separately.”

## 测试步骤

1. 记下 Max 的音频设置（Options → Audio Status）：
   - 驱动和设备
   - 采样率（应为 44100 Hz，和模型一致）
   - I/O Vector Size、Signal Vector Size
   - Audio Status 显示的输入／输出延迟
2. 打开 `exp003-p1-forward-test.maxpat`，点 `open` 选择一个 `__orig.wav`，点 `1` 播放，再打开 `ezdac~`。
3. 监听：发 `1` 听原声，发 `2` 听重建。记录：
   - 有没有爆音、断续；
   - CPU 读数大致是多少；
   - Max Console 有没有报错。
4. 测延迟：
   1. 先在录音区点 `open`，存成 `.wav`；
   2. 从头播放一个起音清楚的机械声文件（例如 typewriter），点录音区的 `1`；
   3. 录 15 秒以上后点 `0` 停止；
   4. 运行下面的命令。

   ```bash
   python3 scripts/measure_max_latency.py <录音.wav>
   ```

   脚本测的是 Max 信号链内的延迟（模型＋nn~ 缓冲）。如果改用麦克风输入，实际延迟还要加上 Audio Status 显示的输入／输出延迟。4070 上离线渲染测得的 238 ms 不含 nn~ 缓冲，**不能直接当作 Max 中的延迟**。
5. 打开 `exp003-p1-latent-test.maxpat`，同样播放：
   1. 先保持缩放 1、偏移 0，确认声音与 forward 版本相近；
   2. 一次只改一维的缩放或偏移，记录听到的变化，以及该维编码器输出的大致范围（看数字显示）；
   3. 把缩放设为 0，该维就由偏移手动给定。

## 记录要求

- 结果写进 [exp-003](../../../experiments/exp-003-mixed-insects-machine-plan.md) 和 [docs/log.md](../../../docs/log.md)，并注明：
  - 模型编号；
  - nn~ 缓冲；
  - Max 音频设置；
  - 测试用的文件。
- 只写听到和测到的结果。不要把某一维命名为“自然—机械”之类的语义轴，除非有反复试听的记录支持。即便有，也要写明这是试听得出的映射，不是模型提供的功能。
- 这是第一阶段模型（还没有对抗训练），音质偏闷属于预期。最终模型导出后要重新测一遍：第二阶段只改解码器，所以潜在结构不变，但音色、CPU 占用和延迟都可能变化。
