import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.dashboard')

FEEDBACK_FILE = 'storage/feedback.json'


def update_dashboard(core):
    status = core.status()
    decisions = core.decision.get_latest()
    now = datetime.now()
    fmt = '%Y-%m-%d %H:%M:%S'

    lines = []
    lines.append('---')
    lines.append('类型: 看板')
    lines.append('更新时间: ' + now.isoformat())
    lines.append('---')
    lines.append('')
    lines.append('# 灵机控制中心')
    lines.append('')
    lines.append('> *更新时间: ' + now.strftime(fmt) + '*')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 系统状态')
    lines.append('')
    lines.append('- **状态**: ' + status['mode'])
    lines.append('- **运行时长**: ' + status['uptime'])
    lines.append('- **主模型**: ' + status['primary_model'])
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 今日 TOP6 赚钱机会')
    lines.append('')

    if decisions.get('decisions'):
        for i, d in enumerate(decisions['decisions'], 1):
            lines.append('### ' + str(i) + '. ' + d['title'][:60])
            lines.append('')
            lines.append('- **得分**: ' + str(d['decision_score']))
            lines.append('- **速度**: ' + d['speed'])
            lines.append('- **变现**: ' + d['monetization'])
            lines.append('- **难度**: ' + str(d.get('difficulty', '?')))
            lines.append('- **建议**: ' + d.get('recommendation', ''))
            lines.append('- **摘要**: ' + d.get('summary', '')[:200])
            lines.append('')
    else:
        lines.append('*暂无决策数据*')
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('## 我的反馈')
    lines.append('')
    lines.append('> 在下方写下你对这些机会的想法，灵机会记住你的偏好。')
    lines.append('')
    lines.append('- **喜欢的**: ')
    lines.append('- **不喜欢的**: ')
    lines.append('- **已执行的**: ')
    lines.append('- **失败的**: ')
    lines.append('- **新想法**: ')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 最近日志')
    lines.append('')
    log_path = Path(core.settings.log_dir) / 'journal' / ('journal_' + now.strftime('%Y%m%d') + '.jsonl')
    if log_path.exists():
        entries = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l:
                    try:
                        entries.append(json.loads(l))
                    except Exception:
                        pass
        for entry in entries[-10:]:
            ts = entry.get('timestamp', '')[:19]
            lines.append('- [' + ts + '] ' + entry.get('action', '') + ' -> ' + entry.get('result', ''))
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 备份')
    lines.append('')
    lines.append('- **备份目录**: ' + str(core.settings.backup_path))
    lines.append('- **决策历史**: 90 days')

    dash_dir = core.settings.vault_path / 'PEMIS' / 'dashboard'
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_file = dash_dir / 'Control Center.md'
    with open(dash_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logger.info('Control Center updated')