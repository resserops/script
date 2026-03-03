#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import time
import sys

def screen_active_win():
    print("Start screen active on Windows system")
    ES_SYSTEM_REQUIRED = 0x00000001  # 下次空闲检测保持系统处于运行状态
    ES_DISPLAY_REQUIRED = 0x00000002 # 下次空闲检测保持屏幕开启
    ES_CONTINUOUS = 0x80000000       # 后续所有空闲检测持续生效

    try:
        while True:
            # 避免永久影响系统状态，不设置持续生效，脉冲式激活
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            time.sleep(60)

    except KeyboardInterrupt:
        sys.exit(0)

    except Exception as e:
        print(f"Unknown exception: {e}")
        sys.exit(1)


def screen_active_win_mouse():
    print("Start screen active on Windows system")
    
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    
    try:
        while True:
            p = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
            ctypes.windll.user32.SetCursorPos(p.x + 1, p.y + 1)
            ctypes.windll.user32.SetCursorPos(p.x, p.y)
            time.sleep(60)
            
    except KeyboardInterrupt:
        sys.exit(0)

    except Exception as e:
        print(f"Unknown exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        screen_active_win()
    else:
        print("Error: Only support Windows system")
        sys.exit(1)
