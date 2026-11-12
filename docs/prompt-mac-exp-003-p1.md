继续 Nature–Machine Latent 项目。这台是装了 Max/MSP 的 Mac，用于试听和演奏，**不进行任何训练或训练试跑**（训练全部在 RTX 4070 台式机上）。

先读仓库 https://github.com/orangespy-arts/nature-machine-latent （已有就 `git pull`，没有就问我放在哪里再 clone）：
- `AGENTS.md`（项目规则：技术判断要有资料依据，给出来源链接；区分 RAVE 本身能力、外围程序实现、需要试听或实测确认的效果）。注意其中“设备分工”只写了 4070 和 5070，还没有这台 Mac；要补写前先问我。
- `docs/log.md` 最上面 2026-11-11、2026-11-12 的几条
- `experiments/exp-003-mixed-insects-machine-plan.md`

## 现状

- exp-003：自然（forest）＋机械（S105）混合训练，RAVE 2.3.1 v2_small，单声道 44.1 kHz，训练集按块数 1:1。4070 上正在第二阶段（对抗训练），预计 2026-11-13 约 18:45 完成，届时会另行导出最终模型。
- 已导出**第一阶段模型**（step 1,000,000，尚未对抗训练），streaming：
  `exports/exp-003/exp003-forest-s105ck01-p1-step1000000_streaming.ts`
  SHA-256 `b2b4e1fa67973afd587c76576b083bdbc67e9283c1563bf3029b7d7bb26fb7a2`
  - 在 Windows 上用 torch 2.5.0 导出，导出时隐藏 GPU、按 CPU 载入权重；latent 4 维（fidelity 0.95），full latent 128；导出日志称兼容 RAVE VST。
  - 4070 上 CPU 离线渲染测得重建比原声晚约 238 ms（17 个文件一致）。Max 中的总延迟还要加上音频与 nn~ 缓冲，须在本机实测。
  - 第一阶段模型通常偏闷、细节少，音质结论要等最终模型复核；第二阶段只改解码器（编码器冻结），潜在结构不变。
- 已生成试听文件（17 个 heldout 文件，训练未使用：机械 10、自然 7），从 4070 拷贝到本机，说明见 `listening/exp-003/p1-step1000000/README.txt`：
  - `level-matched/<machine|nature>/<名称>__ab.wav`：原声最响 10 秒 → 1 秒静音 → 对齐后的重建
  - `level-matched/.../__orig.wav`、`__recon.wav`：同增益调响度的完整原声与重建
  - `raw-level/`：原电平；`summary.csv`：电平、峰值、延迟、增益
  - 数据上：机械重建电平比原声低 1–2 dB；自然中 birdsong_d、night_forest_a、stream_birdsong 低 4–6 dB；rolling_chain 有 15 个样本削波。**尚未试听**。
- 资料（来源：https://github.com/acids-ircam/nn_tilde/releases）：nn~ v1.6.0 用 torch 2.5.1 构建，Mac 版为通用二进制并已签名。与导出用的 torch 2.5.0 同属 2.5，**是否能加载仍须本机实测**。

## 这次请做

1. **核对拷贝**：在包含 `exports/` 和 `listening/` 的数据根目录下运行
   `tr '\134' '/' < listening/exp-003/p1-step1000000/SHA256SUMS.txt | tr -d '\r' | shasum -a 256 -c`
   （清单为 Windows 路径，共 88 个文件）。报告不一致或缺失的文件。
2. **陪我试听**：我会听 `level-matched` 下的 `__ab.wav`，把听感告诉你。帮我整理成表（文件、类别、节奏/音色是否保留、闷/糊/杂音、是否出现跨类特征），写进 `experiments/exp-003-mixed-insects-machine-plan.md` 新的一节“第一阶段模型试听（2026-11-12）”，并在 `docs/log.md` 顶部记一条。只记录我的听感，不替我下结论。
3. **Max 加载测试**（我确认后再做）：
   - 只读检查：macOS 版本、芯片（Apple Silicon / Intel）、Max 版本、已装 nn~ 版本（Package Manager 或 `~/Documents/Max 9/Packages/` 等位置）。
   - 若 nn~ 不是 v1.6.0 或载入被 macOS 拦截，先说明原因和处理办法（附来源），经我同意再安装、升级或改签名。
   - 帮我搭一个最小 patch：`sfplay~` 播放一个 heldout `__orig.wav` → `nn~ <模型> forward` → `dac~`；再搭 `encode` → 4 路潜在信号 → `decode` 的版本，方便观察和手动改动潜在值。patch 放进仓库合适位置（先问我），不要把模型或音频放进 Git。
   - 实测并记录：能否加载、CPU 占用、是否爆音、实际延迟（说明测法和 Max 音频设置：采样率、I/O vector size、signal vector size、nn~ buffer）。不要沿用 4070 的数字。
4. 不改系统设置，不安装或升级软件，除非先问我。

注意：不承诺模型理解语义、自动形成“自然—机械”控制轴，或对任意麦克风输入产生指定声音；4 个潜在维度各自控制什么，只能靠试听和实验确认。潜在插值、距离互动等属于 Max 中的外围程序，不是模型本身的行为。
