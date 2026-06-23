"""OppGenerator: calls Ollama/qwen to analyze vault content and generate opportunity cards."""
import json, logging, hashlib, os, re, uuid
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.oppgen')

OLLAMA_URL = 'http://127.0.0.1:11434/api/chat'


class OppGenerator:
    def __init__(self, settings, index):
        self.settings = settings
        self.index = index
        self.opp_dir = settings.storage_path / 'opportunities'
        self.opp_dir.mkdir(parents=True, exist_ok=True)
        self.model = settings.llm_model
        self.fallback_model = settings.fallback_llm

    def _call_ollama(self, prompt, model=None):
        import requests
        m = model or self.model
        for attempt in range(2):
            try:
                resp = requests.post(
                    OLLAMA_URL,
                    json={'model': m, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
                    timeout=300
                )
                resp.raise_for_status()
                return resp.json().get('message', {}).get('content', '')
            except Exception as e:
                logger.warning('Ollama call failed (%s attempt %d): %s', m, attempt + 1, e)
                if m != self.fallback_model:
                    m = self.fallback_model
                    logger.info('Falling back to %s', m)
                else:
                    return ''
        return ''

    def generate_opportunity(self, source_label, source_files_text):
        """Call qwen to analyze a batch of vault content and produce an opportunity card."""
        prompt = """你是一个赚钱机会分析师。分析下面知识库内容，给出一个赚钱机会。

输出格式：
---
score: 0.85
type: opportunity
speed: fast
monetization: 带货|信息差|服务
difficulty: 2
tags: #标签1 #标签2
---
# 标题

**可行性分析**：
- 为什么可以做：原因
- 参考案例：案例
- 所需条件：条件

**执行方案**：
- 第1-3天：动作
- 第4-10天：动作
- 第11天起：动作
- 第3周起：动作

---

知识库内容：
""" + source_files_text[:3000]

        response = self._call_ollama(prompt)

        # Try to extract frontmatter and body
        if '---' in response:
            try:
                parts = response.split('---')
                if len(parts) >= 3:
                    body = '---' + parts[1] + '---' + '---'.join(parts[2:])
                else:
                    body = response
            except Exception:
                body = response
        else:
            body = response

        # Extract score for frontmatter
        score = 0.5
        m = re.search(r'score:\s*([\d.]+)', response)
        if m:
            try:
                score = float(m.group(1))
            except ValueError:
                pass

        # Generate id
        oid = str(uuid.uuid4())
        body = re.sub(r'id:\s*["\']?[^"\'\n]+["\']?', 'id: ' + repr(oid), body)

        # Save file
        # Extract title for filename
        title_match = re.search(r'#\s+(.+)', body)
        title = title_match.group(1).strip() if title_match else 'opportunity'
        safe = ''.join(c for c in title if c.isalnum() or c in ' _-').strip()[:30].lower().replace(' ', '_')
        if not safe:
            safe = 'opp'
        fname = 'opp_' + safe + '.md'
        fpath = self.opp_dir / fname
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(body)

        logger.info('Generated opportunity: %s (score=%.2f)', fname, score)
        return {
            'file': fname,
            'score': score,
            'title': title,
            'path': str(fpath),
        }

    def scan_and_generate(self):
        """Scan vault content and generate new opportunity cards."""
        entries = self.index.get_all()
        # Group by directory
        vault_notes = [e for e in entries if e.get('source') == 'vault' and e.get('type') == 'note']
        if not vault_notes:
            logger.warning('No vault notes to analyze')
            return []

        # Pick the largest notes by content_hash length (proxy for content richness)
        # Actually load content to analyze
        loaded = []
        for e in vault_notes[:50]:  # max 50 files per scan
            # Try to find the actual file
            for root, dirs, files in os.walk(str(self.settings.vault_path)):
                for fn in files:
                    if fn.endswith('.md') and (fn.startswith(e['id']) or e['id'] in fn):
                        fp = os.path.join(root, fn)
                        try:
                            text = open(fp, 'r', encoding='utf-8').read()
                            if len(text) > 100:
                                loaded.append((e['id'], e.get('title', ''), text[:2000]))
                        except Exception:
                            pass
                        break
                if len(loaded) > 20:
                    break
            if len(loaded) > 20:
                break

        if not loaded:
            logger.warning('Could not load any vault file content')
            return []

        # Group into batches by topic
        batches = self._group_by_topic(loaded)
        results = []

        for label, texts in batches.items():
            combined = '\n\n---\n\n'.join(texts[:5])  # max 5 files per call
            if len(combined) < 200:
                continue
            result = self.generate_opportunity(label, combined)
            if result:
                results.append(result)

        logger.info('Scan complete: generated %d opportunities from %d batches', len(results), len(batches))
        return results

    def _group_by_topic(self, loaded):
        """Simple grouping by directory/file prefix."""
        groups = {}
        for eid, title, text in loaded:
            # Determine group from id/title pattern
            group = 'general'
            if '直播' in title or '话术' in title or '麻将' in title:
                group = '直播话术'
            elif 'AI' in title or '工具' in title or 'agent' in title.lower() or 'github' in title.lower():
                group = 'AI工具'
            elif '一人' in title or 'OPC' in title or '公司' in title:
                group = '一人公司'
            elif '灵感' in title or '文案' in title:
                group = '灵感文案'
            if group not in groups:
                groups[group] = []
            groups[group].append(text)
        return groups