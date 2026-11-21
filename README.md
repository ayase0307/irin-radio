# 艾琳電台 · IRIN RADIO

每天早上九十秒，用中文把 AI 圈的重點唸給你聽。

- **網址**：https://ayase0307.github.io/irin-radio/
- **新聞來源**：每日 AI 新聞 cron（AI News / The Batch / HF Papers / alphaXiv / arXiv cs.AI / LMArena / Artificial Analysis 七站輪替）＋ Hacker News、X 熱議
- **聲音**：Fish Audio（AD学姐）
- **播出時間**：每天 09:30（Asia/Taipei）

## 這是什麼

不是影片，是一集「台本 JSON ＋ 一支 mp3」，由 `index.html` 這個單檔播放器在瀏覽器裡播成節目：
播放位置對齊 `lines_timed`，字幕、標題卡、來源連結與角色嘴型都跟著聲音走。

## 怎麼做一集

```bash
# 1) 寫台本 spec（tools/specs/<日期>-<語言>.json）
# 2) 逐句 TTS → 量長度 → 串接 → 產生時間碼
python tools/build_episode.py --spec tools/specs/2026-11-06-zh.json --date 2026-11-06 --lang zh
# 3) 發布到 gh-pages（音檔只保留站台設定的近 30 天）
SHARE_FONT=C:/Windows/Fonts/msjh.ttc tools/publish.sh
```

## 授權與出處

- 播放器、角色素材與格式：[myradio](https://github.com/monoradio102/myradio) by monoradio102，MIT License（見 `LICENSE`）。
- 節目內容（台本與語音）由本站自行產生。
- 新聞縮圖直接連向原站的 OGP 圖片，不另存、不再散布。
