# visual：定位揭示的实时 AI 画面（v0）

黑屏上只在标记所在处实时生成画面；位置决定用哪个区域（虫／混合体／机械）的提示词与底图，每次移动换种子，画面不同。
概念与路线依据见 [docs/concept-visual-reveal.md](../docs/concept-visual-reveal.md)。不依赖 TouchDesigner。
声画一起启动：见 [docs/guide-run-reveal.md](../docs/guide-run-reveal.md)。

在 4070 上用 `E:\envs\streamdiffusion-td\venv`（StreamDiffusion、OpenCV、python-osc 均已在内），模型在 `E:\hf-cache`（`HF_HOME`）。

其他机器：环境变量 `STREAMDIFFUSION_ROOT` 指向含 `utils\wrapper.py` 的 StreamDiffusion 目录（默认 `E:\envs\streamdiffusion-td`）；`SD_ACCELERATION`（或 `layout.json` 的 `generation.acceleration`）可设 `xformers`（默认）／`none`／`tensorrt`。RTX 50 系列（sm_120）上 xformers 可能不支持，可改 `none`。找不到 `utils\wrapper.py` 时（如 5070 上 pip 装的 streamdiffusion 0.1.1）自动改用 `sdgen.CoreWrapper`。`VISUAL_CPU_THREADS`（默认 4）限制 OpenMP／torch／OpenCV 的 CPU 线程，避免与 Max nn~（CPU 推理）抢 CPU。

```powershell
$py = "E:\envs\streamdiffusion-td\venv\Scripts\python.exe"
& $py visual\reveal.py --windowed            # 鼠标：按住左键 = 标记存在
& $py visual\reveal.py --input demo          # 自动演示：标记沿曲线移动、出现／消失
& $py visual\reveal.py --list_cameras        # 列出摄像头
& $py visual\reveal.py --calibrate           # 摄像头中依次点投影区域四角（左上、右上、右下、左下）
& $py visual\reveal.py --input camera        # 摄像头追踪
& $py visual\sweep_strength.py --out <目录>   # 对照图：区域 × 加噪强度 × 种子
& $py visual\make_markers.py                 # 生成可打印的 ArUco 标记（visual/markers/）
```

按键：`q`／`Esc` 退出，`f` 全屏，`d` 调试信息（帧率、区域、机械比例、种子；`--debug` 启动时默认开），`g` 显示区域位置（`--guide` 启动时默认开），`m` 对照窗，`c` 摄像头调试窗（画面＋颜色掩膜）。

## 标记：ArUco（默认）

`layout.json` 中 `camera.mode` 默认为 `aruco`：识别黑白方块图案（OpenCV 4.11 自带 `cv2.aruco`，字典 DICT_4X4_50），只看明暗对比，不受光线颜色和白平衡影响，并能分辨标记编号（可用于“叶子卡／齿轮卡”等不同物件；当前程序只取画面中最大的一个标记的位置，编号显示在对照窗中，尚未用于生成）。

- 打印 `visual/markers/aruco_4x4_all.pdf`：第 1 页 4 个小标记（约 6.8 cm），之后每页一个大标记（约 15 cm）。**按实际大小／100% 打印，不要剪掉白边**；拿的时候手指捏白边，不要遮住黑框。
- 哑光纸比亮面纸好（反光会让局部发白）。
- `camera.aruco.ids`：只认指定编号，默认 `[0, 1, 2, 3]`（与打印的一致），`null` 为任意编号。`camera.aruco.params`：传给 OpenCV `DetectorParameters` 的参数，默认 `polygonalApproxAccuracyRate: 0.06`。
- 离线合成测试（2026-11-17，真实摄像头背景上贴标记，4 个旋转角度）：正常、亮度 ×0.35 加噪、×0.15 加噪、过曝 ×1.8、发灰、暖色／蓝色偏色、70% 不均匀光照、模糊 σ2／σ4、标记边长 25–120 px，全部识别。合成图没有真实的反光、遮挡和压缩噪声，**结论偏乐观，需实物实测**。每帧检测约 3.5 ms（1280×720）。

## 手电光斑（`--input light`，2026-11-23）

摄像头对着黑色幕布，用手电照幕布，光斑的位置代替标记；之后的画面、声音、OSC 与其他输入**完全相同**（同一 `layout.json` 区域、提示词、贴图大小，光斑大小不影响画面）。改动前的版本存为 Git 标签 `reveal-v0-mouse`。

- 识别（`tracker.detect_light`）：取亮度（各通道最大值，偏黄／偏蓝的手电也算）→ 模糊 → 背景 = 亮度中位数 → 阈值 `max(min_v, 背景+min_contrast, 背景+(峰值−背景)×rel)` → 最大的实心亮块 → 质心。光线强弱未定，所以阈值随画面自适应，不用点选。
- 参数在 `layout.json` 的 `camera.light`：`min_contrast`（光斑比背景至少亮多少，0–255，默认 40；手电很弱时调小）、`rel`、`min_area_frac`（光斑最小面积占画面比例）、`min_fill`（亮像素占比，排除空心图形和细线）、`exposure`（`null` 自动曝光；数值为手动曝光，DirectShow 下 log2 秒，如 `-6`，是否生效取决于摄像头驱动，未测）。
- 离线合成测试（2026-11-23，1280×720，光斑中心饱和、边缘渐暗、带杂散光圈）：背景 15／光斑 255、弱手电 20／80、自动曝光把背景拉到 70、小光斑半径 30 px、暖色手电、噪声 σ20、横向不均匀照明 +60、柔边、真实摄像头帧压暗作背景，各 8 个随机位置全部识别，中心误差约 1 px；无手电时 9 种背景／噪声组合无误报；光斑旁有一条亮线时仍取光斑。光斑与背景亮度差 < 40（如 20／55）时不识别（按 `min_contrast` 设计）。每帧约 12 ms。**合成图不等于实物，需在黑幕布上实测。**
- 注意：
  - 只取画面中最大的亮块。幕布外的灯、窗户、屏幕会被当成光斑：让摄像头只拍幕布，或用 `--calibrate` 后只看校准区域（未实现过滤，校准只做坐标映射）。
  - **如果投影也打在这块幕布上**，摄像头会同时看到投影画面，生成的画面本身可能被当成光斑而自我维持。要么投到别处，要么需另行处理（例如红外手电＋带红外滤镜的摄像头），未测。
  - 摄像头被 Windows 隐私设置禁用时，画面是灰底锁形图标，图标中的实心部分可能被当成光斑。

```powershell
& $py visualeveal.py --input light --camera_test                # 只看识别：左 画面＋绿圈，右 阈值掩膜
& $py visualeveal.py --input light --windowed --debug --monitor # 完整运行
```

`--camera_index N` 可临时换摄像头（不改 `layout.json`）。5070 笔记本：index 0 是内置摄像头，index 1 是 OBS 虚拟摄像头。

## 标记：颜色（`camera.mode = "color"`）

**点选标记颜色**：在对照窗左边（或 `--camera_test` 窗口左边）的摄像头画面上点一下标记，程序取该处颜色作为识别目标，保存到 `visual/local/marker.json`（本机，不进 Git），下次启动自动读取。光线或标记变了就再点一次。实测：同一红色纸盒在不同光线下 HSV 从（H 1–3，S≈235）变为（H 3–6，S≈130），后者与皮肤几乎相同——**红色标记容易与手混淆，建议改用绿色或蓝色标记**。

对照窗（`--monitor` 或 `m`）：左边是摄像头原画面（绿圈 = 识别到的标记），右边是输出画面（黄十字 = 映射后的位置），便于检查两者是否对应。`--snapshot_dir` 存的截图也是这张对照图。

常用的测试命令：

```powershell
& $py visual\reveal.py --input camera --windowed --debug --monitor
```

## 文件

| 文件 | 作用 |
| --- | --- |
| `layout.json` | 画布尺寸、9 个区域（位置按 2026-11-17 草图量取、提示词、底图、机械比例 a）、生成／显示／摄像头／OSC 参数 |
| `reveal.py` | 主程序：输入 → 区域权重 → 生成线程 → 黑色画布上贴柔边圆形画面 → 全屏；发 OSC |
| `sdgen.py` | StreamDiffusion 封装：按权重混合提示词 embedding 与底图，换种子 |
| `tracker.py` | 鼠标／演示／摄像头输入，ArUco 或 HSV 颜色追踪，4 点透视校准，点选颜色 |
| `make_markers.py`／`markers/` | 生成并存放可打印的 ArUco 标记（PNG 300 dpi 与 PDF） |
| `sweep_strength.py` | 出对照图挑参数 |
| `local/` | 本机校准等（不进 Git） |

## 关键参数（`layout.json`）

- `generation.t_index`：越小加噪越多、越偏离底图。2026-11-17 对照（占位色块底图）：0–5 主体清楚，15–20 基本是模糊色团；默认 5。
- `display.patch_px`：每次显示的画面块边长（像素，画布 2048×1152）。2026-11-17 用户要求放大：640 → 1000，`feather`（柔边宽度）0.35 → 0.25；`style` 加入 “extreme close-up … the subject fills the whole frame”，主体在生成图中占比明显增大（对照图复核）。代价：画布合成在 CPU 上，演示模式显示帧率约 41 → 26 fps，生成帧率不变（约 13 fps）。
- `generation.reseed_distance`：标记移动超过此距离（画布高度的比例）就换种子；标记重新出现也换。`reseed_interval_s` > 0 时停留不动也定时换。
- `regions[].base`：底图路径（相对 `visual/`）；`null` 用占位色块。底图比提示词更能控制每个区域的样子。
- `camera.mode`：`aruco`（默认）或 `color`。`camera.hsv_*`：颜色模式的范围；本机点选结果在 `visual/local/marker.json` 中覆盖它。
- `osc`：发往 `host:port`，地址 `<prefix>/present`（0/1）、`/pos`（x y，0–1）、`/mix`（机械比例 a，按区域 a 值反距离加权，指数为 `osc.mix_power`，默认同 `generation.blend_power`）、`/region`（最近区域名）、`/seed`（`osc.seed_on`：`appear` 只在标记出现时发，`move` 每次画面换种子都发）。默认本机 7400；接 Mac 时改为 Mac 的 IP。

## v0 实测（2026-11-17，RTX 4070，2048×1152 窗口，demo 输入）

- 显示约 41 fps；标记可见时生成约 13 fps（75 ms/帧）。单独跑生成约 19 fps，差距来自同进程的画布合成与 Python GIL。
- 未装 TensorRT；摄像头延迟、端到端延迟未测（本机当时没接摄像头）。

## 摄像头实测（2026-11-17，CAMERA - UAC，USB VID 1B3F）

- 1280×720：默认格式约 11 fps，MJPG 约 27 fps → `camera.fourcc` 设为 MJPG。
- 使用中多次从 USB 掉线（系统中留下 12 条历史实例）；`tracker.py` 读取连续失败约 1 秒后每 2 秒重开。若掉线时 `read()` 阻塞不返回，重连不会触发——第二次测试在约 69 秒后停止出帧，原因（掉线或被拔出）未确认。
- 红色标记（红色纸盒）识别稳定。原阈值 S≥120 会把手掌和画面角落的橙红物体当成标记；按截图实测（JPEG 缩图，近似）：纸盒 H 1–3、S 5% 分位 220；手掌 S 中位 152；角落物体 H 4–7、S 约 190。阈值改为 H 0–4／175–180、S≥200、V≥90，在 33 张截图上去掉了这两类误判，纸盒各帧仍识别。
- 完整联动测试（摄像头 → 生成）：前约 60 秒标记处正常生成虫类画面，之后摄像头掉线，画面随之消失（程序与显示正常）。设备记录显示当天摄像头插在 “Generic USB Hub”（Hub #4，端口 1、4），2025 年曾直接插在主板 USB 3.0 根集线器上；Windows USB 选择性暂停为开启。优先改插主机背板端口再测。
- 环境很暗时画面接近全黑，颜色识别需要照明；暗场装置可考虑改用 LED 标记＋亮度追踪（未实现）。

## 已知限制与待做

- “混合体”提示词出图仍以昆虫为主，机械感弱，需改提示词或做底图。
- 区域之间是提示词 embedding 与底图的线性混合，是外围做法；中间状态是否好看要看图。模型不理解“虫”“机械”的含义。
- ArUco 尚未用实物在真实光线下测；若摄像头看着投影面，投影内容可能遮盖或干扰标记。
- 首次出现时偶有一帧接近底图的亮团（预热），待观察。
- ArUco 实物测试（2026-11-17，标记 ID 3 显示在手机屏幕上，5 分钟，293 张截图）：前 230 秒约 97% 识别；之后室内变亮、手机屏幕严重过曝（白光溢进黑框），识别降到约 65%。离线在截图（缩小＋JPEG，绝对值低于实时）上比较：gamma 压暗、CLAHE 反而变差；`polygonalApproxAccuracyRate` 0.03→0.06 使识别 164→185／293、后段 32→45／69，但出现 1 次其他编号误读 → 采用 0.06，并把 `ids` 限定为 [0,1,2,3] 过滤误读。**发光屏幕易过曝，正式使用建议哑光打印纸。**
- 待做：TensorRT 加速、画布合成移到 GPU、Max 端 OSC 接收 patch、真实底图。
