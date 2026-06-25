import os, json, requests, logging, uuid
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("pemis.oppgen")

# DeepSeek API
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Fallback Ollama
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "qwen3:8b-q4_K_M"


class OppGenerator:
    def __init__(self, settings, index):
        self.settings = settings
        self.index = index
        self.opp_dir = settings.storage_path / "opportunities"
        self.opp_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.environ.get("DEEPSEEK_API_KEY") or getattr(settings, "deepseek_api_key", "")
        if not self.api_key:
            logger.warning("No DeepSeek API key found, checking .env...")
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("DEEPSEEK_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()
                        break

    def _call_deepseek(self, prompt):
        if not self.api_key:
            logger.warning("No DeepSeek API key, falling back to Ollama")
            return self._call_ollama(prompt)
        try:
            logger.info("Calling DeepSeek API...")
            resp = requests.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": "Bearer " + self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "max_tokens": 4096,
                    "temperature": 0.3
                },
                timeout=120
            )
            resp.raise_for_status()
            result = resp.json()
            text = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            logger.info(
                "DeepSeek responded: len=%d, prompt_tokens=%d, completion_tokens=%d",
                len(text),
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0)
            )
            return text
        except Exception as e:
            logger.warning("DeepSeek error: %s, falling back to Ollama", e)
            return self._call_ollama(prompt)

    def _call_ollama(self, prompt):
        logger.info("Falling back to Ollama %s ...", OLLAMA_MODEL)
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_predict": 4096, "temperature": 0.3}
                },
                timeout=120
            )
            resp.raise_for_status()
            text = resp.json()["message"]["content"]
            logger.info("Ollama responded: len=%d", len(text))
            return text
        except Exception as e:
            logger.warning("Ollama error: %s", e)
            return ""

    def _call_llm(self, prompt):
        """Try DeepSeek first, fallback to Ollama."""
        return self._call_deepseek(prompt)

    def _extract_json(self, text):
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
        try:
            fixed = text.strip()
            if fixed.startswith("'''"):
                fixed = fixed.split("'''")[1] if "'''" in fixed[3:] else fixed
                if fixed.startswith("json"):
                    fixed = fixed[4:]
            return json.loads(fixed)
        except Exception:
            pass
        return None

    def analyze_file(self, file_path):
        try:
            p = Path(file_path)
            text = p.read_text(encoding="utf-8")
        except Exception:
            return None
        if len(text.strip()) < 100:
            return None
        content = text.strip()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end+3:].strip()
        if len(content) < 50:
            return None

        prompt = (
            "你是一个编导思维的分析师。分析以下内容，用编导视角输出JSON。\n"
            "输出**只有**一个合法的JSON对象：\n"
            "{\n"
            '  "can_make_money": true/false,\n'
            '  "direction": "带货|信息差|服务|工具|SaaS|流量套利|知识付费|内容变现",\n'
            '  "title": "中文标题（15字以内）",\n'
            '  "summary": "详细分析摘要（300-500字，说明为什么能赚钱、目标用户画像、核心痛点、市场规模判断）",\n'
            '  "how": "具体操作步骤（300-500字，分步骤：1.准备工作 2.执行流程 3.推广方式 4.变现闭环。需要什么资源、预期成本和时间、第一个订单怎么来）",\n'
            '  "content_structure": "内容结构分析（100字以内：这个内容按什么逻辑组织的，适合什么形式）",\n'
            '  "operation_structure": "运营结构分析（100字以内：适合什么运营节奏、发布频率、平台选择）",\n'
            '  "business_structure": "商业结构分析（100字以内：变现路径怎么串联、利润点在哪、可扩展性）",\n'
            '  "risk_analysis": "风险分析（100字以内：平台政策风险、竞争风险、执行风险）",\n'
            '  "ai_replace_rate": "AI替代率0-100（数字，AI能完成这个工作的百分比。比如脚本撰写80%、剪辑50%、运营20%）",\n'
            '  "mvp": "最小可行产品（50字以内：最低成本起步方案，1-3天内能验证什么）",\n'
            '  "next_action": "下一步行动（50字以内：看完这个分析后马上该做的事）",\n'
            '  "reference": "真实的参考案例名称",\n'
            '  "reference_url": "案例链接（必须是真实可访问的网址。确实不知道就写空字符串）",\n'
            '  "difficulty": "1-5整数（1最简单、5最难）",\n'
            '  "speed": "fast|mid|slow",\n'
            '  "feasibility": "200字以内可行性分析",\n'
            '  "bottleneck": "100字以内执行卡点"\n'
            "}\n"
            "如果完全无法赚钱，can_make_money为false。\n"
            "注意：分析必须有深度，不能编造。参考案例必须真实。\n"
            "内容如下：\n" + content[:4000]
        )
        resp = self._call_llm(prompt)
        data = self._extract_json(resp) if resp else None
        if not data or not data.get("can_make_money"):
            return None
        return {
            "direction": str(data.get("direction", "服务")),
            "title": str(data.get("title", "")),
            "summary": str(data.get("summary", "")),
            "how": str(data.get("how", "")),
            "reference": str(data.get("reference", "")),
            "reference_url": str(data.get("reference_url", "")),
            "feasibility": str(data.get("feasibility", "")),
            "bottleneck": str(data.get("bottleneck", "")),
            "content_structure": str(data.get("content_structure", "")),
            "operation_structure": str(data.get("operation_structure", "")),
            "business_structure": str(data.get("business_structure", "")),
            "risk_analysis": str(data.get("risk_analysis", "")),
            "ai_replace_rate": str(data.get("ai_replace_rate", "0")),
            "mvp": str(data.get("mvp", "")),
            "next_action": str(data.get("next_action", "")),
            "difficulty": int(data.get("difficulty", 3)),
            "speed": str(data.get("speed", "mid")),
        }

    def generate_card(self, file_path, analysis):
        oid = str(uuid.uuid4())
        d = analysis.get("direction", "服务")
        title = analysis.get("title", "").strip()
        summary = analysis.get("summary", "").strip()
        how = analysis.get("how", "").strip()
        ref = analysis.get("reference", "").strip()
        ref_url = analysis.get("reference_url", "").strip()
        feasibility = analysis.get("feasibility", "").strip()
        bottleneck = analysis.get("bottleneck", "").strip()
        content_structure = analysis.get("content_structure", "").strip()
        operation_structure = analysis.get("operation_structure", "").strip()
        business_structure = analysis.get("business_structure", "").strip()
        risk_analysis = analysis.get("risk_analysis", "").strip()
        ai_replace_rate = analysis.get("ai_replace_rate", "0")
        mvp = analysis.get("mvp", "").strip()
        next_action = analysis.get("next_action", "").strip()
        difficulty = analysis.get("difficulty", 3)
        speed = analysis.get("speed", "mid")
        score = 0.5
        if summary and len(summary) > 100:
            score += 0.15
        if how and len(how) > 100:
            score += 0.15
        if ref:
            score += 0.05
        if ref_url:
            score += 0.05
        if difficulty <= 2:
            score += 0.1
        score = min(round(score, 2), 0.95)

        now = datetime.now().strftime("%Y-%m-%d")

        ref_section = ref
        if ref_url and ref_url.startswith("http"):
            ref_section = "[" + ref + "](" + ref_url + ")"
        elif ref_url:
            ref_section = ref + " (" + ref_url + ")"
        if not ref_section:
            ref_section = "待补充"

        body_parts = [
            "---",
            "id: " + repr(oid),
            "score: " + str(score),
            "type: opportunity",
            "speed: " + speed,
            "monetization: " + d,
            "source: auto_generated",
            "difficulty: " + str(difficulty),
            "confidence: " + str(round(score, 2)),
            "tags: #auto",
            "created: " + now,
            "---",
            "",
            "# " + title,
            "",
            "**Score**: " + str(score) + " | **速度**: " + speed + " | **变现方式**: " + d + " | **难度**: " + str(difficulty),
            "",
            "---",
            "",
            "## 分析摘要",
            "",
            summary or "待补充",
            "",
            "---",
            "",
            "## 操作思路",
            "",
            how or "待补充",
            "",
            "---",
        ]
        if feasibility:
            body_parts += ["## 可行性分析", "", feasibility, "", "---", ""]
        if bottleneck:
            body_parts += ["## 执行卡点", "", bottleneck, "", "---", ""]
        # Director thinking sections
        if content_structure:
            body_parts += ["## 内容结构", "", content_structure, "", "---", ""]
        if operation_structure:
            body_parts += ["## 运营结构", "", operation_structure, "", "---", ""]
        if business_structure:
            body_parts += ["## 商业结构", "", business_structure, "", "---", ""]
        if risk_analysis:
            body_parts += ["## 风险分析", "", risk_analysis, "", "---", ""]
        if ai_replace_rate and ai_replace_rate != "0":
            body_parts += ["## AI替代率", "", str(ai_replace_rate) + "%", "", "---", ""]
        if mvp:
            body_parts += ["## MVP最小方案", "", mvp, "", "---", ""]
        if next_action:
            body_parts += ["## 下一步行动", "", next_action, "", "---", ""]
        body_parts += [
            "## 参考案例",
            "",
            ref_section,
            "",
            "---",
            "",
            "> 此机会由灵机自动分析生成。你可以编辑修改或填写反馈。",
        ]
        body = "\n".join(body_parts)

        safe = ""
        for c in title[:15]:
            if c.isalnum() or c in " _-":
                safe += c
            elif '\u4e00' <= c <= '\u9fff':
                safe += c
            elif '\u3000' <= c <= '\u303f' or '\uff00' <= c <= '\uffef':
                safe += c
            else:
                safe += "_"
        safe = safe.strip(" _-").lower().replace(" ", "_") or "auto"
        fpath = self.opp_dir / ("opp_" + safe + ".md")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(body)
        logger.info("Generated: %s (%s)", fpath.name, title[:30])
        return {"file": fpath.name, "title": title}

    def scan_and_generate(self):
        logger.info("scan_and_generate: scanning vault for new opportunities...")
        count = 0
        for mf in self.settings.vault_path.rglob("*.md"):
            if "PEMIS" in str(mf):
                continue
            stem = mf.stem.lower()
            already = False
            for oppf in self.opp_dir.glob("*.md"):
                if stem in oppf.stem.lower():
                    already = True
                    break
            if already:
                continue
            try:
                analysis = self.analyze_file(mf)
                if analysis:
                    self.generate_card(mf, analysis)
                    count += 1
            except Exception as e:
                logger.error("Scan error for %s: %s", mf.name, e)
        if count:
            logger.info("scan_and_generate complete: %d new opportunities", count)
        return []

    def save_feedback(self, opp_id, interest, can_do, timing, notes):
        path = self.opp_dir / "feedback.json"
        fb = []
        if path.exists():
            try:
                fb = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        fb.append({
            "opp_id": opp_id,
            "interest": interest,
            "can_do": can_do,
            "timing": timing,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        })
        path.write_text(json.dumps(fb, ensure_ascii=False, indent=2), encoding="utf-8")
        return []
