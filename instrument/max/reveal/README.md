# reveal-sound：画面工具 → 声音（v1；2026-11-18 在 4070 上与画面联动跑通，听感未评）

接收 4070 上画面工具（[visual/reveal.py](../../../visual/README.md)）发出的 OSC，用 RAVE 潜在插值让声音与画面对应。
`reveal-sound.maxpat`（Mac，手动 open 两个源）与 `reveal-sound-4070.maxpat`（4070，自动载入源并开音频）都由 `make_reveal_sound_patch.py` 生成（后者加 `--target 4070`），改映射时改脚本再重新生成，不要手改 JSON。

## 在 4070 上一起跑画面和声音

日常启动按 [docs/guide-run-reveal.md](../../../docs/guide-run-reveal.md)。

```powershell
Start-Process "D:\MaxMsp\Max.exe" "E:\Github\nature-machine-latent\instrument\max\reveal\reveal-sound-4070.maxpat"
```

等约 2 秒（自动载入源并开音频），再在仓库根目录开画面：

```powershell
E:\envs\streamdiffusion-td\venv\Scripts\python.exe visual\reveal.py --input demo --windowed --debug
```

`--input demo` 换成 `mouse`（按住左键＝标记出现）或 `camera` 即可。`layout.json` 的 `osc.host` 保持 `127.0.0.1`。
标记出现时声音淡入，靠近中央“机械”时 a 变大，左右位置对应声像；标记消失时淡出。
检查 Max 端是否在工作（不需要看 Max 窗口）：

```powershell
E:\envs\streamdiffusion-td\venv\Scripts\python.exe instrument\max\reveal\sound_status.py --seconds 20
```

2026-11-18 实测：`a` 在 0–0.97 间随位置变，`env` 随出现／消失淡入淡出，`level` 峰值 0.005–0.38；画面帧率不受影响。

## 对应关系（人为设计，可改）

| 画面工具发出 | 声音 |
| --- | --- |
| `/reveal/mix a`（0–1，区域 a 值按距离加权：虫 0、混合体 0.5、机械 1） | 每个潜在维度 `z = z自然 + a·(z机械 − z自然)`，再 decode；50 ms 平滑 |
| `/reveal/present 0/1` | 1 → 400 ms 淡入，0 → 800 ms 淡出（与画面淡入淡出一致）；黑屏时无声 |
| `/reveal/pos x y` | x → 等功率左右声像；y 暂未使用 |
| `/reveal/seed n`（标记每移动一段换一次） | 两个源各跳到 0–8000 ms 的随机位置；`speedlim 1000` 限制最多每秒一次 |
| `/reveal/region name` | 仅显示 |

这与 [render_interpolation.py](../../../scripts/render_interpolation.py) 离线插值是同一做法（对两段的 4 维潜在轨迹线性插值）。模型不理解“自然／机械”，中间状态听起来是什么要试听判断。导出模型的 encode 是随机采样、decode 会给 4 维以外补噪声（见 [docs/log.md](../../../docs/log.md) 2026-11-17），所以同一输入每次略有不同。

## 依据

- nn~ 写法（`nn~ <模型> encode|decode 2048`，encode 4 个信号出口、decode 4 个入口）沿用 [exp-003 测试 patch](../exp-003/README.md)。
- `sfplay~` 的 `seek <毫秒>` 从指定位置开始播放；`loop` 属性开关循环（[sfplay~ 参考](https://docs.cycling74.com/reference/sfplay~/)）。
- `cos~` 输出 cos(2π·输入)（[cos~ 参考](https://docs.cycling74.com/reference/cos~/)），所以左 = cos~(x/4)、右 = cos~((1−x)/4)。
- `udpreceive` 解码 OSC 并作为 Max 消息输出（[udpreceive 参考](https://docs.cycling74.com/reference/udpreceive/)）；文档没写明 OSC 地址是否成为 `route` 可匹配的选择器；2026-11-18 在 4070（Max 9.0.8，Windows）上实测可以匹配。
- 4070 端已验证：画面工具（demo 输入）发出上述 5 种消息，每秒约 15–25 条；demo 中 seed 可达每秒 11 次（`visual/osc_monitor.py` 监听统计）。

## Mac 上的步骤

1. 模型：`exp003-forest-s105ck01-final-step1500000_streaming.ts` 放在 `~/Documents/Max 9/Packages/nn_tilde/models/`（交接包 `handoff/mac-exp003-final/` 中有，SHA-256 `c902955f…b8799c`）。
2. 打开 `reveal-sound.maxpat`，两个源各点 `open`：
   - 自然源：建议 heldout `night_forest_a__orig.wav` 或 `birdsong_d__orig.wav`；
   - 机械源：建议 `torque_wrench_turning_constant__orig.wav` 或 `rolling_chain__orig.wav`；
   （位于 `listening/exp-003/final-step1500000/level-matched/`。与 4070 上插值试听文件的配对一致，便于对照。）
3. 打开 `ezdac~`。**先不接 4070**：点 present 下的 `1 400` 淡入，拖动 `mix a` 数字框 0 → 1，听过渡；点 `0 800` 淡出。
4. 记录：Max Console 有无报错、CPU 读数（两个 encode + 一个 decode 同时运行，M1 8 GB 上未测）、有无爆音断续。
5. 接 4070：
   - 两台在同一局域网。Mac 上查 IP（系统设置 → 网络，或终端 `ipconfig getifaddr en0`）。
   - 4070 上把 `visual/layout.json` 的 `osc.host` 改成 Mac 的 IP（端口 7400 不变）。
   - Mac 首次收到时 macOS 可能询问是否允许 Max 接收网络连接，选允许。
   - 4070 上运行 `visual\reveal.py --input camera --windowed --debug --monitor`（或 `--input demo`）。
   - Mac 上 present／pos／mix／seed 的数字应跟着变；收不到时在 4070 上先用 `visual\osc_monitor.py --host 127.0.0.1` 确认本机发出。

## 待确认

- M1 上 CPU 占用与稳定性；若过高，备选：只留一个 encode（另一源预先编码成多声道文件播放）——是否可行需验证 nn~ decode 对输入信号的处理方式。
- 声音延迟（模型约 238 ms + nn~ 缓冲 + 网络）与画面延迟是否明显不同步。
- 声音审美：插值中间点是否有意义；跳位是否过于突兀（可改为交叉淡化）；y 坐标、区域、标记编号是否要用上。
