"""在 Windows／4070 上运行 RAVE 2.3.1 训练的包装（参数与 `rave train` 完全相同）。

唯一改动：模型进入第二阶段（对抗训练，`warmed_up=True`）后关闭 cuDNN。

原因（2026-11-11 在 4070 实测，torch 2.5.0+cu121，内置 cuDNN 9.1.0）：
- v2_small 切换到对抗训练后的第一步，判别器反向传播报
  `CUDA error: an illegal memory access was encountered`（rave/model.py:404，
  CUDA_LAUNCH_BLOCKING=1 下可稳定复现）。
- 关闭 cuDNN 后同样设置可越过切换并持续训练。
- 第一阶段保留 cuDNN：开启约 13.5 步/秒，关闭约 10.6 步/秒；第二阶段关闭后约 5.3–5.6 步/秒。

用法（RAVE 环境的 Python）：
    python scripts/rave_train_windows.py --config v2_small --db_path <db> --out_path <dir> --name <name> \
        --channels 1 --gpu 0 [其他 rave train 参数]
"""
import functools
import sys

import torch

import rave.model
from scripts.main_cli import main as rave_main

_original_training_step = rave.model.RAVE.training_step


@functools.wraps(_original_training_step)
def _training_step(self, batch, batch_idx):
    if self.warmed_up and torch.backends.cudnn.enabled:
        torch.backends.cudnn.enabled = False
        print(f"\n[rave_train_windows] 进入对抗训练阶段（global_step={self.global_step}），已关闭 cuDNN", flush=True)
    return _original_training_step(self, batch, batch_idx)


rave.model.RAVE.training_step = _training_step

if __name__ == "__main__":
    sys.argv = ["rave", "train"] + sys.argv[1:]
    rave_main()
