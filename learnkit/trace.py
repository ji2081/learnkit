"""
trace — "왜 치는지 모를 때"에 대한 답: 코드가 한 줄씩 무슨 일을 하는지 보여준다.

초보자가 코드를 따라 치기만 하고 길을 잃는 건, 실행이 **한순간에** 일어나기
때문이다. 입력과 결과 사이가 까맣다. 그 사이를 열어서 한 줄씩 보여주면
"내가 지금 뭘 만들고 있는지"가 눈에 들어온다.

파이썬은 이걸 위한 문을 이미 열어놨다 — `sys.settrace`.
인터프리터가 줄을 실행할 때마다 우리 함수를 불러주고, 그 시점의 프레임에서
지역 변수를 그대로 꺼내볼 수 있다.

    steps = walk(공부기록, [2, 4, 1])
    for s in steps:
        print(s.lineno, s.code, s.changed)

주의: settrace는 디버거와 같은 자리를 쓴다. 수업용으로 잠깐 켜는 용도다.
"""

from __future__ import annotations

import linecache
import reprlib
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["Step", "walk", "format_steps"]

_MAX_STEPS = 500        # 무한 루프에서 메모리가 터지지 않게
_MAX_REPR = 60          # 값이 길면 잘라서 보여준다

# repr()로 통째로 문자열을 만든 뒤 자르면, 원소가 30만 개인 리스트도 전부 만들고 버린다.
# reprlib은 필요한 만큼만 만든다 — 큰 데이터에서 30배 이상 빠르다.
_요약 = reprlib.Repr()
_요약.maxlist = _요약.maxtuple = _요약.maxset = _요약.maxdict = 8
_요약.maxstring = _요약.maxother = _MAX_REPR
_요약.maxlevel = 3


def _short(value: Any) -> str:
    """값을 한 눈에 들어오게. 길면 자른다."""
    try:
        text = _요약.repr(value)
    except Exception:
        return f"<{type(value).__name__}>"
    return text if len(text) <= _MAX_REPR else text[: _MAX_REPR - 1] + "…"


def _찍기(space: dict) -> dict:
    """그 순간의 지역 변수를 **글자로 굳혀** 남긴다.

    frame.f_locals는 살아있는 객체를 담고 있다. 리스트처럼 나중에 바뀌는 값을
    그대로 들고 있으면, 나중에 출력할 때 '그때 값'이 아니라 '최종 값'이 보인다.
    append로 조금씩 채워지는 리스트는 변화 자체가 감지되지도 않는다
    (같은 객체라 `is` 비교가 True). 그래서 여기서 바로 글자로 굳힌다.
    """
    return {k: _short(v) for k, v in space.items()}


@dataclass
class Step:
    """코드 한 줄이 실행된 순간의 기록."""

    lineno: int
    code: str
    changed: dict = field(default_factory=dict)     # 이 줄에서 바뀐 값 (글자로 굳힘)
    returned: Any = None
    is_return: bool = False

    def describe(self) -> str:
        """사람이 읽는 한 줄 설명."""
        if self.is_return:
            return f"→ 결과: {_short(self.returned)}"
        if not self.changed:
            return ""
        return " · ".join(f"{k} = {v}" for k, v in self.changed.items())


def walk(func: Callable, *args: Any, max_steps: int = _MAX_STEPS, **kwargs: Any):
    """func를 실행하면서 한 줄씩 기록한다. (결과, [Step, ...])을 돌려준다.

    func 안쪽만 따라간다. 파이썬 내부나 다른 라이브러리까지 파고들지 않는다 —
    학습자가 보고 싶은 건 자기가 쓴 줄뿐이니까.
    """
    target = getattr(func, "__code__", None)
    if target is None:
        raise TypeError("walk()는 파이썬으로 작성된 함수만 따라갈 수 있어요.")

    filename = target.co_filename
    steps: list[Step] = []
    prev: dict[str, str] = {}          # 직전 줄까지의 지역 변수 (글자로 굳힌 상태)
    pending: int | None = None         # 아직 결과를 확정 못 한 줄

    def source(lineno: int) -> str:
        return linecache.getline(filename, lineno).strip()

    def flush(frame, *, returned: Any = None, is_return: bool = False) -> None:
        """직전 줄이 만들어낸 변화를 확정해 기록한다."""
        nonlocal prev
        if pending is None or len(steps) >= max_steps:
            return
        now = _찍기(frame.f_locals)
        changed = {k: v for k, v in now.items() if prev.get(k) != v}
        steps.append(Step(
            lineno=pending,
            code=source(pending),
            changed=changed,
            returned=returned,
            is_return=is_return,
        ))
        prev = now

    def local_tracer(frame, event, arg):
        nonlocal pending
        if event == "line":
            flush(frame)
            pending = frame.f_lineno
        elif event == "return":
            flush(frame, returned=arg, is_return=True)
            pending = None
        return local_tracer

    def tracer(frame, event, arg):
        # 우리가 지목한 함수의 호출에만 붙는다.
        nonlocal prev, pending
        if event == "call" and frame.f_code is target:
            prev = _찍기(frame.f_locals)
            pending = None
            return local_tracer
        return None

    이전 = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = func(*args, **kwargs)
    finally:
        sys.settrace(이전)      # 원래 상태로. 디버거를 쓰고 있었을 수도 있다.

    linecache.checkcache(filename)
    return result, steps


def format_steps(steps: list[Step], *, number: bool = True) -> list[str]:
    """Step들을 화면에 뿌리기 좋은 문자열 줄로."""
    출력 = []
    for i, s in enumerate(steps, 1):
        머리 = f"{i:>2}. " if number else ""
        설명 = s.describe()
        # 소스를 읽을 수 없는 경우(대화형 셸, exec 등)엔 줄 번호로 대신한다
        본문 = s.code or f"({s.lineno}번째 줄)"
        줄 = f"{머리}{본문}"
        if 설명:
            줄 = f"{줄}\n{' ' * len(머리)}   {설명}"
        출력.append(줄)
    return 출력
