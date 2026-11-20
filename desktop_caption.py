"""Coloración opcional de la barra NATIVA de Windows 11, sin marcos personalizados."""
from __future__ import annotations
import ctypes
import os
import time
from ctypes import wintypes

NAVY_COLORREF = 0x00452B10  # RGB #102B45 codificado en COLORREF (BGR)
WHITE_COLORREF = 0x00FFFFFF


def colorize_caption(title: str, attempts: int = 40) -> bool:
    """Solicita barra azul marino/texto blanco (Windows 11, build 22000+).

    Nunca interrumpe el arranque si DWM no permite personalizar el marco.
    """
    if os.name != 'nt':return False
    try:
        user32=ctypes.windll.user32
        user32.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR]
        user32.FindWindowW.restype=wintypes.HWND
        dwm=ctypes.windll.dwmapi.DwmSetWindowAttribute
        dwm.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        dwm.restype=ctypes.c_long
        hwnd=None
        for _ in range(attempts):
            hwnd=user32.FindWindowW(None,title)
            if hwnd:break
            time.sleep(.15)
        if not hwnd:return False
        bg=ctypes.c_uint32(NAVY_COLORREF)
        fg=ctypes.c_uint32(WHITE_COLORREF)
        a=dwm(hwnd,35,ctypes.byref(bg),ctypes.sizeof(bg))
        b=dwm(hwnd,36,ctypes.byref(fg),ctypes.sizeof(fg))
        return a==0 and b==0
    except (OSError,AttributeError,ValueError):
        return False
