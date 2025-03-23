from dataclasses import dataclass


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int

    def left(self) -> int:
        return self.x
    
    def top(self) -> int:
        return self.y

    def translate(self, x: int, y: int):
        self.x += x
        self.y += y