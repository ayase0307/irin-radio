#!/usr/bin/env python
"""客製化 irin-radio：換站名、加 zh 語系、清空樣板集數。"""
import json
import pathlib
import re

ROOT = pathlib.Path("D:/Users/msdn/Hermes/work/irin-radio")

# ---------- 1) station.json ----------
station = {
    "format": "myradio/station-1",
    "name": "艾琳電台",
    "description": "AI、影片生成、開源模型的昨日重點，每天早上九十秒，用中文說給你聽。",
    "tagline": "AI 日報，每天早上九十秒",
    "logo": "logo.svg",
    "url": "https://ayase0307.github.io/irin-radio/",
    "repo": "https://github.com/ayase0307/irin-radio",
    "language": "zh",
    "languages": ["zh"],
    "schedule": {"every": "day", "time": "09:30", "timezone": "Asia/Taipei"},
    "episodes": "episodes.json",
    "character": {
        "pack": "character/character.json",
        "thumbnail": "character/base.png",
        "note": "AI 生成的播報角色（樣板角色，MIT）",
    },
    "credits": [
        "聲：Fish Audio（AD学姐）",
        "播放器：myradio by monoradio102（MIT License）",
    ],
    "caster": "聲：AD学姐",
    "audio": {"dir": "audio", "keep_days": 30},
    "weather": False,
}
(ROOT / "station.json").write_text(json.dumps(station, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# ---------- 2) index.html：加 zh 語系 ----------
p = ROOT / "index.html"
h = p.read_text(encoding="utf-8")

zh = '''  zh: { share: "分享", copied: "已複製", resumeAt: t => `從 ${t} 繼續播放`, from0: "從頭播放", heard: "聽過", partway: t => `停在 ${t}`, rate: "播放速度", wxHere: "目前位置", wxCredit: "天氣：Open-Meteo（CC BY 4.0）", wxNoGeo: "無法取得定位", wxPrompt: "從右上角選地點就會顯示天氣", wxChoose: "選擇地點", wxUseHere: "使用我的位置", wxJapan: "日本", wxWorld: "世界", wxHi: "高", wxLo: "低", wxRain: "降雨", copyHint: "點一下複製", native: "分享…", copyLink: "複製連結", copyEmbed: "複製嵌入碼", openPage: "開啟頁面", news: "新聞", none: "沒有補充", jump: "跳到這段", bye: "明天見！", related: "相關文章", open: "開啟原文 ↗",
        notFound: c => `找不到連結（${c}）`, source: "來源", script: "逐字稿", past: "過往節目", talk: "留言", talkNote: "留言需要 GitHub 帳號；留言存在 GitHub Discussions，這裡由 giscus.app 載入。",
        expired: "這集的音檔已下架（逐字稿還在下面）", loading: "載入中…", empty: "還沒有節目",
        muted: "目前靜音 · 點一下開啟", sep: "・", colon: "：" },
'''
if "  zh: {" not in h:
    h = h.replace("};\nlet LANG = \"ja\";", zh + "};\nlet LANG = \"ja\";", 1)
    assert "  zh: {" in h, "zh 語系插入失敗"

h = h.replace('const NAMES = { ja: "日本語", en: "English" };',
              'const NAMES = { ja: "日本語", en: "English", zh: "中文" };', 1)

# 中文日期
h = h.replace(
    'const dateFmt = d => LANG === "ja" || !UI[LANG] ? dateJp(d)\n  : new Date(d + "T00:00:00").toLocaleDateString(LANG, { weekday: "short", month: "short", day: "numeric", year: "numeric" });',
    'const dateFmt = d => LANG === "ja" || !UI[LANG] ? dateJp(d)\n  : new Date(d + "T00:00:00").toLocaleDateString(LANG === "zh" ? "zh-TW" : LANG, { weekday: "short", month: "short", day: "numeric", year: "numeric" });',
    1)

# 靜態 HTML 的日文預設字（JS 會覆寫，但首屏要對）
for a, b in [
    ("記事をひらく ↗", "開啟原文 ↗"),
    ("音声オフ・クリックでオン", "目前靜音 · 點一下開啟"),
    (">コメント<", ">留言<"),
    (">台本を読む<", ">逐字稿<"),
    (">これまでの放送<", ">過往節目<"),
    ("<title>ものラジオ</title>", "<title>艾琳電台 · IRIN RADIO</title>"),
    ('<html lang="ja">', '<html lang="zh-Hant">'),
]:
    h = h.replace(a, b)

p.write_text(h, encoding="utf-8")

# ---------- 3) 集數清空 ----------
for f in (ROOT / "episodes").glob("*.json"):
    f.unlink()
(ROOT / "episodes.json").write_text("[]\n", encoding="utf-8")
print("station.json / index.html / episodes 已更新")
print("zh 語系:", "  zh: {" in p.read_text(encoding='utf-8'))
