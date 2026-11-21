"""StreamDiffusion img2img 生成核心：按区域权重混合提示词与底图，可随时换种子。

依赖 E:\\envs\\streamdiffusion-td（dotsimulate/StreamDiffusion 的 utils/wrapper.py 与 venv 中的 streamdiffusion 包）。
做法依据该版本源码（streamdiffusion/pipeline.py）：
- prepare() 用 generator+seed 生成 init_noise；img2img 时 add_noise(img_latent, init_noise[0], 0)。
  换种子 = 重新生成 init_noise。
- prompt_embeds 由 pipe.encode_prompt 得到；提示词混合 = 对各区域的 embedding 加权平均（外围做法，效果需看图）。
- t_index 越小加噪越多、越偏离底图（50 步调度中的索引）。
"""
import os
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

torch.set_num_threads(int(os.environ.get('VISUAL_CPU_THREADS', '4')))  # 见 reveal.py 顶部说明

SD_ROOT = Path(os.environ.get('STREAMDIFFUSION_ROOT', r'E:\envs\streamdiffusion-td'))
sys.path.insert(0, str(SD_ROOT))


def region_weights(regions, x, y, power=2.0, aspect=16 / 9):
    """反距离权重；x 方向按画布宽高比放大，使距离对应真实像素距离。"""
    d = np.array([np.hypot((x - r['x']) * aspect, y - r['y']) for r in regions])
    if d.min() < 1e-6:
        w = (d < 1e-6).astype(float)
    else:
        w = 1.0 / d ** power
    return w / w.sum()


def placeholder_base(region, index, size=512):
    """没有底图时的占位：黑底上的几团随机色块，给 img2img 一点结构。"""
    rng = np.random.default_rng(1000 + index)
    palette = {'insect': (90, 110, 50), 'hybrid': (150, 110, 50), 'machine': (120, 120, 130)}
    base = np.array(palette.get(region.get('kind'), (100, 100, 100)), float)
    yy, xx = np.mgrid[0:size, 0:size] / size
    img = np.zeros((size, size, 3))
    for _ in range(6):
        cx, cy = rng.uniform(0.3, 0.7, 2)
        sx, sy = rng.uniform(0.05, 0.18, 2)
        blob = np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))
        img += blob[..., None] * (base * rng.uniform(0.6, 1.4, 3))
    return np.clip(img, 0, 255).astype(np.uint8)


def load_base(region, index, root, size=512):
    p = region.get('base')
    if p:
        path = Path(p) if Path(p).is_absolute() else Path(root) / p
        return np.asarray(Image.open(path).convert('RGB').resize((size, size), Image.LANCZOS))
    return placeholder_base(region, index, size)


class CoreWrapper:
    """没有 utils/wrapper.py 时（如 5070 上 pip 装的 streamdiffusion 0.1.1）的替代。

    只实现 Generator 用到的部分：.stream、prepare()、__call__(image) -> PIL。
    构建方式照 StreamDiffusionWrapper：StableDiffusionPipeline → StreamDiffusion(cfg_type) → taesd → prepare → 预热。
    """

    def __init__(self, model_id_or_path, t_index_list, acceleration='none', vae_id='madebyollin/taesd',
                 cfg_type='none', width=512, height=512, warmup=10, seed=0, device='cuda', **_):
        from diffusers import AutoencoderTiny, StableDiffusionPipeline
        from streamdiffusion import StreamDiffusion

        try:
            pipe = StableDiffusionPipeline.from_pretrained(model_id_or_path, torch_dtype=torch.float16, variant='fp16')
        except (OSError, ValueError):
            pipe = StableDiffusionPipeline.from_pretrained(model_id_or_path, torch_dtype=torch.float16)
        pipe = pipe.to(device=device, dtype=torch.float16)
        if acceleration == 'xformers':
            pipe.enable_xformers_memory_efficient_attention()
        elif acceleration not in ('none', None, ''):
            raise ValueError(f'CoreWrapper 不支持 acceleration={acceleration!r}（只支持 none／xformers）')
        self.stream = StreamDiffusion(pipe, t_index_list=t_index_list, torch_dtype=torch.float16,
                                      width=width, height=height, cfg_type=cfg_type)
        self.stream.vae = AutoencoderTiny.from_pretrained(vae_id).to(device=pipe.device, dtype=pipe.dtype)
        self.warmup, self.seed = warmup, seed

    def prepare(self, prompt, num_inference_steps=50, guidance_scale=1.0, negative_prompt='', delta=1.0):
        self.stream.prepare(prompt=prompt, negative_prompt=negative_prompt, num_inference_steps=num_inference_steps,
                            guidance_scale=guidance_scale, delta=delta, generator=torch.Generator(), seed=self.seed)

    def __call__(self, image):
        from streamdiffusion.image_utils import postprocess_image
        return postprocess_image(self.stream(image), output_type='pil')[0]


def _make_wrapper(**kw):
    try:
        from utils.wrapper import StreamDiffusionWrapper  # noqa: E402
        return StreamDiffusionWrapper(**kw)
    except ModuleNotFoundError as e:
        if e.name not in ('utils', 'utils.wrapper'):
            raise
        print('utils/wrapper.py not found; using installed streamdiffusion core (CoreWrapper)')
        return CoreWrapper(**kw)


class Generator:
    def __init__(self, layout, root, device='cuda'):
        g = layout['generation']
        self.size = g['size']
        self.regions = layout['regions']
        self.power = g['blend_power']
        self.aspect = layout['canvas']['width'] / layout['canvas']['height']
        self.w = _make_wrapper(
            model_id_or_path=g['model'], t_index_list=[g['t_index']], mode='img2img',
            acceleration=os.environ.get('SD_ACCELERATION', g.get('acceleration', 'xformers')), use_lcm_lora=False, use_tiny_vae=True, vae_id='madebyollin/taesd',
            cfg_type='none', width=self.size, height=self.size, warmup=10, seed=0, device=device,
        )
        style = layout.get('style', '')
        self.prompts = [f"{r['prompt']}, {style}" if style else r['prompt'] for r in self.regions]
        self.w.prepare(prompt=self.prompts[0], num_inference_steps=g['num_inference_steps'], guidance_scale=1.0)
        s = self.w.stream
        if isinstance(self.w, CoreWrapper):  # 原 wrapper 在构造时预热；这里 prepare 后再预热
            warm = Image.fromarray(np.zeros((self.size, self.size, 3), np.uint8))
            for _ in range(self.w.warmup):
                self.w(warm)
        with torch.no_grad():
            self.embeds = torch.stack([
                s.pipe.encode_prompt(prompt=p, device=s.device, num_images_per_prompt=1,
                                     do_classifier_free_guidance=False)[0][0]
                for p in self.prompts])  # (R, 77, D)
        self.bases = np.stack([load_base(r, i, root, self.size) for i, r in enumerate(self.regions)]).astype(np.float32)
        self.seed = 0

    def reseed(self, seed):
        s = self.w.stream
        gen = torch.Generator().manual_seed(int(seed))
        s.init_noise = torch.randn(s.init_noise.shape, generator=gen).to(device=s.device, dtype=s.dtype)
        self.seed = int(seed)

    def weights(self, x, y, power=None):
        return region_weights(self.regions, x, y, self.power if power is None else power, self.aspect)

    @torch.no_grad()
    def generate(self, weights):
        s = self.w.stream
        wt = torch.tensor(weights, device=s.device, dtype=self.embeds.dtype)
        emb = (wt[:, None, None] * self.embeds).sum(0, keepdim=True)
        s.prompt_embeds = emb.repeat(s.batch_size, 1, 1)
        base = np.tensordot(weights, self.bases, axes=1).clip(0, 255).astype(np.uint8)
        out = self.w(image=Image.fromarray(base))
        return np.asarray(out.convert('RGB'))
