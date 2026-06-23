import json, logging, shutil
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.dashboard')

OPP_VAULT_DIR = 'PEMIS/opportunities'


def sync_opps_to_vault(core):
    src = core.settings.storage_path / 'opportunities'
    dst = core.settings.vault_path / OPP_VAULT_DIR
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in src.glob('*.md'):
        try:
            shutil.copy2(f, dst / f.name)
            copied += 1
        except Exception:
            pass
    for f in dst.glob('*.md'):
        if not (src / f.name).exists():
            f.unlink()
    if copied:
        logger.info('Synced %d opportunities to vault', copied)


def load_opp_summary(core, file_id):
    opp_dir = core.settings.storage_path / 'opportunities'
    if not opp_dir.exists():
        return '', ''
    for f in opp_dir.glob('*.md'):
        try:
            text = f.read_text(encoding='utf-8')
            if 'id: ' + repr(file_id) in text or file_id in text[:200]:
                title = ''
                for line in text.splitlines():
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                body = text.strip()
                if body.startswith('---'):
                    end = body.find('---', 3)
                    if end != -1:
                        body = body[end + 3:].strip()
                summary_lines = []
                found_title = False
                for line in body.splitlines():
                    if line.startswith('# '):
                        found_title = True
                        continue
                    if found_title and line.strip() and not line.startswith('**Score'):
                        summary_lines.append(line.strip())
                        if len(''.join(summary_lines)) > 200:
                            break
                summary = ' '.join(summary_lines)[:300]
                return title, summary
        except Exception:
            pass
    return '', ''


def get_opp_filename(core, opp_id):
    opp_dir = core.settings.storage_path / 'opportunities'
    if not opp_dir.exists():
        return ''
    for f in opp_dir.glob('*.md'):
        try:
            txt = f.read_text(encoding='utf-8')
            if 'id: ' + repr(opp_id) in txt or opp_id in txt[:200]:
                return f.name
        except Exception:
            pass
    return ''


def update_dashboard(core):
    sync_opps_to_vault(core)

    decisions = core.decision.get_latest()
    now = datetime.now()
    fmt = '%Y-%m-%d %H:%M:%S'
    vp = core.settings.vault_path

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
    lines.append('- **模型**: ' + core.settings.llm_model)
    lines.append('- **备用模型**: ' + core.settings.fallback_llm)
    lines.append('')
    lines.append('---')
    lines.append('')

    if decisions.get('decisions'):
        lines.append('## 今日 TOP' + str(len(decisions['decisions'])) + ' 赚钱机会')
        lines.append('')

        for i, d in enumerate(decisions['decisions'], 1):
            opp_title, opp_summary = load_opp_summary(core, d['id'])
            opp_filename = get_opp_filename(core, d['id'])

            lines.append('### ' + str(i) + '. ' + (opp_title or d['title'][:60]))
            lines.append('')
            lines.append('**评分**: ' + str(d['score']) + '  |  **决策分**: ' + str(d['decision_score']))
            lines.append('**速度**: ' + d['speed'] + '  |  **变现**: ' + d['monetization'] + '  |  **难度**: ' + str(d.get('difficulty', '?')))
            lines.append('')

            if opp_summary:
                lines.append('> ' + opp_summary)
                lines.append('')

            if opp_filename:
                target = OPP_VAULT_DIR + '/' + opp_filename
                link_text = target.replace('.md', '')
                lines.append('📄 **查看完整分析**: [[' + link_text + '|' + (opp_title or d['title'][:40]) + ']]')
                lines.append('')

            # Per-opportunity feedback
            lines.append('**我的反馈**:')
            lines.append('- 感兴趣程度（1-5）: ')
            lines.append('- 我能做吗: ')
            lines.append('- 打算什么时候执行: ')
            lines.append('- 备注: ')
            lines.append('')
            lines.append('---')
            lines.append('')
    else:
        lines.append('*暂无决策数据*')
        lines.append('')
        lines.append('---')
        lines.append('')

    # All opportunities table
    lines.append('## 全部机会列表')
    lines.append('')
    lines.append('| 文件名 | 评分 | 速度 | 变现 |')
    lines.append('|--------|------|------|------|')
    opp_dir_storage = core.settings.storage_path / 'opportunities'
    if opp_dir_storage.exists():
        for f in sorted(opp_dir_storage.glob('*.md')):
            try:
                txt = f.read_text(encoding='utf-8')
                score = '0'
                speed = '-'
                mon = '-'
                for l in txt.splitlines():
                    if l.startswith('score:'):
                        score = l.split(':')[1].strip().strip("'").strip('"')
                    elif l.startswith('speed:'):
                        speed = l.split(':')[1].strip()
                    elif l.startswith('monetization:'):
                        mon = l.split(':')[1].strip().strip("'").strip('"')
                target = OPP_VAULT_DIR + '/' + f.name
                link_text = target.replace('.md', '')
                lines.append('| [[' + link_text + '|' + f.name.replace('.md', '') + ']] | ' + score + ' | ' + speed + ' | ' + mon + ' |')
            except Exception:
                pass
    lines.append('')
    lines.append('---')
    lines.append('')

    # Feedback already recorded indicator
    prefs = {}
    prefs_path = core.settings.storage_path / 'user_preferences.json'
    if prefs_path.exists():
        try:
            prefs = json.loads(prefs_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    if prefs:
        lines.append('## 我已记录的反馈')
        lines.append('')
        if prefs.get('liked'):
            for item in prefs['liked']:
                lines.append('- 👍 **喜欢**: ' + item.get('content', '')[:100])
        if prefs.get('disliked'):
            for item in prefs['disliked']:
                lines.append('- 👎 **不感兴趣**: ' + item.get('content', '')[:100])
        if prefs.get('executed'):
            for item in prefs['executed']:
                lines.append('- ✅ **已执行**: ' + item.get('content', '')[:100])
        if prefs.get('failed'):
            for item in prefs['failed']:
                lines.append('- ❌ **失败**: ' + item.get('content', '')[:100])
        lines.append('')
        lines.append('---')
        lines.append('')

    # Feedback writing area
    lines.append('## 写反馈')
    lines.append('')
    lines.append('把下面填写好后保存文件，灵机会自动读取：')
    lines.append('')
    lines.append('- **喜欢的机会**: ')
    lines.append('- **不感兴趣的**: ')
    lines.append('- **已执行的**: ')
    lines.append('- **失败的**: ')
    lines.append('- **新想法**: ')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Recent logs
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

    dash_dir = vp / 'PEMIS' / 'dashboard'
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_file = dash_dir / 'Control Center.md'
    with open(dash_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logger.info('Control Center updated with full opp links and feedback section')