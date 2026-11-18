# TouchDesigner の Textport で 1 回だけ実行する:
#   import os; exec(open(os.path.expanduser('~/StrudelTD/td_watch.py'), encoding='utf-8').read())
# 同じフォルダの td_inbox.py が更新されたら、TD の中で自動実行する「監視役」(td_watch)を作る。
# 結果と出力・エラーは td_inbox.log に書く。消すには TD で /project1/td_watch を削除する(TD を閉じても消える)。
root = op('/project1')
old = root.op('td_watch')
if old:
    old.destroy()
d = root.create(executeDAT, 'td_watch')
d.nodeX, d.nodeY = -300, -450
d.text = '''
import os, io, time, traceback, contextlib
import td

DIR = os.path.expanduser(os.environ.get('STRUDELTD_DIR', '~/StrudelTD')) + '/'
INBOX = DIR + 'td_inbox.py'
LOG = DIR + 'td_inbox.log'
state = {'m': os.path.getmtime(INBOX) if os.path.exists(INBOX) else 0}


def onFrameStart(frame):
    if frame % 15:
        return
    try:
        m = os.path.getmtime(INBOX)
    except OSError:
        return
    if m <= state['m']:
        return
    state['m'] = m
    buf = io.StringIO()
    t0 = time.time()
    try:
        code = open(INBOX, encoding='utf-8').read()
        g = dict(vars(td))
        g['__name__'] = '__inbox__'
        with contextlib.redirect_stdout(buf):
            exec(compile(code, INBOX, 'exec'), g)
        status = 'OK'
    except BaseException:
        buf.write(traceback.format_exc())
        status = 'ERROR'
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('%s %s (%.2fs)\\n' % (time.strftime('%H:%M:%S'), status, time.time() - t0))
        f.write(buf.getvalue())
    return
'''
try:
    d.par.framestart = 1
except Exception as e:
    print('framestart:', e)
try:
    d.par.active = 1
except Exception as e:
    print('active:', e)
print('td_watch ready. 監視中:', d.path)
