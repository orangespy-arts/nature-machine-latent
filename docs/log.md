# 项目日志

按日期记录重要决定、完成的工作和下一步。新记录放在最上方。
具体训练参数与试听结果另存于 `experiments/`，并从这里链接对应实验。

## 2026-11-23｜手电光斑输入（`--input light`）

- 用户要求：先保存上一版，再做新版——摄像头看黑色幕布，用手电照，光斑的位置像鼠标／标记一样触发画面，画面与最新版完全相同；光线强弱未定，但光斑是明显比周围亮的圆。
- 保存：Git 标签 `reveal-v0-mouse`（指向 `d78a29e`，本地，未推送）。
- 实现：`camera.mode = "light"`（`tracker.detect_light`），`--input light` 只把摄像头模式改为 light，其余流程不变；默认 `camera.mode` 仍为 aruco，旧命令行为不变。阈值随背景与峰值亮度自适应，取最大的实心亮块的质心；新增 `--camera_index`。
- 离线合成测试全部识别、中心误差约 1 px、无手电时无误报（详见 [visual/README.md](../visual/README.md)）。5070 上 index 0 内置摄像头返回 Windows“已禁用”占位图，index 1 是 OBS 虚拟摄像头，当时未接 USB 摄像头。
- 实物测试（同日，USB 摄像头，灰墙、开灯）：完整联动手电 → 生成画面跑通（显示 23.5／生成 10.5 fps）。摄像头 1280×720 只有 7.7 fps（不支持 MJPG）→ 光斑模式默认 640×480（29 fps）；复测 60 秒 29 张截图全部正确。开灯的灰墙上白色开关面板、被照亮的手、金属筒身曾被误识别，黑幕布暗室下未验证。内置摄像头（index 0）一直返回锁形占位图，隐私设置为允许，原因未查。
- 声画联动（同日，手电＋Max）：第一次 Max 没出声——Console 显示 `admme: unable to open wave output device`（插上 USB 摄像头后发生，原因未确认），DSP 打开后自动关闭。Max 音频驱动改为 `ad_directsound`、输出设备“扬声器 (Realtek(R) Audio)”后正常（这是 Max 本机偏好设置，会保留）。复测 90 秒：`sound_status.py` 显示 env 随光斑出现／消失在 0–1.0 间淡入淡出，a 在 0.00–0.99 间随位置变化，输出电平最高约 0.20；画面同时生成 9.4 fps。听感（是否卡顿、声画延迟）待用户确认。
- 风险（未测）：投影若打在同一块幕布上，摄像头会看到生成画面本身；环境中其他光源会被当成光斑。

## 2026-11-21｜5070 上画面工具用本机已装的 StreamDiffusion 跑通（demo，无 OSC）

- 用户决定在 5070 上用本机已装的 StreamDiffusion：`C:\AI\sdtest`（Python 3.11.9，torch 2.11.0+cu128，GPU sm_120 可用，streamdiffusion 0.1.1 pip 包，diffusers 0.24.0；无 xformers、无 python-osc），sd-turbo 与 taesd 已在 `%USERPROFILE%\.cache\huggingface` 缓存。
- 该 pip 包没有 dotsimulate 版的 `utils/wrapper.py`；`visual/sdgen.py` 新增 `CoreWrapper`，导入不到 `utils.wrapper` 时改用 `streamdiffusion.StreamDiffusion` 核心类，按原 wrapper 的方式构建（StableDiffusionPipeline fp16 → cfg_type none → taesd → prepare → 预热 10 次）。4070 上能导入 wrapper，仍走原路径。
- 启动：`SD_ACCELERATION=none`、`HF_HUB_OFFLINE=1`、`reveal.py --input demo --windowed --no_osc --debug`。模型离线载入成功，显存约 3.0 GB，用户确认窗口出现、有画面。退出时：显示帧率中位数 20.5 fps，生成 10.0 fps（97 ms/帧，标记可见时）；4070 同条件为 27／13.9 fps。
- 经用户同意，`pip install --no-deps python-osc`（1.10.3）装入 `C:\AI\sdtest`，未改动其他包。开启 OSC 再跑 demo，`osc_monitor.py --host 127.0.0.1 --seconds 150` 收到全部 5 种消息：present／pos／mix 各 2464 条（稳定后每秒约 14–26 条），region 283 条，seed 726 条（每秒最多约 10 次；Max patch 中有每秒一次的限速）。
- 开 OSC 时显示 18.3／生成 10.5 fps，与不开时相近。
- 交接包由用户用 U 盘拷来，放在 `D:\nature-machine-latent-5070-reveal\`（31 个文件 SHA256 一致）。用户装了 Max 9.0.8（`C:\Program Files\Max 9\`）；经同意下载 nn~ v1.6.0 Windows 版（SHA-256 与 4070 相同），装入 `文档\Max 9\Packages\nn_tilde\`，并把 exp-003 最终模型复制到 `models\`（哈希一致）。见 [5070 环境](environment-5070.md)。
- 声音：Max 打开 `reveal-sound-5070.maxpat` 后自动开音频，sr 44100；未出现标记时 env／level 为 0（正常）。
- 声画联动（demo 输入，`sound_status.py` 记录 120 秒）：a 在 0–0.77 变化，env 在 0–1 间淡入淡出，输出电平最高 0.42（音量 0.5，无削波），说明 nn~ 已载入模型并出声。同时画面显示 19.9／生成 11.0 fps，与只开画面时相近。Max `adstatus cpu` 读数只在 0、1、100 间跳，不能作为 CPU 占用参考。
- 未测：听感、爆音断续、声画延迟差、与 4070 画面是否一致、鼠标／摄像头输入、Max Console 是否有报错（未查看）。

## 2026-11-21｜5070 鼠标试听：声音映射与卡顿修正（影响 4070 共用的 visual 程序）

- 用户反馈 1：画面中央有齿轮，但声音不像机械。实测 `a` 最高 0.83：反距离权重（指数 2）下，机械点在 (0.433, 0.432) 而非屏幕正中，正中 a≈0.71。单独渲染 9 区域中的虫／混合体／机械各 3 个种子，画面区分正常，不是 5070 生成问题。用户决定改映射：`layout.json` 新增 `osc.mix_power: 6.0`，只用于 `/mix`，画面仍用 2。计算：正中 a 0.71 → 0.97，区域间中点仍为 0.25／0.75；实测中央 a 达 0.99–1.00、四角 0.00–0.05。
- 用户反馈 2：按住鼠标时像在反复播一段录音的开头，松开淡出时才完整。先按设计改为 `osc.seed_on: "appear"`（`/seed` 只在标记出现时发，原为画面每换种子就发，Max 端每秒最多跳一次），用户反馈仍卡。A/B 测试（画面 `--no_osc`，Max 手动淡入）：只在按住生成画面时卡。CPU 采样：生成时画面程序占约 20／24 核（Intel Core Ultra 9 275HX），Max nn~ 为 CPU 推理，被挤占。
- 修正：`reveal.py`／`sdgen.py` 在导入前把 OMP／MKL／OpenBLAS／numexpr、OpenCV、torch 线程限制为 `VISUAL_CPU_THREADS`（默认 4）。复测生成时画面程序约 4.9 核（最高 5.6），用户确认声音不再卡。本次复测时 Max 设为 High、画面设为 BelowNormal 优先级（仅本次进程，未写入程序）；不改优先级是否也不卡未单独测。
- nn~ 用 GPU：v1.6.0 源码有 `@gpu` 属性（[nn_base.h](https://github.com/acids-ircam/nn_tilde/blob/v1.6.0/src/frontend/maxmsp/shared/nn_base.h#L171)），无 CUDA 时退回 CPU（[backend.cpp](https://github.com/acids-ircam/nn_tilde/blob/v1.6.0/src/backend/backend.cpp#L474)）；官方 Windows 包只带 `torch_cpu.dll`，所以这台不能用 GPU 跑 nn~，需自行用 CUDA 12.8+ libtorch 编译，未尝试。
- 未测：限制线程后的生成帧率、4070 上新映射与 4 线程的效果、听感细节、声画延迟差。

## 2026-11-21｜整理 5070 声画联动拷贝包

- 用户决定在 5070 笔记本上也运行声画联动（画面＋声音，5070 上已有 CUDA 与 StreamDiffusion，之后装 Max 与 nn~）；仍不在 5070 上训练。
- `make_reveal_sound_patch.py` 新增 `--target 5070`：两个源只写文件名，WAV 与 patch 放在同一文件夹（Max 先在已打开 patch 所在文件夹找文件，[search path 文档](https://docs.cycling74.com/max8/vignettes/search_path)）。
- `visual/sdgen.py` 的加速方式改为可配置：`SD_ACCELERATION` 环境变量或 `layout.json` 的 `generation.acceleration`，默认仍为 xformers。原因：RTX 50 系列（sm_120）需 torch ≥2.7 且 CUDA ≥12.8 构建，xformers 有不支持 sm_120 的报告（[PyTorch 论坛](https://discuss.pytorch.org/t/rtx-5050-sm-120-support-timeline-when-in-stable-pytorch/224288)、[xformers 报告](https://discuss.pytorch.org/t/use-xformers-with-rtx50-series/224056)）。4070 上的 torch 2.1.0+cu118 环境不能搬到 5070。
- 拷贝包 `E:\nature-machine-latent-data\handoff\5070-reveal\`（74.5 MB，31 个文件＋SHA256SUMS）：`PROMPT-5070.md`（本机环境检查：GPU／torch／xformers／StreamDiffusion 接口／模型缓存／Max／nn~，再按顺序做声音、画面、联动测试，结果写 `RESULTS-5070.md`）、`max\`（5070 patch、模型、4 个源 WAV）、`nature-machine-latent\`（visual、instrument/max/reveal、两份文档的副本）。
- 4070 上从包内 `max\` 打开 5070 patch 测试：两个源按文件名自动载入，发 OSC 后输出电平最高 0.25，a 与包络正常。未测：5070 上的一切。

## 2026-11-18｜素材来源更正：全部为作者本人的田野录音

- 用户确认：森林（forest-v001，46 个）与机械（S105，566 个）两批素材**全部是作者本人的田野录音**，版权归作者。此前文档中的“第三方音效素材／来源待确认／许可 unknown”为错误记录。
- 已更新当前文档：README、`datasets/README.md`、`docs/materials-forest.md`、`docs/materials-s105.md`、`docs/processing-forest-s105ck01-v001.md`、`docs/concept-mechanical-insects.md`、exp-001／002／003。清单 `s105-v001.csv`（566 条）与 `forest-v001.csv`（46 条）的 source 改为 “Author's own field recording (…)”，license 改为 `author-owned`。
- 未改：本日志早先条目、首次扫描报告与重命名映射（`*-report.json`、`*-renames.json`）作为历史记录保留，其中的原文件夹名与原文件名照旧。
- 待用户自己处理：4070 `E:\nature-machine-latent-data\SOURCES.md` 与本次更正保持一致。
- 用途：本项目计划投 xCoAx 2027（截止 2027-01-31），并作为博士研究计划中声音引擎的技术基础。

## 2026-11-18｜声画联动在 4070 上跑通（Max 9 ＋ nn~ Windows）

- 用户在 4070 上装了 Max 9.0.8，决定画面与声音都在 4070 上运行（OSC 走 127.0.0.1）。经同意下载 nn~ v1.6.0 Windows 版（CPU libtorch），装入 Max 9 Packages，复制 exp-003 最终模型；见 [environment-4070.md](environment-4070.md)。
- `make_reveal_sound_patch.py` 新增 `--target 4070`，生成 `reveal-sound-4070.maxpat`：打开后自动载入两个源（night_forest_a／torque_wrench_turning_constant）、自动开音频。两版 patch 都把状态（输出峰值、a、包络、CPU、采样率）用 OSC 发到 7401；新增 `sound_status.py` 读取，不看屏幕即可检查。
- 联动实测（画面 demo 输入 75 秒、状态记录 55 秒）：`route` 能直接匹配 OSC 地址；a 随位置在 0–0.97 变化，包络随 present 淡入淡出（0.21–1.0），输出峰值 0.005–0.38（音量 0.5，无削波）；画面帧率不受影响（显示 27、生成 13.9 fps）；Max DSP CPU 读数 0 与 35–54 % 之间跳动。
- 未验证：听感（插值是否好听、跳位是否突兀）、有无爆音断续、声画延迟差、摄像头输入下的联动。

## 2026-11-17｜声音部分 v1：画面 OSC → Max 潜在插值（未在 Mac 测试）

- 新增 [instrument/max/reveal](../instrument/max/reveal/README.md)：`reveal-sound.maxpat`（由 `make_reveal_sound_patch.py` 生成）。两路源 `sfplay~` → 各自 `nn~ encode` → 每维按 OSC `/reveal/mix` a 线性插值 → `nn~ decode`；`/reveal/present` 控制淡入 400 ms／淡出 800 ms（同画面）；`/reveal/pos` x 控制等功率声像；`/reveal/seed` 使两源随机跳位（限每秒一次）。映射为人为设计。
- 4070 上验证画面工具确实发出 5 种 OSC 消息（每秒约 15–25 条；demo 中 seed 可达每秒 11 次，故加限速）；新增 `visual/osc_monitor.py`。patch 连接端口号已用脚本校验（87 个对象、86 条连线），但尚未在 Max 中打开。
- 待 Mac：`route` 能否匹配 OSC 地址、两个 encode＋一个 decode 在 M1 上的 CPU、声画延迟差、听感。

## 2026-11-17｜画面工具：标记改为 ArUco（应对展厅光线不确定）

- 实测颜色标记不可靠：同一红色纸盒在两种光线下 HSV 从（H 1–3，S≈235）变为（H 3–6，S≈130），后者与手掌几乎相同；收紧阈值会漏掉纸盒，放宽会把手当成标记。另加了点选颜色功能（`visual/local/marker.json`），并拒绝过灰的取样。
- 讨论了不依赖光线的方案（自控照明、红外 LED＋滤光、ArUco、可见 LED＋低曝光）；用户选 ArUco。本机 OpenCV 4.11 自带 `cv2.aruco`；摄像头手动曝光设置部分生效（亮度 84→60，−7 与 −10 无差别）。
- `visual/tracker.py` 新增 ArUco 模式并设为默认；`visual/make_markers.py` 生成可打印标记（`visual/markers/`，PDF＋300 dpi PNG）。合成测试（暗、过曝、偏色、不均匀光、模糊、25–120 px）全部识别，每帧约 3.5 ms；未经实物实测。
- 5 分钟完整测试中摄像头插在主机背板端口，全程未掉线（约 7–8 fps，暗光下曝光长）。
- ArUco 实物测试（手机屏幕显示 ID 3，5 分钟）：前 230 秒约 97% 识别，之后室内变亮、屏幕过曝时约 65%；离线比较后 `polygonalApproxAccuracyRate` 设为 0.06、ID 限定 0–3。最初只看了前 84 张截图（80 张识别），生成画面跟随位置正常。之后按用户要求放大画面：画面块 640 → 1000 px、柔边 0.35 → 0.25、风格词加入特写“主体充满画面”；显示帧率约 41 → 26 fps。

## 2026-11-17｜自制画面工具 v0（不用 TouchDesigner）

- 用户决定不用 TouchDesigner，做自己的工具。新增 [visual/](../visual/README.md)：Python＋OpenCV＋StreamDiffusion，用 `E:\envs\streamdiffusion-td` 环境，无新下载。
- 功能：黑屏；标记（鼠标／演示路径／摄像头颜色追踪＋4 点校准）所在处生成画面；9 个区域按草图布局，位置的反距离权重混合各区域提示词 embedding 与底图；移动超过阈值或重新出现时换种子；OSC 发送位置、机械比例 a、区域、种子供 Max 使用。
- 加噪强度对照（占位底图）：t_index 0–5 主体清楚、种子间差异明显，15–20 为模糊色团；默认 5。“混合体”出图偏昆虫，机械感弱。
- demo 输入实测：显示约 41 fps，生成约 13 fps（75 ms/帧），无 TensorRT。
- 接上 USB 摄像头（CAMERA - UAC）：MJPG 下 1280×720 约 27 fps；使用中多次掉线，已加自动重连。红色纸盒识别稳定；收紧 HSV 阈值后排除了手掌与背景橙红物体的误判（33 张截图复核）。摄像头→画面的完整联动与端到端延迟尚未测。

## 2026-11-17｜整理本机已有的 StreamDiffusionTD 到 E 盘

- 只读检查发现本机 2025-02 装过 StreamDiffusionTD（`D:\StreamDiffusion-main\`，三套 venv，其中一套可用、一套重复、一套不完整），sd-turbo 与 taesd 已缓存在 C 盘，另有 TouchDesigner 2023.11600、NDI 6、CUDA 11.8。
- 经用户同意，复制可用的一套到 `E:\envs\streamdiffusion-td\`、模型缓存到 `E:\hf-cache\`（设用户变量 `HF_HOME`），改写写死路径；离线验证通过，img2img 512×512 约 19.3 fps（无 TensorRT）。细节见 [4070 环境检查](environment-4070.md)。
- 经用户确认，永久删除原件：`D:\StreamDiffusion-main`（16.89 GB）、空的 `D:\StreamDifussionTDBase`、`C:\Users\Administrator\.cache\huggingface`（4.82 GB）。删除后重跑离线验证，结果相同（19.3 fps）。`E:\` 根目录与 `E:\Download\` 中的 `.tox` 原件未动。

## 2026-11-17｜视听装置：画面路线选定为 4070 上 StreamDiffusion 实时生成

- 用户提出视听装置：固定布局（四角“虫”、中央“机械”、之间“混合体”），平时黑屏，摄像头追踪一个标记，标记所在处才出现画面，且每次移动画面不同。
- 比较了预生成素材、按位置混合、StyleGAN、StreamDiffusion、FluxRT、Daydream Scope 等路线；FluxRT、Scope 视频模型、Self-Forcing 需 20–32 GB 显存，本地不可行。用户选定 **StreamDiffusion 实时生成，在 4070 上运行**；演出时 4070 需作为画面主机，最终演出设备仍未定。
- 记录与资料依据：[概念草案：摄像头定位揭示的 AI 画面](concept-visual-reveal.md)。尚未安装或测试；4070 台式机帧率、闪烁、端到端延迟均待测。

## 2026-11-17｜exp-003 第 12 步：生成自然↔机械插值与原声混合对照

- 修正两份日志中被 `\f` 转义吃掉的路径（`listening\exp-003\final-step1500000\`）和数据目录 `LOG.md` 中断行的 Mac 核对命令；`docs/training-steps-exp-003.md` 第 7–11 步标为完成，第 12 步进行中。
- 核对 RAVE 2.3.1 源码（`scripts/export.py` `VariationalScriptedRAVE`、`rave/blocks.py` `VariationalEncoder.reparametrize`）：导出模型的 `encode` 对后验随机采样，经 PCA 只保留前 4 维；`decode` 给其余维度补随机噪声。所以潜在插值只作用于这 4 维，结果带随机性。
- 新增 `scripts/render_interpolation.py`：两段等长留出素材先调到同一 RMS，按 a = 0／0.25／0.5／0.75／1 线性插值 z 后 decode，并输出同比例直接混合原声的对照组、0→1 sweep 和连续试听序列；`--seed` 固定后重跑逐字节相同（已验证）。
- 4070 GPU 生成三对（初选，未试听）：night_forest_a ↔ torque_wrench_turning_constant、night_forest_a ↔ ratchet_lever_snap_open_close_sequence_slow、birdsong_d ↔ rolling_chain，各 10 秒；输出 4070 `listening\exp-003\final-step1500000-interp\`（93 MB，49 项 SHA256SUMS 核对通过，含 README.txt）。
- 数据上：插值中间点的 RMS 比两端低约 2–4 dB（直接混合也有类似下降）；一对在 a=0.75／1 有 2／4 个样本削波。中间点是否构成“过渡”、是否比直接混合更有价值，**待 Mac 试听**。

## 2026-11-13｜exp-003 训练完成；导出最终模型并生成试听文件

- 18:29 到达 1,500,000 步正常结束（runner 记 exit code 0，全程 1 次运行、未重启）；第二阶段约 5.3–5.4 步/秒。
- `best.ckpt` 停在第一阶段（11-12 16:42）：第二阶段验证不再改善，不能代表最终模型。最终模型用 `epoch_1500000.ckpt`（SHA-256 `3785047F…24FB286`）导出：4070 `exports\exp-003\exp003-forest-s105ck01-final-step1500000_streaming.ts`，SHA-256 `c902955f…b8799c`；导出仍在 CPU 上进行，latent 4 维。
- `scripts/render_listening.py` 新增 `--device`；用 GPU 重建同一批 17 个 heldout 文件（14 秒），输出到 4070 `listening\exp-003\final-step1500000\`，可与 `p1-step1000000\` 逐一对比。
- 数据上（未试听）：机械与较响的自然素材重建电平比第一阶段更接近原声；但两个很安静的自然文件（forest_crickets_birdsong −56 dBFS、forest_wind_leaves_birdsong −54 dBFS）重建约 −38／−40 dBFS，比原声响 15–18 dB，而第一阶段模型对它们的重建比原声更安静。CPU 重跑结果相同，排除 GPU 推理差异。是否为解码器在安静输入上加入的噪声底，需要试听确认。
- 给 Mac 的交接说明见 [prompt-mac-exp-003-final.md](prompt-mac-exp-003-final.md)；4070 上整理了拷贝包 `handoff\mac-exp003-final\`（约 605 MB，88 个文件核对一致）。

## 2026-11-12｜落地装置去掉花盆；乐器方向改为“虫—机械耦合体＋Max 调和”

- 用户决定去掉花盆，植物和土壤湿度传感器一并去掉。[落地装置原型概念](concept-installation-prototype.md) 已更新，原内容移到第 7 节备查。Blender 草图 proto-v1、proto-v3 中的花盆未改动。
- 乐器方向（讨论中，尚未实现）：
  - 不训练新模型；
  - 观众可操作的部分是虫与机械的耦合体，包括翅膀、齿轮、腹节；
  - 在 Max 中用 `nn~ encode` 把选定素材录成潜在轨迹作为“锚点”，传感器在锚点之间调和。
- 锚点之间的中间声音是否可用尚未试听；没有花盆后，“慢速长期状态”如何实现待定。

## 2026-11-12｜第一阶段模型 4 个潜在维度初步试听（Mac）

- 用户在 latent-test patch 中逐维把偏移调到约 +40：
  - 四维都为 0：车间白噪音；
  - z1：纸片被风吹、齿轮声；
  - z2：蟋蟀叫，又像数字跳动的电子声；
  - z3：像蜂鸟；
  - z4：像水生昆虫、青蛙。
- 按 RAVE v2.3.1 源码：4 维是 PCA 后方差最大的前 4 个方向；decode 时其余 124 维填随机噪声。+40 可能远超正常编码范围，属于外推。
- 这只是单次听感，不是语义定义。详见 [exp-003 第 4a 节](../experiments/exp-003-mixed-insects-machine-plan.md)。
- 待补：
  - 音频设置；
  - 播放的文件；
  - 各维正常范围；
  - −40 方向的对照。

## 2026-11-12｜落地装置第一个原型的形态概念（5070）

- 以申请书中的乐器方案为起点，用户确定以下条件：
  - 做落地装置；第一个原型搭在一个现成钢架上，不去现场；
  - 扬声器放在外部；
  - 用 PLA 打印；
  - 用土壤湿度传感器插在花盆里。
- 当前倾向：钢架作为虫的“机械身体”，打印部件用卡扣夹在杆上，花盆作为栖地。
- 详见 [落地装置原型概念](concept-installation-prototype.md)。
- 尚未建模、打印或测试。土壤湿度的时间尺度、压电误触发、AS5600 靠近钢杆等问题待验证。
- 需要的数据：钢杆直径、钢架尺寸、打印机型号。

## 2026-11-12｜设备分工调整；Mac 上 nn~ 载入第一阶段模型

- **设备分工**（用户决定，已写入 `AGENTS.md`）：
  - 4070：训练、导出、生成试听文件。
  - Mac（M1，8 GB）：素材准备、试听、Max／nn~ 与潜在空间探索，Arduino 接在 Mac 上。
  - 5070：3D 建模、切片、连接打印机，不训练。
  - 演出设备暂不决定。
  - 相关文档已同步：README、5070 环境、素材整理流程、roadmap、exp-003 步骤表。
- **Mac 环境**：见 [Mac 环境检查](environment-mac.md)。
  - 经用户同意安装 nn~ v1.6.0：签名有效，无隔离标记，Max 9.0.9 以原生 arm64 运行。
  - 第一阶段模型（torch 2.5.0 导出）能在 nn~（torch 2.5.1 构建）中载入并出声。
  - 试听包 88 个文件的 SHA-256 全部一致。
- **新增测试工具**：[instrument/max/exp-003](../instrument/max/exp-003/README.md) 中有 forward 和 encode→4 维→decode 两个测试 patch；`scripts/measure_max_latency.py` 用于测 Max 内的延迟，用已知 238 ms 的文件验证测得 239 ms。
- **用户听感**：在 Max 中用 forward 听，机械声的重建“有虫鸣的感觉”。具体文件、对照原声和出现方式尚未记录，尚未下结论。
- **尚未测**：CPU 占用、实际延迟、`__ab.wav` 逐个试听。

## 2026-11-12｜exp-003 进入第二阶段；导出第一阶段模型

- 17:01 到达第 1,000,000 步，`rave_train_windows.py` 按预期关闭 cuDNN 进入对抗训练，未崩溃、未重启；第二阶段约 5.4 步/秒，整卡显存约 7.5 GB（第一阶段约 4 GB）。预计 11-13 约 18:45 完成。
- 应用户要求导出第一阶段模型（`epoch_1000000.ckpt`，streaming），4070 `exports\exp-003\exp003-forest-s105ck01-p1-step1000000_streaming.ts`，SHA-256 `b2b4e1fa…26fb7a2`；latent_size 4（fidelity 0.95）。两段 heldout 音频 encode/decode 运行正常，**尚未试听**。
- 新增 `scripts/render_listening.py`，用该模型重建 17 个 heldout 文件，输出到 4070 `listening\exp-003\p1-step1000000\`（原电平、统一响度、A/B 对照、summary.csv）。streaming 延迟约 238 ms（各文件一致）。尚未试听。
- 用途：提前试听重建、探索潜在空间。第二阶段冻结编码器（RAVE 2.3.1 `blocks.py` 中 `warmed_up` 后 `z.detach()`），潜在结构此后不变，但解码音质会变，结论需用最终模型复核。

## 2026-11-11｜exp-003 正式训练启动；E 核降速问题与对策

- 用户 20:27:50 用 `run_training_windows.ps1` 启动正式训练（`--max_steps 1500000`），运行目录 `checkpoints\exp-003\exp003-forest-s105ck01_d744cc98b7\`；第 10,000 步首次验证并保存检查点，未重启。
- 约 23,600 步起第一阶段从 13.7 降到约 11 步/秒：训练主线程被 Windows 10 调度到 E 核。用户手动把进程限制到 P 核（逻辑核 0–15）后回到 13.55 步/秒。
- `run_training_windows.ps1` 新增 `-AffinityMask`（默认 65535），续训子进程继承；当前运行中的续训进程也已补设。详见 [4070 环境检查](environment-4070.md) 第 6 条。
- 按 13.5 步/秒估，第一阶段约在 11-12 傍晚结束。

## 2026-11-11｜exp-003 划分定稿、预处理、测速，修复第二阶段崩溃

- 用户确认平衡口径为“模型实际听到的声音两边一样”：按 RAVE 训练块数 1:1。自然侧另留出 birdsong_e、stream_birdsong，最终训练机械 934 块、自然 936 块；划分定稿为 [forest-s105ck01-v001-split.csv](../datasets/manifests/forest-s105ck01-v001-split.csv)，生成脚本 `scripts/make_split_forest_s105ck01.py`（可逐字节复现）。
- 4070 上复制 train／heldout 并核对哈希，预处理得到 1870 条（约 3 小时 5 分钟）。
- 测速：第一阶段约 13.5 步/秒；官方 `rave train` 在进入第二阶段第一步因 cuDNN 报 CUDA illegal memory access。新增 `scripts/rave_train_windows.py`（第二阶段关闭 cuDNN，约 5.1–5.6 步/秒）和 `scripts/run_training_windows.ps1`（崩溃后自动从最新检查点续训，最多 5 次），均已验证。
- 更正：检查点只在验证时保存（每 10,000 步），不是每个 epoch；LMDB 预处理后 `data.mdb` 可能保持 `--max_db_size` 大小。
- 估时：第一阶段约 20.6 小时；第二阶段每 50 万步约 26 小时。详见 [exp-003](../experiments/exp-003-mixed-insects-machine-plan.md)。正式训练待用户确认后启动。

## 2026-11-11｜删除清单校验脚本

- 按用户要求删除 `scripts/validate_manifest.py` 及其测试 `scripts/test_validate_manifest.py`，并移除 `scripts/README.md`、`datasets/README.md` 中的用法说明。
- 此后不再有自动的清单结构、许可字段、录音分组／相同哈希跨划分检查；许可栏可保持 unknown 进入训练划分。
- 历史校验报告 `datasets/manifests/s105-validation-20261106.json` 与本日志早前记录保留不动。

## 2026-11-11｜公开文档中的素材来源改为中性描述

- 应用户要求，仓库当前文档不再写具体下载路径与商业音效包名称，改为“第三方音效素材，来源见本地私有记录”；涉及 `datasets/README.md`、`docs/materials-forest.md`、`docs/materials-s105.md`、`experiments/exp-002…`、本日志一处。
- 原有来源信息完整保存在 4070 `E:\nature-machine-latent-data\SOURCES.md`（不进 Git）。Git 历史仍含旧文字，未改写历史。
- `scripts/rename_s105.ps1` 不再写死本机路径，改为必填参数 `-Root`（该脚本已执行过，映射文件存在时拒绝重跑）。
- 两批素材许可仍未核实；改写描述不改变来源或授权状态。

## 2026-11-11｜forest-s105ck01-v001 到达 4070 并起草留出划分

- 笔记本处理好的 forest-s105ck01-v001（见 [处理记录](processing-forest-s105ck01-v001.md)）已放到 4070 `E:\nature-machine-latent-data\raw\dataset1\`；234 个文件 SHA-256 与两份处理报告全部一致。
- 起草 [留出划分草案](../datasets/manifests/forest-s105ck01-v001-split-draft.csv)：按整组留出。机械按设备／名称分 88 组（同一台机器的多个文件为一组），自然按原素材编号系列分 25 组（同标题的连号视为同一次录音）；无组跨两边。
- 草案留出：机械 6 组 10 个文件 313.5 秒（4.9%）；自然 4 组 5 个文件 466.4 秒（7.3%）。分组规则来自文件名推断，未经试听确认；待用户审阅。
- 这一套使用全部森林素材＋匹配的机械素材，不再只取虫鸣；exp-003 第 2 节待按最终划分更新。

## 2026-11-11｜这一轮改为自然＋机械混合训练

- 用户决定这一轮使用自然与机械混合素材。新建 [exp-003 混合训练计划](../experiments/exp-003-mixed-insects-machine-plan.md)；exp-002 纯机械计划保留并暂停。
- 建议：自然只取虫鸣、机械只取一个声音家族，按秒数 1:1；训练原始片段 6–7 分钟、检验 1.5–2 分钟，来自不同原始录音。比例待用户确认。
- 森林素材按文件名明确为纯虫鸣的只有 60 秒（FOREST-0010），其余虫鸣候选多混有鸟鸣，需试听截取；干净虫鸣可能不够，届时如实报告。
- 已说明边界：混合训练不会自动形成自然—机械控制轴，过渡区域需训练后插值试听确认。

## 2026-11-11｜自然／机械配对素材整理

- 森林素材 46 个统一为 44.1 kHz、单声道、24-bit：两声道取平均下混（RAVE preprocess 单声道时只取左声道，故事先下混），soxr 重采样，不归一化、不剪辑。
- 从 `机械_ ck_01_03` 中按声学特征初筛出 188 个文件，共 6392.08 秒，与森林素材 6394.88 秒对等；**未试听**。
- 建立配对目录 `datasets/processed/forest-s105ck01-v001/{nature,machine}`；18 个机械文件为防削波整体衰减 0.01–1.13 dB。
- 机械侧实际发声约 3692 秒，与森林侧有效时长不对等；电平、许可、数据划分仍待处理。
- 完整步骤、依据与复现命令：[处理记录](processing-forest-s105ck01-v001.md)。

## 2026-11-11｜4070 台式机环境检查

- 在 4070 台式机只读检查：Windows 10 专业版、i7-13700K、32 GB 内存、RTX 4070 12 GB、驱动 546.33；E: 剩余约 218 GB，C:/D: 空间紧张。
- 已有 Python 3.12（仅 CPU 版 torch）与 3.11.9；未装 RAVE、torchaudio、FFmpeg、Conda；本机尚无素材音频。
- 核对 RAVE：master 代码与 2.3.1 相同；2.3.1 固定 scipy 1.10.0，训练环境须用 Python 3.11。v2_small 官方最低 8 GB 显存，本机可作候选；v2 需 16 GB，不适合。
- 用户确认布局：数据根目录 `E:\nature-machine-latent-data\`，虚拟环境 `E:\envs\rave-2.3.1\`，均在仓库外；本机路径写入 `.env`。
- 安装 Python 3.11.9 虚拟环境：torch 2.5.0+cu121（受 nn-tilde 固定）、acids-rave 2.3.1、FFmpeg 9.0.2（仅在环境内）。依赖清单：[configs/requirements-4070-rave-2.3.1.txt](../configs/requirements-4070-rave-2.3.1.txt)。
- 用合成音频验证：预处理 → v2_small 300 步 smoke 训练 → 检查点恢复 → streaming 导出与加载，全部通过；整卡显存峰值约 3.9 GiB。
- Windows 实测问题：官方 `rave preprocess` 并行读取报错／停滞，且大小写重复收录文件 → 新增 [scripts/rave_preprocess_windows.py](../scripts/rave_preprocess_windows.py) 串行包装；LMDB 写入时按 `--max_db_size` 预占磁盘（中断会留下满额文件，正常结束后缩回实际大小）；训练须加 `--gpu 0`。详见 [4070 环境检查](environment-4070.md)。
- 在数据目录写入 `E:\nature-machine-latent-data\AGENTS.md`（目录约定、只读原始素材、本机 RAVE 用法）和 `LOG.md`（目录操作日志，记录 smoke 产物位置）；仓库 `AGENTS.md` 增加指向说明。
- 尚未传入真实素材或正式测速；phase 2 速度与显存未验证。

## 2026-11-06｜纯机械版本训练计划

- 用户选择先尝试纯机械版本，并要求训练计划。
- 建立 [exp-002 纯机械虫声训练计划](../experiments/exp-002-mechanical-insects-plan.md)：选材与声音基线 → 数据划分 → 4070 测速／恢复验证 → 重建学习与对抗微调 → 导出与距离互动。
- 第一轮不加入真实虫鸣，不训练 prior；五分钟仅作低数据量 pilot，后续视结果扩充。未启动训练，不承诺固定训练天数。

## 2026-11-06｜新概念：机械声音模拟虫声

- 用户提出用更干净的机械素材模拟虫声：观众靠近装置，听到似乎来自昆虫的声音，而声音来源实际上是机械素材。
- 记录为 [机械虫声概念草案](concept-mechanical-insects.md)，包含人工身体与自然听感的关系、素材实验、RAVE 能力边界和待决定问题。
- 尚未完成试听实验、训练或确定最终方案；距离互动与暂时弱化麦克风属于建议，尚未定案。

## 2026-11-06｜机械素材移入与标签清理

- 566 个机械音效已移入 `datasets/raw/machine/s105-v001/`；原下载目录已不存在。移动在用户补充“清理后再移入”之前已执行，随后在项目目录内完成清理。
- 清除标准 RIFF INFO、ID3、iXML 艺术家／日期标签与 BEXT 原始日期，保留版权及其他说明；专有 SMED 数据未解析或清除。
- 566 个文件逐一确认 PCM SHA-256 未变、目标标准标签无残留，更新主清单完整文件哈希；清单与 78 条试听候选关联校验通过。
- 完整元数据恢复备份：`datasets/raw/machine/s105-tag-backup-v2/`；首次权限失败留下的 `s105-tag-backup/` 仅含首文件备份。音频及备份均被 Git 忽略。
- [清理报告](../datasets/manifests/s105-tags-cleaned.json) 记录前后哈希及清除字段；历史扫描报告和原名映射保留清理前信息。

## 2026-11-06｜机械素材英文命名

- 按用户要求直接重命名本地下载目录内的 566 个 WAV：英文小写、下划线、去除包前缀和数字代码，同名变体用字母后缀区分；原子目录不变。
- 保存 `s105-v001-renames.json` 原名映射，更新完整清单与 78 条试听候选路径。
- 566 个文件 SHA-256 校验一致，清单及候选关联校验通过，未修改音频内容。

## 2026-11-06｜简化自然素材文件名

- 去除项目内自然音效文件名的来源代码与数字，保留英文声音名称；同名文件用 `_a`、`_b` 等后缀区分。
- 清单和原名映射已同步更新，46 个音频 SHA-256 校验通过，下载目录原件未变。

## 2026-11-06｜自然素材英文命名

- 按用户要求将项目内 46 个自然音效改为英文小写文件名，单词与原素材编号用下划线连接，无空格；批次子目录改为 `forest_ambience`。
- 同步更新 `forest-v001.csv` 路径，并保存 `forest-v001-renames.json` 原名映射；素材 ID 和 SHA-256 不变，46 个文件重新校验一致。
- 下载目录原件保持原名；英文名称只翻译原文件名，不代表已试听分类。

## 2026-11-06｜自然素材复制到项目目录

- 按用户要求将 46 个自然声 WAV 复制到 `datasets/raw/nature/forest-v001/`，按素材批次归档，保留原子目录及文件名，下载目录原件不变。
- 所有副本 SHA-256 与原清单一致，清单与副本路径校验通过。
- 补充 `datasets/README.md`；扩充 `.gitignore` 的音频扩展名规则并覆盖大小写，整个 `datasets/raw/` 继续排除在 Git 外。

## 2026-11-06｜登记森林自然素材

- 用户提供森林自然、林地鸟鸣素材目录；只读扫描 46 个 WAV，约 1 小时 46 分 35 秒、3.65 GB。
- 完成 SHA-256、PCM 读取检查和清单校验，未发现字节完全重复或结构读取错误；未试听或修改音频，未启动训练。
- 已保存 [素材报告与试听入口](materials-forest.md)。下一步试听筛选一个声音家族，确定五分钟实验片段。

## 2026-11-06｜新增技术讨论约束

- 用户要求：讨论技术方案前收集资料，对照真实 RAVE 模型判断可行性。
- 已写入根目录 [AGENTS.md](../AGENTS.md)：关键技术判断提供来源，区分模型能力、外围实现和待实测效果；概念设计不能作为技术验证。

## 2026-11-06｜清单校验与现状核对

- 阅读项目计划、素材管理流程和已有 S105 清点结果，继续推进 M1 素材准备。
- 新增 `scripts/validate_manifest.py`，检查清单结构、候选关联、路径安全及跨集合分组／重复哈希泄漏；不修改音频或人工标注。
- 对 566 条清单和 78 条试听候选执行校验，并核对本机原始文件存在，未发现错误。报告见 [清单校验结果](../datasets/manifests/s105-validation-20261106.json)。此次未重算哈希或检查音频质量。
- 566 条素材的录音分组、声音分类、声学分类和许可均待补充，数据划分均为 unassigned；78 条试听候选均为 pending。所有素材尚未划分，因此本次无跨集合泄漏不代表已验证同源关系。
- 修正 README 中“仅建立项目骨架”的过时描述；下一步仍为确认来源授权、试听筛选及音频质量检查，本机不启动训练。

## 2026-10-30｜项目启动与目录建立

### 补充：5070 笔记本检查

- [x] 检查当前笔记本显卡、内存、磁盘与基础工具。
- 确认 RTX 5070 Laptop GPU 为 8 GB 显存，CPU 为 Core Ultra 9 275HX，内存约 32 GB。
- 当前检查的 Python 环境未安装 PyTorch、torchaudio 或 RAVE；FFmpeg 未在 PATH 中找到。
- 用户明确本机不进行任何训练或短训练试跑；移除本机训练环境安装与 GPU 训练验证待办。
- 详细结果与待办见 [5070 环境检查](environment-5070.md)。

### 补充：开始素材整理

- 已建立 [第一批素材整理流程](material-intake.md)，采用原件保留、先登记后试听的方式。
- 已扫描 S105 金属转动碰撞音效：566 个 WAV，约 5 小时 36 分钟，11.79 GB，全部为 96 kHz / 24-bit / 双声道。
- 已生成完整清单、SHA-256 校验值与扫描报告；未发现完全重复文件或 PCM 数据读取错误。
- 已按文件名生成 78 条优先试听候选，尚未试听、确认许可或划分数据集。
- 原始文件未移动、删除或转换。详见 [S105 素材报告](materials-s105.md)。

### 创作方向

使用 RAVE 探索自然声与机械声之间的声音变化，最终用于两种场景：

- 实时演奏乐器：由演奏者控制音色、变化速度和声音活动。
- 自动声景装置：由外部控制程序组织声音的长期发展，并允许人工介入。

第一轮建议聚焦“气流与振动”：风、树叶、虫鸣、风扇、电机与管道声。
这是当前的起步方案，具体素材范围仍待试听和整理后确认。

### 设备与初始方案

- 已有设备：RTX 4070 台式机、RTX 5070 笔记本。
- 确定分工：4070 台式机承担全部训练及试跑；5070 笔记本用于素材准备、试听、项目管理、演奏和装置调试。
- 候选训练配置：RAVE `v2_small`、单声道；尚未试跑或验证环境。
- 首个演奏原型目标：四个控制参数、冻结按钮、独立音量控制、手动／自动平滑切换。
- 控制参数的语义需通过模型试听与映射建立，不能假定潜在空间自动对应“自然—机械”等轴。

### 已完成

- 建立项目 README，以及配置、脚本、素材清单、实验、乐器和装置目录。
- 编写 M1 素材准备、M2 第一个模型、M3 实时乐器、M4 自动装置四阶段计划。
- 建立素材 CSV 清单，包含来源、许可、录音分组、校验值与数据划分字段。
- 建立实验记录模板，覆盖环境版本、训练命令、检查点、试听与导出信息。
- 添加 `.gitignore`，默认排除音频、模型检查点、数据库、日志与本机配置。
- 添加 `.env.example`，说明两台电脑可使用不同的数据路径；目前没有程序自动加载该文件。

### 当前状态

项目处于准备阶段。本地 Git 已初始化，首次提交已推送到 GitHub 的 `main` 分支（用户已确认）。
远程仓库：[orangespy-arts/nature-machine-latent](https://github.com/orangespy-arts/nature-machine-latent)。
尚未安装 RAVE 或启动训练。首批素材保留在用户提供的仓库外目录，已完成只读登记。
笔记本已确认有 8 GB 显存；首批素材共 566 个，授权情况与演奏宿主软件仍待确认。

### 下一步

- [x] 初始化本地 Git，完成首次提交，连接 GitHub 仓库并推送到 `main`。
- [ ] 建立仓库外的数据目录与独立备份。
- [ ] 确认首批素材来源，填写清单并试听筛选。
- [ ] 按原始录音分组划分训练、验证与测试集。
- [ ] 在台式机准备训练环境，确认实际版本与显存需求。
- [ ] 创建 `exp-001` 实验记录，在 4070 台式机进行小规模试跑。

相关文档：[项目计划](roadmap.md) · [素材管理](data-management.md) · [实验模板](../experiments/TEMPLATE.md)
