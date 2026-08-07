"""
learnkit — 모두를 위한 파이썬 학습 도구 모음 (만들어가는 중)

플랫폼이 아니라, 어떤 파이썬 자료에든 '흥미와 난이도 다이얼'을 끼워 넣는 작은 라이브러리.

핵심:
  · Lesson      : 수업을 한 번 정의 → 콘솔/위젯/웹앱으로 렌더
  · renderers   : '어떻게 보여줄지'의 확장점 (Protocol — 새 화면을 붙일 수 있음)
  · error_tutor : 무서운 에러를 '친절한 한국어'로

설계 철학: '난이도 다이얼'(보기→바꾸기→만들기)로 특수학급~대학을 한 정의로 품는다.
접근성: 다중 표현(글·그림·소리)·읽어주기·고대비·큰 글씨가 코어에 내장.
"""

__version__ = "0.1.0"

from . import ai                       # noqa: F401
from . import error_tutor              # noqa: F401
from . import renderers                # noqa: F401
from . import trace                    # noqa: F401
from .error_tutor import install, uninstall, tutor, register_rule   # noqa: F401
from .learner import Learner           # noqa: F401
from .lesson import Lesson             # noqa: F401
from .renderers import Renderer, View, register   # noqa: F401
from .trace import Step, walk          # noqa: F401

__all__ = [
    "Lesson",
    "Learner",
    "Renderer",
    "View",
    "Step",
    "register",
    "walk",
    "renderers",
    "error_tutor",
    "trace",
    "ai",
    "install",
    "uninstall",
    "tutor",
    "register_rule",
]
