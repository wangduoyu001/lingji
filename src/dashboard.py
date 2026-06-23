import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.dashboard')


def update_dashboard(core):
    status = core.status()
    decisions = core.decision.get_latest()
    now = datetime.now()
    fmt = '%Y-%m-%d %H:%M:%S'

    lines = []
    lines.append('---')
    lines.append('type: dashboard')
    lines.append('updated: ' + now.isoformat())
    lines.append('---')
    lines.append('')
    lines.append('# LingJi Control Center')
    lines.append('')
    lines.append('> *Last updated: ' + now.strftime(fmt) + '*')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## System Status')
    lines.append('')
    mode_icon = {'NORMAL': 'Green', 'DEGRADED': 'Yellow', 'SAFE': 'Red'}
    icon = mode_icon.get(status['mode'], 'White')
    lines.append('- **Status**: ' + icon + ' ' + status['mode'])
    lines.append('- **Uptime**: ' + status['uptime'])
    lines.append('- **Primary Model**: ' + status['primary_model'])
    lines.append('- **Fallback Model**: ' + status['fallback_model'])
    lines.append('- **Embed Model**: ' + status['embed_model'])
    fa = 'Yes' if status.get('fallback_embed_active',False) else 'No'
    lines.append('- **Fallback Active**: ' + fa)
    lines.append('- **Cache Size**: ' + str(status.get('cache_size',0)) + ' entries')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Data Stats')
    lines.append('')
    lines.append('- **Total Opportunities**: ' + str(status['index_entries']))
    lines.append('- **Errors**: ' + str(status.get('error_count',0)))
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Top 3 Money Opportunities')
    lines.append('')

    if decisions.get('decisions'):
        for i, d in enumerate(decisions['decisions'], 1):
            lines.append('### ' + str(i) + '. ' + d['title'][:60])
            lines.append('')
            lines.append('- **MoneyScore**: ' + str(d['decision_score']))
            lines.append('- **Score**: ' + str(d['score']))
            lines.append('- **Speed**: ' + d['speed'])
            lines.append('- **Monetization**: ' + d['monetization'])
            lines.append('- **Difficulty**: ' + str(d.get('difficulty', '?')))
            lines.append('- **Recommendation**: ' + d.get('recommendation', ''))
            lines.append('- **Summary**: ' + d.get('summary', '')[:200])
            lines.append('')
    else:
        lines.append('*No decision data yet.*')
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('## Recent Logs')
    lines.append('')
    log_file = Path(core.settings.log_dir) / 'journal' / ('journal_' + now.strftime('%Y%m%d') + '.jsonl')
    if log_file.exists():
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l:
                    try:
                        logs.append(json.loads(l))
                    except Exception:
                        pass
        for entry in logs[-20:]:
            ts = entry.get('timestamp', '')[:19]
            action = entry.get('action', '')
            result = entry.get('result', '')
            lines.append('- [' + ts + '] ' + action + ' -> ' + result)
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Backup')
    lines.append('')
    lines.append('- **Snapshot dir**: ' + str(core.settings.backup_path) + '')
    lines.append('- **Decision history**: 90 days')
    lines.append('- **Git**: wangduoyu001/pemis-lingji')
    lines.append('')

    dash_dir = core.settings.vault_path / 'PEMIS' / 'dashboard'
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_file = dash_dir / 'Control Center.md'
    with open(dash_file, 'w', encoding='utf-8') as f:
        f.write(chr(10).join(lines))
    logger.info('Control Center updated')
