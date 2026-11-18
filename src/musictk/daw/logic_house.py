"""Logic Pro に読み込ませるハウス曲の MIDI を作る。

使い方:
  python -m musictk.daw.logic_house out.mid [--form short|full] [--key A] [--bpm 122] [--prog deep|soul|dark|lift] [--seed 1]

- short: 32 小節（Intro 8 / Groove 8 / Break 8 / Drop 8）約 1 分。音色を試すとき用
- full : 96 小節 約 3 分。Intro 16 / Groove 16 / Break 16 / Build 8 / Drop 16 / Groove2 16 / Outro 8
- 区間の最後の小節に「つなぎ」（スネアのロール・キック抜き）、区間の頭にクラッシュを入れる
- トラック: Drums（10ch・GM 配置）/ Bass / Chords / Lead。区間マーカー・テンポ・調入り
- リードは和音の構成音の上を歩くように作る（強拍は和音の音、弱拍は音階の隣の音）
"""
import argparse
import random

import mido

TPB = 480
BAR = TPB * 4
S16 = TPB // 4
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
MINOR = [0, 2, 3, 5, 7, 8, 10]  # 自然的短音階

# 進行: (根音の音階度数 0-6, 和音の形 = 根音からの半音)
PROGS = {
    "deep": [(0, [0, 3, 7, 10, 14]), (5, [0, 4, 7, 11, 14]), (3, [0, 3, 7, 10, 14]), (4, [0, 5, 7, 10, 12])],  # i9 VImaj9 iv9 v7sus
    "soul": [(0, [0, 3, 7, 10, 14]), (3, [0, 3, 7, 10, 14]), (6, [0, 4, 7, 10, 14]), (2, [0, 4, 7, 11, 14])],  # i9 iv9 VII9 IIImaj9
    "dark": [(0, [0, 3, 7, 10]), (0, [0, 3, 7, 10]), (5, [0, 4, 7, 11]), (4, [0, 3, 7, 10])],               # i7 i7 VImaj7 v7
    "lift": [(5, [0, 4, 7, 11, 14]), (6, [0, 4, 7, 10, 14]), (0, [0, 3, 7, 10, 14]), (0, [0, 3, 7, 10, 14])],  # VI VII i i
}

# Logic 13 が MIDI を開くときプログラム番号から選ぶ音色（2026-11-07 に試した結果）。
# 4（E.Piano）・16/18（オルガン）など一部は「外部 MIDI（GM デバイス）」になって鳴らないので使わない。
#   メロディ系: 0 Studio Grand / 5 80s Wave Bells / 38 Pulse Bass / 39 Taureg Moon Bass / 48 Kensington（弦、2026-11-08 素材削除で鳴らない）
#              80 Reverse Engineering / 81 The Final Lead / 87 Ambient Lead / 88 Glistening Pad / 89 Classic Pad / 90 Epic Cloud Formation
#   ドラム（10ch）: 0 SoCal / 8 Retro Rock / 16 Tough Kit / 24・25 Drum Synth Kit / 32 Roots / 48 以上 Latin
SOUNDS = {"drums": 25, "bass": 39, "chords": 0, "lead": 87}

# 区間ごとに鳴らすもの
#   kick / clap / hats（closed=閉じたハットの 16 分, open=裏のオープン, shaker=8 分のシェイカー）
#   bass（groove / hold=伸ばす）/ chords（stab / pad）/ lead（True でフレーズ）/ fill（最後の小節のつなぎ）
FORMS = {
    "short": [
        ("Intro", 8, dict(kick=True, hats="closed", open_from=4, chords="stab", chords_from=4, fill="roll")),
        ("Groove", 8, dict(kick=True, clap=True, hats="closed", open_from=0, bass="groove", chords="stab", fill="drop")),
        ("Break", 8, dict(hats="shaker", bass="hold", chords="pad", fill="roll")),
        ("Drop", 8, dict(kick=True, clap=True, hats="closed", open_from=0, bass="groove", chords="stab", lead=True, rim=True)),
    ],
    "full": [
        ("Intro", 16, dict(kick=True, hats="closed", open_from=8, chords="stab", chords_from=12, fill="roll")),
        ("Groove", 16, dict(kick=True, clap=True, hats="closed", open_from=0, bass="groove", chords="stab", fill="drop")),
        ("Break", 16, dict(hats="shaker", bass="hold", chords="pad", lead_soft=True)),
        ("Build", 8, dict(hats="closed", chords="stab", build=True, fill="roll")),
        ("Drop", 16, dict(kick=True, clap=True, hats="closed", open_from=0, bass="groove", chords="stab", lead=True, rim=True, fill="drop")),
        ("Groove2", 16, dict(kick=True, clap=True, hats="closed", open_from=0, bass="groove2", chords="stab2", rim=True, fill="roll")),
        ("Outro", 8, dict(kick=True, hats="closed", open_from=0, bass="groove", outro=True)),
    ],
}
KICK, RIM, SNARE, CLAP, CHH, OHH, CRASH, SHAKER = 36, 37, 38, 39, 42, 46, 49, 70


class Part:
    def __init__(self, name, channel, program=None):
        self.name, self.ch, self.program, self.ev = name, channel, program, []

    def note(self, start, length, note, vel):
        vel = max(1, min(127, int(vel)))
        self.ev += [(start, 1, note, vel), (start + length, 0, note, 0)]

    def track(self):
        t = mido.MidiTrack([mido.MetaMessage("track_name", name=self.name, time=0)])
        if self.program is not None:
            t.append(mido.Message("program_change", channel=self.ch, program=self.program, time=0))
        now = 0
        for tick, kind, n, v in sorted(self.ev, key=lambda e: (e[0], e[1])):
            t.append(mido.Message("note_on" if kind else "note_off", channel=self.ch, note=n, velocity=v, time=tick - now))
            now = tick
        t.append(mido.MetaMessage("end_of_track", time=0))
        return t


def build(key, bpm, prog_name, seed, form="short"):
    rnd = random.Random(seed)
    tonic = NOTE[key]
    prog = PROGS[prog_name]
    sections = FORMS[form]

    chords_notes, roots = [], []
    for deg, shape in prog:
        pc = (tonic + MINOR[deg % 7]) % 12
        root = 48 + pc if pc <= 7 else 36 + pc       # 和音の根音を C3〜G3 付近に
        voiced = sorted(root + i for i in shape)
        while voiced[-1] > 74:                        # 高すぎる音は 1 オクターブ下げる
            voiced = sorted(v - 12 if v > 74 else v for v in voiced)
        chords_notes.append(voiced)
        roots.append(24 + pc if pc >= 4 else 36 + pc)  # ベースは E1〜D#2
    # Groove2 用: 一番上の音を 1 オクターブ下げた転回形（響きを少し変える）
    chords_inv = [sorted(v[:-1] + [v[-1] - 12]) for v in chords_notes]

    drums, bass = Part("Drums", 9, SOUNDS["drums"]), Part("Bass", 0, SOUNDS["bass"])
    chords, lead = Part("Chords", 1, SOUNDS["chords"]), Part("Lead", 2, SOUNDS["lead"])

    bass_pool = [[(2, 3, 0), (6, 2, 12), (10, 3, 0), (14, 2, 7)],
                 [(2, 2, 0), (5, 1, 0), (7, 2, 12), (10, 2, 0), (13, 1, 10), (14, 2, 7)],
                 [(0, 2, 0), (3, 2, 0), (6, 2, 12), (10, 4, 0), (14, 2, 3)],
                 [(2, 4, 0), (8, 1, 12), (10, 3, 0), (14, 1, 7), (15, 1, 10)]]
    bass_a, bass_b, bass_c = rnd.sample(bass_pool, 3)
    stab_pool = [(3, 6, 11), (2, 7, 10), (3, 7, 10, 14), (2, 6, 11, 14)]
    stab, stab2 = rnd.sample(stab_pool, 2)

    # リードの 4 小節フレーズ
    scale = {(tonic + i) % 12 for i in MINOR}
    pool = [n for n in range(67, 86) if n % 12 in scale]

    def nearest(target, cands):
        return min(cands, key=lambda n: abs(n - target))

    rhythm = rnd.choice([[0, 3, 6, 8, 10, 12], [0, 2, 4, 7, 10, 14], [0, 3, 4, 8, 11, 14], [0, 4, 6, 8, 12, 14]])
    phrase, prev = [], 76
    for b in range(4):
        tones = [n for n in pool if n % 12 in {x % 12 for x in chords_notes[b]}]
        for i, st in enumerate(rhythm):
            strong = st in (0, 8)
            n = nearest(prev + rnd.choice([-3, 0, 2, 4] if strong else [-2, -1, 1, 2]), tones if strong else pool)
            nxt = rhythm[i + 1] if i + 1 < len(rhythm) else 16
            phrase.append((b * 16 + st, max(1, nxt - st - (0 if strong else 1)), n))
            prev = n
    tonic_notes = [x for x in pool if x % 12 == tonic]

    markers, bar0 = [], 0
    for name, length, f in sections:
        markers.append((name, bar0))
        for i in range(length):
            bar, b0, ci = bar0 + i, (bar0 + i) * BAR, (bar0 + i) % 4
            last = i == length - 1
            fade = 1.0 - (i / length) * 0.6 if f.get("outro") else 1.0
            fill = f.get("fill") if last else None

            # --- ドラム ---
            if i == 0 and name != "Intro":
                drums.note(b0, BAR, CRASH, 90)
            if f.get("kick") and fill != "drop":
                for beat in range(4):
                    drums.note(b0 + beat * TPB, S16, KICK, 110 * fade)
            if f.get("kick") and fill == "drop":          # 最後の小節は 3 拍目までキック、4 拍目は抜く
                for beat in range(3):
                    drums.note(b0 + beat * TPB, S16, KICK, 110)
            if f.get("clap"):
                for beat in (1, 3):
                    drums.note(b0 + beat * TPB, S16, CLAP, 100 * fade)
            hats = f.get("hats")
            if hats and (f.get("open_from") is not None and i >= f["open_from"]):
                for beat in range(4):
                    drums.note(b0 + beat * TPB + 2 * S16, S16, OHH, 80 * fade)
            if hats == "closed":
                for step in range(16):
                    vel = 70 if step % 4 == 2 else 45 + rnd.randint(-6, 6)
                    drums.note(b0 + step * S16, S16 // 2, CHH, vel * fade)
            elif hats == "shaker":
                for step in range(0, 16, 2):
                    drums.note(b0 + step * S16, S16 // 2, SHAKER, 60 + rnd.randint(-8, 8))
            if f.get("rim") and bar % 2 == 1:
                drums.note(b0 + 14 * S16, S16, RIM, 85)
            if f.get("build"):                               # Build: スネアがだんだん細かく・大きく
                step = 4 if i < length // 2 else (2 if i < length - 2 else 1)
                for s in range(0, 16, step):
                    drums.note(b0 + s * S16, S16 // 2, SNARE, 50 + 60 * (i * 16 + s) / (length * 16))
            if fill == "roll":                               # 最後の 2 拍をスネアのロール
                for s in range(8, 16):
                    drums.note(b0 + s * S16, S16 // 2, SNARE, 60 + s * 4)

            # --- ベース ---
            kind = f.get("bass")
            if kind in ("groove", "groove2"):
                pat = (bass_a if bar % 2 == 0 else bass_b) if kind == "groove" else (bass_c if bar % 2 == 0 else bass_a)
                for st, ln, iv in pat:
                    if fill == "drop" and st >= 12:
                        continue
                    bass.note(b0 + st * S16, ln * S16, roots[ci] + iv, 100 * fade)
            elif kind == "hold":
                bass.note(b0, BAR - S16, roots[ci], 70)

            # --- 和音 ---
            ck = f.get("chords")
            if ck and i >= f.get("chords_from", 0):
                notes = chords_inv[ci] if ck == "stab2" else chords_notes[ci]
                if ck == "pad":
                    for n in notes:
                        chords.note(b0, BAR - 10, n, 60)
                else:
                    for st in (stab2 if ck == "stab2" else stab):
                        for n in notes:
                            chords.note(b0 + st * S16, S16 * 2, n, 78 * fade)

            # --- リード ---
            if f.get("lead") or (f.get("lead_soft") and i >= length // 2):
                rep, b_in = divmod(i, 4)
                soft = f.get("lead_soft")
                for idx, (st, ln, n) in enumerate(phrase):
                    if st // 16 != b_in:
                        continue
                    if soft and st % 16 not in (0, 8):          # Break 後半は強拍の音だけ、小さく
                        continue
                    last_note = idx == len(phrase) - 1 and (i + 4 >= length)
                    if last_note:
                        n = nearest(n, tonic_notes)              # 区間の最後は主音で終わる
                    lead.note(b0 + (st % 16) * S16, ln * S16 * (2 if soft else 1), n, 60 if soft else 90)
        bar0 += length
    total = bar0

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    meta = mido.MidiTrack([
        mido.MetaMessage("track_name", name=f"house_{key}m_{prog_name}_{seed}", time=0),
        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0),
        mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0),
        mido.MetaMessage("key_signature", key=f"{key}m", time=0),
    ])
    now = 0
    for name, start in markers:
        meta.append(mido.MetaMessage("marker", text=name, time=start * BAR - now))
        now = start * BAR
    meta.append(mido.MetaMessage("end_of_track", time=total * BAR - now))
    mid.tracks.append(meta)
    for p in (drums, bass, chords, lead):
        mid.tracks.append(p.track())
    return mid, total, markers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--form", default="short", choices=list(FORMS))
    ap.add_argument("--key", default="A", choices=list(NOTE))
    ap.add_argument("--bpm", type=int, default=122)
    ap.add_argument("--prog", default="deep", choices=list(PROGS))
    ap.add_argument("--seed", type=int, default=1)
    for part in SOUNDS:
        ap.add_argument(f"--{part}-prog", type=int, default=SOUNDS[part], dest=f"{part}_prog")
    a = ap.parse_args()
    for part in SOUNDS:
        SOUNDS[part] = getattr(a, f"{part}_prog")
    mid, total, markers = build(a.key, a.bpm, a.prog, a.seed, a.form)
    mid.save(a.out)
    spb = 240 / a.bpm
    print(f"saved {a.out}: {a.key}m {a.prog} seed={a.seed} {a.bpm} BPM, {total} bars = {total * spb:.1f}s")
    for name, start in markers:
        s = start * spb
        print(f"  {int(s // 60)}:{s % 60:04.1f}  {name}")


if __name__ == "__main__":
    main()
