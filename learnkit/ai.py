"""
ai — 키가 있으면 더 똑똑해지고, 없으면 그대로 동작한다

learnkit의 규칙 하나: **AI는 있으면 좋은 것이지, 없으면 안 되는 것이 아니다.**
학교 컴퓨터에는 키를 넣을 수 없는 경우가 많고, 발표장에서 인터넷이 끊길 수도 있다.
그래서 이 모듈의 모든 함수는 키가 없으면 조용히 None을 돌려주고,
부르는 쪽은 그걸 받아 규칙 기반으로 물러난다.

키 넣는 법:

    export ANTHROPIC_API_KEY=sk-...        # macOS / Linux
    setx ANTHROPIC_API_KEY sk-...          # Windows

무엇이 똑똑해지나:

    · 에러 설명   — 규칙 19종 → 상황에 맞는 설명       (error_tutor.py)
    · 힌트·도전 과제 — 안 써도 build 코드를 보고 만들어 줌  (Lesson.suggest)
    · 코드 봐주기  — 학습자가 고친 코드에 말로 피드백      (Lesson.review)
"""

from __future__ import annotations

import json
import os
from typing import Any

__all__ = ["available", "ask", "MODEL"]

MODEL = "claude-3-5-haiku-latest"       # 빠르고 싸다. 수업 중에 기다리면 안 되니까.
_MAX_TOKENS = 500

_TUTOR = (
    "너는 파이썬 입문자를 돕는 다정한 한국어 튜터다.\n"
    "규칙: 쉬운 말로, 짧게. 정답 코드는 주지 말고 스스로 찾도록 힌트만.\n"
    "학습자를 평가하거나 점수 매기지 마라. 코드를 실행하지 마라."
)


def available() -> bool:
    """AI를 쓸 수 있는 상태인가. (키가 있고 라이브러리가 깔려 있나)"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def ask(prompt: str, *, as_json: bool = False, system: str = _TUTOR,
        max_tokens: int = _MAX_TOKENS) -> Any:
    """한 번 물어본다. 키가 없거나 실패하면 None.

    None을 돌려주는 게 이 함수의 계약이다. 부르는 쪽은 반드시
    "None이면 규칙 기반으로" 를 준비해둬야 한다.
    """
    if not available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        r = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        블록 = r.content[0]
        text = getattr(블록, "text", "").strip()
        if not text:
            return None
        if not as_json:
            return text
        # 모델이 앞뒤에 말을 붙여도 JSON 부분만 뽑는다
        시작, 끝 = text.find("{"), text.rfind("}")
        if 시작 == -1 or 끝 == -1:
            return None
        return json.loads(text[시작:끝 + 1])
    except Exception:
        return None      # 네트워크·한도·형식 무엇이 터져도 수업은 계속돼야 한다
