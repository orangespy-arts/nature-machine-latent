继续 Nature–Machine Latent 项目。这台是装了 Max/MSP 的 Mac，用于试听和演奏，**不进行任何训练或训练试跑**（训练全部在 RTX 4070 台式机上）。

先在仓库 `~/Github/nature-machine-latent` 里 `git pull`，然后读：
- `AGENTS.md`（项目规则与设备分工：技术判断要有资料依据，给出来源链接；区分 RAVE 本身能力、外围程序实现、需要试听或实测确认的效果）
- `docs/log.md` 最上面 2026-11-12、2026-11-13 的几条
- `docs/environment-mac.md`、`instrument/max/exp-003/README.md`（这台 Mac 上已做过的第一阶段模型测试）
- `experiments/exp-003-mixed-insects-machine-plan.md`

## 现状

- exp-003：自然（forest）＋机械（S105）混合训练，RAVE 2.3.1 v2_small，单声道 44.1 kHz，训练集按块数 1:1。2026-11-13 18:29 在 4070 上训练完成（1,500,000 步：第一阶段 100 万步＋第二阶段对抗训练 50 万步，未重启）。
- **最终模型**（streaming）：
  `exports/exp-003/exp003-forest-s105ck01-final-step1500000_streaming.ts`
  SHA-256 `c902955fac9a3ba7266cdce332bda712175b622fc9ed6dcccf0003ead9b8799c`
  - 来源 `epoch_1500000.ckpt`（不是 `best.ckpt`：后者停在第一阶段）。Windows 上 torch 2.5.0、CPU 导出；latent 4 维（fidelity 0.95），full latent 128；导出日志称兼容 RAVE VST。
  - 第二阶段冻结编码器、只训练解码器，所以潜在结构与第一阶段模型相同，但解码音质不同。
  - 4070 离线渲染测得重建比原声晚约 238 ms。Max 中的总延迟还要加上音频与 nn~ 缓冲，须在本机实测。
- 第一阶段模型 `exports/exp-003/exp003-forest-s105ck01-p1-step1000000_streaming.ts` 及其试听文件 `listening/exp-003/p1-step1000000/` 如已拷到本机，可作对照。
- **最终模型试听文件**：同一批 17 个 heldout 文件（训练未使用：机械 10、自然 7），说明见 `listening/exp-003/final-step1500000/README.txt`：
  - `level-matched/<machine|nature>/<名称>__ab.wav`：原声最响 10 秒 → 1 秒静音 → 对齐后的重建
  - `level-matched/.../__orig.wav`、`__recon.wav`：同增益调响度的完整原声与重建
  - `raw-level/`：原电平；`summary.csv`：电平、峰值、延迟、增益
  - 数据上（**尚未试听**）：
    - 机械类与较响的自然类，重建电平比第一阶段更接近原声。
    - forest_crickets_birdsong（原声 −56 dBFS）、forest_wind_leaves_birdsong（−54 dBFS）重建约 −38／−40 dBFS，比原声响 15–18 dB；第一阶段时这两个文件的重建比原声更安静。CPU 与 GPU 推理结果相同。可能是解码器在安静输入上加入了噪声底，需试听确认。这两个文件的 level-matched 增益有 14–19 dB，**提醒我先调低音量**。
    - forest_wind_leaves_birdsong 的延迟估计 744.5 ms 不可靠，其 `__ab.wav` 可能错位约 0.5 秒。
    - rolling_chain 17 个、slot_machine_coin_insert_mum_hen 2 个样本削波。
- 本机已装 nn~ v1.6.0，第一阶段模型（同样是 torch 2.5.0 导出）能载入并出声（见 `docs/environment-mac.md`）。最终模型由同一环境导出，**能否载入仍要实测一次**。

## 这次请做

1. **核对拷贝**：在包含 `exports/` 和 `listening/` 的数据根目录下运行
   `tr '\134' '/' < listening/exp-003/final-step1500000/SHA256SUMS.txt | tr -d '\r' | shasum -a 256 -c`
   （清单为 Windows 路径，共 88 个文件）。报告不一致或缺失的文件。
2. **陪我试听**：我会听 `level-matched` 下的 `__ab.wav`，必要时和第一阶段的同名文件对比，把听感告诉你。帮我整理成表（文件、类别、节奏/音色是否保留、闷/糊/杂音、安静段是否出现噪声、和第一阶段相比的变化、是否出现跨类特征），写进 `experiments/exp-003-mixed-insects-machine-plan.md` 新的一节“最终模型试听（2026-11-13）”，并在 `docs/log.md` 顶部记一条。只记录我的听感，不替我下结论。
3. **Max 加载测试**（我确认后再做）：
   - 把最终模型复制到 `~/Documents/Max 9/Packages/nn_tilde/models/`（复制前先告诉我，不删除第一阶段模型）。
   - 沿用 `instrument/max/exp-003/` 的 forward 和 latent 两个 patch，只换模型名；要另存为最终模型版本还是改成可切换模型，先问我。不要把模型或音频放进 Git。
   - 用 `scripts/measure_max_latency.py` 按 README 的方法测延迟。
   - 实测并记录：能否加载、CPU 占用、是否爆音、安静输入（或无输入）时的输出电平、实际延迟（说明测法和 Max 音频设置：采样率、I/O vector size、signal vector size、nn~ buffer）。不要沿用 4070 的数字。
4. 不改系统设置，不安装或升级软件，除非先问我。

注意：不承诺模型理解语义、自动形成“自然—机械”控制轴，或对任意麦克风输入产生指定声音；4 个潜在维度各自控制什么，只能靠试听和实验确认。潜在插值、距离互动等属于 Max 中的外围程序，不是模型本身的行为。
