"""在 Windows 上运行 RAVE 2.3.1 预处理的串行包装。

直接复用已安装 acids-rave 2.3.1 的 scripts/preprocess.py（音频切块、protobuf
格式、LMDB 写入、metadata.yaml 均不变），只替换两处在 Windows 上实测有问题的环节：

1. search_for_audios 同时匹配 *.wav 与 *.WAV；Windows 路径不分大小写，
   每个文件会被收录两次。这里按 os.path.normcase 去重并排序。
2. flatmap 使用 multiprocessing.Pool + Manager().Queue 并行读取音频；
   2026-11-11 在 4070 台式机上实测会出现 protobuf EncodeError（默认 upb 后端）
   或在约 18 个片段后停滞（纯 Python 后端）。这里改为主进程串行读取。

参数与 `rave preprocess` 相同，例如：

    E:\\envs\\rave-2.3.1\\Scripts\\python.exe scripts/rave_preprocess_windows.py ^
        --input_path <音频目录> --output_path <数据库目录> --channels 1 --max_db_size 5

注意：Windows 上 LMDB 会按 --max_db_size 占用磁盘，预处理完成后 data.mdb 可能仍是满额大小。请按数据量显式设置，不要使用默认的 100 GB。
不支持 --lazy（项目在 Windows 上只使用非 lazy 数据库）。
"""

import os
import pathlib
import sys

from absl import app

import scripts.preprocess as P


def _search_for_audios_dedup(path_list, extensions):
    exts = {"." + e.lower().lstrip(".") for e in extensions}
    seen = {}
    for root in map(pathlib.Path, path_list):
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                key = os.path.normcase(os.path.abspath(p))
                seen.setdefault(key, p)
    return [seen[k] for k in sorted(seen)]


def _flatmap_serial(pool, func, iterable, chunksize=None):
    for item in iterable:
        yield from func(item)


class _NoPool:
    def close(self):
        pass


def main(argv):
    if P.FLAGS.lazy:
        sys.exit("rave_preprocess_windows.py 不支持 --lazy")
    P.search_for_audios = _search_for_audios_dedup
    P.flatmap = _flatmap_serial
    P.multiprocessing.Pool = _NoPool
    return P.main(argv)


if __name__ == "__main__":
    app.run(main)
