# 自然／机械配对素材 forest-s105ck01-v001：处理记录

日期：2026-11-11。在 5070 笔记本上完成，只做素材处理，未训练。
原始音频全部保留未改动；所有输出写入新目录，音频不进入 Git。

## 结果

```text
datasets/processed/forest-s105ck01-v001/
  nature/    46 个文件，6394.88 秒（约 106.6 分钟）
  machine/  188 个文件，6392.08 秒（约 106.5 分钟）
```

两侧统一为 44.1 kHz、单声道、24-bit PCM WAV。

## 步骤一：统一森林素材格式

来源：`datasets/raw/nature/forest-v001/forest_ambience/`，46 个 WAV，共 6394.88 秒。
原格式不统一：44 个为 96 kHz／双声道，2 个（`forest_crickets_birdsong`、`forest_wind_leaves_birdsong`）为 44.1 kHz／单声道，全部为 24-bit。

**为什么选 44.1 kHz 单声道：** RAVE 官方 [`scripts/preprocess.py`](https://github.com/acids-ircam/RAVE/blob/master/scripts/preprocess.py) 默认 `--sampling_rate 44100`、`--channels 1`，与项目候选配置（v2_small、单声道）一致。

**为什么预先下混：** 同一脚本在单声道时用 ffmpeg `channelmap` 只取第 0 声道（左声道），不会混合左右声道。部分素材左右声道电平差明显，如 `birdsong_a` 左声道高约 4.7 dB，只取左声道会丢掉右侧内容，所以事先取两声道平均。

**下混前检查：** 计算每个立体声文件的左右声道相关系数。最低约 −0.03（`bird_calls_b`），即两声道基本不相关，不是反相，平均后电平约降 3 dB，不会抵消掉声音。没有文件出现明显反相。

**处理：**
1. 左右声道取平均，下混为单声道。
2. 用 soxr VHQ 重采样至 44100 Hz。
3. 写入 24-bit PCM。
4. 不做响度归一化、降噪、剪辑或去静音。

**输出：** `datasets/processed/nature/forest-v001-44k1-mono/`
**记录：** [forest-v001-44k1-mono.json](../datasets/manifests/forest-v001-44k1-mono.json)
**核对：** 46 个文件格式全部正确；每个文件时长与原件相差 < 0.0001 秒；源文件 SHA-256 与 `forest-v001.csv` 一致。

各文件原有电平差异很大（峰值约 −38 至 −1 dBFS），本次未调整，待试听后再决定是否归一化。

## 步骤二：从机械素材中选出与森林素材时长相同的部分

候选：`datasets/raw/machine/s105-v001/机械_ ck_01_03/`，237 个文件，共 7647.95 秒，比目标多约 1253 秒。

**方法（信号特征初筛，未试听）：**
1. 两组素材都下混单声道、重采样到 44.1 kHz，以 2048 点窗、1024 点跳步分帧。
2. 每个文件计算 9 项特征：
   - 活动帧比例：距文件最响帧 40 dB 以内的帧所占比例，衡量声音是否连续
   - 电平起伏：活动帧电平的 90 与 10 百分位之差
   - 起音密度：每秒谱通量峰值数
   - 谱质心（对数）：亮度
   - 谱平坦度：偏噪声还是偏音调
   - 四个频段能量占比：< 500 Hz、500–2000 Hz、2–8 kHz、> 8 kHz
3. 以两组合并的均值和标准差标准化特征。
4. 每个机械文件取与最近 3 条森林素材的平均欧氏距离作为得分。森林素材内部差异很大（雨、鸟、虫、河），所以比较最近邻，而不是和整体平均比较。
5. 按得分从低到高逐个加入整文件（不剪辑），直到总时长最接近 6394.88 秒。

**结果：** 选中 188 个文件，共 6392.08 秒，比目标少 2.8 秒；排除 49 个。

- 最接近森林素材的：棘轮、手摇葫芦自由轮、磨刀机、自行车变速与辐条、锯片颤动共振等持续转动、摩擦类声音。
- 被排除的：主要是开票机、冲压、卡扣、单次打字等短促孤立的撞击声；另有少数持续但偏低频的长文件，如 `ball_in_metal_pot_turning_sequence`、`wood_gramophone_start_stop`。

**调整过的地方：** 第一版只用森林素材的统计量做标准化。由于森林素材几乎全程有声（活动帧比例约 0.99、方差极小），排序几乎完全由“是否连续”决定。改用合并统计量后，音色特征也能起作用。两版入选文件有 147 个重合，可视为稳定核心；差异集中在边缘文件。

**记录：**
- [s105-ck01-match-forest-v001.csv](../datasets/manifests/s105-ck01-match-forest-v001.csv)：全部 237 条的排名、得分、`selected`、最近的森林素材及特征值
- [s105-ck01-match-forest-v001.json](../datasets/manifests/s105-ck01-match-forest-v001.json)：方法与统计汇总

## 步骤三：建立配对目录

- **nature/**：直接复制步骤一的 46 个输出文件（去掉 `forest_ambience` 子目录），哈希与步骤一报告逐一核对一致。
- **machine/**：将步骤二选中的 188 个原件（96 kHz、双声道、24-bit），按步骤一相同的流程转换为 44.1 kHz、单声道、24-bit。

**峰值保护：** 18 个机械文件重采样后峰值超过 0 dBFS（最高 1.138），原因是原件已接近满幅，重采样后出现样本间峰值。直接写入会削波，所以对这些文件整体衰减到峰值 0.999，衰减量 0.011–1.132 dB。衰减最多的是 `metal_ratchet_small_handling_open_close_slow`（−1.13 dB）和 `slot_machine_coin_insert_hermes_stollwerck`（−1.00 dB）。逐文件衰减量记录在 [forest-s105ck01-v001-machine.json](../datasets/manifests/forest-s105ck01-v001-machine.json) 的 `gain_applied_db` 字段。其余 170 个文件电平未变。

**核对：**
- 两侧文件数、总时长、格式正确。
- machine 文件集与选片清单 `selected=1` 完全一致。
- 机械源文件 SHA-256 与 `s105-v001.csv` 一致，原件未改动。
- 所有输出文件 SHA-256 与处理报告一致。

## 已知限制

- **选片未经试听。** 特征接近不代表听感接近；所有机械文件与森林素材的距离，都明显大于森林素材彼此之间的距离。
- **有效发声时长不对等。** 两侧文件时长相同，但机械侧停顿多，估算有声时间约 3692 秒，约为森林侧的 58%；森林侧几乎全程有声。若需要两侧有效素材量对等，应先去除静音再匹配。
- **电平未统一。** 两侧都保留原始电平（除上述峰值保护外），是否做响度归一化待试听决定。
- **来源与许可未确认。** 两批素材的授权仍为 unknown，用于可发布作品前需核实。
- **未做数据划分。** 尚未按录音分组划分训练／验证／测试集。

## 复现命令

在项目根目录运行，需要项目 `.venv`（numpy、soundfile、soxr）：

```powershell
.venv\Scripts\python -I scripts/convert_audio.py --root datasets/raw/nature/forest-v001 --output datasets/processed/nature/forest-v001-44k1-mono --report datasets/manifests/forest-v001-44k1-mono.json

.venv\Scripts\python -I scripts/select_matching_audio.py --reference datasets/processed/nature/forest-v001-44k1-mono --candidates "datasets/raw/machine/s105-v001/机械_ ck_01_03" --output datasets/manifests/s105-ck01-match-forest-v001.csv --report datasets/manifests/s105-ck01-match-forest-v001.json

.venv\Scripts\python -I scripts/convert_audio.py --root "datasets/raw/machine/s105-v001/机械_ ck_01_03" --selection datasets/manifests/s105-ck01-match-forest-v001.csv --output datasets/processed/forest-s105ck01-v001/machine --report datasets/manifests/forest-s105ck01-v001-machine.json
```

nature 目录为复制操作：把 `datasets/processed/nature/forest-v001-44k1-mono/forest_ambience/*.wav` 复制到 `datasets/processed/forest-s105ck01-v001/nature/`。

脚本拒绝覆盖已存在的输出目录或报告；重跑需换新路径。
注意：步骤一生成时，`convert_audio.py` 还没有峰值保护功能，但该批文件均未超过 0 dBFS，用当前脚本重跑结果相同。
