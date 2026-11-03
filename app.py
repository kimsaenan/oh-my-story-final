"""
Oh! My Story — 아이의 말로 완성하는 4컷 미니 동화 (Oh! My Speaking 6 · Unit 01)
최종 디자인 시안을 그대로 옮긴 스트림릿 시제품.   실행:  streamlit run app.py
(이전 AI 이야기 버전은 app_v1_legacy.py)
"""
from __future__ import annotations

import hashlib
import json

import streamlit as st

import os

from omstory import ai_assist, cuts, speech, ui, voice
from omstory import textbook_audio as tba
from omstory.guard import child_unsafe
from omstory.scene_html import SCENE_CSS, scene_html

UNIT = cuts.UNIT_ID
st.set_page_config(page_title="Oh! My Story", page_icon="📖", layout="wide")
st.markdown(ui.CSS + SCENE_CSS + """<style>
.narr{background:#fff;border:2px dashed #5BC8F0;border-radius:18px;padding:14px 18px;margin:10px 0}
.narr .t{font-weight:800;color:#3AA6CF;font-size:14px}.narr .en{font-size:21px;line-height:1.5;margin:4px 0}.narr .ko{color:#5A6680}
.wk{background:#F4F1FF;border-radius:18px;padding:14px 18px;margin:8px 0}.wk .t{font-weight:800;color:#6A4BD6;font-size:14px}
.wk .en{font-size:24px;margin:4px 0}.wk .ko{color:#5A6680}
.stage{display:inline-block;background:#fff;border:2px solid #F0E3C8;border-radius:14px;padding:2px 12px;font-weight:800}
.note{background:#E6F6FD;border-radius:14px;padding:6px 12px;margin:4px 0}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"screen": "shelf", "hero": "amy", "cut": 1, "ans": {}, "state": {}, "notes": [], "vault": {}, "cover": 4,
             "title": "", "library": [], "open_word": None, "play": None, "mic_seen": "", "msg": "", "followed": set(),
             "layout": cuts.load_layout(), "ai_on": False, "ai_text": {}, "ai_used": {}}.items():
    S.setdefault(k, v)


# ------------------------------------------------------------------ 공통 도우미
def go(screen: str, **kw):
    S.screen = screen
    for k, v in kw.items():
        S[k] = v


def say(text: str, label: str = "🔊 듣기", key: str = "", wide: bool = False):
    """해설(선생님) 목소리로 읽어 줘요."""
    if st.button(label, key=key or "say_" + hashlib.md5(text.encode()).hexdigest()[:8], use_container_width=wide):
        S.play = text


def flush_audio():
    if S.play:
        a = voice.get(S.play)
        if a:
            st.audio(a, format="audio/mp3", autoplay=True)
        else:
            st.caption("🔇 소리를 만들 수 없어요 (tools/pregen_audio.py 를 한 번 실행하면 인터넷 없이도 들려요)")
        S.play = None


def on_word():
    w = S.get(f"wp{S.cut}")
    if w:
        S.open_word = w
        S[f"wp{S.cut}"] = None


@st.dialog("📌 단어 카드")
def word_card(w: str):
    ko, clip_id = cuts.WORDS.get(w, ("", None))
    st.markdown(f"<div class='en' style='font-size:34px'>{ui.E(w)}</div><div class='muted' style='font-size:18px'>{ui.E(ko)}</div>", unsafe_allow_html=True)
    p = tba.clip(UNIT, clip_id) if clip_id else None
    snd = str(p) if p else voice.get(w)
    if snd:
        st.audio(snd, format="audio/mp3", autoplay=True)
        st.caption("교재 원음" if p else "해설 목소리")
    else:
        st.caption("🔇 소리 파일이 아직 없어요 (tools/pregen_audio.py)")
    c1, c2 = st.columns(2)
    if c1.button("🎤 따라 말해 봤어요 (선택)", key=f"fw_{w}", use_container_width=True):
        st.success("좋아요! 점수는 없어요 😊")
    if w in S.vault:
        c2.success("보관함에 있어요")
    elif c2.button("📥 보관함에 담기", key=f"vt_{w}", type="primary", use_container_width=True):
        S.vault[w] = ko
        st.rerun()


def ai_panel():
    with st.sidebar:
        st.markdown("### 🤖 AI 도움 (선택)")
        if not os.getenv("OPENAI_API_KEY"):
            k = st.text_input("OpenAI API 키", type="password", help="이 세션에서만 쓰고 저장하지 않아요. 터미널에서 OPENAI_API_KEY 환경변수로 넣어도 돼요.")
            if k.strip():
                os.environ["OPENAI_API_KEY"] = k.strip()
                st.rerun()
        if ai_assist.available():
            S.ai_on = st.toggle("AI가 문장 만들기", value=S.ai_on, help="끄면 규칙 기반으로 돌아가요. AI가 실패해도 자동으로 규칙으로 전환돼요.")
            st.caption(f"모델: {ai_assist.MODEL()} · 줄거리·그림은 고정, 문장만 AI")
        else:
            S.ai_on = False
            st.caption("키가 없으면 규칙 기반(시연용)으로 동작해요.")


def layout_panel():
    with st.sidebar:
        st.markdown("### 🛠 배치 조정")
        on = st.toggle("그림 위치·크기 바꾸기", key="lay_on")
        if not on:
            return
        cut = st.selectbox("컷", [1, 2, 3, 4], index=(S.cut if S.screen == "cut" else 1) - 1, key="lay_cut")
        for key in cuts.KEYS_BY_CUT[cut]:
            st.markdown(f"**{cuts.LAYOUT_LABELS[key]}**")
            for a, lo, hi in [(a, 0 if a != "width" and a != "height" else 5, 100 if a in ("width", "height") else 90)
                              for a in S.layout[key]]:
                S.layout[key][a] = st.slider({"left": "← 왼쪽에서", "right": "→ 오른쪽에서", "bottom": "↑ 아래에서", "width": "↔ 너비", "height": "↕ 높이"}[a],
                                             lo, hi, int(S.layout[key][a]), key=f"lay_{key}_{a}")
        c1, c2 = st.columns(2)
        if c1.button("💾 저장", use_container_width=True):
            cuts.save_layout(S.layout)
            st.toast("assets/story/layout.json 에 저장했어요")
        if c2.button("↩ 처음 값", use_container_width=True):
            for k in [k for k in S if str(k).startswith("lay_") and k not in ("lay_on", "lay_cut")]:
                del S[k]
            S.layout = {k: dict(v) for k, v in cuts.DEFAULT_LAYOUT.items()}
            st.rerun()
        st.code(json.dumps(S.layout, ensure_ascii=False, indent=1), language="json")


def top(right: str = ""):
    st.markdown(ui.header(f'{ui.icon(34)} Oh! <span style="color:#3AA6CF">My Story</span>', right), unsafe_allow_html=True)


def reset_story():
    S.update(cut=1, ans={}, state={}, notes=[], followed=set(), cover=4, title="", ai_text={}, ai_used={})


# ------------------------------------------------------------------ 화면들
def shelf():
    top()
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    with c1:
        st.markdown("<div class='hero'><h2>내가 말하면, 내 동화책이 돼요!</h2><p>Wacky의 질문에 말하면 4컷 미니 동화가 완성돼요. 한국어로 말해도 괜찮아요.</p></div>", unsafe_allow_html=True)
        if st.button("📖 새 동화 만들기", type="primary"):
            reset_story()
            go("hero")
            st.rerun()
        st.caption("Oh! My Speaking 6 · Unit 01 'Let's have fun!'  (2~8단원은 수업 후 열려요)")
    with c2:
        st.image(str(cuts.ASSETS / "characters" / "wacky.png"), width=240)
    if S.library:
        st.markdown("### 📚 내 책장")
        cols = st.columns(4)
        for i, b in enumerate(S.library):
            with cols[i % 4]:
                st.markdown(scene_html(b["cover"], b["hero"], b["state"], True, S.layout, False), unsafe_allow_html=True)
                if st.button(f"📘 {b['title']}", key=f"bk{i}", use_container_width=True):
                    go("book", book=i)
                    st.rerun()
    st.markdown("### 🗂 내 단어 보관함")
    if S.vault:
        cols = st.columns(4)
        for i, (w, ko) in enumerate(S.vault.items()):
            if cols[i % 4].button(f"🔊 {w}\n{ko}", key=f"v{i}", use_container_width=True):
                S.open_word = w
                st.rerun()
    else:
        st.caption("동화 속 단어를 눌러서 '보관함에 담기'를 하면 여기에 쌓여요.")


def hero_pick():
    top()
    st.markdown("## 누가 주인공일까요?")
    st.caption("교재 친구 중에서 골라요. 주인공은 이야기 끝까지 나와요.")
    cols = st.columns(2)
    for col, (k, h) in zip(cols, cuts.HEROES.items()):
        with col:
            st.image(str(cuts.ASSETS / h["file"]), width=220)
            if st.button(f"{h['name']} ({h['ko']})로 시작", key=f"h_{k}", type="primary", use_container_width=True):
                go("cut", hero=k, cut=1)
                st.rerun()
    if st.button("← 책장으로"):
        go("shelf")
        st.rerun()


def accept(cut: int, text: str):
    text = text.strip()
    if not text:
        return
    if child_unsafe(text):
        S.msg = "다정한 말로 다시 말해 볼까요? 😊"
        return
    res = cuts.interpret(cut, text)
    S.ai_text.pop(cut, None)
    S.ai_used[cut] = False
    if S.ai_on and ai_assist.available():
        with st.spinner("Wacky가 생각하는 중…"):
            ai = ai_assist.refine(cut, S.hero, text)
        if ai:
            res.update(model_en=ai["model_en"], model_ko=ai["model_ko"], fallback=False,
                       reaction=(ai["reaction_en"], ai["reaction_ko"]))
            res["state"] = {**res["state"], **ai["state"]}
            S.ai_text[cut] = (ai["narr_en"], ai["narr_ko"])
            S.ai_used[cut] = True
    S.ans[cut] = {"text": text, **res}
    S.state.update(res["state"])
    S.msg = ""
    note = (res["model_en"], res["model_ko"])
    if note not in S.notes:
        S.notes.append(note)


def cut_screen():
    n, hero = S.cut, S.hero
    info = cuts.CUT_INFO[n]
    a = S.ans.get(n)
    top(ui.progress(n - 1 + (1 if a else 0), cuts.TOTAL_CUTS).replace("말한 문장", "컷"))
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"<span class='stage'>{info['stage']}</span> &nbsp; <b>{n} / {cuts.TOTAL_CUTS}컷</b>", unsafe_allow_html=True)
        st.markdown(scene_html(n, hero, S.state, bool(a), S.layout), unsafe_allow_html=True)
        if a:
            en, ko = S.ai_text.get(n) or cuts.narration(n, hero, S.state)
            st.markdown(f"<div class='narr'><div class='t'>책에는 이렇게 써요 🔊</div><div class='en'>{ui.E(en)}</div><div class='ko'>{ui.E(ko)}</div></div>", unsafe_allow_html=True)
            say(en, "🔊 읽어 주기", key=f"nar{n}")
            st.caption("눌러 보고 싶은 단어를 골라요 👇")
            st.pills("단어", cuts.narration_words(n, S.state), key=f"wp{n}", on_change=on_word, label_visibility="collapsed")
    with right:
        st.markdown(f"<div class='wk'><div class='t'>🤖 Wacky</div><div class='en'>{ui.E(info['q_en'])}</div><div class='ko'>{ui.E(info['q_ko'])}</div></div>", unsafe_allow_html=True)
        say(info["q_en"], "🔊 질문 듣기", key=f"q{n}")
        if not a:
            st.markdown("**내 말로 대답해 봐요** (한국어도 OK)")
            if speech.stt_available():
                audio = st.audio_input("🎤 말하기", key=f"mic{n}")
                if audio is not None:
                    data = audio.getvalue()
                    h = hashlib.md5(data).hexdigest()
                    if h != S.mic_seen:
                        S.mic_seen = h
                        with st.spinner("듣고 있어요…"):
                            accept(n, speech.transcribe(data, list(cuts.WORDS)[:8]))
                        st.rerun()
            with st.form(f"f{n}", clear_on_submit=True):
                t = st.text_input("✏️ 글자로 쓰기", placeholder={1: "예) 서핑 좋아해 / I enjoy surfing.", 2: "예) 꽃게!", 3: "예) 슬퍼 / They are sad.", 4: "예) 모래성 쌓자 / How about building a sandcastle?"}[n])
                if st.form_submit_button("보내기", type="primary") and t.strip():
                    accept(n, t)
                    st.rerun()
            with st.expander("💡 도와줘요"):
                st.caption(f"이렇게 말해 볼 수 있어요: **{info['hint']}**")
                for i, c in enumerate(info["chips_hint"]):
                    if st.button(c, key=f"hint{n}_{i}"):
                        accept(n, c)
                        st.rerun()
            if S.msg:
                st.warning(S.msg)
            if S.ai_on:
                st.caption("🤖 AI 도움 켜짐 — 아이 말에 맞춰 문장을 만들어요")
        else:
            st.markdown(ui.me(a["text"], korean=a["korean"]), unsafe_allow_html=True)
            if a["fallback"]:
                st.caption("잘 못 알아들었어요. 이렇게 말해 볼까요? 😊")
            st.markdown(f"<div class='wk'><div class='t'>이런 표현은 어때요?</div><div class='en'>{ui.E(a['model_en'])}</div><div class='ko'>{ui.E(a['model_ko'])}</div></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                say(a["model_en"], "🔊 듣기", key=f"m{n}", wide=True)
            with c2:
                if n in S.followed:
                    st.success("따라 말했어요 ⭐")
                elif st.button("🎤 따라 말했어요", key=f"fl{n}", use_container_width=True):
                    S.followed.add(n)
                    st.rerun()
            st.markdown(f"<div class='wk'><div class='t'>🤖 Wacky</div><div class='en' style='font-size:19px'>{ui.E(a.get('reaction', cuts.REACTIONS[n])[0])}</div><div class='ko'>{ui.E(a.get('reaction', cuts.REACTIONS[n])[1])}</div></div>", unsafe_allow_html=True)
            if S.ai_used.get(n):
                st.caption("🤖 이 문장은 AI가 도와서 만들었어요 (안전 검사 통과)")
            c1, c2 = st.columns(2)
            if c1.button("↩ 다시 말하기", key=f"re{n}", use_container_width=True):
                S.ans.pop(n, None)
                S.followed.discard(n)
                st.rerun()
            last = n == cuts.TOTAL_CUTS
            if c2.button("📕 표지 고르기" if last else "다음 컷 ▶", key=f"nx{n}", type="primary", use_container_width=True):
                if last:
                    go("cover")
                else:
                    S.cut = n + 1
                st.rerun()
        with st.expander(f"📝 내가 만든 표현 노트 ({len(S.notes)})", expanded=bool(S.notes)):
            for en, ko in S.notes:
                st.markdown(f"<div class='note'><b class='en'>{ui.E(en)}</div>", unsafe_allow_html=True)
                st.caption(ko)


def cover_pick():
    top()
    st.markdown("## ① 표지 장면을 골라요")
    cols = st.columns(4)
    for i, col in enumerate(cols, start=1):
        with col:
            st.markdown(scene_html(i, S.hero, S.state, True, S.layout, False), unsafe_allow_html=True)
            if st.button(("✅ " if S.cover == i else "") + f"{i}컷 장면", key=f"cv{i}", use_container_width=True,
                         type="primary" if S.cover == i else "secondary"):
                S.cover = i
                st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("← 4컷으로"):
        go("cut", cut=4)
        st.rerun()
    if c2.button("제목 정하기 ▶", type="primary"):
        go("finish")
        st.rerun()


def finish():
    top()
    st.markdown("## ② 책 제목을 정해요")
    cands = cuts.title_candidates(S.hero, S.state)
    left, right = st.columns([2, 3])
    with left:
        st.markdown(scene_html(S.cover, S.hero, S.state, True, S.layout, False), unsafe_allow_html=True)
    with right:
        labels = [t for t, _ in cands] + ["🎤 내가 짓기"]
        pick = st.pills("제목 후보", labels, key="title_pick", selection_mode="single", default=labels[0])
        title = None
        if pick == "🎤 내가 짓기":
            with st.form("ct"):
                t = st.text_input("영어로 짓거나 말해 봐요 (5단어 이하)", placeholder="Amy and the Happy Crabs")
                ok = st.form_submit_button("이 제목으로 확인")
            if ok:
                title, msg = cuts.check_custom_title(t)
                (st.success if title else st.warning)(msg)
                if title:
                    S.custom_title = title
            title = S.get("custom_title") if S.get("custom_title") else None
        elif pick:
            title = pick
            ko = dict(cands)[pick]
            st.caption(ko)
            say(pick, "🔊 제목 듣기", key="tt")
        if st.button("🎉 동화책 완성!", type="primary", disabled=not title):
            S.library.append({"title": title, "cover": S.cover, "hero": S.hero, "state": dict(S.state), "narr": dict(S.ai_text)})
            S.custom_title = None
            go("book", book=len(S.library) - 1)
            st.rerun()
    if st.button("← 표지 다시 고르기"):
        go("cover")
        st.rerun()


def book():
    b = S.library[S.get("book", 0)]
    top()
    if S.get("celebrated") != S.get("book"):
        st.balloons()
        S.celebrated = S.get("book")
    st.markdown(f"## 📘 {b['title']}")
    st.caption("링크로 누구나 볼 수 있어요 · 아이 목소리는 피드백에만 쓰고 30일 뒤 자동 삭제돼요 (보호자 동의 후 이용)")
    cols = st.columns(4)
    for i, col in enumerate(cols, start=1):
        with col:
            st.markdown(scene_html(i, b["hero"], b["state"], True, S.layout, False), unsafe_allow_html=True)
            en, ko = b.get("narr", {}).get(i) or cuts.narration(i, b["hero"], b["state"])
            st.markdown(f"<div class='narr' style='padding:8px 12px'><div class='en' style='font-size:15px'>{ui.E(en)}</div><div class='ko' style='font-size:13px'>{ui.E(ko)}</div></div>", unsafe_allow_html=True)
            say(en, "🔊", key=f"bk_nar{i}")
    st.markdown("**📝 내가 만든 표현**")
    for en, ko in S.notes:
        st.markdown(f"- **{en}** — {ko}")
    c1, c2 = st.columns(2)
    if c1.button("📚 책장으로"):
        go("shelf")
        st.rerun()
    if c2.button("✨ 새 동화 만들기", type="primary"):
        reset_story()
        go("hero")
        st.rerun()


# ------------------------------------------------------------------ 실행
ai_panel()
layout_panel()
{"shelf": shelf, "hero": hero_pick, "cut": cut_screen, "cover": cover_pick, "finish": finish, "book": book}[S.screen]()
if S.open_word:
    w, S.open_word = S.open_word, None
    word_card(w)
flush_audio()
