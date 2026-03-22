from services.openrouter_client import OpenRouterClient


def test_layered_shot_mode_tightens_prompt():
    client = OpenRouterClient()

    prompt = client._create_bar_prompt(
        "Professional cocktail photography of one B-52 layered shot.",
        generation_mode="layered_shot",
    ).lower()

    assert "strict layered shot rendering mode" in prompt
    assert "do not invent extra bands" in prompt


def test_layered_shot_mode_negative_prompt_is_stricter():
    client = OpenRouterClient()

    negative = client._build_negative_prompt("layered_shot").lower()

    assert "fourth layer" in negative
    assert "wrong layer order" in negative
    assert "duplicate shot" in negative
