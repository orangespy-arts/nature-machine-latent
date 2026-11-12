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
   700,
   740
  ],
  "gridsize": [
   15.0,
   15.0
  ],
  "boxes": [
   {
    "box": {
     "maxclass": "comment",
     "text": "exp-003 第一阶段模型 · encode → 4 维潜在 → decode",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      20,
      15,
      620,
      26
     ],
     "fontsize": 16,
     "id": "obj-1"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "每一维：z × 缩放 + 偏移。缩放 1、偏移 0 时等同 forward。\n缩放设 0 时该维不再跟随输入，只由偏移决定（手动给定潜在值）。\n各维控制什么、合理取值范围，都要靠试听确认；下方数字显示编码器当前输出。",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 3,
     "patching_rect": [
      20,
      45,
      660,
      60
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
      150,
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
      150,
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
      150,
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
      150,
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
      120,
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
      120,
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
      190,
      77,
      22
     ],
     "id": "obj-9"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "nn~ exp003-forest-s105ck01-p1-step1000000_streaming encode 2048",
     "numinlets": 1,
     "numoutlets": 4,
     "outlettype": [
      "signal",
      "signal",
      "signal",
      "signal"
     ],
     "patching_rect": [
      20,
      230,
      455,
      22
     ],
     "id": "obj-10"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "nn~ exp003-forest-s105ck01-p1-step1000000_streaming decode 2048",
     "numinlets": 4,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      520,
      560,
      22
     ],
     "id": "obj-11"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "z1",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      20,
      270,
      40,
      20
     ],
     "id": "obj-12"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "snapshot~ 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "float"
     ],
     "patching_rect": [
      20,
      295,
      105,
      22
     ],
     "id": "obj-13"
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
      20,
      325,
      60,
      22
     ],
     "id": "obj-14"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "*~ 1.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      410,
      49,
      22
     ],
     "id": "obj-15"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "+~ 0.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      20,
      450,
      49,
      22
     ],
     "id": "obj-16"
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
      20,
      375,
      55,
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
      375,
      55,
      22
     ],
     "id": "obj-18"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "缩放  偏移",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      20,
      355,
      120,
      20
     ],
     "id": "obj-19"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "loadmess 1.",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      90,
      325,
      70,
      22
     ],
     "id": "obj-20"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "z2",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      170,
      270,
      40,
      20
     ],
     "id": "obj-21"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "snapshot~ 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "float"
     ],
     "patching_rect": [
      170,
      295,
      105,
      22
     ],
     "id": "obj-22"
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
      170,
      325,
      60,
      22
     ],
     "id": "obj-23"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "*~ 1.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      170,
      410,
      49,
      22
     ],
     "id": "obj-24"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "+~ 0.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      170,
      450,
      49,
      22
     ],
     "id": "obj-25"
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
      170,
      375,
      55,
      22
     ],
     "id": "obj-26"
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
      230,
      375,
      55,
      22
     ],
     "id": "obj-27"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "缩放  偏移",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      170,
      355,
      120,
      20
     ],
     "id": "obj-28"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "loadmess 1.",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      240,
      325,
      70,
      22
     ],
     "id": "obj-29"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "z3",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      320,
      270,
      40,
      20
     ],
     "id": "obj-30"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "snapshot~ 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "float"
     ],
     "patching_rect": [
      320,
      295,
      105,
      22
     ],
     "id": "obj-31"
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
      320,
      325,
      60,
      22
     ],
     "id": "obj-32"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "*~ 1.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      320,
      410,
      49,
      22
     ],
     "id": "obj-33"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "+~ 0.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      320,
      450,
      49,
      22
     ],
     "id": "obj-34"
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
      320,
      375,
      55,
      22
     ],
     "id": "obj-35"
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
      380,
      375,
      55,
      22
     ],
     "id": "obj-36"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "缩放  偏移",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      320,
      355,
      120,
      20
     ],
     "id": "obj-37"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "loadmess 1.",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      390,
      325,
      70,
      22
     ],
     "id": "obj-38"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "z4",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      470,
      270,
      40,
      20
     ],
     "id": "obj-39"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "snapshot~ 100",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "float"
     ],
     "patching_rect": [
      470,
      295,
      105,
      22
     ],
     "id": "obj-40"
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
      470,
      325,
      60,
      22
     ],
     "id": "obj-41"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "*~ 1.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      470,
      410,
      49,
      22
     ],
     "id": "obj-42"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "+~ 0.",
     "numinlets": 2,
     "numoutlets": 1,
     "outlettype": [
      "signal"
     ],
     "patching_rect": [
      470,
      450,
      49,
      22
     ],
     "id": "obj-43"
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
      470,
      375,
      55,
      22
     ],
     "id": "obj-44"
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
      530,
      375,
      55,
      22
     ],
     "id": "obj-45"
    }
   },
   {
    "box": {
     "maxclass": "comment",
     "text": "缩放  偏移",
     "numinlets": 1,
     "numoutlets": 0,
     "linecount": 1,
     "patching_rect": [
      470,
      355,
      120,
      20
     ],
     "id": "obj-46"
    }
   },
   {
    "box": {
     "maxclass": "newobj",
     "text": "loadmess 1.",
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "patching_rect": [
      540,
      325,
      70,
      22
     ],
     "id": "obj-47"
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
      590,
      56,
      22
     ],
     "id": "obj-48"
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
      560,
      60,
      22
     ],
     "id": "obj-49"
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
      560,
      120,
      20
     ],
     "id": "obj-50"
    }
   },
   {
    "box": {
     "maxclass": "ezdac~",
     "numinlets": 2,
     "numoutlets": 0,
     "patching_rect": [
      20,
      630,
      45,
      45
     ],
     "id": "obj-51"
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
      630,
      91,
      22
     ],
     "id": "obj-52"
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
      590,
      42,
      22
     ],
     "id": "obj-53"
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
      590,
      30,
      22
     ],
     "id": "obj-54"
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
      590,
      30,
      22
     ],
     "id": "obj-55"
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
      590,
      300,
      40
     ],
     "id": "obj-56"
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
      470,
      120,
      84,
      22
     ],
     "id": "obj-57"
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
      470,
      150,
      77,
      22
     ],
     "id": "obj-58"
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
      470,
      180,
      98,
      22
     ],
     "id": "obj-59"
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
      470,
      210,
      60,
      22
     ],
     "id": "obj-60"
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
      535,
      210,
      200,
      20
     ],
     "id": "obj-61"
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
      "obj-10",
      0
     ],
     "destination": [
      "obj-13",
      0
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
      "obj-14",
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
      "obj-15",
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
      "obj-16",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-16",
      0
     ],
     "destination": [
      "obj-11",
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
      "obj-15",
      1
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
      "obj-16",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-20",
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
      "obj-10",
      1
     ],
     "destination": [
      "obj-22",
      0
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
      "obj-23",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      1
     ],
     "destination": [
      "obj-24",
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
      "obj-25",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-25",
      0
     ],
     "destination": [
      "obj-11",
      1
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
      "obj-24",
      1
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
      "obj-25",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-29",
      0
     ],
     "destination": [
      "obj-26",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      2
     ],
     "destination": [
      "obj-31",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-31",
      0
     ],
     "destination": [
      "obj-32",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      2
     ],
     "destination": [
      "obj-33",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-33",
      0
     ],
     "destination": [
      "obj-34",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-34",
      0
     ],
     "destination": [
      "obj-11",
      2
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-35",
      0
     ],
     "destination": [
      "obj-33",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-36",
      0
     ],
     "destination": [
      "obj-34",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-38",
      0
     ],
     "destination": [
      "obj-35",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      3
     ],
     "destination": [
      "obj-40",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-40",
      0
     ],
     "destination": [
      "obj-41",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-10",
      3
     ],
     "destination": [
      "obj-42",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-42",
      0
     ],
     "destination": [
      "obj-43",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-43",
      0
     ],
     "destination": [
      "obj-11",
      3
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-44",
      0
     ],
     "destination": [
      "obj-42",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-45",
      0
     ],
     "destination": [
      "obj-43",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-47",
      0
     ],
     "destination": [
      "obj-44",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-49",
      0
     ],
     "destination": [
      "obj-48",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-11",
      0
     ],
     "destination": [
      "obj-48",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-48",
      0
     ],
     "destination": [
      "obj-51",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-48",
      0
     ],
     "destination": [
      "obj-51",
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
      "obj-52",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-11",
      0
     ],
     "destination": [
      "obj-52",
      1
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-53",
      0
     ],
     "destination": [
      "obj-52",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-54",
      0
     ],
     "destination": [
      "obj-52",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-55",
      0
     ],
     "destination": [
      "obj-52",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-57",
      0
     ],
     "destination": [
      "obj-58",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-58",
      0
     ],
     "destination": [
      "obj-59",
      0
     ]
    }
   },
   {
    "patchline": {
     "source": [
      "obj-59",
      0
     ],
     "destination": [
      "obj-60",
      0
     ]
    }
   }
  ]
 }
}
