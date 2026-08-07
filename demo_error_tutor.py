"""
에러 튜터 데모 — 무서운 트레이스백을 '원인·위치·코드·힌트' 네 칸으로

실행:   python demo_error_tutor.py
        (예쁜 출력)  pip install rich
        (진짜 AI)    pip install anthropic && export ANTHROPIC_API_KEY=sk-...

API 키가 없어도 규칙 기반으로 항상 동작합니다. (발표 라이브에 안전)
"""
from learnkit import tutor

# ── 장면 1. 아직 만들지 않은 이름 ──────────────────────────────
print("① 좋아하는 과일을 출력해볼게요!")

with tutor(use_llm=False):
    print(과일)          # NameError — 아직 '과일'을 만들지 않았어요


# ── 장면 2. 오타 — 비슷한 이름을 찾아준다 ──────────────────────
print("\n② 이번엔 오타를 내볼게요. 튜터가 뭘 말해줄까요?")

with tutor(use_llm=False):
    공부시간 = [2, 4, 1, 3, 5]
    print(공부시감)      # NameError — '공부시간'의 오타


# ── 장면 3. 없는 기능 부르기 ───────────────────────────────────
print("\n③ 없는 기능을 불러볼게요.")

with tutor(use_llm=False):
    인사 = "안녕하세요"
    print(인사.uper())   # AttributeError — upper 의 오타


print("\n튜터는 with 블록 안에서만 켜졌다 꺼집니다. 전역은 그대로예요.")
