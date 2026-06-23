import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.dashboard')


def load_opp_full_text(core, file_id):
    """Load the full opportunity markdown from storage/opportunities by matching id in frontmatter"""
    opp_dir = core.settings.storage_path / 'opportunities'
    if not opp_dir.exists():
        return ''
    for f in opp_dir.glob('*.md'):
        try:
            text = f.read_text(encoding='utf-8')
            if 'id: ' + repr(file_id) in text or file_id in text[:200]:
                # Remove frontmatter, return body
                body = text.strip()
                if body.startswith('---'):
                    end = body.find('---', 3)
                    if end != -1:
                        body = body[end + 3:].strip()
                return body
        except Exception:
            pass
    return ''


def update_dashboard(core):
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
    lines.append('- **状态**: NORMAL')
    lines.append('- **模型**: qwen3:8b')
    lines.append('')
    lines.append('---')
    lines.append('')

    if decisions.get('decisions'):
        lines.append('## 今日 TOP' + str(len(decisions['decisions'])) + ' 赚钱机会')
        lines.append('')
        for i, d in enumerate(decisions['decisions'], 1):
            # Load full content
            full = load_opp_full_text(core, d['id'])
            lines.append('### ' + str(i) + '. ' + d['title'][:60])
            lines.append('')
            lines.append('**评分**: ' + str(d['score']) + '  |  **决策分**: ' + str(d['decision_score']))
            lines.append('**速度**: ' + d['speed'] + '  |  **变现**: ' + d['monetization'] + '  |  **难度**: ' + str(d.get('difficulty', '?')))
            lines.append('')
            if full:
                lines.append(full)
            else:
                lines.append('*详情见机会文件*')
            lines.append('')
            lines.append('---')
            lines.append('')
    else:
        lines.append('*暂无决策数据*')
        lines.append('')
        lines.append('---')
        lines.append('')

    lines.append('## 我的反馈')
    lines.append('')
    lines.append('把你的想法写在这里，灵机会记住：')
    lines.append('')
    lines.append('- **喜欢的机会**: ')
    lines.append('- **不感兴趣的**: ')
    lines.append('- **已执行的**: ')
    lines.append('- **新想法**: ')
    lines.append('')
    lines.append('---')
    lines.append('')

    log_path = Path(core.settings.log_dir) / 'journal' / ('journal_' + now.strftime('%Y%m%d') + '.jsonl')
    if log_path.exists():
        lines.append('## 最近日志')
        lines.append('')
        entries = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l:
                    try:
                        entries.append(json.loads(l))
                    except Exception:
                        pass
        for entry in entries[-5:]:
            lines.append('- ' + entry.get('timestamp', '')[:19] + ' ' + entry.get('action', ''))
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('**备份目录**: ' + str(core.settings.backup_path))

    dash_dir = core.settings.vault_path / 'PEMIS' / 'dashboard'
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_file = dash_dir / 'Control Center.md'
    with open(dash_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logger.info('Control Center updated with full opportunity content')