"""데모 (콘솔) — 수업을 한 번 정의 → 콘솔 3단계 렌더 + 웹앱 코드 생성."""
from learnkit import Lesson


def 공부기록(hours):
    days = ["월", "화", "수", "목", "금", "토", "일"]
    return [f"{days[i % 7]} {h}" for i, h in enumerate(hours)]


lesson = Lesson(
    title="이번 주 공부 시간 (막대그래프)",
    build=공부기록,
    branches={"이번 주": [2, 4, 1, 3, 5], "지난 주": [1, 2, 2, 4, 3]},
    hint="숫자를 네 실제 공부 시간으로 바꿔봐.",
    challenge="숫자 대신 '★'을 그 수만큼 붙여서 그려보자.",
    big=True, high_contrast=True,
)

if __name__ == "__main__":
    # ① 왜 치는지 모를 때 — 한 줄씩 따라가며 결과부터 눈으로
    lesson.as_console(branch="이번 주", dial="보기", trace=True)

    # ② 내 데이터로 바꿔보기 (힌트가 붙는다)
    lesson.as_console(branch="이번 주", dial="바꾸기", data=[3, 5, 2])

    # ③ 코드를 열고 도전 과제로
    lesson.as_console(branch="이번 주", dial="만들기")

    print("\n웹앱 코드 생성됨:", lesson.as_webapp("lesson_app.py"))
