# Run after OBS is up:  python -m musictk.visuals.obs_bind [--record 65]
# obs-websocket で「StrudelTD OUT」と Strudel の Chrome ウィンドウを探し、キャプチャ元に入れる
# (ウィンドウの番号は起動するたびに変わるため、毎回これで付け直す)。
# --record 秒数 を付けると、その秒数だけ録画して止める。
import argparse
import json
import time
from pathlib import Path

import obsws_python as obs

ap = argparse.ArgumentParser()
ap.add_argument('--record', type=float, default=0, help='録画する秒数(0 なら録画しない)')
args = ap.parse_args()

cfg = json.loads((Path.home() / 'Library/Application Support/obs-studio/plugin_config/obs-websocket/config.json').read_text())
cl = obs.ReqClient(host='localhost', port=cfg['server_port'],
                   password=cfg['server_password'] if cfg.get('auth_required') else None, timeout=5)

TARGETS = {
    'TD 映像 (StrudelTD OUT)': lambda n: 'StrudelTD OUT' in n,
    'Strudel (Chrome)': lambda n: 'strudel' in n.lower() and 'chrome' in n.lower(),
}
ok = True
for src, match in TARGETS.items():
    items = cl.get_input_properties_list_property_items(src, 'window').property_items
    hit = [i for i in items if match(i['itemName'])]
    if not hit:
        ok = False
        print(f'NG {src}: ウィンドウが見つかりません。候補:')
        for i in items[:15]:
            print('   ', i['itemName'])
        continue
    cl.set_input_settings(src, {'window': hit[0]['itemValue']}, True)
    cl.set_input_mute(src, True)  # 音は BlackHole 2ch だけから録る
    print(f'OK {src} <- {hit[0]["itemName"]}')

# 録音の音量をそろえる: 圧縮(小さいジャンルを持ち上げる)→ リミッター(-3 dB。mp4 にしたあとも 0 dB を超えない)。2回目からはそのまま
have = {f['filterName'] for f in cl.get_source_filter_list('BlackHole 2ch').filters}
for name, kind, settings in [
    ('音量そろえ', 'compressor_filter', {'ratio': 2.0, 'threshold': -18.0, 'attack_time': 5, 'release_time': 80, 'output_gain': 7.0}),
    ('リミッター -3dB', 'limiter_filter', {'threshold': -3.0, 'release_time': 60}),
]:
    if name not in have:
        cl.create_source_filter('BlackHole 2ch', name, kind, settings)
print('BlackHole 2ch のフィルター:', [f['filterName'] for f in cl.get_source_filter_list('BlackHole 2ch').filters])

v = cl.get_video_settings()
print(f'キャンバス {v.base_width}x{v.base_height} / 出力 {v.output_width}x{v.output_height} / '
      f'{v.fps_numerator / v.fps_denominator:g}fps')

if args.record and ok:
    cl.start_record()
    print(f'録画中... {args.record:g} 秒')
    time.sleep(args.record)
    print('保存先:', cl.stop_record().output_path)
