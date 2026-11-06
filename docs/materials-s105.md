# S105 金属转动碰撞音效：首次清点

日期：2026-10-30。
本机素材根目录：`D:\BaiduNetdiskDownload\S105 金属转动碰撞音效`。
上述为首次扫描位置；当前素材已移入项目 `datasets/raw/machine/s105-v001/`。清单相对路径不变，当前元数据清理情况见 [目录说明](../datasets/README.md)。
清单中的路径均相对此目录。文件保留在原位置，未复制、移动、重命名、转换或删除。

更新：2026-11-06 按用户要求，在上述下载目录内将音频文件名改为英文小写、下划线连接，去掉 `MECK` 包前缀和数字／型号代码 `B3`；同名变体以 `_a`、`_b` 等区分。保留三个原子目录。完整清单与试听候选的路径已更新；原名可通过 [重命名映射](../datasets/manifests/s105-v001-renames.json) 查询。以下首次清点与试听示例保留历史名称。

## 扫描结果

| 项目 | 结果 |
| --- | --- |
| 文件数 | 566 个 WAV |
| 总大小 | 11,793,885,690 字节，约 11.79 GB / 10.98 GiB |
| 总时长 | 20,155.675 秒，约 5 小时 35 分 56 秒 |
| 规格 | 全部为 96 kHz、24-bit、双声道 PCM |
| 三个子目录文件数 | 237 / 139 / 190 |
| 字节完全相同的重复文件 | 0 组 |
| WAV / PCM 数据读取错误 | 0 |
| 随包说明或授权文件 | 本次目录扫描未发现；仅发现 WAV 文件 |

全文件计算 SHA-256，并读取 PCM 数据验证长度。
这不是听感质量评估：尚未检测削波、静音、编码不同的相似音频，也未试听或核实授权。
总时长是文件时长之和，不是筛选后的有效训练时长。

## 产物

- [完整素材清单](../datasets/manifests/s105-v001.csv)：566 条记录，编号 S105-0001 至 S105-0566。
- [机器可读报告](../datasets/manifests/s105-v001-report.json)。
- [优先试听清单](../datasets/manifests/s105-listening-queue-v001.csv)：78 条，由文件名关键词初筛。

完整清单的声音类别、声学分类和录音分组尚未填写，避免将文件名推断当作已确认信息。
许可标记为 unknown，数据划分标记为 unassigned。三个素材子目录不等于三个录音场次。
`assets.csv` 仍为总清单模板，未自动合并本批素材。

## 试听入口

候选清单匹配了 motor、fan、vent、turning、rotating、spinning、friction、scrap、wheel、gear 等文件名关键词。
它只用于安排试听顺序，不代表其他文件不适合，也不代表候选已通过质量检查。

可从以下几个声音形态不同的候选开始：

| 编号 | 文件名 | 试听关注点 |
| --- | --- | --- |
| S105-0001 | Ball in Metal Pot Turning Sequence.wav | 旋转和金属共振如何变化 |
| S105-0006 | Bicycle Gear Shift Sequence Pedaling 01.wav | 连续运动与齿轮事件的关系 |
| S105-0092 | Metal Gear Rattling Long.wav | 持续纹理、周期性和颗粒感 |
| S105-0112 | Metal Scissors Scrape Sequence Long.wav | 摩擦纹理、亮度与无关背景声 |
| S105-0219 | Torque Wrench Turning Constant.wav | 稳定运动是否有可演奏的变化 |
| S105-0241 | MECK MOVEMENT Washers Spinning on Brake Disc Resonating.wav | 衰减、共振与事件间隙 |

在试听清单中填写 review（keep / hold / exclude）及 listening_notes。
排除只改变清单，不删除原件。确认录音关系与许可后再决定数据划分。

## 下一步

- [ ] 确认原始素材包来源和使用许可。
- [ ] 试听候选，标记可用声音与片段范围。
- [ ] 检查近似重复素材和同源录音关系。
- [ ] 按实际听感汇总持续纹理与短促碰撞素材。
- [ ] 根据机械侧的听感寻找自然声配对，再决定第一版训练集范围。
