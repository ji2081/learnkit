"""
learner — 같은 자료가 '어디까지 펼쳐질지'

하나의 자료는 여러 수준의 사람을 만난다.
처음 보는 사람에게 맞추면 아는 사람이 지루해하고,
아는 사람에게 맞추면 처음인 사람이 첫 줄에서 멈춘다.
가운데를 잡으면 양쪽 다 놓친다.

교실에서 겪은 일이지만 교실만의 문제는 아니다 —
README도, 온보딩 문서도, 튜토리얼도 같은 자리에 선다.

그래서 자료를 여러 벌로 나누는 대신, **펼쳐지는 정도**를 값으로 뺐다.

    Lesson   = 무엇을 다룰지 (한 번만 정의)
    Learner  = 어디까지 펼칠지 (받는 쪽에 따라)

같은 정의가 그대로 있고, 펼침만 달라진다.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

__all__ = ["Learner"]


@dataclass(frozen=True)
class Learner:
    """자료를 어디까지 펼칠지.

        처음 = Learner("처음 보는 사람", dial="보기", big=True, high_contrast=True)
        깊게 = Learner("더 파고들 사람", dial="만들기")

        lesson.render_for(처음)
        lesson.render_for(깊게)

    비워둔 항목은 Lesson의 값을 그대로 따른다. 달라져야 하는 것만 적으면 된다.
    """

    name: str = ""

    # 어디까지 펼칠지
    dial: str = "보기"
    branch: str | None = None

    # 어떤 화면으로
    renderer: str = "console"
    big: bool | None = None
    high_contrast: bool | None = None
    speak: bool | None = None

    # 중간 과정을 보여줄지
    trace: bool = False

    note: str = ""          # 메모 (화면에는 안 나온다)

    # ── 반복해서 쓰게 된 조합 세 가지 ─────────────────────────

    @classmethod
    def 보기부터(cls, name: str = "", **kwargs: Any) -> "Learner":
        """결과부터 눈으로. 큰 글씨·고대비, 중간 과정도 펼쳐서."""
        return replace(
            cls(name, dial="보기", big=True, high_contrast=True,
                speak=True, trace=True),
            **kwargs,
        )

    @classmethod
    def 바꿔보기(cls, name: str = "", **kwargs: Any) -> "Learner":
        """데이터를 자기 것으로 바꿔보며. 힌트가 붙는다.

        접근성은 그대로 켜둔다 — 단계가 올라간다고 큰 글씨가 필요 없어지지 않는다.
        """
        return replace(cls(name, dial="바꾸기", big=True, high_contrast=True), **kwargs)

    @classmethod
    def 만들어보기(cls, name: str = "", **kwargs: Any) -> "Learner":
        """코드를 열고 도전 과제로. 여기서부터는 개발자의 세계다."""
        return replace(
            cls(name, dial="만들기", big=True, high_contrast=True, trace=True), **kwargs
        )

    # ── 조정 ────────────────────────────────────────────────

    def 더(self, **kwargs: Any) -> "Learner":
        """일부만 바꾼 새 값. 원본은 그대로 둔다.

            기본 = Learner.보기부터()
            소리끔 = 기본.더(speak=False)
        """
        return replace(self, **kwargs)

    def __str__(self) -> str:
        표시 = [self.dial]
        if self.big:
            표시.append("큰 글씨")
        if self.high_contrast:
            표시.append("고대비")
        if self.speak:
            표시.append("읽어주기")
        if self.trace:
            표시.append("따라가기")
        이름 = self.name or "이름 없음"
        return f"{이름} ({' · '.join(표시)})"
