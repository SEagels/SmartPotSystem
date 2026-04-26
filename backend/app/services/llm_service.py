from __future__ import annotations

import json

import httpx

from app.config import settings

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


async def generate_llm_suggestion(context: dict) -> tuple[str, dict]:
    if settings.LLM_API_KEY:
        try:
            return await _call_llm(context), {}
        except Exception:
            pass
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
    prompt = f"""你是一位专业的园艺养护顾问。请根据以下植物传感器数据，用中文给出一段简短的养护建议（50-100字）：

环境数据：{json.dumps(context, ensure_ascii=False)}

请从浇水、光照、温度、病害四个方面给出建议。语气亲切自然。"""

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            settings.LLM_API_URL,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
