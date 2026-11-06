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

- 原件：`D:\BaiduNetdiskDownload\【SFX】森林自然 林地鸟鸣 长时值音效【DFSJ】`，保持不变。
- 项目副本根目录：`datasets/raw/nature/forest-v001/`。
- `manifests/forest-v001.csv` 的 `relative_path` 相对上述副本根目录，已更新为英文小写路径。
- 音频文件名仅使用英文小写及下划线，无空格；已去掉来源代码和数字。同名素材用 `_a`、`_b` 等必要后缀区分，避免覆盖。批次内部目录为 `forest_ambience`。英文名称仅翻译原文件名，不表示经过试听确认。原素材编号仍可通过映射查询。
- `forest-v001-renames.json` 保存素材 ID、原相对路径、新相对路径和校验值，用于追溯下载目录的原件。`forest-v001-report.json` 保留首次扫描时的目录信息。
- 按“自然素材／素材批次”归档。鸟鸣、虫鸣、风叶、雨声等细分类待试听后写入清单，不仅凭文件名移动分类。
- 素材共 46 个 WAV；来源、许可、录音分组和训练划分尚待确认。详见 [素材报告](../docs/materials-forest.md)。

在项目根目录校验：

```powershell
python scripts/validate_manifest.py --manifest datasets/manifests/forest-v001.csv --root datasets/raw/nature/forest-v001
```

## 机械素材

- 566 个 S105 音效已从下载目录移入 `datasets/raw/machine/s105-v001/`，下载目录不再保留这一份素材。
- `manifests/s105-v001.csv` 和试听候选清单中的 `relative_path` 均相对此新根目录；三个批次子目录保持不变。
- 已清除标准 RIFF INFO、ID3、iXML 中的艺术家／日期字段及 BEXT 原始日期；版权、其他说明及未解析的 Soundminer 专有 SMED 数据保留。这不等于删除所有来源信息。
- 清理前元数据保存在 `raw/machine/s105-tag-backup-v2/`；[清理报告](manifests/s105-tags-cleaned.json) 记录修改前后文件 SHA-256 和不变的 PCM 校验值。`s105-tag-backup/` 是首次因写入权限失败而留下的单文件备份，不是完整备份集。
- 主清单使用清理后的文件哈希；重命名映射、首次扫描报告保留历史记录，不作为当前完整文件哈希使用。

```powershell
python scripts/validate_manifest.py --manifest datasets/manifests/s105-v001.csv --queue datasets/manifests/s105-listening-queue-v001.csv --root datasets/raw/machine/s105-v001
```
