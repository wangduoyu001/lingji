import json, logging, shutil
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.dashboard')

# === Vector Store Interface (reserved for future Qdrant) ===
# When Qdrant is enabled, this module will also:
# 1. Send opportunity cards to vector store
# 2. Provide semantic search over vault content
# 3. Sync content_hash changes to vector index
# === End Vector Store Interface ===

OPP_VAULT_DIR = 'PEMIS/opportunities'
DASH_VAULT_DIR = 'PEMIS/dashboard'


def sync_opps_to_vault(core):
    """Sync opportunities from storage to the Obsidian vault."""
    src = core.settings.storage_path / 'opportunities'
    dst = core.settings.vault_path / OPP_VAULT_DIR
    if not src.exists():
        logger.warning('Source opp dir not found: %s', src)
        return
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    removed = 0
    for f in src.glob('*.md'):
        try:
            shutil.copy2(f, dst / f.name)
            copied += 1
        except Exception as e:
            logger.error('Copy error %s: %s', f.name, e)
    # Remove files in dst that no longer exist in src
    dst_files = {f.name for f in dst.glob('*.md')}
    src_files = {f.name for f in src.glob('*.md')}
    for name in dst_files - src_files:
        try:
            (dst / name).unlink()
            removed += 1
        except Exception:
            pass
    if copied or removed:
        logger.info('Synced opportunities: %d copied, %d removed', copied, removed)


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
    """Compact Control Center: one screen, no scrolling needed."""
    sync_opps_to_vault(core)
    decisions = core.decision.get_latest()
    now = datetime.now()
    fmt = '%Y-%m-%d %H:%M'
    vp = core.settings.vault_path
    status = core.status() if hasattr(core, 'status') else {}

    lines = []
    lines.append('---')
    lines.append('类型: 看板')
    lines.append('更新时间: ' + now.isoformat())
    lines.append('---')
    lines.append('')
    lines.append('# 灵机控制中心')
    lines.append('')
    lines.append('> 更新时间: ' + now.strftime(fmt))
    lines.append('')
    lines.append('---')
    lines.append('')

    # Line 1: System status (one line)
    mode = status.get('mode', 'NORMAL')
    uptime = status.get('uptime', '刚刚启动')
    entries = status.get('index_entries', 0)
    fb_time = status.get('feedback_read')
    fb_str = fb_time.strftime('%H:%M') if fb_time else '-'
    lines.append('🟢 **' + str(mode) + '** | 运行 ' + str(uptime) + ' | ' + str(entries) + ' 条 | 反馈读取: ' + fb_str)
    lines.append('')

    # Line 2: Today's top 3 (one line each, compact)
    output = decisions.get('decisions', [])
    if output:
        lines.append('**💰 今天最值得做的3件事**')
        lines.append('')
        for i, d in enumerate(output[:3], 1):
            title = d['title'][:25]
            score = str(d['decision_score'])
            speed_icon = '⚡' if d.get('speed') == 'fast' else '🐢' if d.get('speed') == 'slow' else '➡️'
            lines.append(str(i) + '. ' + speed_icon + ' **' + title + '**  (评分 ' + score + ')')
            opp_filename = get_opp_filename(core, d['id'])
            if opp_filename:
                target = OPP_VAULT_DIR + '/' + opp_filename
                lines.append('   [[' + target.replace('.md', '') + '|查看详情 →]]')
            lines.append('')
    else:
        lines.append('*暂无决策*')
        lines.append('')
    lines.append('---')
    lines.append('')

    # Line 3: Quick feedback
    lines.append('**📝 反馈与备注**')
    lines.append('')
    lines.append('- 喜欢/感兴趣: ')
    lines.append('- 不感兴趣/放弃: ')
    lines.append('- 已开始执行: ')
    lines.append('- 我想到的新方向: ')
    lines.append('')
    lines.append('*(填好后保存，灵机自动读取)*')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Line 4: Last feedback record (compact)
    prefs_path = Path(core.settings.storage_path) / 'user_preferences.json'
    if prefs_path.exists():
        try:
            prefs = json.loads(prefs_path.read_text(encoding='utf-8'))
            records = []
            for key in ('liked', 'disliked', 'executed', 'failed'):
                items = prefs.get(key, [])
                if items:
                    label_map = {'liked':'👍','disliked':'👎','executed':'✅','failed':'❌'}
                    records.append(label_map.get(key, key) + ' ' + items[-1].get('content','')[:50])
            if records:
                lines.append('**最近反馈:**')
                lines.append('')
                for r in records[-3:]:
                    lines.append('- ' + r)
                lines.append('')
                lines.append('---')
                lines.append('')
        except Exception:
            pass

    # Write file
    dash_dir = vp / DASH_VAULT_DIR
    dash_dir.mkdir(parents=True, exist_ok=True)
    dash_file = dash_dir / 'Control Center.md'
    with open(dash_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logger.info('Control Center updated (compact)')
