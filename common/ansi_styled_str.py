#! /usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["styled"]

class AnsiStyledStr(str):
    COLOR_MAP = {
        "black": 0,
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "white": 7
    }

    def __init__(self, s: str):
        self.s = s
        self._styles = set()
        self._fore = None
        self._back = None
    
    def bold(self):
        self._styles.add("1")
        return self
    
    def dim(self):
        self._styles.add("2")
        return self
    
    def italic(self):
        self._styles.add("3")
        return self
    
    def underline(self):
        self._styles.add("4")
        return self
    
    def blink(self):
        self._styles.add("5")
        return self
    
    def reverse(self):
        self._styles.add("7")
        return self
    
    def hidden(self):
        self._styles.add("8")
        return self
    
    def strike(self):
        self._styles.add("9")
        return self

    def black(self, light=False):
        return self.fore("black", light)
    
    def red(self, light=False):
        return self.fore("red", light)
    
    def green(self, light=False):
        return self.fore("green", light)
    
    def yellow(self, light=False):
        return self.fore("yellow", light)
    
    def blue(self, light=False):
        return self.fore("blue", light)
    
    def magenta(self, light=False):
        return self.fore("magenta", light)
    
    def cyan(self, light=False):
        return self.fore("cyan", light)

    def white(self, light=False):
        return self.fore("white", light)
    
    def fore(self, color, light=False):
        color = color.lower()
        if color not in self.COLOR_MAP:
            raise ValueError(f"unexpected color: {color}")
        base = 90 if light else 30
        self._fore = str(base + self.COLOR_MAP[color])
        return self
    
    def f256(self, color):
        self._fore = f"38;5;{color}"
        return self

    def frgb(self, r, g, b):
        self._fore = f"38;2;{r};{g};{b}"
        return self

    def back(self, color, light=False):
        color = color.lower()
        if color not in self.COLOR_MAP:
            raise ValueError(f"unexpected color: {color}")
        base = 100 if light else 40
        self._back = str(base + self.COLOR_MAP[color])
        return self
    
    def b256(self, color):
        self._back = f"48;5;{color}"
        return self

    def brgb(self, r, g, b):
        self._back = f"48;2;{r};{g};{b}"
        return self
    
    def __add__(self, other):
        return self.__str__() + str(other)

    def __iadd__(self, other):
        self._s += str(other)
        return self

    def __radd__(self, other):
        return str(other) + self.__str__()
    
    def __str__(self):
        codes = list(self._styles)
        if self._fore:
            codes.append(self._fore)
        if self._back:
            codes.append(self._back)
        if not codes:
            return self.s
        return f"\033[{';'.join(codes)}m{self.s}\033[0m"

def styled(s):
    return AnsiStyledStr(s)
