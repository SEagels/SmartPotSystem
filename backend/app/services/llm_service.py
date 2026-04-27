from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting from LLM output for plain-text display."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    return text.strip()

_RULE_MESSAGES = {
    "good": [
        "今日环境适宜，土壤湿度维持在正常范围，植株状态良好。明日建议继续保持当前养护节奏。",
        "各项指标正常，植株生长环境稳定，无需调整养护策略。",
        "今日温湿度适宜，土壤水分充足，植株表现健康。",
    ],
    "dry": [
        "土壤湿度偏低，建议适当增加补水量或补水频率。下次预计补水时间可能提前。",
        "环境偏干，注意增加空气湿度，可考虑早晚叶面喷雾。",
    ],
    "wet": [
        "土壤湿度偏高，建议减少补水量，确保根部有充足氧气。",
        "环境偏湿，注意排水和通风，避免根部积水腐烂。",
    ],
    "hot": [
        "温度偏高，注意遮阴和通风，避免叶片灼伤。适当增加补水量。",
    ],
    "cold": [
        "温度偏低，注意保暖，减少补水频率，避免根部受冻。",
    ],
}

# 根据 API URL 自动选择模型名称
def _pick_model(url: str) -> str:
    url_lower = url.lower()
    if "deepseek" in url_lower:
        return "deepseek-chat"
    if "dashscope" in url_lower or "aliyun" in url_lower:
        return "qwen-plus"
    if "bigmodel" in url_lower:
        return "glm-4-flash"
    return "gpt-4o-mini"


async def generate_llm_suggestion(context: dict) -> tuple[str, dict]:
    if settings.LLM_API_KEY:
        try:
            result = await _call_llm(context)
            logger.info("LLM 养护建议生成成功")
            return result, {}
        except Exception as e:
            logger.warning("LLM 调用失败，回退到规则建议: %s", e)
    return generate_suggestion(
        context.get("environment_summary", {}),
        context.get("watering_count", 0),
        context.get("health_score", 100),
    )


def generate_suggestion(
    env: dict,
    watering_count: int,
    health_score: int,
) -> tuple[str, dict]:
    temp = env.get("temperature", {})
    humidity = env.get("humidity", {})
    soil = env.get("soil_moisture", {})

    temp_avg = temp.get("avg")
    soil_avg = soil.get("avg")
    hum_avg = humidity.get("avg")

    attention_items = []

    if soil_avg is not None and soil_avg < 25:
        suggestion = _RULE_MESSAGES["dry"][0]
        attention_items.append("土壤湿度偏低，建议增加补水")
    elif soil_avg is not None and soil_avg > 65:
        suggestion = _RULE_MESSAGES["wet"][0]
        attention_items.append("土壤湿度过高，注意排水")
    elif temp_avg is not None and temp_avg > 30:
        suggestion = _RULE_MESSAGES["hot"][0]
        attention_items.append("高温预警，注意遮阴")
    elif temp_avg is not None and temp_avg < 10:
        suggestion = _RULE_MESSAGES["cold"][0]
        attention_items.append("低温预警，注意保暖")
    elif health_score and health_score < 60:
        suggestion = "植株健康评分偏低，请检查叶片是否有病害迹象，必要时咨询园艺专家。"
        attention_items.append("健康评分偏低")
    else:
        import random
        suggestion = random.choice(_RULE_MESSAGES["good"])

    next_watering = "明日预计需补水1次，约50ml" if soil_avg is not None and soil_avg < 35 else "目前土壤湿度正常，暂不需要补水"
    detail = {
        "watering_recommendation": next_watering,
        "next_watering_time": None,
        "attention_items": attention_items,
    }

    return suggestion, detail


async def _call_llm(context: dict) -> str:
    env = context.get("environment_summary", {})
    has_data = any(
        env.get(k, {}).get("avg") is not None
        for k in ("temperature", "humidity", "soil_moisture")
    )

    if has_data:
        data_block = f"环境数据：{json.dumps(context, ensure_ascii=False)}"
        hint = ""
    else:
        data_block = f"上下文：{json.dumps(context, ensure_ascii=False)}"
        hint = "（注意：目前暂无传感器数据，请根据上下文给出通用养护提醒，建议用户先检查设备是否在线。）"

    prompt = f"""你是一位专业的园艺养护顾问。请根据以下植物传感器数据，用中文给出一段简短的养护建议（80-150字）：

{data_block}
{hint}
请从浇水、光照、温度、病害四个方面给出建议。如果有异常指标请重点提醒。语气亲切自然，像一位细心的园丁朋友。回答中不要使用任何 Markdown 格式标记（如 ** 或 # 等）。"""

    model = _pick_model(settings.LLM_API_URL)
    logger.info("调用 LLM: url=%s model=%s", settings.LLM_API_URL, model)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            settings.LLM_API_URL,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        return _strip_markdown(raw)
