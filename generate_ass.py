#!/usr/bin/env python3
"""
テロップリスト + Whisperタイムスタンプ → ASS字幕生成
縦書き左端表示、暗背景付き
"""
import json
import re
import argparse
from difflib import SequenceMatcher

# ASS header
# BorderStyle 3 = opaque box background
# Alignment 7 = top-left
# BackColour alpha: 80 (hex) = 50% transparent
ASS_HEADER = """\ufeff[Script Info]
Title: 石の形講座 裂かれ形
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tategaki,IPAGothic,38,&H00FFFFFF,&H000000FF,&H00000000,&H80384030,-1,0,0,0,100,100,8,0,3,2,0,7,8,0,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

GO_SYNONYMS = {
    'カケツギ': ['かけつぎ', 'かけ継ぎ'],
    'ツナギ': ['つなぎ', '繋ぎ'],
    'ノゾキ': ['のぞき', '覗き'],
    'シチョウ': ['しちょう', '視聴'],
    'ケイマ': ['けいま', '桂馬'],
    'アタリ': ['あたり', '当たり'],
    'ワタリ': ['わたり', '渡り'],
    'ワリコミ': ['わりこみ', '割り込み'],
    'オサエ': ['おさえ', '抑え'],
    'オサえる': ['おさえる', '抑える'],
    'サガリ': ['さがり', '下がり'],
    'キズ': ['きず', '傷'],
    'キリ': ['きり', '切り'],
    '裂かれ形': ['裂かたち', '裂かれている形', 'さかれがた'],
    'ウチコミ': ['うちこみ', '打ち込み'],
}

def time_to_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def to_vertical(text):
    """横書き→縦書き変換: 各文字を\\Nで区切る"""
    # 句読点・記号の縦書き変換
    vertical_map = {
        '（': '︵', '）': '︶',
        '「': '﹁', '」': '﹂',
        '、': '︑', '。': '︒',
        '？': '？', '！': '！',
        '・': '・',
    }
    chars = []
    for ch in text:
        ch = vertical_map.get(ch, ch)
        chars.append(ch)
    return '\\N'.join(chars)

def parse_telop_list(md_path):
    telops = []
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('- '):
                text = line[2:].strip()
                if text:
                    telops.append(text)
    return telops

def norm(text):
    text = text.replace('　', '').replace('・', '').replace('…', '')
    text = re.sub(r'[、。！？\s（）\(\)「」]+', '', text)
    return text.lower()

def expand(text):
    variants = [norm(text)]
    for term, readings in GO_SYNONYMS.items():
        if term in text:
            for r in readings:
                variants.append(norm(text.replace(term, r)))
    return variants

def score(telop, seg_text):
    ns = norm(seg_text)
    best = 0
    for nt in expand(telop):
        if nt in ns or ns in nt:
            s = 0.9
        else:
            s = SequenceMatcher(None, nt, ns).ratio()
        best = max(best, s)
    return best

def find_anchors(telops, transcript, threshold=0.45):
    anchors = []
    t_start = 0
    for ti, telop in enumerate(telops):
        best_score = 0
        best_ti = -1
        proportion = ti / max(len(telops), 1)
        expected_pos = int(proportion * len(transcript))
        window_start = max(0, min(t_start - 10, expected_pos - 100))
        window_end = min(len(transcript), max(t_start + 150, expected_pos + 100))
        for si in range(max(0, window_start), window_end):
            combined = transcript[si]['text']
            if si + 1 < len(transcript):
                combined += transcript[si + 1]['text']
            s = max(score(telop, combined), score(telop, transcript[si]['text']))
            if s > best_score:
                best_score = s
                best_ti = si
        if best_score >= threshold and best_ti >= t_start - 5:
            anchors.append((ti, best_ti, best_score))
            t_start = best_ti + 1
    return anchors

def interpolate(telops, transcript, anchors):
    result = []
    all_a = []
    if not anchors or anchors[0][0] > 0:
        all_a.append((0, 0, 0))
    all_a.extend(anchors)
    if not anchors or anchors[-1][0] < len(telops) - 1:
        all_a.append((len(telops) - 1, len(transcript) - 1, 0))
    seen = set()
    unique = []
    for a in all_a:
        if a[0] not in seen:
            seen.add(a[0])
            unique.append(a)
    all_a = sorted(unique, key=lambda x: x[0])

    for ai in range(len(all_a)):
        ti_s, si_s, sc = all_a[ai]
        if ai + 1 < len(all_a):
            ti_e, si_e, _ = all_a[ai + 1]
        else:
            ti_e, si_e = ti_s, si_s
        t_s = transcript[si_s]['start']
        t_e = transcript[min(si_e, len(transcript)-1)]['start']
        n = max(ti_e - ti_s, 1)
        for j in range(n):
            ti = ti_s + j
            if ti >= len(telops):
                break
            frac = j / n
            t = t_s + frac * (t_e - t_s)
            result.append({
                'text': telops[ti],
                'start': t,
                'anchor': (ti == ti_s and sc > 0),
            })
    if len(result) < len(telops):
        lt = result[-1]['start'] + 4.0 if result else 0
        for ti in range(len(result), len(telops)):
            result.append({'text': telops[ti], 'start': lt, 'anchor': False})
            lt += 4.0
    return result

def generate_ass(timed, output_path):
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(ASS_HEADER)
        for i, m in enumerate(timed):
            st = m['start']
            if i + 1 < len(timed):
                dur = min(timed[i+1]['start'] - st, 8.0)
                dur = max(dur, 1.5)
            else:
                dur = 5.0
            vtext = to_vertical(m['text'])
            f.write(f"Dialogue: 0,{time_to_ass(st)},{time_to_ass(st + dur)},Tategaki,,0,0,0,,{vtext}\n")
    print(f"Generated: {output_path} ({len(timed)} entries)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('transcript')
    parser.add_argument('telop_list')
    parser.add_argument('-o', '--output', default='/tmp/telops.ass')
    args = parser.parse_args()

    with open(args.transcript) as f:
        transcript = json.load(f)
    telops = parse_telop_list(args.telop_list)
    print(f"Transcript: {len(transcript)} segs | Telops: {len(telops)}")

    anchors = find_anchors(telops, transcript)
    print(f"Anchors: {len(anchors)}/{len(telops)}")

    timed = interpolate(telops, transcript, anchors)
    generate_ass(timed, args.output)

if __name__ == '__main__':
    main()
