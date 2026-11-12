{
 "patcher": {
  "fileversion": 1,
  "appversion": {
   "major": 9,
   "minor": 0,
   "revision": 9,
   "architecture": "x64",
   "modernui": 1
  },
  "classnamespace": "box",
  "rect": [
   100,
   100,
   720,
   560
  ],
  "gridsize": [
   15.0,
   15.0
  ],
  "boxes": [
   {
    "box": {
     "maxclass": "comment",
     "text": "exp-003 第一阶段模型 · forward 试听测试",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      20,
      15,
      520,
      26
     ],
     "fontsize": 16,
     "id": "obj-1"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "模型 exp003-forest-s105ck01-p1-step1000000_streaming（latent 4，streaming）；nn~ v1.6.0，缓冲 2048。\n先在 Options → Audio Status 记下采样率、I/O / Signal Vector Size，再开 DSP。",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 2,
     "patching_rect": [
      20,
      45,
      620,
      40
     ],
     "id": "obj-2"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "open",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      20,
      130,
      42,
      22
     ],
     "id": "obj-3"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "1",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      75,
      130,
      30,
      22
     ],
     "id": "obj-4"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "0",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      110,
      130,
      30,
      22
     ],
     "id": "obj-5"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "loop $1",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      145,
      130,
      63,
      22
     ],
     "id": "obj-6"
    }
   },
   {
    "box": {
     "maxclass": "toggle",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      "int"
     ],
     "parameter_enable": 0,
     "patching_rect": [
      145,
      100,
      22,
      22
     ],
     "id": "obj-7"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "open 选 __orig.wav；1 播放 / 0 停；勾选循环",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      175,
      100,
      260,
      20
     ],
     "id": "obj-8"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "sfplay~ 1",
     "numinlets": 2,
     "numoutlets": 2,
     "outlettype": [
      "signal",
      "bang"
     ],
     "patching_rect": [
      20,
      170,
      77,
      22
     ],
     "id": "obj-9"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "nn~ exp003-forest-s105ck01-p1-step1000000_streaming forward 2048",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      230,
      462,
      22
     ],
     "id": "obj-10"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "原声 → 模型 → 重建（约晚 238 ms + 缓冲，以实测为准）",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      20,
      258,
      400,
      20
     ],
     "id": "obj-11"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "selector~ 2 2",
     "numinlets": 3,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      330,
      105,
      22
     ],
     "id": "obj-12"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "1",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      20,
      295,
      30,
      22
     ],
     "id": "obj-13"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "2",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      55,
      295,
      30,
      22
     ],
     "id": "obj-14"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "0",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      90,
      295,
      30,
      22
     ],
     "id": "obj-15"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "监听：1 原声 / 2 重建（默认）/ 0 静音",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      125,
      295,
      300,
      20
     ],
     "id": "obj-16"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "*~ 0.5",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      400,
      56,
      22
     ],
     "id": "obj-17"
    }
   },
   {
    "box": {
     "maxclass": "flonum",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "bang"
     ],
     "parameter_enable": 0,
     "patching_rect": [
      80,
      370,
      60,
      22
     ],
     "id": "obj-18"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "音量（初值 0.5）",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      145,
      370,
      120,
      20
     ],
     "id": "obj-19"
    }
   },
   {
    "box": {
     "maxclass": "ezdac~",
     "numinlets": 2,
     "numoutlets": 0,
     "patching_rect": [
      20,
      440,
      45,
      45
     ],
     "id": "obj-20"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "sfrecord~ 2",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      330,
      440,
      91,
      22
     ],
     "id": "obj-21"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "open",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      330,
      400,
      42,
      22
     ],
     "id": "obj-22"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "1",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      385,
      400,
      30,
      22
     ],
     "id": "obj-23"
    }
   },
   {
    "box": {
     "maxclass": "message",
     "text": "0",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      420,
      400,
      30,
      22
     ],
     "id": "obj-24"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "录音（测延迟）：open 存为 .wav → 1 开始 → 0 停\n左声道 = 原声，右声道 = 模型输出",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 2,
     "patching_rect": [
      455,
      400,
      300,
      40
     ],
     "id": "obj-25"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "loadmess 1",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      330,
      130,
      84,
      22
     ],
     "id": "obj-26"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "metro 250",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "bang"
     ],
     "patching_rect": [
      330,
      160,
      77,
      22
     ],
     "id": "obj-27"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "adstatus cpu",
     "numinlets": 2,
     "numoutlets": 2,
     "outlettype": [
      "",
      "int"
     ],
     "patching_rect": [
      330,
      190,
      98,
      22
     ],
     "id": "obj-28"
    }
   },
   {
    "box": {
     "maxclass": "flonum",
     "numinlets": 1,
     "numoutlets": 2,
     "outlettype": [
      "",
      "bang"
     ],
     "parameter_enable": 0,
     "patching_rect": [
      330,
      220,
      60,
      22
     ],
     "id": "obj-29"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "Max DSP CPU %（每 250 ms）",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      395,
      220,
      200,
      20
     ],
     "id": "obj-30"
    }
   }
  ],
  "lines": [
   {
    "patchline": {
     "source": [
      "obj-7",
      0
     ],
     "destination": [
      "obj-6",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-3",
      0
     ],
     "destination": [
      "obj-9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-4",
      0
     ],
     "destination": [
      "obj-9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-5",
      0
     ],
     "destination": [
      "obj-9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-6",
      0
     ],
     "destination": [
      "obj-9",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-9",
      0
     ],
     "destination": [
      "obj-10",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-9",
      0
     ],
     "destination": [
      "obj-12",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      0
     ],
     "destination": [
      "obj-12",
      2
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-13",
      0
     ],
     "destination": [
      "obj-12",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-14",
      0
     ],
     "destination": [
      "obj-12",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-15",
      0
     ],
     "destination": [
      "obj-12",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-18",
      0
     ],
     "destination": [
      "obj-17",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-12",
      0
     ],
     "destination": [
      "obj-17",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-17",
      0
     ],
     "destination": [
      "obj-20",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-17",
      0
     ],
     "destination": [
      "obj-20",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-9",
      0
     ],
     "destination": [
      "obj-21",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      0
     ],
     "destination": [
      "obj-21",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-22",
      0
     ],
     "destination": [
      "obj-21",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-23",
      0
     ],
     "destination": [
      "obj-21",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-24",
      0
     ],
     "destination": [
      "obj-21",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-26",
      0
     ],
     "destination": [
      "obj-27",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-27",
      0
     ],
     "destination": [
      "obj-28",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-28",
      0
     ],
     "destination": [
      "obj-29",
      0
     ]
    }
   }
  ]
 }
}
