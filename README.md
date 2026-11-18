# musictk

[![CI](https://github.com/masatomoto-cmyk/music-tech-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/masatomoto-cmyk/music-tech-toolkit/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**音楽機材・DAW・映像ツールをつなぐ、小さな Python ツール集。**
Small Python tools that connect music hardware, DAWs and live visuals.

自分の音楽制作（Roland S-1 / P-6、Logic Pro、FL Studio、TouchDesigner、OBS、Blender）の中で
繰り返し使った作業を、テストつきのコマンドと関数に整理したものです。
These grew out of my own music production workflow and were cleaned up into tested, documented commands.

## 何ができるか / What's inside

| 領域 | モジュール | できること |
|---|---|---|
| 機材 Hardware | `musictk.hardware.s1` | Roland S-1 を USB MIDI で操作（つまみ名で CC 送信、音出し、**USB 音声を録って音量と音程を測る**） |
| | `musictk.hardware.bassline` | S-1 用のアシッドベースを MIDI ファイルに書き出す（フィルターの動き入り・シード固定） |
| | `musictk.hardware.phrase` | P-6 のベースの各小節の根音に合わせて、S-1 のリフを自動生成 |
| | `musictk.hardware.jam` | S-1 をその場で鳴らして、フィルターを開閉する |
| MIDI | `musictk.midi.spy` / `replay` | 仮想 MIDI ポートで DAW の出力を **時刻つきで記録** し、**同じタイミングで再生**（Logic 経由か直接かの切り分けに使う） |
| DAW | `musictk.daw.logic_house` | Logic Pro 用のハウス曲を MIDI で生成（Drums / Bass / Chords / Lead、区間マーカー・テンポ・調つき） |
| | `musictk.daw.flp` | FL Studio の `.flp` を読む最小パーサー（4 種類のイベント長に対応） |
| 映像 Visuals | `musictk.visuals.obs_bind` | OBS WebSocket でキャプチャ元のウィンドウを付け直し、指定秒数だけ録画 |
| | `musictk.visuals.blender_audio_react` | 曲を 1 コマずつ周波数分析して、Blender の明かりや物にキーを打つ |
| | `touchdesigner/td_watch.py` | ファイルを書き換えるだけで TouchDesigner 内のコードを実行する監視役（編集 → 即反映のループ） |
| 研究 Research | `musictk.research.subtitles` | YouTube の字幕（WebVTT / json3）を `[分:秒] 文` の行に整える |

## 使い方 / Quick start

```bash
git clone https://github.com/masatomoto-cmyk/music-tech-toolkit.git
cd music-tech-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # OBS 連携も使うなら ".[dev,obs]"
pytest -q
```

```bash
# S-1 のつまみを動かして、ドの音を 1 秒鳴らす
s1 set cutoff=40 reso=90
s1 note C4 --dur 1

# S-1 用ベースラインを 8 小節ぶん MIDI にする（同じ seed なら毎回同じ結果）
s1-bassline bass.mid --bpm 128 --bars 8 --key C --seed 1

# Logic に読み込ませるハウス 1 曲分（約 3 分）
house-midi house.mid --form full --key A --bpm 122 --prog deep --seed 1

# DAW の MIDI 出力を記録 → あとから同じ間隔で再生
midi-spy session.log
midi-replay session.log --only note,control_change --from 10 --to 40
```

## 設計メモ / Design notes

- **MIDI を書く部分は「純粋な関数」に分けてある**（`bassline.build_events`、`phrase.bar_roots`、`logic_house.build` など）。
  機材がなくても CI でテストできます。ポートを開く処理は `main()` の中だけ。
- 乱数は `--seed` で固定。同じ入力なら同じ MIDI が出るので、DAW 側の差分を見比べられます。
- ノート・CC の同時刻の並びは「ノートオフ → CC → ノートオン」に統一（`hardware/common.py`）。
  新しい音を鳴らす前にフィルターを動かし終えるためです。
- S-1 の CC 番号は Roland 公式マニュアル（S-1 v1.02 Control change list）と照合。
  `tests/test_s1.py` で番号の重複・範囲外を検出します。
- 機材が要るもの（S-1 への送信、OBS、Blender、TouchDesigner）は、動作を自分の環境（macOS）で確認したものだけを載せています。

## ディレクトリ

```
src/musictk/
  hardware/   Roland S-1 / P-6
  midi/       MIDI の記録と再生
  daw/        Logic Pro / FL Studio
  visuals/    OBS / Blender
  research/   字幕の整形
touchdesigner/  TouchDesigner の中で動かすスクリプト
tests/          pytest（機材なしで動く）
```

## 動作環境 / Requirements

Python 3.10+、[mido](https://mido.readthedocs.io/)、python-rtmidi。OBS 連携は `obsws-python`。
実機の操作は macOS（USB MIDI）で確認しています。

## ライセンス / License

MIT — see [LICENSE](LICENSE).
