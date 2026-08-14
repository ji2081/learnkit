"""
python -m learnkit — 설치하고 바로 확인해보는 입구

    python -m learnkit              # 세 수준이 어떻게 다른지
    python -m learnkit tutor        # 에러 튜터
    python -m learnkit trace        # 한 줄씩 따라가기
    python -m learnkit ai           # AI가 켜져 있는지
    python -m learnkit new 내수업.py  # 내 수업 파일 뼈대 만들기

설치는 저장소에서 받으세요. PyPI의 `learnkit` 은 이름이 같은 다른 패키지입니다.

    git clone https://github.com/ji2081/learnkit.git
    cd learnkit && pip install -e ".[all]"

README를 읽기 전에 '무엇인지' 먼저 보이는 게 낫다고 생각해서 뒀다.
"""

from __future__ import annotations

import sys
import textwrap

from . import Learner, Lesson, __version__, tutor


def 공부기록(hours):
    """이번 주 공부 시간을 요일과 함께 정리한다.

    컴프리헨션 대신 for 문으로 쓴 이유 — '한 줄씩 따라가기'가 반복을 보여주려면
    반복이 밖으로 나와 있어야 한다. 컴프리헨션은 파이썬 3.11 이하에서
    별도 코드 객체라 안쪽이 추적되지 않는다.
    """
    days = ["월", "화", "수", "목", "금", "토", "일"]
    결과 = []
    for i, h in enumerate(hours):
        결과.append(f"{days[i % 7]} {h}시간")
    return 결과


def _예제() -> Lesson:
    return Lesson(
        title="이번 주 공부 시간",
        build=공부기록,
        branches={"이번 주": [2, 4, 1, 3, 5], "지난 주": [1, 2, 2, 4, 3]},
        hint="숫자를 네 실제 공부 시간으로 바꿔봐.",
        challenge="숫자 대신 '★'을 그 수만큼 붙여보자.",
    )


def 수준들() -> None:
    """같은 정의가 세 수준으로 펼쳐지는 모습."""
    lesson = _예제()
    for 수준 in (Learner.보기부터("처음 보는 사람"),
                Learner.바꿔보기("좀 해본 사람"),
                Learner.만들어보기("더 파고들 사람")):
        print(f"\n{'─' * 58}\n▶ {수준}\n{'─' * 58}")
        lesson.render_for(수준)
    print(f"\n{'─' * 58}")
    print("정의 1개 · 펼침 3가지 · 자료 제작 1회")


def 튜터() -> None:
    """에러를 친절한 한국어로 — 오타까지 찾아준다."""
    print("에러를 일부러 내봅니다.\n")
    with tutor(use_llm=False):
        공부시간 = [2, 4, 1, 3, 5]      # noqa: F841
        print(공부시감)  # type: ignore[name-defined]  # noqa: F821 — 일부러 낸 오타


def 따라가기() -> None:
    """코드가 한 줄씩 무슨 일을 하는지."""
    _예제().as_console(dial="보기", trace=True)


_뼈대 = '''"""내 수업 — learnkit"""
from learnkit import Learner, Lesson


def 만들기(items):
    """여기를 바꾸면 결과가 바뀝니다."""
    return [f"{i + 1}. {x}" for i, x in enumerate(items)]


lesson = Lesson(
    title="내 수업",
    build=만들기,
    branches={"기본": ["사과", "배", "감"]},
    hint="branches의 값을 네가 좋아하는 것들로 바꿔봐.",
    challenge="번호 대신 '⭐'를 붙여보자.",
)

if __name__ == "__main__":
    lesson.render_for(Learner.보기부터())
    lesson.render_for(Learner.만들어보기())
'''


def 새로만들기(path: str) -> None:
    """내 수업 파일 뼈대를 만들어준다."""
    try:
        with open(path, "x", encoding="utf-8") as f:
            f.write(_뼈대)
    except FileExistsError:
        print(f"'{path}' 가 이미 있어요. 다른 이름을 써주세요.")
        return
    print(f"만들었어요: {path}\n실행:  python {path}")


def 에이아이() -> None:
    """AI가 켜져 있는지 확인하고, 켜져 있으면 힌트를 만들어 본다."""
    from . import ai

    if not ai.available():
        print("AI 꺼짐 — 규칙 기반으로 동작 중입니다.\n")
        print("켜려면 키를 넣고 다시 실행해 주세요:")
        print("  export ANTHROPIC_API_KEY=sk-...     (macOS / Linux)")
        print("  setx ANTHROPIC_API_KEY sk-...       (Windows)")
        print("  pip install anthropic")
        print("\n키가 없어도 learnkit의 모든 기능은 그대로 동작합니다.")
        return

    print(f"AI 켜짐 ({ai.MODEL})\n")
    수업 = Lesson(title="이번 주 공부 시간", build=공부기록,
                 branches={"이번 주": [2, 4, 1, 3, 5]})
    print("힌트·도전 과제를 만들어 볼게요...\n")
    제안 = 수업.suggest()
    if 제안:
        print(f"  힌트     {제안.get('hint', '(없음)')}")
        print(f"  도전 과제 {제안.get('challenge', '(없음)')}")
    else:
        print("  받아오지 못했어요. 규칙 기반으로 계속됩니다.")


_명령 = {"levels": 수준들, "tutor": 튜터, "trace": 따라가기, "ai": 에이아이}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("-h", "--help", "help"):
        print(textwrap.dedent(__doc__ or ""))
        return 0
    if args and args[0] in ("-V", "--version"):
        print(f"learnkit {__version__}")
        return 0
    if args and args[0] == "new":
        새로만들기(args[1] if len(args) > 1 else "내수업.py")
        return 0

    이름 = args[0] if args else "levels"
    할일 = _명령.get(이름)
    if 할일 is None:
        print(f"'{이름}' 는 모르는 명령이에요. 쓸 수 있는 것: "
              f"{', '.join(_명령)}, new")
        return 1
    할일()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
