# 启动指南：声画联动（5070 笔记本）

画面（StreamDiffusion）和声音（Max 9 ＋ nn~）都在 5070 笔记本上运行，两者通过本机 OSC（127.0.0.1:7400）连接。
标记出现的地方才有画面，同时声音淡入；标记消失，画面和声音一起淡出。
4070 台式机的版本见 [guide-run-reveal.md](guide-run-reveal.md)，两台的路径和 Python 环境不同。

本机位置（2026-11-21）：

| 用途 | 路径 |
| --- | --- |
| 项目仓库（画面程序） | `D:\Github\nature-machine-latent` |
| 画面 Python 环境 | `C:\AI\sdtest\Scripts\python.exe` |
| 声音 patch、模型、源 WAV | `D:\nature-machine-latent-5070-reveal\max\` |
| Max | `C:\Program Files\Max 9\Max.exe`（9.0.8） |
| nn~ 与模型 | `C:\Users\wangz\Documents\Max 9\Packages\nn_tilde\`（v1.6.0，`models\` 里有 exp-003 最终模型） |

详细环境见 [environment-5070.md](environment-5070.md)。

## 0. 开始前

- 笔记本**插上电源**（用电池时 GPU、CPU 都会降频）。
- 打开前先 `git pull`，拿到最新的画面程序：

```powershell
cd D:\Github\nature-machine-latent; git pull
```

## 1. 打开声音（Max）

```powershell
Start-Process "C:\Program Files\Max 9\Max.exe" "D:\nature-machine-latent-5070-reveal\max\reveal-sound-5070.maxpat"
```

- 等约 2 秒：patch 会自动载入两个声音源（自然：night_forest_a，机械：torque_wrench），并打开音频。
- 这时**没有声音是正常的**：要等画面里出现标记才会出声。
- patch 只写了文件名，所以 `max\` 文件夹里的 patch 和 WAV 必须放在一起，不要单独移动 patch。

## 2. 打开画面

在 PowerShell 里运行（第一次加载模型要 1–2 分钟）。三条命令开头的环境变量都要带：
`SD_ACCELERATION=none`（这台没有 xformers）、`HF_HUB_OFFLINE=1`（模型已在本机缓存，不联网）。

**鼠标**（按住左键＝标记出现）：

```powershell
cd D:\Github\nature-machine-latent; $env:SD_ACCELERATION='none'; $env:HF_HUB_OFFLINE='1'; C:\AI\sdtest\Scripts\python.exe visual\reveal.py --windowed
```

**自动演示**（标记自己移动、出现、消失）：

```powershell
cd D:\Github\nature-machine-latent; $env:SD_ACCELERATION='none'; $env:HF_HUB_OFFLINE='1'; C:\AI\sdtest\Scripts\python.exe visual\reveal.py --input demo --windowed
```

**摄像头＋ArUco 标记**（这台**未测过**；需先校准，见 [visual/README.md](../visual/README.md)）：

```powershell
cd D:\Github\nature-machine-latent; $env:SD_ACCELERATION='none'; $env:HF_HUB_OFFLINE='1'; C:\AI\sdtest\Scripts\python.exe visual\reveal.py --input camera --windowed
```

- 去掉 `--windowed` 就是全屏；加 `--guide` 显示各区域的灰点和名字，加 `--debug` 显示左上角调试信息。
- 退出时终端会打印帧率。2026-11-21 实测（demo）：显示约 18–20 fps，生成约 10–11 fps（4070 约 27／14 fps）。

## 3. 怎么玩

- 四角是“虫”（声音偏自然），中央是“机械”（声音偏机械），两者之间是混合体。
- 中央的机械点在画面略偏左上（按 `g` 可看到灰点 `machine`），越靠近它声音越接近纯机械源。
- 左右移动时，声音也在左右声道之间移动。
- 每次按下（标记出现），声音从两个源的一个新位置开始；按住移动时声音连续播放。画面则每移动一段距离换一张。

## 4. 画面窗口里的按键

| 键 | 作用 |
| --- | --- |
| `q` 或 `Esc` | 退出 |
| `f` | 全屏／窗口切换 |
| `d` | 显示／隐藏左上角绿色调试信息 |
| `g` | 显示／隐藏区域位置的灰点和名称 |
| `m` | 对照窗（摄像头原画面＋输出画面） |
| `c` | 摄像头调试窗 |

## 5. 出问题时

**听不到声音**

1. 确认画面里标记确实出现了（鼠标模式要按住左键）。
2. patch 左下方 `ezdac~`（喇叭图标）旁的“总音量”数字（初始 0.5），可以拖大。
3. Max 菜单 **Options → Audio Status**：Output Device 选你的耳机／音箱，采样率为 44100，Audio 为 On。
4. 只想试听声音、不开画面：在 patch 里点 present 下面的 `1 400` 淡入，拖动 `mix a` 数字（0 自然 → 1 机械），点 `0 800` 淡出。
5. 检查 Max 端是否在工作（会打印 a、包络、输出电平）：

   ```powershell
   cd D:\Github\nature-machine-latent; C:\AI\sdtest\Scripts\python.exe instrument\max\reveal\sound_status.py --seconds 20
   ```

   - 显示 `(nothing received)`：Max 没开或 patch 没载入。
   - `env` 一直是 0：画面没发出 present（画面程序没开、或加了 `--no_osc`）。
   - 这里的 `cpu` 读数在这台只会在 0／1／100 之间跳，不用看。

**按住时声音卡、像在反复播一段开头**

nn~ 在 CPU 上运行，画面生成时会和它抢 CPU。画面程序已默认只用 4 个 CPU 线程（2026-11-21 修正后用户确认不卡）。如果又出现：

1. 确认用的是最新代码（`git pull`）。
2. 把 Max 调成高优先级、画面调成低优先级（只对本次运行有效，关掉程序就恢复）：

   ```powershell
   (Get-Process Max).PriorityClass = 'High'; Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'reveal\.py' } | ForEach-Object { (Get-Process -Id $_.ProcessId).PriorityClass = 'BelowNormal' }
   ```

3. 仍卡时，把线程再减少（例如 2），重新打开画面：在命令开头加 `$env:VISUAL_CPU_THREADS='2';`。

这台的 nn~ 不能改用 GPU：官方 Windows 版只带 CPU 版 libtorch。

**画面程序启动报错**

- `No module named 'utils'`：用的是旧版 `sdgen.py`。`git pull`；不要用拷贝包里 `nature-machine-latent\` 文件夹的旧副本。
- 联网或下载相关报错：确认带了 `$env:HF_HUB_OFFLINE='1'`。

## 6. 结束

画面窗口按 `q`；Max 直接关闭窗口（问是否保存时选**不保存**，patch 由脚本生成）。

## 注意

- 这台不做 RAVE 训练，只用导出的模型。
- 换声音源：在 patch 里点对应的 `open` 选别的文件（只这一次有效）。`max\` 里还有备选源 `birdsong_d__orig.wav`、`rolling_chain__orig.wav`。
- 声音映射可在 `visual/layout.json` 的 `osc` 里调：`mix_power`（越大，靠近区域中心时越接近该区域的声音）、`seed_on`（`appear` 只在按下时跳位，`move` 每次换画面都跳）。这两项 4070 与 5070 共用。
- 已验证（2026-11-21）：demo 与鼠标输入下声画联动、中央 a 可达 0.99–1.00、限制线程后按住不卡。未验证：摄像头输入、声画延迟差、长时间运行的稳定性。
