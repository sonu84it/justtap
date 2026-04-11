STYLE_PROMPTS = {
    "magic": "Transform the image into a magical polished scene with luminous highlights, subtle spark effects, and whimsical depth.",
    "viral": "Transform the image into a bold viral social-media visual with crisp contrast, bright focal points, and scroll-stopping energy.",
    "cinematic": "Transform the image into a cinematic frame with dramatic lighting, filmic color grading, and premium storytelling atmosphere.",
    "fantasy": "Transform the image into a fantasy artwork with enchanted scenery, elevated wonder, and rich imaginative worldbuilding details.",
    "meme": "Transform the image into a playful meme-ready image with comedic exaggeration, punchy framing, and internet-native humor."
}


def get_style_prompt(style: str) -> str:
    try:
        return STYLE_PROMPTS[style]
    except KeyError as error:
        supported = ", ".join(STYLE_PROMPTS.keys())
        raise ValueError(f"Unsupported style '{style}'. Supported styles: {supported}.") from error
