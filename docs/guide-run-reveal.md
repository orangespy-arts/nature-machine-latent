# 启动指南：声画联动（4070）

画面（StreamDiffusion）和声音（Max 9 ＋ nn~）都在 4070 台式机上运行，两者通过本机 OSC（127.0.0.1:7400）连接。
标记出现的地方才有画面，同时声音淡入；标记消失，画面和声音一起淡出。
5070 笔记本的版本见 [guide-run-reveal-5070.md](guide-run-reveal-5070.md)。

## 1. 打开声音（Max）

```powershell
Start-Process "D:\MaxMsp\Max.exe" "E:\Github\nature-machine-latent\instrument\max\reveal\reveal-sound-4070.maxpat"
```

- 等约 2 秒：patch 会自动载入两个声音源（自然：night_forest_a，机械：torque_wrench），并打开音频。
- 这时**没有声音是正常的**：要等画面里出现标记才会出声。
- Max 已经开着这个 patch 时，不用再开一次。

## 2. 打开画面

选一种输入方式，在 PowerShell 里运行（第一次加载模型要十几秒）：

**鼠标**（按住左键＝标记出现）：

```powershell
cd E:\Github\nature-machine-latent; E:\envs\streamdiffusion-td\venv\Scripts\python.exe visual\reveal.py --windowed
```

**自动演示**（标记自己移动、出现、消失）：

```powershell
cd E:\Github\nature-machine-latent; E:\envs\streamdiffusion-td\venv\Scripts\python.exe visual\reveal.py --input demo --windowed
```

**摄像头＋ArUco 标记**（需先校准，见 [visual/README.md](../visual/README.md)）：

```powershell
cd E:\Github\nature-machine-latent; E:\envs\streamdiffusion-td\venv\Scripts\python.exe visual\reveal.py --input camera --windowed
```

去掉 `--windowed` 就是全屏。

## 3. 怎么玩

- 四角是“虫”（声音偏自然），中央是“机械”（声音偏机械），两者之间是混合体。
- 左右移动时，声音也在左右声道之间移动。
- 每次移动一段距离，画面换一张，声音源也跳到别的位置（最多每秒一次）。

## 4. 画面窗口里的按键

| 键 | 作用 |
| --- | --- |
| `q` 或 `Esc` | 退出 |
| `f` | 全屏／窗口切换 |
| `d` | 显示／隐藏左上角绿色调试信息（加 `--debug` 启动时默认显示） |
| `g` | 显示／隐藏区域位置的灰点和名称（加 `--guide` 启动时默认显示） |
| `m` | 对照窗（摄像头原画面＋输出画面） |
| `c` | 摄像头调试窗 |

## 5. 听不到声音时

1. 确认画面里标记确实出现了（鼠标模式要按住左键）。
2. patch 左下方 `ezdac~`（喇叭图标）旁的“总音量”数字（初始 0.5），可以拖大。
3. Max 菜单 **Options → Audio Status**：Output Device 选你的耳机／音箱，采样率为 44100，Audio 为 On。
4. 只想试听声音、不开画面：在 patch 里点 present 下面的 `1 400` 淡入，拖动 `mix a` 数字（0 自然 → 1 机械），点 `0 800` 淡出。
5. 检查 Max 端是否在工作（会打印 a、包络、输出电平、CPU）：

   ```powershell
   cd E:\Github\nature-machine-latent; E:\envs\streamdiffusion-td\venv\Scripts\python.exe instrument\max\reveal\sound_status.py --seconds 20
   ```

   - 显示 `(nothing received)`：Max 没开或 patch 没载入。
   - `env` 一直是 0：画面没发出 present（看画面程序是否开着、`visual/layout.json` 的 `osc.host` 是否为 `127.0.0.1`）。

## 6. 结束

画面窗口按 `q`；Max 直接关闭窗口（问是否保存时选不保存，patch 由脚本生成）。

## 注意

- StreamDiffusion 用 GPU，训练也用 GPU：**不要和 RAVE 训练同时跑**。
- 换声音源：在 patch 里点对应的 `open` 选别的文件（只这一次有效）；要长期改，改 `instrument/max/reveal/make_reveal_sound_patch.py` 里的 `AUTOLOAD` 再重新生成，见 [instrument/max/reveal/README.md](../instrument/max/reveal/README.md)。
- 已验证：鼠标／演示输入下声画联动正常（2026-11-18）。未验证：听感、爆音、声画延迟差、摄像头输入下的完整联动。
