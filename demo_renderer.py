"""
데모 — 새 화면을 직접 붙여보기 (learnkit의 확장점)

learnkit을 고치지 않고 렌더러를 하나 추가한다. 필요한 건 두 가지뿐:

    name: str
    def render(self, view, **options)

상속도, 등록 절차도 없다. 모양만 맞으면 그것은 이미 렌더러다(Protocol).
수업 환경이 특이해도(전자칠판, 점자 단말기, 슬랙 봇…) 각자 붙일 수 있게 하려는 의도다.

여기서는 '프린트해서 나눠줄 종이 워크시트'를 만들어본다.
학교에는 컴퓨터를 못 쓰는 시간도 있고, 화면을 오래 못 보는 학생도 있다.

실행:  python demo_renderer.py
"""
from learnkit import Learner, Lesson, register, renderers
from learnkit.renderers import pad


@register
class 워크시트렌더러:
    """종이로 나눠줄 워크시트. 막대는 네모칸으로, 답은 빈칸으로."""

    name = "worksheet"

    def render(self, view, **options):
        빈칸 = options.get("빈칸", True)      # 숫자를 가리고 직접 채우게 할지
        폭 = 46
        # 한글은 화면에서 2칸을 먹는다. pad()가 그걸 맞춰준다.
        칸 = lambda 글, 정렬="<": pad(글, 폭, 정렬)

        줄 = ["┌" + "─" * 폭 + "┐",
              "│" + 칸(view.title, "^") + "│",
              "│" + 칸(" 이름: ______________   날짜: ____ / ____") + "│",
              "├" + "─" * 폭 + "┤"]

        for 글, 막대 in view.rows():
            보일막대 = "□" * len(막대) if 빈칸 else 막대
            줄.append("│" + 칸(f" {pad(글, 10)}{보일막대}") + "│")

        줄.append("├" + "─" * 폭 + "┤")
        물음 = view.hint or view.challenge or "무엇을 알 수 있나요?"
        줄.append("│" + 칸(f" Q. {물음}") + "│")
        줄.append("│" + 칸(" " + "_" * (폭 - 3)) + "│")
        줄.append("└" + "─" * 폭 + "┘")
        return "\n".join(줄)


def 공부기록(hours):
    days = ["월", "화", "수", "목", "금", "토", "일"]
    return [f"{days[i % 7]} {h}" for i, h in enumerate(hours)]


lesson = Lesson(
    title="이번 주 공부 시간",
    build=공부기록,
    branches={"이번 주": [2, 4, 1, 3, 5]},
    hint="가장 많이 공부한 날은 언제인가요?",
    challenge="숫자 대신 '★'을 그 수만큼 붙여보자.",
)

if __name__ == "__main__":
    print("등록된 렌더러:", ", ".join(renderers.available()))

    print("\n[ 종이 워크시트 — 빈칸 ]")
    print(lesson.render("worksheet", branch="이번 주", dial="바꾸기"))

    print("\n[ 같은 정의를 마크다운으로 ]")
    print(lesson.render("markdown", branch="이번 주", dial="만들기"))

    print("\n[ 펼침 값으로도 고를 수 있다 ]")
    print(lesson.render_for(Learner(dial="바꾸기", renderer="worksheet")))
