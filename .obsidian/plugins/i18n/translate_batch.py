#!/usr/bin/env python3
"""Batch translate Obsidian i18n plugin entries using curl subprocess."""
import json, re, sys, time, subprocess, os

API_KEY = 'sk-78564dcc63104bcdb7d1694aca86fe41'
API_URL = 'https://api.deepseek.com/v1/chat/completions'

def call_api_via_curl(messages):
    """Call DeepSeek API using curl subprocess."""
    body = json.dumps({
        'model': 'deepseek-chat',
        'messages': messages,
        'temperature': 0.1,
        'max_tokens': 4000
    })
    
    cmd = [
        'curl', '-s', '--connect-timeout', '30', '--max-time', '120',
        API_URL,
        '-H', f'Authorization: Bearer {API_KEY}',
        '-H', 'Content-Type: application/json',
        '-d', body
    ]
    
    for attempt in range(3):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=130)
            if result.returncode != 0:
                print(f'  curl error (attempt {attempt+1}): {result.stderr[:200]}', flush=True)
                time.sleep(3)
                continue
            data = json.loads(result.stdout)
            if 'choices' not in data:
                print(f'  API error: {data.get("error", data)}', flush=True)
                time.sleep(3)
                continue
            return data['choices'][0]['message']['content']
        except subprocess.TimeoutExpired:
            print(f'  curl timeout (attempt {attempt+1})', flush=True)
            time.sleep(3)
        except Exception as e:
            print(f'  Error (attempt {attempt+1}): {e}', flush=True)
            time.sleep(3)
    return None

def translate_batch(entries, context=''):
    prompt = """将以下英文UI文本翻译成简体中文。规则：
1. 保持HTML标签、代码变量名、URL、正则表达式完全不变
2. 只返回JSON数组，格式：["译文1","译文2",...]
3. 不要添加任何解释或额外内容"""
    
    items = [f"{i+1}. {e}" for i, e in enumerate(entries)]
    user_msg = context + '\n'.join(items)
    
    text = call_api_via_curl([
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': user_msg}
    ])
    
    if text is None:
        return None, 'API call failed'
    
    text = text.strip()
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return None, f'No JSON array found in: {text[:200]}'
    
    try:
        result = json.loads(match.group())
        return result, None
    except json.JSONDecodeError as e:
        return None, f'JSON parse error: {e} - {match.group()[:200]}'

def should_translate(src):
    if not src or not src.strip():
        return False
    stripped = src.strip().strip('"\'`')
    if not stripped:
        return False
    if stripped.replace('.','').replace('-','').isdigit():
        return False
    return True

def translate_file(filepath, plugin_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries_src = []
    refs = []
    
    for fk in data['dict']:
        for sk in data['dict'][fk]:
            for i, item in enumerate(data['dict'][fk][sk]):
                src = item.get('source', '')
                tgt = item.get('target', '')
                if src and src == tgt and should_translate(src):
                    entries_src.append(src)
                    refs.append((fk, sk, i))
    
    if not entries_src:
        print(f'{plugin_name}: all done, nothing to translate', flush=True)
        return
    
    print(f'{plugin_name}: {len(entries_src)} entries to translate', flush=True)
    
    BATCH = 20
    for bi in range(0, len(entries_src), BATCH):
        batch = entries_src[bi:bi+BATCH]
        batch_num = bi // BATCH + 1
        total_batches = (len(entries_src) + BATCH - 1) // BATCH
        
        ctx = f'Batch {batch_num}/{total_batches} for {plugin_name}:\n'
        
        for attempt in range(3):
            translations, err = translate_batch(batch, ctx)
            if translations is not None and len(translations) == len(batch):
                for j, trans in enumerate(translations):
                    idx = bi + j
                    fk, sk, ei = refs[idx]
                    data['dict'][fk][sk][ei]['target'] = trans
                done = min(bi + BATCH, len(entries_src))
                pct = done / len(entries_src) * 100
                print(f'  [{plugin_name}] {done}/{len(entries_src)} ({pct:.0f}%)', flush=True)
                break
            else:
                print(f'  Batch {batch_num} attempt {attempt+1} failed: {err}', flush=True)
                time.sleep(2)
        else:
            print(f'  Batch {batch_num} FAILED permanently', flush=True)
        time.sleep(0.3)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    total = sum(1 for fk in data['dict'] for sk in data['dict'][fk] for item in data['dict'][fk][sk] if item.get('source',''))
    done = sum(1 for fk in data['dict'] for sk in data['dict'][fk] for item in data['dict'][fk][sk] if item.get('source','') and item.get('source','') != item.get('target',''))
    print(f'{plugin_name} COMPLETE: {done}/{total}', flush=True)


if __name__ == '__main__':
    BASE = r'E:\obsidian\本地知识库\.obsidian\plugins\i18n\translations'
    files = [
        ('VjpNAAJ8mydZREJsJhz89EGu8J5-1Vy3.json', 'obsidian-tagfolder'),
        ('xeLgAhAvMDs6RTll9Udiv2vVwpVVdrrf.json', 'teleprompter-plus'),
    ]
    
    for fname, pname in files:
        translate_file(f'{BASE}/{fname}', pname)
        time.sleep(1)
    
    print('ALL DONE!', flush=True)
