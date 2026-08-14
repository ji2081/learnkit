"""
발표용 데모 GIF — 바꾸기 / 접근성 / 도전 과제 / 세 화면 / 따라가기 / 오타.

녹화하지 않고 프레임을 직접 그린다. 한글 폰트가 보장되고, 타이밍을 제어할 수
있고, 실패한 테이크가 없다.

주의 두 가지 (1차 GIF에서 실제로 틀렸던 것들):
  · 폰트는 반드시 index=6 (Noto Sans Mono CJK KR). index=2는 중국어 비례폭이라
    칸이 어긋난다.
  · x는 칸 수 계산이 아니라 실제 폭(textlength)으로 누적한다. 한글 자간이
    정확히 2칸이 아니어서 계산으로 맞추면 벌어진다.

★ 모든 GIF의 첫 프레임 = 최종 결과 화면.
  PDF로 열면 GIF는 첫 프레임만 나오는데, 그때도 말이 되게 하려는 것이다.
"""

from PIL import Image, ImageDraw, ImageFont

# ── 슬라이드 팔레트 (Dracula) ──────────────────────────────
BG     = (0x28, 0x2A, 0x36)
BAR    = (0x21, 0x22, 0x2C)
FG     = (0xF8, 0xF8, 0xF2)
DIM    = (0x62, 0x72, 0xA4)
GREEN  = (0x50, 0xFA, 0x7B)
CYAN   = (0x8B, 0xE9, 0xFD)
YELLOW = (0xF1, 0xFA, 0x8C)
PINK   = (0xFF, 0x79, 0xC6)
ORANGE = (0xFF, 0xB8, 0x6C)
PURPLE = (0xBD, 0x93, 0xF9)
RED    = (0xFF, 0x5F, 0x56)

L_BG, L_BAR = (0xFF, 0xFF, 0xFF), (0xF0, 0xF2, 0xEE)
L_FG, L_DIM, L_GRN = (0x1F, 0x2A, 0x1F), (0x8A, 0x94, 0x88), (0x6B, 0xA0, 0x43)

FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
KR = 6


class Term:
    def __init__(self, cols=58, rows=15, size=21, pad=28, line_h=34, title="learnkit"):
        self.pad, self.line_h, self.title, self.size = pad, line_h, title, size
        self.F = ImageFont.truetype(FONT_R, size, index=KR)
        self.FB = ImageFont.truetype(FONT_B, size, index=KR)
        self.W = int(pad * 2 + self.F.getlength("M") * cols)
        self.H = pad + 44 + line_h * rows + pad

    def draw(self, lines, box=None, size=None):
        F, FB = self.F, self.FB
        line_h = self.line_h
        if size and size != self.size:
            F = ImageFont.truetype(FONT_R, size, index=KR)
            FB = ImageFont.truetype(FONT_B, size, index=KR)
            line_h = int(self.line_h * size / self.size)

        im = Image.new("RGB", (self.W, self.H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, self.W, 44], fill=BAR)
        for i, c in enumerate([RED, (0xFF, 0xBD, 0x2E), (0x27, 0xC9, 0x3F)]):
            d.ellipse([20 + i * 24, 17, 31 + i * 24, 28], fill=c)
        d.text(((self.W - d.textlength(self.title, font=self.F)) / 2, 11),
               self.title, font=self.F, fill=(0x9A, 0xA0, 0xB0))

        top = 44 + self.pad
        if box:
            b0, b1, bc, label = box
            b1 = min(b1, len(lines) - 1)
            if b1 >= b0:
                y0, y1 = top + b0 * line_h - 11, top + (b1 + 1) * line_h + 5
                d.rounded_rectangle([self.pad - 12, y0, self.W - self.pad + 12, y1],
                                    radius=10, outline=bc, width=2)
                if label:
                    lw = d.textlength(label, font=FB)
                    d.rectangle([self.pad + 14, y0 - 13, self.pad + 26 + lw + 12, y0 + 13],
                                fill=BG)
                    d.text((self.pad + 22, y0 - 12), label, font=FB, fill=bc)

        y = top
        for line in lines:
            x = float(self.pad)
            for color, text, bold in line:
                fnt = FB if bold else F
                d.text((x, y), text, font=fnt, fill=color)
                x += d.textlength(text, font=fnt)
            y += line_h
        return im


def seg(*parts):
    out = []
    for p in parts:
        out.append((FG, p, False) if isinstance(p, str)
                   else (p[0], p[1], False) if len(p) == 2 else p)
    return out


B = []          # 빈 줄


def save(name, frames):
    """frames = [(이미지, ms), ...]  ·  마지막(최종) 화면을 맨 앞에도 둔다."""
    최종 = frames[-1][0]
    seq = [(최종, frames[-1][1])] + frames[:-1]
    ims, ms = [f for f, _ in seq], [m for _, m in seq]
    ims[0].save(name, save_all=True, append_images=ims[1:], duration=ms,
                loop=0, optimize=True)
    ims[0].save(name.replace(".gif", "_first.png"))
    print(f"{name:24s} {ims[0].size[0]}x{ims[0].size[1]}  "
          f"aspect {ims[0].size[0]/ims[0].size[1]:.2f}  "
          f"{len(ims)}프레임 {sum(ms)/1000:.1f}초")


def 막대(요일, 값, 색=GREEN, fg=FG, 글자="█"):
    return seg((fg, f"{요일} {값}시간   ", True), (색, 글자 * 값))


def 타이핑(t, cmd, 뒤=None, ms=50, 멈춤=400):
    """명령어가 한 글자씩. 뒤 = 함께 보일 나머지 줄들."""
    뒤 = 뒤 or []
    P = [(GREEN, "$ ", True)]
    out = [(t.draw([P + [(FG, cmd[:i], False)]] + 뒤), ms) for i in range(len(cmd) + 1)]
    out.append((out[-1][0], 멈춤))
    return out


# ═══════════════════════════════════════════════════════════
# ① demo_change.gif → 25p "바꾸기 - 내 데이터로, 힌트와 함께"
#    데이터를 고치면 아래 그림이 그 자리에서 다시 그려진다
# ═══════════════════════════════════════════════════════════
def demo_change():
    t = Term(cols=60, rows=11, title="python -m learnkit 바꾸기")

    def 판(hours, hint=True, 강조=(), box=None):
        L = [seg((YELLOW, "힌트  ", True), (FG, "숫자를 네 공부 시간으로 바꿔봐"))] if hint else [B]
        L += [B, seg((DIM, "  "), (PINK, "hours"), (FG, " = "),
                     (CYAN, "[" + ", ".join(map(str, hours)) + "]")), B,
              seg((GREEN, " 이번 주 공부 시간 ", True))]
        요일 = ["월", "화", "수", "목", "금"]
        for i, h in enumerate(hours):
            L.append(막대(요일[i], h, ORANGE if i in 강조 else GREEN))
        return L

    f = []
    # 처음 상태
    시작 = 판([2, 4, 1])
    for n in range(1, len(시작) + 1):
        f.append((t.draw(시작[:n]), 150))
    f.append((f[-1][0], 1100))

    # 숫자를 고친다
    꼬리 = ", 3, 5]"
    for i in range(len(꼬리) + 1):
        L = list(시작)
        L[2] = seg((DIM, "  "), (PINK, "hours"), (FG, " = "),
                   (YELLOW, "[2, 4, 1" + 꼬리[:i]))
        f.append((t.draw(L), 95))
    f.append((f[-1][0], 520))

    # 그 자리에서 다시 그려진다
    끝 = 판([2, 4, 1, 3, 5], 강조=(3, 4))
    상자 = (4, 9, ORANGE, " 바로 다시 그려집니다 ")
    for n in range(5, len(끝) + 1):
        f.append((t.draw(끝[:n], box=상자), 210))
    f.append((t.draw(끝, box=상자), 3000))
    save("demo_change.gif", f)


# ═══════════════════════════════════════════════════════════
# ② demo_access.gif → 32p "접근성이 중요했던 순간"
#    옵션을 켜는 순간 화면이 실제로 달라진다
# ═══════════════════════════════════════════════════════════
def demo_access():
    t = Term(cols=58, rows=11, size=19, line_h=31, title="learnkit")
    흐림, 어두운초록 = (0xA8, 0xAE, 0xBC), (0x3F, 0x8F, 0x55)

    보통 = [seg((DIM, " 이번 주 공부 시간 ")), B,
            막대("월", 2, 어두운초록, 흐림), 막대("화", 4, 어두운초록, 흐림),
            막대("수", 1, 어두운초록, 흐림), B,
            seg((DIM, "기본 화면 — 작은 글씨, 낮은 대비"))]
    f = [(t.draw(보통), 1700)]

    앞 = [(DIM, "학습자 = ", False), (CYAN, "Learner", False), (FG, ".보기부터(", False)]
    옵션 = "big=True, high_contrast=True)"
    for i in range(len(옵션) + 1):
        f.append((t.draw(보통 + [B, 앞 + [(YELLOW, 옵션[:i], True)]]), 55))
    f.append((f[-1][0], 950))

    큰 = [seg((YELLOW, " 이번 주 공부 시간 ", True)), B,
          막대("월", 2, GREEN, (0xFF, 0xFF, 0xFF)),
          막대("화", 4, GREEN, (0xFF, 0xFF, 0xFF)),
          막대("수", 1, GREEN, (0xFF, 0xFF, 0xFF))]
    for n in range(1, len(큰) + 1):
        f.append((t.draw(큰[:n], size=29), 230))
    f.append((t.draw(큰 + [B, seg((GREEN, "big=True · high_contrast=True", True))],
                     size=29), 3000))
    save("demo_access.gif", f)


# ═══════════════════════════════════════════════════════════
# ③ demo_challenge.gif → 26p "만들기 - 코드를 열고, 도전 과제로"
#    고친 코드가 바로 화면이 된다
# ═══════════════════════════════════════════════════════════
def demo_challenge():
    t = Term(cols=62, rows=12, title="learnkit")
    머리 = [
        seg((PURPLE, " 도전 과제 ", True), (FG, "  숫자 대신 ★을 그 수만큼 붙여보자")), B,
        seg((DIM, "# 방금 실행된 그 함수입니다 (inspect.getsource)")),
        seg((PINK, "def "), (GREEN, "공부기록"), (FG, "(hours):")),
        seg((FG, "    결과 = []")),
        seg((PINK, "    for "), (FG, "i, h "), (PINK, "in "), (FG, "enumerate(hours):")),
    ]
    f = []
    for n in range(1, len(머리) + 1):
        f.append((t.draw(머리[:n]), 140))
    f.append((f[-1][0], 500))

    앞 = seg((FG, '        결과.append(f"{days[i % 7]} " + '))
    for s, ms, 색 in [('"█" * h)', 900, CYAN), ('"█" * h', 150, CYAN),
                      ('"█"', 150, CYAN), ('"★"', 260, YELLOW),
                      ('"★" * h', 150, YELLOW), ('"★" * h)', 900, YELLOW)]:
        f.append((t.draw(머리 + [앞 + [(색, s, True)]]), ms))
    코드 = 머리 + [앞 + [(YELLOW, '"★" * h)', True)], B]

    결과 = [막대("월", 2, YELLOW, 글자="★"), 막대("화", 4, YELLOW, 글자="★"),
            막대("수", 1, YELLOW, 글자="★")]
    상자 = (len(코드), len(코드) + 2, YELLOW, " 고친 코드가 바로 화면이 됩니다 ")
    for n in range(1, 4):
        f.append((t.draw(코드 + 결과[:n], box=상자), 250))
    f.append((t.draw(코드 + 결과, box=상자), 3000))
    save("demo_challenge.gif", f)


# ═══════════════════════════════════════════════════════════
# ④ demo_screens.gif → 18·19p "같은 정의, 세 가지 화면"
#    정의는 그대로 두고 renderer만 바꾼다
# ═══════════════════════════════════════════════════════════
def demo_screens():
    W, H = 1000, 570
    FT = ImageFont.truetype(FONT_R, 20, index=KR)
    FTB = ImageFont.truetype(FONT_B, 20, index=KR)
    F17 = ImageFont.truetype(FONT_R, 17, index=KR)
    F17B = ImageFont.truetype(FONT_B, 17, index=KR)
    F26 = ImageFont.truetype(FONT_B, 26, index=KR)
    DATA = [("월", 2), ("화", 4), ("수", 1), ("목", 3), ("금", 5)]

    def base(라벨):
        im = Image.new("RGB", (W, H), (0xEE, 0xF4, 0xE7))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([28, 22, W - 28, 128], radius=10, fill=BG)
        d.text((48, 34), "lesson = Lesson(", font=FT, fill=FG)
        d.text((48, 62), '    title="이번 주 공부 시간",', font=FT, fill=YELLOW)
        d.text((48, 90), "    build=공부기록)", font=FT, fill=FG)
        d.text((W - 200, 34), "정의는 하나", font=FTB, fill=CYAN)

        d.text((44, 146), "lesson.보여주기(renderer=", font=FT, fill=(0x3C, 0x4A, 0x3C))
        x = 44 + d.textlength("lesson.보여주기(renderer=", font=FT)
        d.text((x, 146), f'"{라벨}"', font=FTB, fill=(0x4A, 0x7A, 0x2E))
        d.text((x + d.textlength(f'"{라벨}"', font=FTB), 146), ")", font=FT,
               fill=(0x3C, 0x4A, 0x3C))
        for i, nm in enumerate(["console", "notebook", "webapp"]):
            cx, on = 660 + i * 108, nm == 라벨
            d.rounded_rectangle([cx, 142, cx + 98, 172], radius=15,
                                fill=L_GRN if on else (0xD8, 0xE4, 0xD2))
            d.text((cx + 49 - d.textlength(nm, font=F17B) / 2, 147), nm,
                   font=F17B, fill=(0xFF, 0xFF, 0xFF) if on else L_DIM)
        return im, d

    def 창(d, 밝음, 라벨):
        d.rounded_rectangle([28, 192, W - 28, H - 26], radius=10,
                            fill=L_BG if 밝음 else BG)
        d.rectangle([28, 192, W - 28, 228], fill=L_BAR if 밝음 else BAR)
        if not 밝음:
            for i, c in enumerate([RED, (0xFF, 0xBD, 0x2E), (0x27, 0xC9, 0x3F)]):
                d.ellipse([48 + i * 22, 204, 58 + i * 22, 214], fill=c)
        d.text(((W - d.textlength(라벨, font=F17)) / 2, 200), 라벨, font=F17,
               fill=L_DIM if 밝음 else (0x9A, 0xA0, 0xB0))

    def console(n):
        im, d = base("console"); 창(d, False, "터미널")
        d.text((56, 248), " 이번 주 공부 시간 ", font=FTB, fill=GREEN)
        for i, (요, 값) in enumerate(DATA[:n]):
            y = 288 + i * 32
            d.text((56, y), f"{요} {값}시간", font=FTB, fill=FG)
            d.text((186, y), "█" * 값, font=FT, fill=GREEN)
        return im

    def 밝은화면(라벨, 헤더, n, 웹=False):
        im, d = base(라벨); 창(d, True, 헤더)
        y0 = 248
        if 웹:
            d.rounded_rectangle([300, 200, 700, 222], radius=11, fill=(0xFF, 0xFF, 0xFF))
            d.text((318, 201), "localhost:8501", font=F17, fill=L_DIM)
        else:
            d.rectangle([56, 246, 62, 276], fill=L_GRN)
            d.text((78, 248), "In [1]:  lesson.보여주기()", font=F17, fill=L_DIM)
            y0 = 286
        d.text((78, y0), "이번 주 공부 시간", font=F26, fill=L_FG)
        if 웹:
            d.rounded_rectangle([78, 290, 420, 322], radius=6, fill=(0xF4, 0xF7, 0xF1),
                                outline=(0xD8, 0xE4, 0xD2), width=1)
            d.text((92, 294), "hours = 2, 4, 1, 3, 5", font=F17, fill=L_FG)
            d.rounded_rectangle([436, 290, 528, 322], radius=6, fill=L_GRN)
            d.text((458, 294), "실행", font=F17B, fill=(0xFF, 0xFF, 0xFF))
            y0 = 296
        for i, (요, 값) in enumerate(DATA[:n]):
            y = y0 + 44 + i * 30
            d.text((78, y), f"{요} {값}시간", font=F17, fill=L_FG)
            d.rounded_rectangle([176, y + 5, 176 + 값 * 34, y + 19], radius=4, fill=L_GRN)
        return im

    f = []
    for 만들기 in (console,
                   lambda n: 밝은화면("notebook", "Jupyter", n),
                   lambda n: 밝은화면("webapp", "Chrome", n, 웹=True)):
        for n in range(1, 6):
            f.append((만들기(n), 140 if n < 5 else 2000))
    f.append((console(5), 2000))
    save("demo_screens.gif", f)


# ═══════════════════════════════════════════════════════════
# ⑤ demo_trace.gif → 22p "보기 - 결과만이 아니라 과정까지"
#    1차 GIF는 컴프리헨션을 보여주고 있었다 (코드·슬라이드는 for 문)
# ═══════════════════════════════════════════════════════════
def demo_trace():
    t = Term(cols=70, rows=19, size=18, line_h=29, title="python -m learnkit trace")
    앞 = [seg((GREEN, " 이번 주 공부 시간 ", True)), B,
          막대("월", 2), 막대("화", 4), 막대("수", 1), 막대("목", 3), 막대("금", 5), B]
    f = []
    for n in range(1, len(앞) + 1):
        f.append((t.draw(앞[:n]), 135))
    f.append((f[-1][0], 700))

    따라 = [
        seg((FG, " 1. "), (FG, 'days = ["월", "화", "수", ...]')),
        seg((FG, "      "), (CYAN, "days = ['월', '화', '수', ...]")),
        seg((FG, " 2. "), (FG, "결과 = []")),
        seg((FG, "      "), (CYAN, "결과 = []")),
        seg((FG, " 3. "), (FG, "for i, h in enumerate(hours):")),
        seg((FG, "      "), (CYAN, "i = 0 · h = 2")),
        seg((FG, " 4. "), (FG, '결과.append(f"{days[i % 7]} {h}시간")')),
        seg((FG, "      "), (GREEN, "결과 = ['월 2시간']", True)),
        seg((FG, " …  "), (DIM, "(반복)")),
        seg((FG, "      "), (GREEN, "결과 = ['월 2시간', '화 4시간', '수 1시간', ...]", True)),
    ]
    상자 = (len(앞), len(앞) + len(따라) - 1, ORANGE, " 한 줄씩 따라가기 ")
    for n in range(1, len(따라) + 1):
        f.append((t.draw(앞 + 따라[:n], box=상자), 520 if n % 2 == 0 else 190))
    f.append((t.draw(앞 + 따라, box=상자), 3000))
    save("demo_trace.gif", f)


# ═══════════════════════════════════════════════════════════
# ⑥ demo_typo.gif → 28p "3. 에러를 친절한 한국어로"
#    1차 GIF는 비례폭 폰트로 그려져 칸이 어긋나 있었다
# ═══════════════════════════════════════════════════════════
def demo_typo():
    t = Term(cols=66, rows=13, size=19, line_h=31, title="python -m learnkit tutor")
    앞 = [seg((DIM, "에러를 일부러 내봅니다.")), B,
          seg((DIM, "Traceback (most recent call last):")),
          seg((DIM, '  File "내수업.py", line 4, in <module>')),
          seg((DIM, "    print(공부시감)")),
          seg((RED, "NameError: name '공부시감' is not defined", True)), B]
    f = []
    for n in range(1, len(앞) + 1):
        f.append((t.draw(앞[:n]), 140))
    f.append((f[-1][0], 620))

    카드 = [
        seg((FG, "원인  ", True), (FG, "아직 만들지 않은 이름을 사용했어요.")),
        seg((FG, "위치  ", True), (FG, "내수업.py 4번째 줄")),
        seg((FG, "코드  ", True), (CYAN, "print(공부시감)")),
        seg((FG, "힌트  ", True), (FG, "'공부시감'을 쓰기 전에 먼저 만들어주세요.")),
        seg((FG, "      "), (YELLOW, "혹시 '공부시간'을 쓰려던 건 아닌가요?", True)),
    ]
    상자 = (len(앞), len(앞) + len(카드) - 1, GREEN, " 튜터 (규칙 기반 · 인터넷 없이) ")
    for n in range(1, len(카드) + 1):
        f.append((t.draw(앞 + 카드[:n], box=상자), 900 if n == 5 else 180))
    f.append((t.draw(앞 + 카드, box=상자), 3000))
    save("demo_typo.gif", f)


if __name__ == "__main__":
    demo_change()
    demo_access()
    demo_challenge()
    demo_screens()
    demo_trace()
    demo_typo()
