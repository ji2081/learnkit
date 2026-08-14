"""
renderers — '무엇을 가르칠지'와 '어떻게 보여줄지'를 가르는 경계선.

learnkit의 핵심 주장은 *한 번 정의하면 어디로든*이다. 그 주장이 성립하려면
Lesson은 화면을 몰라야 하고, 화면은 Lesson 내부를 몰라야 한다. 그 사이를
잇는 게 이 모듈이다.

  Lesson  ──▶  View (그릴 재료만 담은 값)  ──▶  Renderer (그리는 방법)

Renderer는 상속이 아니라 `Protocol`이다. learnkit을 임포트하지 않아도,
아래 두 가지만 있으면 그것은 이미 렌더러다:

    name: str
    def render(self, view: View, **options) -> Any

덕분에 새 화면을 붙이는 데 필요한 건 클래스 하나와 `register()` 한 줄이다.
(→ 이게 "같이 만들어요"의 실제 확장점)
"""

from __future__ import annotations

import ast
import html
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


def disp_width(text: str) -> int:
    """터미널에서 실제로 차지하는 칸 수.

    한글·한자·가나는 len()이 1이지만 화면에서는 2칸을 먹는다. 이걸 모르면
    표나 박스를 그릴 때 오른쪽 선이 어긋난다. 한국어 자료를 다루는 텍스트
    렌더러라면 거의 반드시 만나는 문제라 여기 둔다.
    """
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, width: int, align: str = "<") -> str:
    """disp_width 기준으로 칸을 맞춘다. (str.ljust의 한글 버전)"""
    남은 = max(width - disp_width(text), 0)
    if align == ">":
        return " " * 남은 + text
    if align == "^":
        왼 = 남은 // 2
        return " " * 왼 + text + " " * (남은 - 왼)
    return text + " " * 남은


_숫자 = re.compile(r"-?\d+(?:\.\d+)?")


def bar(line: Any, cap: int = 40) -> str:
    """줄에 담긴 숫자만큼 막대를 그린다. 숫자가 없으면 글자 수만큼.

    결과를 '글'과 '그림' 두 가지로 동시에 보여주기 위한 최소 장치.

    숫자는 **글자 안에 박혀 있어도** 찾는다. "월 2시간"의 2를 못 읽으면
    막대가 글자 수로 그려져서, 값이 다른데 길이가 같아 보이는 일이 생긴다.
    보여주려고 만든 그림이 조용히 거짓말을 하면 안 된다.
    """
    s = str(line)
    찾은 = _숫자.findall(s)
    if not 찾은:
        return "█" * min(disp_width(s), cap)
    # 자릿수가 아주 많으면 float가 inf가 되어 round()가 터진다.
    # 학습자가 숫자를 길게 누르기만 해도 나는 일이라 여기서 막는다.
    값 = float(찾은[-1])
    if not math.isfinite(값):
        return "█" * cap
    return "█" * min(max(round(값), 0), cap)


@dataclass(frozen=True)
class View:
    """렌더러가 화면을 그리는 데 필요한 전부.

    Lesson을 통째로 넘기지 않고 이 값만 넘긴다. 렌더러가 Lesson의 내부
    구조에 기대지 못하게 막아서, 나중에 Lesson이 바뀌어도 렌더러가 안 깨진다.
    """

    title: str
    dial: str
    branch: str | None = None
    result: list | None = None
    error: dict | None = None
    hint: str = ""
    challenge: str = ""
    source: str | None = None
    build_name: str = "build"
    branches: dict | None = None
    dials: tuple = ("보기", "바꾸기", "만들기")
    big: bool = False
    high_contrast: bool = False
    steps: list | None = None       # 한 줄씩 따라간 기록 (trace=True일 때만)

    @property
    def failed(self) -> bool:
        return self.error is not None

    def bar(self, line: Any) -> str:
        return bar(line)

    def rows(self) -> list[tuple[str, str]]:
        """(글, 막대) 쌍. 다중 표현의 최소 단위."""
        return [(str(line), self.bar(line)) for line in (self.result or [])]


@runtime_checkable
class Renderer(Protocol):
    """화면 하나를 그리는 것. 상속이 아니라 모양만 맞으면 된다."""

    name: str

    def render(self, view: View, **options: Any) -> Any:
        ...


_RENDERERS: dict[str, Renderer] = {}


def register(renderer: Renderer | type | None = None, *, name: str | None = None):
    """렌더러를 등록한다. 클래스에 데코레이터로 붙여도 되고, 인스턴스를 넘겨도 된다.

        @register
        class MyRenderer:
            name = "my"
            def render(self, view, **opts): ...
    """
    def _add(obj):
        inst = obj() if isinstance(obj, type) else obj
        key = name or getattr(inst, "name", None)
        if not key:
            raise ValueError("렌더러에 name이 필요합니다.")
        if not isinstance(inst, Renderer):
            raise TypeError(
                f"'{key}'는 렌더러 모양이 아닙니다. "
                "name 속성과 render(view, **options) 메서드가 필요해요."
            )
        _RENDERERS[key] = inst
        return obj

    return _add(renderer) if renderer is not None else _add


def get(name: str) -> Renderer:
    try:
        return _RENDERERS[name]
    except KeyError:
        raise KeyError(
            f"'{name}' 렌더러가 없어요. 지금 쓸 수 있는 건: {', '.join(available())}"
        ) from None


def available() -> list[str]:
    return sorted(_RENDERERS)


# ─────────────────────────────────────────────────────────────
# 기본 렌더러 셋 — 콘솔 · 주피터 위젯 · 웹앱
# 각각이 '같은 View를 다르게 그리는 방법' 하나씩이다.
# ─────────────────────────────────────────────────────────────


@register
class ConsoleRenderer:
    """터미널. rich가 있으면 예쁘게, 없으면 표준 print로 물러난다."""

    name = "console"

    def render(self, view: View, **options: Any) -> None:
        try:
            self._rich(view)
        except ImportError:
            self._plain(view)

    def _rich(self, view: View) -> None:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.markup import escape

        c = Console()
        title_style = "bold white on dark_green" if view.high_contrast else "bold green"
        c.print()
        c.print(f" {view.title} ", style=title_style)
        c.print(f"[dim]갈래: {escape(str(view.branch))}  ·  난이도: {escape(view.dial)}[/dim]")

        if view.failed:
            err = view.error or {}
            c.print(Panel(
                f"[bold]원인[/bold] {escape(err.get('원인', ''))}\n"
                f"[bold]위치[/bold] {escape(err.get('위치', ''))}\n"
                f"[bold]힌트[/bold] {escape(err.get('힌트', ''))}",
                title="tutor", border_style="red"))
            return

        gap = "\n" if view.big else ""
        for text, drawn in view.rows():
            c.print(f"{gap}[bold]{escape(text)}[/bold]   [green]{drawn}[/green]")

        if view.steps:
            from .trace import format_steps
            몸 = "\n".join(escape(줄) for 줄 in format_steps(view.steps))
            c.print(Panel(몸, title="한 줄씩 따라가기", border_style="yellow"))

        if view.dial == "바꾸기":
            c.print(r"[cyan]-> as_console(dial='바꾸기', data=[...]) 로 데이터를 '내 것'으로 바꿔보세요[/cyan]")
            if view.hint:
                c.print(f"[dim]힌트: {escape(view.hint)}[/dim]")
        elif view.dial == "만들기":
            if view.source:
                # 코드는 마크업이 아니라 코드로 — 대괄호가 먹히지 않게
                c.print(Panel(Syntax(view.source.rstrip(), "python", theme="monokai",
                                     background_color="default", word_wrap=True),
                              title="build (직접 고쳐보기)", border_style="cyan"))
            if view.challenge:
                c.print(Panel(escape(view.challenge), title="도전 과제", border_style="magenta"))

    def _plain(self, view: View) -> None:
        print(f"\n== {view.title} ==  (갈래:{view.branch} / 난이도:{view.dial})")
        if view.failed:
            err = view.error or {}
            print(f"tutor 원인:{err.get('원인')} | 위치:{err.get('위치')} | 힌트:{err.get('힌트')}")
            return
        for text, drawn in view.rows():
            print(f"{text}   {drawn}")
        if view.steps:
            from .trace import format_steps
            print("\n-- 한 줄씩 따라가기 --")
            for 줄 in format_steps(view.steps):
                print(줄)
        if view.dial == "바꾸기" and view.hint:
            print(f"힌트: {view.hint}")
        elif view.dial == "만들기":
            if view.source:
                print(view.source)
            if view.challenge:
                print(f"도전: {view.challenge}")


@register
class WidgetRenderer:
    """주피터. 갈래·난이도·내 데이터를 위젯으로 만져가며 즉시 확인."""

    name = "widget"

    def render(self, view: View, **options: Any) -> Any:
        import ipywidgets as w
        from IPython.display import display, HTML

        rerun = options.get("rerun")          # 값이 바뀌면 다시 계산해줄 콜백
        branch = w.Dropdown(options=list(view.branches or {}), description="갈래")
        dial = w.ToggleButtons(options=list(view.dials), description="난이도")
        data = w.Textarea(description="내 데이터", placeholder="쉼표로 구분")
        out = w.Output()

        font = "20px" if view.big else "15px"
        bg, fg = ("#000", "#fff") if view.high_contrast else ("#fff", "#111")
        style = f"font-size:{font};background:{bg};color:{fg};padding:8px;"

        def draw(*_):
            out.clear_output()
            with out:
                vals = [s.strip() for s in data.value.split(",") if s.strip()] or None
                cur = rerun(branch.value, dial.value, vals) if rerun else view
                if cur.failed:
                    err = cur.error or {}
                    display(HTML(
                        f"<div style='{style}'>tutor<br>원인: {err.get('원인','')}"
                        f"<br>힌트: {err.get('힌트','')}</div>"))
                    return
                # 학습자 데이터에 <b> 같은 게 들어와도 태그로 해석되면 안 된다
                rows = "".join(
                    f"<div>{html.escape(t)} &nbsp; "
                    f"<span style='color:green'>{b}</span></div>"
                    for t, b in cur.rows())
                extra = ""
                if dial.value == "바꾸기" and cur.hint:
                    extra = f"<p style='color:#0a7'>힌트: {html.escape(cur.hint)}</p>"
                elif dial.value == "만들기":
                    if cur.source:
                        extra += f"<pre>{html.escape(cur.source)}</pre>"
                    if cur.challenge:
                        extra += (f"<p style='color:#a0a'>도전: "
                                  f"{html.escape(cur.challenge)}</p>")
                display(HTML(f"<div style='{style}'>{rows}{extra}</div>"))

        for ctrl in (branch, dial, data):
            ctrl.observe(draw, "value")
        draw()
        return display(w.VBox([branch, dial, data, out]))


@register
class MarkdownRenderer:
    """마크다운 문자열. 수업 결과를 문서로 남기거나 다른 곳에 붙일 때.

    화면이 아니라 텍스트를 돌려주는 렌더러 — 같은 View가 꼭 '보여주는 것'이
    될 필요는 없다는 예이기도 하다.
    """

    name = "markdown"

    def render(self, view: View, **options: Any) -> str:
        줄 = [f"# {view.title}", "", f"> 갈래: {view.branch} · 난이도: {view.dial}", ""]
        if view.failed:
            err = view.error or {}
            줄 += ["```", f"원인: {err.get('원인')}", f"위치: {err.get('위치')}",
                   f"힌트: {err.get('힌트')}", "```"]
            return "\n".join(줄)

        줄 += ["| 항목 | 그래프 |", "|---|---|"]
        # 값에 | 가 들어가면 표가 깨진다 (f-string 안에서는 역슬래시를 못 쓴다)
        막대기 = "\\|"
        줄 += [f"| {글.replace('|', 막대기)} | `{막대}` |" for 글, 막대 in view.rows()]

        if view.steps:
            from .trace import format_steps
            줄 += ["", "<details><summary>한 줄씩 따라가기</summary>", "", "```"]
            줄 += format_steps(view.steps)
            줄 += ["```", "", "</details>"]

        if view.dial == "바꾸기" and view.hint:
            줄 += ["", f"💡 {view.hint}"]
        elif view.dial == "만들기":
            if view.source:
                줄 += ["", "```python", view.source.rstrip(), "```"]
            if view.challenge:
                줄 += ["", f"🎯 {view.challenge}"]
        return "\n".join(줄)


@register
class BlocksRenderer:
    """블록 순서로. 블록코딩으로 배운 학습자가 파이썬으로 넘어올 때의 다리.

    오조봇·뚜루뚜루 같은 블록코딩에서 학습자가 보는 건 '순서대로 쌓인 명령'이다.
    파이썬도 결국 같은 일을 하는데, 화면에는 텍스트 덩어리로만 보인다.

    그런데 우리는 이미 `trace`로 실행 순서를 갖고 있다. 그걸 블록으로 세우면
    "블록에서 하던 그 순서가 여기서도 똑같이 일어난다"가 눈에 보인다.

    ※ trace=True 로 켠 수업에서만 블록이 나온다(순서를 알아야 세울 수 있으므로).
    """

    name = "blocks"

    def render(self, view: View, **options: Any) -> str:
        폭 = options.get("width", 44)
        위 = "┌" + "─" * 폭 + "┐"
        칸막이 = "├" + "─" * 폭 + "┤"
        아래 = "└" + "─" * 폭 + "┘"

        폭 = max(폭, 12)      # 너무 좁으면 자르기가 끝나지 않는다

        def 줄(글: str) -> str:
            # 박스 밖으로 삐져나가면 블록으로 안 보인다. 넘치면 자른다.
            글 = " " + 글
            while disp_width(글) > 폭 and len(글) > 1:
                글 = 글[:-2] + "…"
            return "│" + pad(글, 폭) + "│"

        출력 = [위, 줄("▶ 시작")]

        if not view.steps:
            출력 += [칸막이, 줄("(순서를 보려면 trace=True 로 켜주세요)")]
        else:
            보일것 = view.steps[:options.get("max_blocks", 12)]
            for i, s in enumerate(보일것, 1):
                출력.append(칸막이)
                본문 = s.code or f"{s.lineno}번째 줄"
                출력.append(줄(f"{i}. {본문}"))
                설명 = s.describe()
                if 설명:
                    출력.append(줄(f"     {설명}"))
            if len(view.steps) > len(보일것):
                출력 += [칸막이, 줄(f"… {len(view.steps) - len(보일것)}개 더")]

        출력 += [칸막이, 줄("■ 끝"), 아래]

        if view.dial == "만들기" and view.challenge:
            출력 += ["", f"★ 도전: {view.challenge}"]
        elif view.dial == "바꾸기" and view.hint:
            출력 += ["", f"💡 {view.hint}"]
        return "\n".join(출력)


@register
class WebappRenderer:
    """웹앱. 화면을 그리는 게 아니라 '그릴 streamlit 코드'를 생성한다.

    다른 두 렌더러와 성격이 다르다 — 여기서는 파이썬이 파이썬을 써낸다.
    학습자의 build 함수 소스를 그대로 심어서, 생성된 앱이 learnkit 없이도
    혼자 돌아가게 만든다(수업 자료를 그냥 파일 하나로 배포할 수 있게).
    """

    name = "webapp"

    def render(self, view: View, **options: Any) -> str:
        path = options.get("path", "lesson_app.py")
        if not view.build_name.isidentifier():
            raise ValueError(
                "webapp 렌더러는 이름 있는 함수(def)만 지원합니다. lambda 대신 def를 쓰세요."
            )
        code = self._code(view)
        # 돌아가지 않는 파일을 조용히 써놓지 않는다.
        # branches에 임의 객체가 들어가면 repr이 코드가 아니게 된다.
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(
                "웹앱 코드를 만들지 못했습니다. branches의 값이 글로 옮길 수 있는 "
                f"것인지 확인해 주세요(숫자·문자열·리스트 등). — {e.msg}"
            ) from None
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return path

    @staticmethod
    def _code(view: View) -> str:
        # bar()를 소스로 심지 않고 자족적인 형태로 다시 쓴다.
        # getsource로 퍼오면 그 함수가 기대는 것들(typing.Any, 모듈 레벨 정규식,
        # disp_width…)이 같이 안 따라와서 생성물이 실행 즉시 죽는다.
        return f'''# 자동 생성됨 — learnkit webapp 렌더러
# learnkit이 있으면 에러 튜터까지, 없으면 그대로 혼자 돌아갑니다.
#   streamlit run {"lesson_app.py"}
import math
import re
import unicodedata

import streamlit as st

BRANCHES = {view.branches!r}
HINT = {view.hint!r}
CHALLENGE = {view.challenge!r}
SOURCE = {(view.source or "")!r}
{view.source or ""}

_숫자 = re.compile(r"-?\\d+(?:\\.\\d+)?")


def _폭(text):
    """한글은 화면에서 2칸을 먹는다. (learnkit.renderers.disp_width 와 같은 규칙)"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def bar(line, cap=40):
    """줄에 담긴 숫자만큼 막대를 그린다. (learnkit.renderers.bar 와 같은 규칙)"""
    s = str(line)
    찾은 = _숫자.findall(s)
    if not 찾은:
        return "█" * min(_폭(s), cap)
    값 = float(찾은[-1])
    if not math.isfinite(값):
        return "█" * cap
    return "█" * min(max(round(값), 0), cap)


st.set_page_config(page_title={view.title!r})
st.markdown(
    "<style>html,body,[class*=css]{{font-size:{20 if view.big else 16}px}}</style>",
    unsafe_allow_html=True,
)
st.title({view.title!r})

branch = st.selectbox("갈래", list(BRANCHES))
dial = st.radio("난이도", {list(view.dials)!r}, horizontal=True)
raw = st.text_input("내 데이터 (쉼표로)", ", ".join(map(str, BRANCHES[branch])))
items = [s.strip() for s in raw.split(",") if s.strip()] if dial != "보기" else BRANCHES[branch]

try:
    for line in {view.build_name}(items):
        st.write(f"**{{line}}**", bar(line))
    if dial == "바꾸기" and HINT:
        st.info("힌트: " + HINT)
    if dial == "만들기":
        st.code(SOURCE, language="python")
        if CHALLENGE:
            st.warning("도전: " + CHALLENGE)
except Exception as e:
    # 학습자가 코드를 깨뜨리는 건 예상된 흐름 — 튜터가 받아준다
    try:
        from learnkit.error_tutor import explain
        정보 = explain(type(e), e, e.__traceback__)
        st.error("**원인** " + 정보["원인"])
        if 정보.get("코드"):
            st.code(정보["코드"], language="python")
        st.info("**힌트** " + 정보["힌트"])
    except ImportError:
        st.error(f"{{type(e).__name__}}: {{e}} — 입력을 확인해 보세요")
'''
