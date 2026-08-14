"""
Lesson — '한 번 정의 → 여러 형태로 렌더' 하는 작은 코어 (learnkit의 심장)

Lesson이 아는 것은 *무엇을 가르칠지*뿐이다. 화면은 모른다.
화면 그리는 일은 전부 renderers.py의 Renderer들이 맡는다.

  Lesson.to_view()  ─▶  View  ─▶  Renderer.render()

코어에 내장:
  · 난이도 다이얼 : 보기(관찰) → 바꾸기(내 데이터 + 힌트) → 만들기(코드 수정 + 도전과제)
  · 에러 튜터 연결 : 학습자가 build를 깨도 {원인·위치·힌트}로 받아줌
  · 접근성 : 다중 표현(글 + 막대그래프), 고대비, 큰 글씨, 읽어주기(TTS)
    ※ 스크린리더 ARIA·키보드 내비게이션은 아직 못 했다. (→ CONTRIBUTING의 열린 과제)
"""

from __future__ import annotations

import dataclasses
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from .error_tutor import explain
from . import renderers
from .learner import Learner
from .renderers import View


def _펼침(결과: Any) -> Any:
    """build가 제너레이터를 돌려주면 리스트로 펼친다.

    `yield`를 쓰는 건 학습자가 충분히 할 수 있는 일인데, 그대로 두면 화면에
    `<generator object ...>` 한 줄만 찍힌다. 결과가 안 보이는 게 이 도구가
    없애려던 문제라, 여기서 펼쳐 준다. 무한 제너레이터는 막지 못한다.
    """
    if hasattr(결과, "__next__") and not isinstance(결과, (list, tuple, str)):
        return list(결과)
    return 결과


def _default_build(items: list) -> list:
    """공통 뼈대 기본값: 리스트를 번호 매겨 보여주기 (반복 개념)."""
    return [f"{i + 1}. {x}" for i, x in enumerate(items)]


@dataclass
class Lesson:
    title: str
    build: Callable[[list], list] = _default_build
    branches: dict = field(default_factory=dict)
    dials: tuple = ("보기", "바꾸기", "만들기")
    hint: str = ""
    challenge: str = ""
    # 접근성은 나중에 붙이는 옵션이 아니라 기본값이다.
    # 나중에 붙이려고 하면 대개 안 붙이게 된다.
    big: bool = True
    high_contrast: bool = True
    speak: bool = False          # 소리는 교실 상황을 타므로 기본은 끔

    # ── 계산 ────────────────────────────────────────────────

    def run(self, branch: str | None = None, data: list | None = None):
        """수업을 한 번 실행한다. 반환은 (결과, 에러) 두 칸.

        에러를 던지지 않고 돌려주는 이유: 학습자가 build를 깨뜨리는 건
        '실패'가 아니라 예상된 흐름이라서. 튜터가 그 자리에서 받아준다.

        주의 — 이건 계산만 한다. 화면에 보여주려면 as_console(...) 등을 쓸 것.
        """
        items = data if data is not None else self.branches.get(branch, [])
        try:
            return _펼침(self.build(list(items))), None
        except Exception as e:
            return None, explain(type(e), e, e.__traceback__)

    def walk(self, branch: str | None = None, data: list | None = None):
        """수업을 한 줄씩 따라가며 실행한다. → (결과, [Step, ...])

        "왜 치는지 모를 때"를 위한 것. 입력과 결과 사이의 까만 구간을 연다.
        """
        from .trace import walk as _walk
        branch = branch or next(iter(self.branches), None)
        items = data if data is not None else self.branches.get(branch, [])
        return _walk(self.build, list(items))

    # ── AI 거들기 (키가 없으면 조용히 아무 일도 안 한다) ──────

    def suggest(self, 적용: bool = False) -> dict:
        """build 코드를 보고 힌트와 도전 과제를 만들어 준다.

            lesson.suggest()            # 제안만 받아보기
            lesson.suggest(적용=True)    # 비어 있는 항목에 바로 채우기

        자료를 만들 때 제일 손이 많이 가는 게 '좋은 힌트 쓰기'다. 코드는 금방
        쓰는데 "뭐라고 도와줘야 스스로 찾을까"는 오래 걸린다. 거기를 거든다.

        키가 없으면 빈 딕셔너리를 돌려준다 — 선생님이 직접 쓰면 된다.
        """
        from . import ai

        소스 = self._source()
        if not 소스 or not ai.available():
            return {}

        받음 = ai.ask(
            "아래는 학습자에게 보여줄 파이썬 수업 코드다.\n"
            "JSON으로만 답하라. 키는 정확히 hint, challenge 두 개.\n"
            "hint: '바꾸기' 단계에서 학습자가 데이터를 자기 것으로 바꿔보도록 권하는 한 문장.\n"
            "challenge: '만들기' 단계에서 코드를 직접 고쳐볼 도전 과제 한 문장.\n"
            "둘 다 반말로, 정답은 알려주지 말 것.\n\n"
            f"수업 제목: {self.title}\n"
            f"코드:\n{소스}",
            as_json=True,
        )
        if not isinstance(받음, dict):
            return {}

        제안 = {k: str(받음[k]).strip() for k in ("hint", "challenge") if k in 받음}
        if 적용:
            if 제안.get("hint") and not self.hint:
                self.hint = 제안["hint"]
            if 제안.get("challenge") and not self.challenge:
                self.challenge = 제안["challenge"]
        return 제안

    def review(self, 고친코드: str) -> str | None:
        """학습자가 '만들기' 단계에서 고친 코드를 말로 봐준다.

        에러 튜터는 '깨졌을 때'를 받아주지만, 돌아가는데 더 나아질 수 있는
        코드는 아무도 안 봐준다. 그 자리를 메운다.

        키가 없으면 None. (그러면 선생님이 보면 된다)
        """
        from . import ai

        return ai.ask(
            "학습자가 아래 원래 코드를 고쳤다. 고친 코드를 봐주고 2~3문장으로 답하라.\n"
            "먼저 잘한 점 하나를 짚고, 그다음 더 해볼 것 하나를 권하라.\n"
            "정답 코드는 쓰지 말고, 점수도 매기지 마라. 반말로.\n\n"
            f"[원래]\n{self._source() or ''}\n\n[고친 것]\n{고친코드}"
        )

    # ── 어디까지 펼칠지 ──────────────────────────────────────

    def to_view_for(self, learner: Learner, data: list | None = None) -> View:
        """정해진 만큼 펼친 화면 재료.

        Lesson의 값이 기본값이고, Learner가 채운 것만 덮어쓴다.
        (정의는 그대로 두고, 달라져야 하는 지점만 바뀐다.)
        """
        view = self.to_view(learner.branch, learner.dial, data, trace=learner.trace)
        고름 = lambda 학습자값, 기본값: 기본값 if 학습자값 is None else 학습자값
        return dataclasses.replace(
            view,
            big=고름(learner.big, self.big),
            high_contrast=고름(learner.high_contrast, self.high_contrast),
        )

    def render_for(self, learner: Learner, data: list | None = None, **options: Any):
        """정해진 만큼만 펼쳐서 낸다.

            lesson.render_for(Learner.보기부터())      # 결과만
            lesson.render_for(Learner.만들어보기())     # 코드까지

        정의 하나에서 펼침만 달라진다.
        """
        view = self.to_view_for(learner, data)
        result = renderers.get(learner.renderer).render(view, **options)
        말하기 = self.speak if learner.speak is None else learner.speak
        if view.result and 말하기:
            self._speak(" / ".join(map(str, view.result)), 켬=True)
        return result

    # ── 화면 재료 만들기 ────────────────────────────────────

    def to_view(self, branch: str | None = None, dial: str = "보기",
                data: list | None = None, trace: bool = False) -> View:
        """지금 상태를 렌더러가 그릴 수 있는 값(View)으로 굳힌다."""
        branch = branch or next(iter(self.branches), None)
        steps = None
        if trace:
            # 추적 실행이 결과도 같이 돌려주므로 build를 한 번만 부른다.
            # 두 번 부르면 파일을 쓰거나 카운터를 올리는 build에서 두 번 일어난다.
            try:
                result, steps = self.walk(branch, data)
                error = None
            except TypeError:
                steps = None        # lambda 등 따라갈 수 없는 build
                result, error = self.run(branch, data)
            except Exception as e:
                result, error = None, explain(type(e), e, e.__traceback__)
        else:
            result, error = self.run(branch, data)
        return View(
            steps=steps,
            title=self.title,
            dial=dial,
            branch=branch,
            result=result,
            error=error,
            hint=self.hint,
            challenge=self.challenge,
            source=self._source(),
            build_name=getattr(self.build, "__name__", "build"),
            branches=self.branches,
            dials=self.dials,
            big=self.big,
            high_contrast=self.high_contrast,
        )

    # ── 렌더 ────────────────────────────────────────────────

    def render(self, renderer: str = "console", branch: str | None = None,
               dial: str = "보기", data: list | None = None,
               trace: bool = False, **options: Any) -> Any:
        """이름으로 렌더러를 골라 그린다. 새 화면은 renderers.register()로 추가."""
        view = self.to_view(branch, dial, data, trace=trace)
        result = renderers.get(renderer).render(view, **options)
        if view.result:
            self._speak(" / ".join(map(str, view.result)))
        return result

    def as_console(self, branch: str | None = None, dial: str = "보기",
                   data: list | None = None, trace: bool = False):
        """터미널로. trace=True면 코드가 한 줄씩 무슨 일을 했는지도 보여준다."""
        return self.render("console", branch, dial, data, trace=trace)

    def as_widget(self):
        """주피터 위젯으로. 위젯을 만질 때마다 다시 계산되도록 콜백을 넘긴다."""
        def rerun(branch, dial, data):
            return self.to_view(branch, dial, data)
        return self.render("widget", rerun=rerun)

    def as_webapp(self, path: str = "lesson_app.py") -> str:
        """streamlit 앱 코드를 써낸다. 반환값은 생성된 파일 경로."""
        return self.render("webapp", path=path)

    # ── 내부 ────────────────────────────────────────────────

    @staticmethod
    def _as_bar(line) -> str:
        """(호환용) 막대 그리기는 renderers.bar로 옮겼다."""
        return renderers.bar(line)

    def _source(self) -> str | None:
        """학습자에게 보여줄 build 함수의 실제 소스. '만들기' 단계의 재료."""
        try:
            return inspect.getsource(self.build)
        except (OSError, TypeError):
            return None

    def _speak(self, text: str, 켬: bool | None = None):
        """읽어준다. 켬=None이면 Lesson의 기본값을 따른다.

        Learner가 speak=True로 켰는데 Lesson이 False면 안 읽어주던 버그가 있었다.
        누가 켰는지를 호출부가 정하고, 여기서는 시키는 대로만 한다.
        """
        if not (self.speak if 켬 is None else 켬):
            return
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.say(text)
            eng.runAndWait()
        except Exception:
            # TTS가 없거나 실패해도 수업은 계속돼야 한다
            print(f"[읽어주기] {text}")
