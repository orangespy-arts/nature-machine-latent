# 本地素材目录

音频保存在本项目的 `datasets/raw/`，由根目录 `.gitignore` 排除；Git 只管理清单与说明。这里的本地副本不是独立备份。

```text
datasets/
  raw/
    machine/
      s105-v001/           # 机械素材，保留原批次子目录
      s105-tag-backup-v2/  # 清理前的元数据备份，不进入 Git
    nature/
      forest-v001/
        forest_ambience/
          night_forest_a.wav
          dawn_birdsong_a.wav
          ...
  manifests/
    forest-v001.csv
    forest-v001-report.json
    forest-v001-renames.json
```

## 森林自然素材

- 原件：笔记本本地下载目录（第三方音效素材，具体来源见本地私有记录，不进 Git），保持不变。
- 项目副本根目录：`datasets/raw/nature/forest-v001/`。
- `manifests/forest-v001.csv` 的 `relative_path` 相对上述副本根目录，已更新为英文小写路径。
- 音频文件名仅使用英文小写及下划线，无空格；已去掉来源代码和数字。同名素材用 `_a`、`_b` 等必要后缀区分，避免覆盖。批次内部目录为 `forest_ambience`。英文名称仅翻译原文件名，不表示经过试听确认。原素材编号仍可通过映射查询。
- `forest-v001-renames.json` 保存素材 ID、原相对路径、新相对路径和校验值，用于追溯下载目录的原件。`forest-v001-report.json` 保留首次扫描时的目录信息。
- 按“自然素材／素材批次”归档。鸟鸣、虫鸣、风叶、雨声等细分类待试听后写入清单，不仅凭文件名移动分类。
- 素材共 46 个 WAV；来源、许可、录音分组和训练划分尚待确认。详见 [素材报告](../docs/materials-forest.md)。

## 机械素材

- 566 个 S105 音效已从下载目录移入 `datasets/raw/machine/s105-v001/`，下载目录不再保留这一份素材。
- `manifests/s105-v001.csv` 和试听候选清单中的 `relative_path` 均相对此新根目录；三个批次子目录保持不变。
- 已清除标准 RIFF INFO、ID3、iXML 中的艺术家／日期字段及 BEXT 原始日期；版权、其他说明及未解析的 Soundminer 专有 SMED 数据保留。这不等于删除所有来源信息。
- 清理前元数据保存在 `raw/machine/s105-tag-backup-v2/`；[清理报告](manifests/s105-tags-cleaned.json) 记录修改前后文件 SHA-256 和不变的 PCM 校验值。`s105-tag-backup/` 是首次因写入权限失败而留下的单文件备份，不是完整备份集。
- 主清单使用清理后的文件哈希；重命名映射、首次扫描报告保留历史记录，不作为当前完整文件哈希使用。


## 森林素材预处理版本 forest-v001-44k1-mono

- 输出：`datasets/processed/nature/forest-v001-44k1-mono/`（被 Git 忽略），46 个文件，共 6394.88 秒，目录结构与原件相同；原件未修改。
- 处理：各声道取平均下混为单声道 → soxr VHQ 重采样至 44100 Hz → 24-bit PCM。未做响度归一化、降噪或剪辑。（生成时脚本尚无峰值保护；本批无文件超过 0 dBFS。）
- 依据：RAVE `scripts/preprocess.py` 默认 `--sampling_rate 44100`、`--channels 1`，且单声道时仅通过 ffmpeg `channelmap` 取第 0 声道，不做下混；因此预先下混，避免只用左声道。
- 下混前检查过左右声道相关性：最低约 −0.03（`bird_calls_b`），无明显反相抵消；不相关声道平均后电平约降 3 dB。
- 记录：[forest-v001-44k1-mono.json](manifests/forest-v001-44k1-mono.json) 保存处理参数、源与输出 SHA-256、时长和峰值。

```powershell
.venv\Scripts\python -I scripts/convert_audio.py --root datasets/raw/nature/forest-v001 --output datasets/processed/nature/forest-v001-44k1-mono --report datasets/manifests/forest-v001-44k1-mono.json
```

## 机械素材时长匹配初筛 s105-ck01-match-forest-v001

- 从 `机械_ ck_01_03`（237 个文件，7647.95 秒）中选出 188 个整文件，共 6392.08 秒，与 forest-v001 总时长 6394.88 秒相差 2.8 秒。
- 方法：两组素材都下混单声道、44.1 kHz，计算活动帧比例、电平起伏、起音密度、谱质心、谱平坦度及四个频段能量占比；以两组合并的均值和标准差标准化；对每个机械文件取与最近 3 条森林素材的平均距离作为得分；按得分从低到高累加，直到最接近目标时长。
- 这是信号特征初筛，**不是试听结论**，也不代表“听起来像自然声”。所有机械文件与森林素材的距离都明显大于森林素材彼此之间的距离。
- 文件时长不等于有效发声时长：入选文件按“距最响帧 40 dB 以内”估算的活动时长约 3692 秒，森林素材则几乎全程有声。若需要相同的有效时长，应先剪掉静音再匹配。
- 改用仅以森林素材的统计量标准化（更偏重连续性）时，163 个入选文件中有 147 个与本版重合，差异集中在边缘文件。
- 清单：[s105-ck01-match-forest-v001.csv](manifests/s105-ck01-match-forest-v001.csv)（全部 237 条，含排名、得分、`selected` 字段、最近的森林素材及特征值）；汇总：[s105-ck01-match-forest-v001.json](manifests/s105-ck01-match-forest-v001.json)。原件未复制、未修改。

```powershell
.venv\Scripts\python -I scripts/select_matching_audio.py --reference datasets/processed/nature/forest-v001-44k1-mono --candidates "datasets/raw/machine/s105-v001/机械_ ck_01_03" --output datasets/manifests/s105-ck01-match-forest-v001.csv --report datasets/manifests/s105-ck01-match-forest-v001.json
```

## 自然／机械配对目录 forest-s105ck01-v001

```text
datasets/processed/forest-s105ck01-v001/   # 被 Git 忽略
  nature/    # 46 个文件，6394.88 秒：forest-v001-44k1-mono 的逐字节副本（去掉 forest_ambience 子目录）
  machine/   # 188 个文件，6392.08 秒：s105-ck01-match-forest-v001 中 selected=1 的文件
```

- 两侧统一为 44.1 kHz、单声道、24-bit PCM。machine 侧由原件经 `convert_audio.py --selection` 生成，处理方式与 nature 侧相同（声道平均下混，soxr VHQ 重采样，无归一化或剪辑）。
- 例外：18 个机械文件重采样后峰值超过 0.999，被整体衰减 0.011–1.132 dB，以免写入时削波。每个文件的衰减量见 [forest-s105ck01-v001-machine.json](manifests/forest-s105ck01-v001-machine.json) 中的 `gain_applied_db`。
- 已核对：nature 副本哈希与 [forest-v001-44k1-mono.json](manifests/forest-v001-44k1-mono.json) 一致；machine 文件集与选片清单一致，源文件哈希与 `s105-v001.csv` 一致。
- 两侧文件时长相当，但实际发声时长不对等：machine 侧估算约 3692 秒有声，nature 侧几乎全程有声。选片仅为特征初筛，未经试听。

```powershell
.venv\Scripts\python -I scripts/convert_audio.py --root "datasets/raw/machine/s105-v001/机械_ ck_01_03" --selection datasets/manifests/s105-ck01-match-forest-v001.csv --output datasets/processed/forest-s105ck01-v001/machine --report datasets/manifests/forest-s105ck01-v001-machine.json
```
