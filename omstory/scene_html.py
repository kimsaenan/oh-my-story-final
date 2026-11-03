"""scene_html.py — 장면(배경 + 주인공 + 스티커)을 HTML/CSS로 그려요. 위치·크기는 cuts.LAYOUT 값(%)을 따라가서 슬라이더로 조절할 수 있어요."""
from __future__ import annotations

from html import escape

from . import cuts, ui


def scene_html(cut: int, hero: str, state: dict, answered: bool, layout: dict, show_label: bool = False) -> str:
    bg = ui.b64(str(cuts.ASSETS / cuts.CUT_INFO[cut]["bg"].replace("story/", "story/")))
    parts = [f'<img class="sc-bg" src="{bg}" alt="">']
    for it in cuts.scene_items(cut, hero, state, answered):
        L = layout[it["key"]]
        src = ui.b64(str(cuts.ASSETS / it["file"]))
        if it["kind"] in ("hero", "hero_item"):
            style = f"left:{L['left']}%;bottom:{L['bottom']}%;height:{L['height']}%"
            parts.append(f'<img class="sc-it sc-h" style="{style}" src="{src}" alt="">')
        else:
            style = f"right:{L['right']}%;bottom:{L['bottom']}%;width:{L['width']}%"
            parts.append(f'<img class="sc-it sc-a" style="{style}" src="{src}" alt="">')
    return f'<div class="sc">{"".join(parts)}</div>'


SCENE_CSS = """<style>
.sc{position:relative;width:100%;aspect-ratio:1.6/1;border-radius:22px;overflow:hidden;background:#BFE9F7;box-shadow:0 4px 16px rgba(30,42,74,.12)}
.sc-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.sc-it{position:absolute;object-fit:contain;object-position:bottom}
.sc-h{aspect-ratio:1/1;width:auto}
.sc-a{height:auto}
.sc-tag{position:absolute;background:#fff;color:#1E2A4A;font-weight:800;font-size:13px;padding:2px 10px;border-radius:12px;transform:translateY(100%)}
</style>"""
