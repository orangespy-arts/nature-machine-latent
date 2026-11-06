# 数据与训练脚本

`clear_wav_artist_year.py` 用于清除标准 WAV 艺术家／日期标签，先备份原元数据，再原位修改等长元数据块，核对 PCM 校验值不变，最后更新清单完整文件 SHA-256。支持 RIFF INFO、ID3v2.3/v2.4、iXML 和 BEXT 日期；不解析 Soundminer SMED，保留版权及其他说明。参数为 `--root`、`--manifest`、`--report`、`--backup`；报告与备份目录必须使用新路径。

`inventory_audio.py` 使用 Python 标准库只读扫描 WAV，生成独立清单、SHA-256 和汇总报告，检查 PCM 数据长度。
参数：`--root` 素材根目录、`--output` 新 CSV 路径、`--report` 新 JSON 路径、`--prefix` 素材编号前缀。
已存在的输出文件会被拒绝覆盖，防止丢失人工标注。该脚本不进行训练、试听判断或音频修改。

## 清单校验

`validate_manifest.py` 使用 Python 标准库检查必需列、编号与路径重复、数值与 SHA-256 格式、录音分组／相同哈希跨集合泄漏，以及试听候选与主清单的关联。可选 `--root` 只检查文件存在与路径范围，不解码或重新计算哈希。

```powershell
python scripts/validate_manifest.py --manifest datasets/manifests/s105-v001.csv --queue datasets/manifests/s105-listening-queue-v001.csv
python -m unittest discover -s scripts -p 'test_*.py'
```

可加 `--root "本机素材根目录"` 和 `--report "新的报告.json"`。报告不覆盖已有文件；父目录需已存在。退出码：0 表示未发现结构或一致性错误，1 表示报告含错误，2 表示参数或文件读取错误。

整理阶段允许 unknown 许可和 unassigned 划分，并统计待补字段。已划分素材缺少录音分组、来源或许可时会报错。字段有值不代表内容已核实；校验通过不等于可以训练，来源占位文本、许可适用范围和同源录音关系仍需人工确认。

后续在此添加音频质量检查、预处理、训练与导出脚本。
脚本应通过参数接收本机路径，避免写死盘符；处理后的音频应输出到新目录，保留原始录音。
