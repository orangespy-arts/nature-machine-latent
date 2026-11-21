# 概念草案：摄像头定位揭示的 AI 画面

记录日期：2026-11-17。状态：路线已由用户选定（实时生成，4070），尚未测试；画面风格、标记方式、投影形态未定。

## 用户想要的效果

- 画面按固定布局分区：四角为“虫”，中央为“机械”，两者之间为四个“机械和虫的混合体”（用户草图）。
- 平时黑屏。摄像头捕捉一个定位标记（例如一个圆），标记在哪里，哪里才出现画面。
- 每一次移动看到的画面都不一样。

## 路线比较与决定

| 路线 | 是否实时 AI | 本地可行性 | 许可 |
| --- | --- | --- | --- |
| 1 预生成大量变体，随机抽取 | 否 | Mac 即可 | 取决于出图模型 |
| 2 按位置连续混合预生成图 | 否 | Mac 即可 | 同上 |
| 3 自训练 StyleGAN 潜在游走 | 是 | 训练需 ≥12 GB 显存，4070 处于下限，待测 | NVIDIA Source Code License，仅限非商业 |
| 4 StreamDiffusion + SD-Turbo 实时 img2img | 是 | 4070 笔记本约 24 fps @512²（TouchDiffusion 表），4070 台式机待测 | 代码 Apache-2.0；SD-Turbo 商用按 Stability AI 条款 |
| FluxRT、Daydream Scope 视频模型、Self-Forcing | 是 | 需 ≥20–32 GB 显存，本地不可行 | 多为非商业或待查 |

**2026-11-17 用户选定路线 4**：在 4070 上用 StreamDiffusion 实时生成。演出时 4070 需作为画面主机；最终演出设备仍未定。

2026-11-17 用户决定不使用 TouchDesigner，自制工具：见 [visual/](../visual/README.md)（v0 已可运行）。

## 拟定结构（待验证）

```
摄像头 → 标记位置 (x, y)
   ├─ 画面（4070）：位置所在区域的底图 / 提示词 → StreamDiffusion img2img（每次移动换种子或加噪）
   │                → 以位置为中心的柔边遮罩，其余黑屏；检测不到标记时渐隐
   └─ 声音（Mac）：到中心的距离 → 自然↔机械比例 a → nn~ 潜在插值（见 scripts/render_interpolation.py）
```

- 标记识别：按颜色／亮度识别比按形状稳定。摄像头若看着投影面，投影光会改变标记颜色；可让摄像头看不受投影照射的区域，或用红外 LED＋红外滤光片。待定。
- 位置与“虫／机械”的对应是人为设计的映射，RAVE 和 StreamDiffusion 都不理解“虫”“机械”的语义。
- 同一输入、同一种子输出相同；“每次不同”靠改变种子、噪声或输入实现。扩散模型逐帧生成易闪烁；daydreamlive 分支提供 StreamV2V 时间一致性和种子混合，可缓解，效果待测。

## 4070 上的最小验证

1. 新建独立环境（不动 `E:\envs\rave-2.3.1\`），安装 StreamDiffusion 与 SD-Turbo。
   - 本机驱动 546.33 最高支持 CUDA 12.3：原版 StreamDiffusion 的 torch 2.1.0+cu121 可用；daydreamlive 分支建议的 torch 2.8.0+cu128 需先升级驱动，或改用 torch 2.7.1+cu118。
2. 512×512、1 步 img2img，测：无 TensorRT／有 TensorRT 的帧率、显存、首帧延迟。
3. 用“虫”“机械”“混合体”提示词各出一批，看风格与闪烁是否可接受。
4. 接一个摄像头位置输入，测“标记移动 → 画面出现”的端到端延迟。

## 资料依据

- [StreamDiffusion](https://github.com/cumulo-autumn/StreamDiffusion)：RTX 4090 上 SD-Turbo 1 步 img2img 约 94 fps；安装用 Python 3.10、torch 2.1.0（cu118／cu121）。
- [daydreamlive/StreamDiffusion](https://github.com/daydreamlive/StreamDiffusion)：在原版基础上增加 SDXL、ControlNet、IP-Adapter、StreamV2V、种子混合；torch 2.7.1（cu118）或 2.8.0（cu128／cu129）；Apache-2.0；Windows 上 TensorRT 与 demo 未见说明。
- [TouchDiffusion](https://github.com/olegchomp/TouchDiffusion)：4070 Laptop 约 24 fps（sd-turbo，512×512，batch 1）。
- [SD-Turbo](https://huggingface.co/stabilityai/sd-turbo)：原生 512×512；商用参照 Stability AI 许可。
- [StyleGAN3 许可](https://github.com/NVlabs/stylegan3/blob/main/LICENSE.txt)、[FluxRT](https://github.com/tensorforger/FluxRT)、[Daydream Scope](https://github.com/daydreamlive/scope)、[Self-Forcing](https://github.com/guandeh17/Self-Forcing)：用于排除或备选，见上表。
- 定位：[cv.jit](https://cycling74.com/packages/cvjit)（Max，支持 Apple Silicon）、[TouchDesigner Blob Track TOP](https://docs.derivative.ca/Blob_Track_TOP)。
