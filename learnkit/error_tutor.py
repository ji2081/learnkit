"""
error_tutor — 파이썬 에러를 '친절한 한국어'로 바꿔주는 작은 조교

무서운 빨간 트레이스백을 초보자가 읽을 수 있는 네 칸으로 바꾼다:

    원인 · 위치 · 코드 · 힌트

어떻게:
  · 규칙        : 에러 종류별 기본 설명 (register_rule로 확장 가능)
  · 메시지 파싱  : 에러 메시지에서 실제 이름/키/모듈을 뽑아 구체적으로
  · 오타 추천    : 에러가 난 프레임의 진짜 이름들을 꺼내 difflib으로 비슷한 걸 찾음
  · 코드 인용    : linecache로 문제가 난 그 줄을 그대로 보여줌
  · LLM + 폴백   : 키가 있으면 LLM, 없거나 실패하면 규칙 기반 (오프라인에서도 동작)

붙는 방식:
  · 일반 스크립트 → sys.excepthook
  · 주피터        → shell.set_custom_exc
  · 잠깐만        → with tutor(): ...
"""

from __future__ import annotations

import builtins
import difflib
import json
import linecache
import os
import re
import sys
import traceback
from contextlib import contextmanager

# ── 에러 종류별 기본 설명 (원인, 기본 힌트) ──────────────────────────
_RULES: dict[str, tuple[str, str]] = {
    "NameError":          ("아직 만들지 않은 이름을 사용했어요.", "쓰기 전에 먼저 값을 넣어주세요."),
    "SyntaxError":        ("문법이 살짝 어긋났어요.", "따옴표·괄호의 짝, 콜론(:)이 빠지지 않았는지 보세요."),
    "IndentationError":   ("들여쓰기가 어긋났어요.", "같은 묶음은 칸 수를 똑같이 맞춰주세요."),
    "TabError":           ("탭과 공백이 섞였어요.", "들여쓰기를 공백 4칸으로 통일해 보세요."),
    "TypeError":          ("서로 다른 종류를 섞어서 생긴 문제예요.", "숫자와 글자는 바로 못 더해요. str()/int()로 맞춰보세요."),
    "ValueError":         ("값의 형태가 기대와 달라요.", "예: int(\"가나다\")처럼 숫자가 아닌 걸 숫자로 바꾸려 했는지 보세요."),
    "IndexError":         ("리스트에 없는 위치를 꺼내려 했어요.", "len()으로 길이를 넘지 않는지 확인해요."),
    "KeyError":           ("딕셔너리에 없는 키를 찾았어요.", "키 이름을 다시 확인하거나 .get()을 써보세요."),
    "ZeroDivisionError":  ("0으로는 나눌 수 없어요.", "나누는 값이 0이 아닌지 먼저 확인해요."),
    "AttributeError":     ("그 객체에는 없는 기능을 불렀어요.", "오타이거나 타입이 기대와 다른지 확인해요."),
    "ModuleNotFoundError": ("설치되지 않은 라이브러리예요.", "pip install 로 먼저 설치해 주세요."),
    "ImportError":        ("가져오려는 것을 찾지 못했어요.", "이름의 철자와 라이브러리 버전을 확인해 보세요."),
    "FileNotFoundError":  ("그 경로에 파일이 없어요.", "파일명과 폴더 위치를 확인해요. 확장자도 빠지지 않았는지."),
    "PermissionError":    ("파일을 열 권한이 없어요.", "다른 프로그램이 파일을 쓰고 있는지 확인해 보세요."),
    "UnboundLocalError":  ("함수 안에서 값을 넣기 전에 먼저 꺼내 썼어요.", "함수 맨 위에서 먼저 값을 정해주세요."),
    "RecursionError":     ("함수가 자기 자신을 끝없이 불렀어요.", "멈추는 조건(기저 사례)을 넣어주세요."),
    "StopIteration":      ("더 꺼낼 것이 없어요.", "for 문을 쓰거나 next(..., 기본값)으로 받아보세요."),
    "OverflowError":      ("숫자가 너무 커졌어요.", "값의 범위를 줄이거나 나눠서 계산해 보세요."),
    "UnicodeDecodeError": ("글자 인코딩이 맞지 않아요.", "파일을 열 때 encoding='utf-8'을 넣어보세요."),
}

_MAX_MSG = 300      # LLM에 보내는 메시지 길이 제한
_USE_LLM = True     # install(use_llm=False)로 끔. 환경변수는 건드리지 않는다.
_PREV_HOOK = None   # uninstall()로 되돌리기 위한 원래 훅
_INSTALLED = False


def register_rule(name: str, 원인: str, 힌트: str) -> None:
    """새 에러 설명을 추가한다. (기여의 가장 쉬운 입구)

        register_rule("JSONDecodeError",
                      "JSON 모양이 아니에요.", "따옴표와 쉼표를 확인해 보세요.")
    """
    _RULES[name] = (원인, 힌트)


# ── 어디서 났는지 ────────────────────────────────────────────────

def _last_frame(tb):
    """에러가 실제로 난 가장 안쪽 프레임."""
    last = None
    for frame, lineno in traceback.walk_tb(tb):
        last = (frame, lineno)
    return last


def _location(tb) -> str:
    last = _last_frame(tb)
    if not last:
        return "위치 미상"
    frame, lineno = last
    return f"{os.path.basename(frame.f_code.co_filename)} {lineno}번째 줄"


def _source_line(tb) -> str:
    """문제가 난 그 줄의 코드를 그대로. 초보자에게 '어디'보다 강력한 단서."""
    last = _last_frame(tb)
    if not last:
        return ""
    frame, lineno = last
    line = linecache.getline(frame.f_code.co_filename, lineno)
    return line.strip()


# ── 오타 추천 ────────────────────────────────────────────────────

def _names_in_scope(frame) -> list[str]:
    """그 시점에 실제로 존재하던 이름들 — 지역 · 전역 · 내장 순."""
    if frame is None:
        return []
    seen = []
    for space in (frame.f_locals, frame.f_globals, vars(builtins)):
        for key in space:
            if not key.startswith("_") and key not in seen:
                seen.append(key)
    return seen


def _did_you_mean(exc_type, exc, tb) -> str | None:
    """'혹시 이걸 쓰려던 건 아닌가요?' — difflib으로 가장 비슷한 이름을 찾는다.

    파이썬 3.12부터는 인터프리터가 비슷한 걸 알려주지만, 영어이고
    3.9~3.11에서는 아예 없다. 여기서는 한국어로, 더 낮은 버전에서도.
    """
    name = exc_type.__name__
    last = _last_frame(tb)
    frame = last[0] if last else None
    target = getattr(exc, "name", None)      # 3.10+ 에는 exc.name 이 있다

    if name == "NameError":
        if not target:
            m = re.search(r"name '([^']+)'", str(exc))
            target = m.group(1) if m else None
        candidates = _names_in_scope(frame)
    elif name == "AttributeError":
        obj = getattr(exc, "obj", None)
        if not target:
            m = re.search(r"has no attribute '([^']+)'", str(exc))
            target = m.group(1) if m else None
        candidates = [a for a in dir(obj) if not a.startswith("_")] if obj is not None else []
    else:
        return None

    if not target or not candidates:
        return None
    close = difflib.get_close_matches(target, candidates, n=1, cutoff=0.7)
    if close and close[0] != target:
        return f"혹시 '{close[0]}'을(를) 쓰려던 건 아닌가요?"
    return None


# ── 구체적 힌트 ──────────────────────────────────────────────────

def _specific_hint(name: str, msg: str) -> str | None:
    """에러 메시지에서 실제 이름/모듈/속성을 뽑아 구체적 힌트를 만든다."""
    if name == "NameError":
        m = re.search(r"name '([^']+)'", msg)
        if m:
            return f"'{m.group(1)}'을(를) 쓰기 전에 먼저 만들어주세요. 예: {m.group(1)} = ..."
    if name == "ModuleNotFoundError":
        m = re.search(r"No module named '([^']+)'", msg)
        if m:
            return f"'{m.group(1)}' 라이브러리가 없어요. 터미널에서  pip install {m.group(1)}  해보세요."
    if name == "AttributeError":
        m = re.search(r"has no attribute '([^']+)'", msg)
        if m:
            return f"'{m.group(1)}' 이라는 기능(속성)이 없어요. 오타이거나 타입이 다를 수 있어요."
    if name == "FileNotFoundError":
        m = re.search(r"No such file or directory: '([^']+)'", msg)
        if m:
            return f"'{m.group(1)}' 파일을 못 찾았어요. 경로와 파일명을 확인해 보세요."
    if name == "KeyError":
        return f"{msg} 키가 딕셔너리에 없어요. 키 이름을 확인하거나 .get()을 써보세요."
    return None


def _via_llm(name: str, msg: str, 코드: str = "") -> dict | None:
    """키가 있으면 LLM에게 구조화된 JSON으로 설명을 받는다. 실패 시 None.

    규칙 기반과 달리 **문제가 난 코드 줄까지 같이 넘긴다** — 같은 NameError라도
    상황에 따라 해줄 말이 다르기 때문이다.
    """
    if not _USE_LLM:
        return None
    from . import ai

    붙임 = f"\n문제가 난 줄: {코드[:120]}" if 코드 else ""
    data = ai.ask(
        "아래 에러를 보고 JSON으로만 답하라. 키는 정확히 원인, 힌트 두 개.\n"
        "1~2문장, 쉬운 말. 정답 코드는 주지 말고 힌트만.\n"
        '예시: {"원인": "...", "힌트": "..."}\n'
        f"에러: {name}: {msg[:_MAX_MSG]}{붙임}",
        as_json=True,
        max_tokens=250,
    )
    if isinstance(data, dict) and "원인" in data and "힌트" in data:
        return {"원인": str(data["원인"]), "힌트": str(data["힌트"])}
    return None


def explain(exc_type, exc, tb) -> dict:
    """에러를 {원인·위치·코드·힌트} 구조로 설명한다. (LLM 우선, 폴백 규칙 기반)"""
    name, msg = exc_type.__name__, str(exc)
    코드줄 = _source_line(tb)
    via = _via_llm(name, msg, 코드줄)
    if via:
        원인, 힌트, 출처 = via["원인"], via["힌트"], "AI"
    else:
        원인, 기본힌트 = _RULES.get(name, (f"'{name}'이 났어요.", "메시지를 천천히 읽어보면 단서가 있어요."))
        힌트, 출처 = (_specific_hint(name, msg) or 기본힌트), "규칙"

    추천 = _did_you_mean(exc_type, exc, tb)
    if 추천:
        힌트 = f"{힌트} {추천}"

    return {
        "원인": 원인,
        "위치": _location(tb),
        "코드": 코드줄,
        "힌트": 힌트,
        "_출처": 출처,
    }


def _render(exc_type, exc, tb, info: dict):
    """원본 에러 + 친절한 카드를 출력. rich 있으면 예쁘게, 없으면 평범하게."""
    칸 = [("원인", info["원인"]), ("위치", info["위치"])]
    if info.get("코드"):
        칸.append(("코드", info["코드"]))
    칸.append(("힌트", info["힌트"]))

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markup import escape
        c = Console()
        c.print()
        c.rule("[dim]원래 에러[/dim]")
        c.print(escape("".join(traceback.format_exception(exc_type, exc, tb))), style="red dim")
        본문 = "\n".join(f"[bold]{k}[/bold]  {escape(str(v))}" for k, v in 칸)
        c.print(Panel(본문, title=f"🤖 튜터 ({info['_출처']})", border_style="green"))
    except Exception:
        print("\n" + "─" * 56)
        traceback.print_exception(exc_type, exc, tb, file=sys.stdout)
        print("─" * 56)
        print(f"🤖 튜터 ({info['_출처']})")
        for k, v in 칸:
            print(f"  {k}: {v}")
        print("─" * 56)


# ── 붙이기 / 떼기 ────────────────────────────────────────────────

def _ipython():
    """주피터 안이면 셸 객체, 아니면 None."""
    try:
        return get_ipython()  # type: ignore  # 주피터가 넣어주는 이름
    except NameError:
        return None


def install(use_llm: bool = True) -> bool:
    """튜터를 켠다. 주피터면 셀 에러를, 일반 스크립트면 종료 에러를 가로챈다.

    use_llm=False 면 규칙 기반으로 고정한다(발표 라이브 데모에 안전).
    """
    global _USE_LLM, _PREV_HOOK, _INSTALLED
    _USE_LLM = use_llm

    ip = _ipython()
    if ip is not None:
        def _custom(shell, etype, evalue, tb_, tb_offset=None):
            _render(etype, evalue, tb_, explain(etype, evalue, tb_))
        ip.set_custom_exc((Exception,), _custom)
    else:
        if not _INSTALLED:
            _PREV_HOOK = sys.excepthook       # 원래 훅을 기억해 둔다
        sys.excepthook = lambda t, e, tb: _render(t, e, tb, explain(t, e, tb))

    _INSTALLED = True
    return True


def uninstall() -> bool:
    """튜터를 끄고 원래 상태로 되돌린다.

    install()만 있고 되돌릴 방법이 없으면, 한 번 켠 주피터 커널은
    끝까지 튜터에 묶인다. 켤 수 있으면 끌 수도 있어야 한다.
    """
    global _PREV_HOOK, _INSTALLED
    if not _INSTALLED:
        return False

    ip = _ipython()
    if ip is not None:
        ip.set_custom_exc((), None)
    else:
        sys.excepthook = _PREV_HOOK or sys.__excepthook__
        _PREV_HOOK = None

    _INSTALLED = False
    return True


@contextmanager
def tutor(use_llm: bool = True):
    """이 블록 안에서만 튜터를 켠다.

        with tutor():
            print(과일)      # 친절한 설명

    전역을 오염시키지 않아서, 수업 자료 안에서 '지금부터 여기만' 쓰기 좋다.
    """
    was = _INSTALLED
    install(use_llm=use_llm)
    try:
        yield
    except Exception as e:
        # 첫 프레임은 이 함수의 yield — 학습자 코드가 아니므로 잘라낸다.
        tb = e.__traceback__
        if tb is not None and tb.tb_next is not None:
            tb = tb.tb_next
        _render(type(e), e, tb, explain(type(e), e, tb))
    finally:
        if not was:
            uninstall()
