#!/usr/bin/env python
"""把一份台本 spec 做成 myradio 的一集：逐句 TTS → 量長度 → 串接 → 產生時間碼 JSON。

用法:
  python tools/build_episode.py --spec tools/specs/2026-11-06-zh.json --date 2026-11-06 --lang zh

spec 格式:
  {"title": str, "opening": [line...], "news": [{"label","points","lines","url","link"}], "closing": [line...]}
  line = {"say": 朗讀文字, "show": 字幕文字}
"""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = r"C:/Users/msdn/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
FISH = r"D:/Users/msdn/Hermes/tools/fish_tts.py"
FFMPEG = r"D:/Users/msdn/Hermes/tools/ffmpeg/bin/ffmpeg"
FFPROBE = r"D:/Users/msdn/Hermes/tools/ffmpeg/bin/ffprobe"
VOICE = "7f92f8afb8ec43bf81429cc1c9199cb1"   # AD学姐
MODEL = "s2.1-pro-free"
GAP = 0.30          # 句與句之間留白（秒）
LEAD = 0.60         # 開場前留白


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-400:]}")
    return r.stdout


def dur(path):
    out = sh([FFPROBE, "-v", "error", "-show_entries", "format=duration",
              "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return round(float(out.strip()), 3)


def tts(text, out_mp3):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        tf = f.name
    try:
        sh([PY, FISH, "--text-file", tf, "--output", str(out_mp3),
            "--voice", VOICE, "--model", MODEL, "--format", "mp3", "--latency", "normal"])
    finally:
        os.unlink(tf)
    if not out_mp3.exists() or out_mp3.stat().st_size == 0:
        raise RuntimeError(f"TTS produced no audio for: {text[:30]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--lang", default="zh")
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    audio_dir = ROOT / "audio"
    audio_dir.mkdir(exist_ok=True)
    cache = ROOT / "tools" / ".tts-cache"
    cache.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="ep-"))

    # 1) 收集句子（依播出順序），每句一個 mp3
    seq = []   # (kind, index, line_dict)
    for ln in spec["opening"]:
        seq.append(("opening", None, ln))
    for i, item in enumerate(spec["news"]):
        for ln in item["lines"]:
            seq.append(("news", i, ln))
    for ln in spec["closing"]:
        seq.append(("closing", None, ln))

    clips, timings = [], []
    t = LEAD
    for n, (kind, idx, ln) in enumerate(seq):
        key = hashlib.sha1((VOICE + ln["say"]).encode("utf-8")).hexdigest()[:16]
        mp3 = cache / f"{key}.mp3"
        if not mp3.exists():
            print(f"  TTS {n + 1}/{len(seq)}: {ln['say'][:26]}…", flush=True)
            tts(ln["say"], mp3)
        wav = work / f"{n:03d}.wav"
        sh([FFMPEG, "-y", "-v", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1", str(wav)])
        d = dur(wav)
        clips.append(wav)
        timings.append({"start": round(t, 3), "end": round(t + d, 3), "show": ln["show"], "kind": kind, "index": idx})
        t += d + GAP

    # 2) 串接（句間插入靜音）
    silence = work / "gap.wav"
    sh([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
        f"anullsrc=r=44100:cl=mono", "-t", str(GAP), str(silence)])
    lead = work / "lead.wav"
    sh([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
        f"anullsrc=r=44100:cl=mono", "-t", str(LEAD), str(lead)])
    listing = work / "list.txt"
    parts = [lead]
    for c in clips:
        parts += [c, silence]
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    out_mp3 = audio_dir / f"{args.date}-{args.lang}.mp3"
    sh([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", str(out_mp3)])
    total = dur(out_mp3)

    # 3) 時間碼：零件與段落
    lines_timed = []
    part_of = {}
    for kind, idx, _ in [("opening", None, None)]:
        break
    pnum = 0
    for i, item in enumerate(spec["opening"]):
        part_of[("opening", None, i)] = 0
    for j, item in enumerate(spec["news"]):
        for k in range(len(item["lines"])):
            part_of[("news", j, k)] = 1 + j
    for k in range(len(spec["closing"])):
        part_of[("closing", None, k)] = 1 + len(spec["news"])

    counters = {}
    for tm in timings:
        key = (tm["kind"], tm["index"])
        k = counters.get(key, 0)
        counters[key] = k + 1
        lines_timed.append({"start": tm["start"], "end": tm["end"], "show": tm["show"],
                            "part": part_of[key + (k,)]})

    segments, seen = [], {}
    for tm, lt in zip(timings, lines_timed):
        key = (tm["kind"], tm["index"])
        if key not in seen:
            seen[key] = {"kind": tm["kind"], "index": tm["index"], "start": lt["start"], "end": lt["end"]}
            segments.append(seen[key])
        else:
            seen[key]["end"] = lt["end"]
    if segments:
        segments[0]["start"] = 0.0

    ep = {
        "format": "monoradio/news-1",
        "date": args.date,
        "lang": args.lang,
        "title": spec["title"],
        "opening": [{"say": l["say"], "show": l["show"]} for l in spec["opening"]],
        "news": spec["news"],
        "closing": [{"say": l["say"], "show": l["show"]} for l in spec["closing"]],
        "seconds": total,
        "lines_timed": lines_timed,
        "segments": segments,
        "made_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
    }
    (ROOT / "episodes").mkdir(exist_ok=True)
    ep_path = ROOT / "episodes" / f"{args.date}-{args.lang}.json"
    ep_path.write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) episodes.json（新集排最前）
    idx_path = ROOT / "episodes.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    idx = [e for e in idx if e.get("date") != args.date]
    idx.insert(0, {"date": args.date, args.lang: {"title": spec["title"], "seconds": total}})
    idx_path.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    print(f"OK {out_mp3.name}  {total:.1f}s  lines={len(lines_timed)}  segments={len(segments)}")
    print(f"   {ep_path.relative_to(ROOT)}  + episodes.json ({len(idx)} 集)")


if __name__ == "__main__":
    sys.exit(main())
