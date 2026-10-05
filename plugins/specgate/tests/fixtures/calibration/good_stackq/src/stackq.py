"""A minimal stack."""


class Stack:
    def __init__(self) -> None:
        self._items: list[int] = []

    def push(self, item: int) -> None:
        self._items.append(item)

    # implements: AC-1
    def peek(self) -> int:
        return self._items[-1]

    # implements: AC-2
    def pop(self) -> int:
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()
