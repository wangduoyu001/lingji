#!/usr/bin/env node
/**
 * Batch translate Obsidian i18n plugin entries using DeepSeek API via fetch.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const API_KEY = 'sk-78564dcc63104bcdb7d1694aca86fe41';
const API_URL = 'https://api.deepseek.com/v1/chat/completions';
const BASE = 'E:/obsidian/本地知识库/.obsidian/plugins/i18n/translations';
const OUT_DIR = 'E:/新建文件夹 (3)/2026-06-14-19-32-38/translated_output';

const PROMPT = `将以下英文UI文本翻译成简体中文。规则：
1. 保持HTML标签、代码变量名、URL、正则表达式完全不变
2. 只返回JSON数组，格式：["译文1","译文2",...]
3. 不要添加任何解释或额外内容`;

async function callAPI(messages) {
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const resp = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: 'deepseek-chat',
                    messages,
                    temperature: 0.1,
                    max_tokens: 4000,
                }),
                signal: AbortSignal.timeout(120000),
            });
            if (!resp.ok) {
                const err = await resp.text();
                console.log(`  HTTP ${resp.status} (attempt ${attempt+1}): ${err.slice(0, 200)}`);
                if (resp.status === 429) { await sleep(5000); continue; }
                return null;
            }
            const data = await resp.json();
            return data.choices?.[0]?.message?.content ?? null;
        } catch (e) {
            console.log(`  Error (attempt ${attempt+1}): ${e.message}`);
            await sleep(3000);
        }
    }
    return null;
}

async function translateBatch(entries, context) {
    const items = entries.map((e, i) => `${i+1}. ${e}`);
    const userMsg = context + items.join('\n');
    const text = await callAPI([
        { role: 'system', content: PROMPT },
        { role: 'user', content: userMsg },
    ]);
    if (!text) return { translations: null, error: 'API call failed' };

    const match = text.trim().match(/\[[\s\S]*\]/);
    if (!match) return { translations: null, error: `No JSON in: ${text.slice(0, 200)}` };

    try {
        let result = JSON.parse(match[0]);
        // Sometimes API returns extra/missing items - trim to match
        if (result.length > entries.length) {
            result = result.slice(0, entries.length);
        } else if (result.length < entries.length) {
            // Fill missing with original text
            while (result.length < entries.length) {
                result.push(entries[result.length]);
            }
        }
        return { translations: result, error: null };
    } catch (e) {
        return { translations: null, error: `JSON parse: ${e.message}` };
    }
}

function shouldTranslate(src) {
    if (!src || !src.trim()) return false;
    const s = src.trim().replace(/^["'`]|["'`]$/g, '');
    if (!s) return false;
    if (/^[\d.\-]+$/.test(s)) return false;
    return true;
}

async function translateFile(fname, pluginName) {
    const data = JSON.parse(readFileSync(join(BASE, fname), 'utf-8'));
    const entries = [];
    const refs = [];

    for (const [fk, sections] of Object.entries(data.dict)) {
        for (const [sk, items] of Object.entries(sections)) {
            items.forEach((item, i) => {
                const src = item.source || '';
                const tgt = item.target || '';
                if (src && src === tgt && shouldTranslate(src)) {
                    entries.push(src);
                    refs.push({ fk, sk, i });
                }
            });
        }
    }

    if (entries.length === 0) {
        console.log(`${pluginName}: already done, skipping`);
        return;
    }

    console.log(`${pluginName}: ${entries.length} entries to translate`);

    const BATCH = 20;
    let written = 0;

    for (let bi = 0; bi < entries.length; bi += BATCH) {
        const batch = entries.slice(bi, bi + BATCH);
        const batchNum = Math.floor(bi / BATCH) + 1;
        const totalBatches = Math.ceil(entries.length / BATCH);
        const ctx = `Batch ${batchNum}/${totalBatches} for ${pluginName}:\n`;

        for (let attempt = 0; attempt < 3; attempt++) {
            const { translations, error } = await translateBatch(batch, ctx);
            if (translations) {
                translations.forEach((trans, j) => {
                    const { fk, sk, i } = refs[bi + j];
                    data.dict[fk][sk][i].target = trans;
                });
                const done = Math.min(bi + BATCH, entries.length);
                const pct = Math.round(done / entries.length * 100);
                console.log(`  [${pluginName}] ${done}/${entries.length} (${pct}%)`);
                written = done;
                break;
            } else {
                console.log(`  Batch ${batchNum} attempt ${attempt+1}: ${error}`);
                await sleep(2000);
            }
        }

        // Save progress every 3 batches
        if (written > 0 && batchNum % 3 === 0) {
            writeFileSync(join(OUT_DIR, fname), JSON.stringify(data, null, 2), 'utf-8');
            console.log(`  [${pluginName}] progress saved to output dir`);
        }
        await sleep(300);
    }

    // Final write
    writeFileSync(join(OUT_DIR, fname), JSON.stringify(data, null, 2), 'utf-8');

    let total = 0, done = 0;
    for (const fk of Object.values(data.dict)) {
        for (const items of Object.values(fk)) {
            for (const item of items) {
                if (item.source) {
                    total++;
                    if (item.source !== item.target) done++;
                }
            }
        }
    }
    console.log(`${pluginName} COMPLETE: ${done}/${total} translated\n`);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    mkdirSync(OUT_DIR, { recursive: true });
    const files = [
        ['VjpNAAJ8mydZREJsJhz89EGu8J5-1Vy3.json', 'obsidian-tagfolder'],
        ['xeLgAhAvMDs6RTll9Udiv2vVwpVVdrrf.json', 'teleprompter-plus'],
    ];

    for (const [fname, pname] of files) {
        await translateFile(fname, pname);
        await sleep(1000);
    }

    console.log('ALL DONE!');
}

main().catch(e => {
    console.error('FATAL:', e);
    process.exit(1);
});
