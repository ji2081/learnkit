"""learnkit 기본 동작 테스트."""
import ast
import sys

import pytest

from learnkit import Learner, Lesson, renderers
from learnkit.error_tutor import explain, install, uninstall, tutor, register_rule, _RULES
from learnkit.renderers import Renderer, View, bar, disp_width, pad
from learnkit.trace import Step, format_steps, walk


def 번호매기기(items):
    return [f"{i + 1}. {x}" for i, x in enumerate(items)]


# ── Lesson 핵심 ──────────────────────────────────────────────

def test_run_정상():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x", "y"]})
    result, err = lesson.run("a")
    assert err is None
    assert result == ["1. x", "2. y"]


def test_run_에러를_튜터가_받음():
    lesson = Lesson(title="t", build=lambda items: [1 / 0], branches={"a": ["x"]})
    result, err = lesson.run("a")
    assert result is None
    assert err["원인"] and err["힌트"]


def test_to_view_렌더_재료를_다_담는다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]},
                    hint="h", challenge="c", big=True)
    view = lesson.to_view("a", dial="만들기")
    assert isinstance(view, View)
    assert view.title == "t" and view.dial == "만들기"
    assert view.build_name == "번호매기기"
    assert view.hint == "h" and view.challenge == "c" and view.big
    assert "번호매기기" in (view.source or "")
    assert not view.failed


def test_view_rows_는_글과_막대_쌍():
    view = Lesson(title="t", build=lambda x: ["월 2"], branches={"a": [1]}).to_view("a")
    assert view.rows() == [("월 2", "██")]


# ── 막대 그리기: 학습자가 아무 값이나 넣어도 안전해야 함 ──────────

@pytest.mark.parametrize("line, expected", [
    ("월 2", 2),        # 정수
    ("금 5", 5),        # 정수
    ("목 -3", 0),       # 음수는 막대 없음
    ("수 2.5", 2),      # 소수는 반올림
    ("토 100", 40),     # 상한 40
    ("일 0", 0),
    ("월 2시간", 2),     # 숫자가 글자에 붙어 있어도
    ("용돈 1000원", 40),
    ("3번 봤어요", 3),
])
def test_bar_숫자를_정확히_반영(line, expected):
    assert len(bar(line)) == expected
    assert len(Lesson._as_bar(line)) == expected   # 호환 경로도 같은 결과


def test_bar_는_값이_다르면_길이도_달라야_한다():
    """'월 2시간'과 '금 5시간'이 같은 길이로 보이면 그림이 거짓말을 하는 것."""
    줄 = ["월 2시간", "화 4시간", "수 1시간", "목 3시간", "금 5시간"]
    길이 = [len(bar(x)) for x in 줄]
    assert 길이 == [2, 4, 1, 3, 5]
    assert len(set(길이)) == len(길이)      # 전부 달라야 한다


def test_bar_숫자없으면_글자폭():
    assert len(bar("사과")) == 4          # 한글 2글자 = 화면 4칸
    assert len(bar("ab")) == 2


# ── 한글 폭 맞추기 (텍스트 렌더러를 만들면 반드시 만나는 문제) ──

def test_disp_width_는_한글을_두_칸으로_센다():
    assert disp_width("abc") == 3
    assert disp_width("사과") == 4           # len()은 2지만 화면은 4칸
    assert disp_width("월 2") == 4           # 월(2) + 공백(1) + 2(1)


def test_pad_로_표가_어긋나지_않는다():
    줄 = [pad("월", 10) + "|", pad("가나다", 10) + "|", pad("ab", 10) + "|"]
    assert len({disp_width(l) for l in 줄}) == 1      # 오른쪽 선이 한 줄로 맞는다


def test_pad_정렬():
    assert pad("가", 6, "^") == "  가  "
    assert pad("가", 6, ">") == "    가"


# ── 렌더러 확장점 ────────────────────────────────────────────

def test_기본_렌더러가_등록되어_있다():
    assert {"console", "widget", "webapp", "markdown", "blocks"} <= set(
        renderers.available())


def test_blocks_는_실행_순서를_블록으로_세운다():
    """블록코딩으로 배운 학습자가 파이썬으로 넘어올 때의 다리."""
    def 계단(hours):
        총합 = 0
        결과 = []
        for h in hours:
            총합 += h
            결과.append(f"{h}시간 (누적 {총합})")
        return 결과

    lesson = Lesson(title="t", build=계단, branches={"a": [1, 2]},
                    challenge="별을 붙여보자")
    글 = lesson.render("blocks", branch="a", dial="만들기", trace=True)
    assert "▶ 시작" in 글 and "■ 끝" in 글
    assert "총합" in 글                      # 값의 변화가 블록 안에
    assert "1." in 글 and "2." in 글         # 순서가 매겨진다
    assert "별을 붙여보자" in 글


def test_blocks_는_trace가_꺼져있으면_알려준다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    글 = lesson.render("blocks", branch="a")
    assert "trace=True" in 글


def test_blocks_박스가_어긋나지_않는다():
    """한글이 섞여도 오른쪽 선이 한 줄로 맞아야 한다."""
    lesson = Lesson(title="t", build=번호매기기,
                    branches={"a": ["사과", "배"]})
    글 = lesson.render("blocks", branch="a", trace=True)
    테두리 = [l for l in 글.split("\n") if l.startswith(("┌", "├", "└", "│"))]
    assert len({disp_width(l) for l in 테두리}) == 1


def test_markdown_렌더러는_문자열을_돌려준다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["사과"]},
                    challenge="별을 붙여보자")
    md = lesson.render("markdown", branch="a", dial="만들기")
    assert md.startswith("# t")
    assert "| 1. 사과 |" in md
    assert "번호매기기" in md          # 만들기 단계라 소스가 들어간다
    assert "별을 붙여보자" in md


def test_새_렌더러를_붙일_수_있다():
    """기여자가 화면을 추가하는 경로 — 상속 없이 모양만 맞추면 된다."""
    받은 = {}

    @renderers.register
    class 조용한렌더러:
        name = "_test_quiet"

        def render(self, view, **options):
            받은["title"] = view.title
            return "그렸음"

    assert isinstance(조용한렌더러(), Renderer)      # Protocol 구조적 검사
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    assert lesson.render("_test_quiet", branch="a") == "그렸음"
    assert 받은["title"] == "t"


def test_모양이_안_맞으면_등록을_거부한다():
    with pytest.raises(TypeError):
        renderers.register(type("엉터리", (), {"name": "_test_bad"}))


def test_없는_렌더러는_쓸_수_있는_목록을_알려준다():
    with pytest.raises(KeyError, match="console"):
        renderers.get("존재하지않음")


# ── 웹앱 코드 생성 ───────────────────────────────────────────

def test_as_webapp_유효한_코드_생성(tmp_path):
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    path = tmp_path / "app.py"
    lesson.as_webapp(str(path))
    assert path.exists()
    소스 = path.read_text(encoding="utf-8")
    ast.parse(소스)
    assert "번호매기기" in 소스          # 학습자 코드가 심겨 있다
    assert "learnkit" not in 소스.split("\n")[2:][0]   # 생성물은 혼자 돌아간다


def test_생성된_웹앱이_실제로_실행된다(tmp_path):
    """문법만 맞으면 안 된다. streamlit을 가짜로 끼워 끝까지 돌려본다.

    getsource로 함수를 퍼오면 그 함수가 기대는 것들(typing.Any, 모듈 레벨
    정규식 등)이 같이 안 따라와서 생성물이 실행 즉시 죽는 버그가 있었다.
    ast.parse만 하는 테스트로는 못 잡는다.
    """
    import subprocess
    import sys as _sys
    import textwrap

    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["사과", "배"]},
                    hint="힌트", challenge="도전")
    앱 = tmp_path / "app.py"
    lesson.as_webapp(str(앱))

    러너 = tmp_path / "run.py"
    러너.write_text(textwrap.dedent(f'''
        import sys, types
        st = types.ModuleType("streamlit")
        st.set_page_config = st.markdown = st.title = lambda *a, **k: None
        st.write = st.info = st.code = st.warning = st.error = lambda *a, **k: None
        st.selectbox = lambda label, opts: list(opts)[0]
        st.radio = lambda label, opts, **k: opts[0]
        st.text_input = lambda label, default: default
        sys.modules["streamlit"] = st
        exec(open(r"{앱}", encoding="utf-8").read())
        print("OK")
    '''), encoding="utf-8")

    결과 = subprocess.run([_sys.executable, str(러너)], capture_output=True, text=True)
    assert 결과.returncode == 0, 결과.stderr
    assert "OK" in 결과.stdout


def test_생성된_웹앱이_에러튜터를_붙인다(tmp_path):
    """세 화면 모두에서 튜터가 받아줘야 '한 정의'라는 말이 성립한다."""
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    path = tmp_path / "app.py"
    lesson.as_webapp(str(path))
    소스 = path.read_text(encoding="utf-8")
    assert "from learnkit.error_tutor import explain" in 소스
    assert "except ImportError" in 소스          # 없어도 앱은 돌아간다


def test_as_webapp_lambda_거부(tmp_path):
    lesson = Lesson(title="t", build=lambda items: items, branches={"a": ["x"]})
    with pytest.raises(ValueError):
        lesson.as_webapp(str(tmp_path / "app.py"))


# ── 에러 튜터 ────────────────────────────────────────────────

def test_explain_구조화_출력():
    try:
        raise NameError("name 'x' is not defined")
    except NameError as e:
        info = explain(type(e), e, e.__traceback__)
    assert {"원인", "위치", "코드", "힌트"}.issubset(info)


def test_explain_메시지에서_이름_추출():
    try:
        raise NameError("name '과일' is not defined")
    except NameError as e:
        info = explain(type(e), e, e.__traceback__)
    assert "과일" in info["힌트"]


def test_explain_문제가_난_코드줄을_인용한다():
    try:
        보이는_변수 = 1 / 0          # noqa: F841
    except ZeroDivisionError as e:
        info = explain(type(e), e, e.__traceback__)
    assert "보이는_변수" in info["코드"]


def test_오타를_찾아_추천한다():
    """difflib으로 실제 스코프의 이름 중 비슷한 걸 제안."""
    공부시간 = [1, 2, 3]            # noqa: F841
    try:
        print(공부시감)              # noqa: F821  — 일부러 오타
    except NameError as e:
        info = explain(type(e), e, e.__traceback__)
    assert "공부시간" in info["힌트"]


def test_속성_오타도_추천한다():
    try:
        "안녕".uper()               # upper 오타
    except AttributeError as e:
        info = explain(type(e), e, e.__traceback__)
    assert "upper" in info["힌트"]


def test_속성_오타_추천은_3_9에서도_된다():
    """`AttributeError.obj`는 파이썬 3.10에서 생겼다.

    3.9에는 없어서 후보 목록이 비었고, 추천이 조용히 사라졌다.
    CI의 3.9 작업에서만 이 테스트가 깨져 알게 됐다.
    """
    try:
        "안녕".uper()
    except AttributeError as e:
        try:
            del e.obj               # 3.9 인 척한다
        except AttributeError:
            pass                    # 이미 3.9 라면 지울 것도 없다
        info = explain(type(e), e, e.__traceback__)
    assert "upper" in info["힌트"]


def test_모듈_속성_오타도_추천한다():
    import math
    try:
        math.sqrtt(4)
    except AttributeError as e:
        info = explain(type(e), e, e.__traceback__)
    assert "sqrt" in info["힌트"]


def test_register_rule_로_설명을_추가할_수_있다():
    register_rule("_TestError", "테스트용 원인", "테스트용 힌트")
    assert _RULES["_TestError"] == ("테스트용 원인", "테스트용 힌트")
    _RULES.pop("_TestError")


# ── 켜고 끄기 ────────────────────────────────────────────────

def test_install_후_uninstall하면_원래_훅으로_돌아온다():
    원래 = sys.excepthook
    install(use_llm=False)
    assert sys.excepthook is not 원래
    uninstall()
    assert sys.excepthook is 원래


def test_컨텍스트매니저는_전역을_오염시키지_않는다():
    원래 = sys.excepthook
    with tutor(use_llm=False):
        assert sys.excepthook is not 원래
    assert sys.excepthook is 원래


def test_컨텍스트매니저가_에러를_삼키고_설명한다(capsys):
    with tutor(use_llm=False):
        raise NameError("name '과일' is not defined")
    출력 = capsys.readouterr().out
    assert "튜터" in 출력 and "과일" in 출력


# ── 정의는 한 번, 펼침은 여러 가지 ───────────────────────────
#
# 하나의 자료가 여러 수준을 만나면 쉽게 아무에게도 안 맞는 평균이 된다.
# 그래서 정의는 한 번만 하고(Lesson), 펼쳐지는 정도만 값으로 뺐다(Learner).
# 아래 테스트들이 그게 실제로 성립하는지 확인한다.

def test_한_정의가_수준마다_다른_화면을_낸다():
    lesson = Lesson(title="t", build=번호매기기,
                    branches={"인문": ["책", "영화"], "숫자": ["용돈 1000"]},
                    hint="바꿔봐", challenge="만들어봐")

    처음 = Learner.보기부터("처음", branch="인문")
    깊게 = Learner.만들어보기("깊게", branch="숫자")

    v1, v2 = lesson.to_view_for(처음), lesson.to_view_for(깊게)

    assert v1.dial == "보기" and v2.dial == "만들기"
    assert v1.branch == "인문" and v2.branch == "숫자"
    assert v1.result == ["1. 책", "2. 영화"]
    assert v2.result == ["1. 용돈 1000"]
    assert v1.steps and v2.steps                # 둘 다 '따라가기'가 켜진 값
    assert v2.source and not v1.source is None  # '만들기'는 소스를 본다


def test_접근성은_모든_수준에서_켜져_있다():
    """단계가 올라간다고 큰 글씨가 필요 없어지지 않는다.

    예전에는 '보기부터' 프리셋에서만 켜져서, 특수학급 학생이 '바꾸기'로
    넘어가는 순간 큰 글씨와 고대비가 사라졌다.
    """
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    assert lesson.big and lesson.high_contrast          # 정의의 기본값부터 켜짐

    for 프리셋 in (Learner.보기부터(), Learner.바꿔보기(), Learner.만들어보기()):
        v = lesson.to_view_for(프리셋)
        assert v.big, f"{프리셋.dial} 단계에서 큰 글씨가 꺼졌다"
        assert v.high_contrast, f"{프리셋.dial} 단계에서 고대비가 꺼졌다"


def test_필요하면_끌_수도_있다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    v = lesson.to_view_for(Learner("끔", big=False))
    assert not v.big and v.high_contrast     # 지정한 것만 꺼진다


def test_비워둔_항목은_정의의_기본값을_따른다():
    """정의는 그대로 두고, 달라져야 하는 것만 덮어쓴다."""
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]},
                    big=True, high_contrast=True)

    그대로 = lesson.to_view_for(Learner("기본"))
    assert 그대로.big and 그대로.high_contrast          # 정의의 기본값 상속

    끔 = lesson.to_view_for(Learner("큰글씨끔", big=False))
    assert not 끔.big and 끔.high_contrast              # 지정한 것만 덮어씀


def test_펼침_세_가지_조합():
    assert Learner.보기부터().dial == "보기"
    assert Learner.보기부터().speak
    assert Learner.바꿔보기().dial == "바꾸기"
    assert Learner.만들어보기().dial == "만들기"
    assert Learner.만들어보기().trace


def test_더_는_원본을_건드리지_않는다():
    원본 = Learner.보기부터("처음")
    조정 = 원본.더(speak=False)
    assert 원본.speak and not 조정.speak
    assert 조정.name == "처음" and 조정.big


def test_렌더러도_고를_수_있다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["사과"]})
    md = lesson.render_for(Learner("문서로", renderer="markdown"))
    assert isinstance(md, str) and "사과" in md


def test_한_정의로_세_수준을_돌린다(capsys):
    lesson = Lesson(title="이번 주", build=번호매기기, branches={"a": ["사과", "배"]})
    수준 = [Learner.보기부터(), Learner.바꿔보기(), Learner.만들어보기()]
    for 수준값 in 수준:
        lesson.render_for(수준값)
    out = capsys.readouterr().out
    assert out.count("이번 주") == 3          # 정의는 하나, 화면은 셋


def test_학습자가_켠_읽어주기가_실제로_동작한다(capsys):
    """Lesson이 speak=False여도, 이 수준에서 켰으면 읽어줘야 한다."""
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["사과"]}, speak=False)
    lesson.render_for(Learner("소리켬", speak=True))
    assert "[읽어주기]" in capsys.readouterr().out    # pyttsx3 없으면 텍스트로 대체


def test_아무도_안_켰으면_안_읽는다(capsys):
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["사과"]}, speak=False)
    lesson.render_for(Learner("조용히"))
    assert "[읽어주기]" not in capsys.readouterr().out


def test_표시가_읽을_수_있다():
    assert "처음" in str(Learner.보기부터("처음"))
    assert "큰 글씨" in str(Learner.보기부터("처음"))


# ── AI (키가 없어도 절대 안 깨져야 한다) ─────────────────────

def test_키가_없으면_ai가_꺼진_상태(monkeypatch):
    from learnkit import ai
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ai.available() is False
    assert ai.ask("아무거나") is None


def test_ai가_꺼져도_suggest는_조용히_비어있다(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    assert lesson.suggest() == {}
    assert lesson.suggest(적용=True) == {}
    assert lesson.hint == "" and lesson.challenge == ""   # 아무것도 안 건드림


def test_ai가_꺼져도_review는_None(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    assert lesson.review("def 번호매기기(items): return items") is None


def test_suggest_적용은_비어있는_항목만_채운다(monkeypatch):
    """선생님이 쓴 힌트를 AI가 덮어쓰면 안 된다."""
    from learnkit import ai
    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "ask",
                        lambda *a, **k: {"hint": "AI힌트", "challenge": "AI도전"})

    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]},
                    hint="선생님이 쓴 힌트")
    제안 = lesson.suggest(적용=True)
    assert 제안 == {"hint": "AI힌트", "challenge": "AI도전"}
    assert lesson.hint == "선생님이 쓴 힌트"      # 있던 건 그대로
    assert lesson.challenge == "AI도전"          # 비어 있던 것만 채움


def test_ai가_이상한_걸_줘도_안_깨진다(monkeypatch):
    from learnkit import ai
    monkeypatch.setattr(ai, "available", lambda: True)
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["x"]})
    for 응답 in (None, "문자열", {"엉뚱한키": 1}, []):
        monkeypatch.setattr(ai, "ask", lambda *a, _r=응답, **k: _r)
        assert isinstance(lesson.suggest(), dict)


def test_에러튜터는_ai가_없으면_규칙으로_간다(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        raise NameError("name '과일' is not defined")
    except NameError as e:
        info = explain(type(e), e, e.__traceback__)
    assert info["_출처"] == "규칙"
    assert "과일" in info["힌트"]


# ── python -m learnkit (설치하고 바로 확인하는 입구) ──────────

def test_명령들이_전부_동작한다(capsys):
    from learnkit.__main__ import main
    for 이름 in ("levels", "tutor", "trace", "ai"):
        assert main([이름]) == 0
        assert capsys.readouterr().out.strip()


def test_ai_명령은_키가_없으면_넣는_법을_알려준다(capsys, monkeypatch):
    from learnkit.__main__ import main
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    main(["ai"])
    출력 = capsys.readouterr().out
    assert "ANTHROPIC_API_KEY" in 출력
    assert "그대로 동작" in 출력          # 없어도 된다는 걸 분명히


def test_모르는_명령은_쓸_수_있는_걸_알려준다(capsys):
    from learnkit.__main__ import main
    assert main(["없는명령"]) == 1
    assert "levels" in capsys.readouterr().out


def test_new_는_실행되는_뼈대를_만든다(tmp_path, capsys):
    """문법만 맞으면 안 된다 — 실제로 돌아가야 한다."""
    import subprocess
    import sys as _sys

    from learnkit.__main__ import main

    파일 = tmp_path / "내수업.py"
    main(["new", str(파일)])
    assert 파일.exists()
    ast.parse(파일.read_text(encoding="utf-8"))

    돌린결과 = subprocess.run([_sys.executable, str(파일)],
                          capture_output=True, text=True)
    assert 돌린결과.returncode == 0, 돌린결과.stderr
    assert "사과" in 돌린결과.stdout

    main(["new", str(파일)])                          # 덮어쓰지 않는다
    assert "이미 있어요" in capsys.readouterr().out


# ── 한 줄씩 따라가기 (①"왜 치는지 모를 때") ──────────────────

def 계단(hours):
    총합 = 0
    결과 = []
    for h in hours:
        총합 += h
        결과.append(f"{h}시간 (누적 {총합})")
    return 결과


def test_walk_결과는_그대로_돌려준다():
    result, steps = walk(계단, [1, 2])
    assert result == ["1시간 (누적 1)", "2시간 (누적 3)"]
    assert steps and all(isinstance(s, Step) for s in steps)


def test_walk_변수가_바뀐_것을_잡아낸다():
    _, steps = walk(계단, [1, 2])
    바뀐이름 = {k for s in steps for k in s.changed}
    assert {"총합", "결과", "h"} <= 바뀐이름


def test_walk_는_그때_값을_남긴다_최종값이_아니라():
    """리스트를 append로 채우면, 각 단계에 '그때까지의 리스트'가 남아야 한다.

    f_locals는 살아있는 객체를 담고 있어서, 그대로 들고 있으면 나중에 출력할 때
    전부 최종값으로 보인다. 실제로 그랬던 버그가 있었다.
    """
    _, steps = walk(계단, [1, 2])
    결과기록 = [s.changed["결과"] for s in steps if "결과" in s.changed]

    assert 결과기록[0] == "[]"                    # 처음엔 비어 있어야 하고
    assert len(set(결과기록)) > 1                 # 단계마다 달라야 한다
    assert "누적 1" in 결과기록[-1]               # 마지막엔 채워져 있어야 한다


def test_walk_마지막은_반환값():
    _, steps = walk(계단, [1])
    assert steps[-1].is_return
    assert steps[-1].returned == ["1시간 (누적 1)"]
    assert "결과" in steps[-1].describe() or "→ 결과" in steps[-1].describe()


def test_walk_는_트레이스를_원래대로_돌려놓는다():
    이전 = sys.gettrace()
    walk(계단, [1])
    assert sys.gettrace() is 이전


def test_walk_는_함수_바깥까지_따라가지_않는다():
    """학습자가 보고 싶은 건 자기 줄뿐. 파이썬 내부로 파고들면 안 된다."""
    _, steps = walk(계단, [1, 2, 3])
    파일들 = {s.code for s in steps}
    assert all("site-packages" not in c for c in 파일들)
    assert len(steps) < 30           # 몇 줄짜리 함수는 기록도 짧아야 한다


def test_walk_는_함수가_아니면_거부한다():
    with pytest.raises(TypeError):
        walk("함수가 아님", [1])


def test_lesson_walk_와_trace_옵션(capsys):
    lesson = Lesson(title="t", build=계단, branches={"a": [1, 2]})
    result, steps = lesson.walk("a")
    assert result and steps

    lesson.as_console("a", trace=True)
    out = capsys.readouterr().out
    assert "한 줄씩 따라가기" in out
    assert "총합" in out


def test_format_steps_는_사람이_읽을_수_있게():
    _, steps = walk(계단, [1])
    줄 = format_steps(steps)
    assert 줄 and any("총합" in l for l in 줄)


# ── 학습자가 이상한 걸 넣어도 안 깨져야 한다 ──────────────────

def test_큰_입력에서도_빠르다():
    """repr()로 통째로 만들어 자르면 30만짜리 리스트를 매 줄 만든다.

    실제로 7.6초가 걸렸다. reprlib은 필요한 만큼만 만든다.
    """
    import time

    def 합(xs):
        총 = 0
        for x in xs:
            총 += x
        return [총]

    시작 = time.perf_counter()
    walk(합, list(range(200_000)))
    걸린시간 = time.perf_counter() - 시작
    assert 걸린시간 < 2.0, f"{걸린시간:.1f}초 — 너무 느립니다"


def test_무한루프가_멈춘다():
    """상한은 기록만 막는 게 아니라 실행도 끊어야 한다."""
    def 무한(xs):
        n = 0
        while True:
            n += 1
        return [n]

    결과, steps = walk(무한, [1], max_steps=50)
    assert 결과 is None
    assert len(steps) <= 51
    assert "멈췄습니다" in steps[-1].code


@pytest.mark.parametrize("값", [
    "점수 " + "1" * 400,      # float가 inf가 되는 길이
    "값 -999999999999",
    "",
    "이모지 🙂🙂",
])
def test_bar가_이상한_값에도_안_터진다(값):
    막대 = bar(값)
    assert isinstance(막대, str) and len(막대) <= 40


def test_웹앱은_돌아가지_않는_파일을_쓰지_않는다(tmp_path):
    """branches에 임의 객체가 있으면 repr이 코드가 아니게 된다."""
    class 학생:
        def __init__(self, 이름):
            self.이름 = 이름

    lesson = Lesson(title="t", build=번호매기기, branches={"a": [학생("민수")]})
    with pytest.raises(ValueError, match="웹앱 코드를 만들지 못했습니다"):
        lesson.as_webapp(str(tmp_path / "app.py"))


# ── 학습자 코드가 동의 없이 밖으로 나가면 안 된다 ──────────────

def test_LLM은_기본으로_꺼져_있다():
    """켜면 학습자가 쓴 코드 줄이 외부 API로 전송된다.

    미성년 학습자의 코드일 수 있으므로 켜는 것은 명시적 선택이어야 한다.
    """
    import inspect as _inspect

    from learnkit import error_tutor as et

    assert et._USE_LLM is False
    assert _inspect.signature(et.install).parameters["use_llm"].default is False
    assert _inspect.signature(et.tutor).parameters["use_llm"].default is False


def test_키가_있어도_켜지_않으면_안_부른다(monkeypatch):
    from learnkit import ai, error_tutor as et
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-가짜")
    불렀나 = []
    monkeypatch.setattr(ai, "ask", lambda *a, **k: 불렀나.append(1))

    with tutor():                       # 기본값 그대로
        pass
    try:
        raise NameError("name '과일' is not defined")
    except NameError as e:
        info = et.explain(type(e), e, e.__traceback__)
    assert not 불렀나
    assert info["_출처"] == "규칙"


# ── 화면에 넣은 값이 그대로 태그가 되면 안 된다 ────────────────

def test_마크다운_표가_깨지지_않는다():
    lesson = Lesson(title="t", build=lambda x: ["사과|배"], branches={"a": [1]})
    md = lesson.render("markdown", branch="a")
    assert r"사과\|배" in md


def test_blocks가_좁은_폭에서도_끝난다():
    lesson = Lesson(title="t", build=번호매기기, branches={"a": ["가나다라마바사"]})
    글 = lesson.render("blocks", branch="a", trace=True, width=0)
    assert 글.count("\n") < 40      # 무한 루프면 여기 못 온다


def test_trace를_켜도_build는_한_번만_돈다():
    """부작용이 있는 build면 두 번 실행되는 게 문제가 된다."""
    센 = []

    def 세는함수(items):
        센.append(1)
        return [str(x) for x in items]

    lesson = Lesson(title="t", build=세는함수, branches={"a": [1, 2]})
    lesson.to_view("a", trace=True)
    assert len(센) == 1, f"{len(센)}번 실행됐습니다"


# ── 발표 슬라이드에 실린 코드가 실제로 동작하는지 ────────────────

def test_콘솔_출력이_대괄호를_먹지_않음(capsys):
    """rich 마크업 때문에 코드의 [i % 7] 같은 부분이 사라지면 안 된다 (슬라이드 24)."""
    def 공부기록(hours):
        days = ["월", "화"]
        return [f"{days[i % 2]} {h}" for i, h in enumerate(hours)]

    lesson = Lesson(title="t", build=공부기록, branches={"a": [1, 2]},
                    challenge="items[i] 대신 items[-1] 을 써보자")
    lesson.as_console("a", dial="만들기")
    out = capsys.readouterr().out
    assert "i % 2" in out
    assert "items[i]" in out


def test_슬라이드23_바꾸기_코드가_실제로_출력한다(capsys):
    """슬라이드에 적힌 '바꾸기' 단계 코드가 화면에 결과를 내야 한다."""
    def 공부기록(hours):
        days = ["월", "화", "수", "목", "금", "토", "일"]
        return [f"{days[i % 7]} {h}" for i, h in enumerate(hours)]

    lesson = Lesson(title="이번 주 공부 시간", build=공부기록,
                    branches={"이번 주": [2, 4, 1, 3, 5]},
                    hint="숫자를 네 실제 공부 시간으로 바꿔봐.")
    lesson.as_console(dial="바꾸기", data=[3, 5, 2, 4, 1])
    out = capsys.readouterr().out
    assert "월 3" in out and "금 1" in out
    assert "숫자를 네 실제" in out


# ── 발표 준비 중 찾은 것들 ──────────────────────────────────

def _팩토리얼(n):
    if n <= 1:
        return 1
    작은값 = _팩토리얼(n - 1)
    return n * 작은값


def test_재귀도_따라간다():
    """상태를 하나로 공유하면 안쪽 호출의 변화가 바깥 기록에 섞인다.

    프레임마다 따로 들고 있어야 한다.
    """
    결과, steps = walk(_팩토리얼, 3)
    assert 결과 == 6
    assert len(steps) > 3                      # 한 겹만 기록되면 안 된다
    assert max(s.depth for s in steps) == 2    # 3 → 2 → 1 세 겹


def test_재귀_깊이별로_값이_섞이지_않는다():
    _, steps = walk(_팩토리얼, 3)
    작은값들 = [(s.depth, s.changed["작은값"]) for s in steps if "작은값" in s.changed]
    assert 작은값들 == [(1, "1"), (0, "2")]    # 깊은 쪽이 먼저, 각자 제 값
