# 数据与训练脚本

`clear_wav_artist_year.py` 用于清除标准 WAV 艺术家／日期标签，先备份原元数据，再原位修改等长元数据块，核对 PCM 校验值不变，最后更新清单完整文件 SHA-256。支持 RIFF INFO、ID3v2.3/v2.4、iXML 和 BEXT 日期；不解析 Soundminer SMED，保留版权及其他说明。参数为 `--root`、`--manifest`、`--report`、`--backup`；报告与备份目录必须使用新路径。

`convert_audio.py` 将 WAV 下混为单声道并用 soxr 重采样（默认 44100 Hz、24-bit），输出到新目录并生成含 SHA-256 的 JSON 报告；可用 `--selection` 只处理选片 CSV 中 `selected=1` 的文件。不归一化、不剪辑；重采样后峰值超过 0.999 的文件整体衰减到 0.999，并记录 `gain_applied_db`。输出目录或报告已存在时拒绝运行。依赖 numpy、soundfile、soxr，在项目 `.venv` 中运行。

`select_matching_audio.py` 按声学特征（活动比例、电平起伏、起音密度、谱质心、谱平坦度、频段能量）计算候选文件与参考素材最近 k 条的距离，按得分累加整文件直到接近目标时长；输出全部候选的排名 CSV 和 JSON 汇总，不复制、不修改音频。结果只是信号特征初筛，不能代替试听。

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

## RAVE 预处理（Windows）

`rave_preprocess_windows.py` 在 Windows 上替代 `rave preprocess`：复用已安装 acids-rave 2.3.1 的预处理代码与数据库格式，只把并行读取改为串行，并按路径去重（官方脚本在 Windows 上会重复收录文件且并行读取报错）。参数与 `rave preprocess` 相同，必须用 RAVE 环境的 Python 运行，并显式设置 `--max_db_size`（GB；写入期间 LMDB 会预占这么多磁盘，中断时会留下满额文件）。不支持 `--lazy`。详见 [4070 环境检查](../docs/environment-4070.md)。

```powershell
$env:PATH = "E:\envs\rave-2.3.1\Scripts;$env:PATH"
python scripts/rave_preprocess_windows.py --input_path <音频目录> --output_path <数据库目录> --channels 1 --max_db_size 5
```

后续在此添加音频质量检查、训练与导出脚本。
脚本应通过参数接收本机路径，避免写死盘符；处理后的音频应输出到新目录，保留原始录音。
