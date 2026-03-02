#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import time
import sys

def screen_active_win():
    print("Start screen active on Windows system")
    # 现代用户极少使用Scroll Lock，轮询影响最小
    SCRLK = 0x91
    
    try:
        while True:
            # 查询键盘按键状态，重置空闲计时器
            ctypes.windll.user32.GetAsyncKeyState(SCRLK)
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("Stop screen active")
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
