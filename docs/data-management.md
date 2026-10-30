# 素材与模型管理

## 仓库外数据目录

```text
nature-machine-latent-data/
  raw/          原始录音，保留原件
  processed/    按数据集版本保存预处理结果
  checkpoints/  按实验编号保存训练检查点
  exports/      按实验编号和训练步数保存演奏模型
  listening/    试听结果
```

此目录需单独创建并备份。GitHub 中的清单不是音频或模型备份。
两台电脑通过稳定的素材编号、相对路径和校验值识别文件，不依赖相同盘符。

## 素材清单

在 `datasets/manifests/assets.csv` 中每个文件填写一行，UTF-8 编码；包含逗号的字段使用 CSV 双引号包围。

| 字段 | 含义 |
| --- | --- |
| asset_id | 唯一编号，例如 NML-0001 |
| relative_path | 相对 raw 目录的路径 |
| recording_group | 同一原始录音或场次的分组编号 |
| category | nature 或 machine |
| sound_family | airflow、vibration、friction 等声学分类 |
| description | 声音、强度、设备、距离及环境描述 |
| source | 自录信息或来源链接 |
| license | 许可或使用授权；未知时标记 unknown |
| duration_seconds | 时长，秒 |
| sample_rate_hz | 采样率 |
| channels | 声道数 |
| sha256 | 原文件 SHA-256 校验值 |
| split | train、validation、test 或 unassigned |
| notes | 质量问题、处理需求等 |

同一 recording_group 及其衍生片段应保持在同一数据划分中。
避免相邻片段或重复文件跨训练与测试集。许可未确认的素材先不纳入可发布数据集。
环境声的噪声纹理可能正是目标，不要未经试听批量降噪。

## 数据集与实验版本

每次正式实验保留所用清单快照，例如 `datasets/manifests/dataset-v001.csv`。
清单或预处理发生变化时建立新版本，并记录处理方式，不覆盖旧实验所依赖的版本。
模型命名示例：`exp-001-step-200000`。记录存储位置与校验值，不使用含糊的 final2 命名。
仅在确认恢复能力和备份后，按明确的保留策略清理旧检查点。
