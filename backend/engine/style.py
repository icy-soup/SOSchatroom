"""Style Layer — apply tone/style adjustments based on addressee relationships."""

from config import CONFIG


def get_style_params(speaker: str, addressee: str) -> dict:
    """Get style adjustment parameters for a speaker-addressee pair."""
    adjustments = CONFIG.get("addressee_style_adjustment", {})
    speaker_adjust = adjustments.get(speaker, {})
    pair_adjust = speaker_adjust.get(addressee, {})
    return {
        "label": pair_adjust.get("label", "中性"),
        "adjust": pair_adjust.get("adjust", {}),
    }


def build_style_instruction(speaker: str, addressee: str) -> str:
    """Build a natural language style instruction for the LLM."""
    params = get_style_params(speaker, addressee)
    label = params["label"]

    label_instructions = {
        "亲近": f"你对{addressee}态度亲近，可以使用亲昵称呼。",
        "亲近/热烈": f"你对{addressee}态度亲近热情，语气可以热烈一些。",
        "亲近/敬语": f"你对{addressee}态度亲近但保持敬语。",
        "亲近/冷静": f"你对{addressee}态度亲近但语气冷静。",
        "疏离": f"你和{addressee}不太熟，保持距离。",
        "疏离/冷静": f"你和{addressee}不太熟，语气冷静保持距离。",
        "热烈": f"你对{addressee}态度热情！",
        "中性": "",
        "冷静/敬语": f"你对{addressee}保持冷静和礼貌。",
        "敬语": f"你对{addressee}保持敬语礼貌。",
    }

    return label_instructions.get(label, "")
