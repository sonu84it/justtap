STYLE_PROMPTS = {
    "magic": (
        "Transform the image into polished one-tap magic with luminous highlights, subtle spark effects, "
        "soft glow, and whimsical depth. Preserve the original subject, pose, composition, and key identity details."
    ),
    "viral": (
        "Transform the image into a bold viral social-media visual with crisp contrast, vibrant color, bright focal points, "
        "and scroll-stopping energy. Preserve the original subject, pose, composition, and key identity details."
    ),
    "cinematic": (
        "Transform the image into a cinematic frame with dramatic lighting, filmic color grading, premium storytelling atmosphere, "
        "and refined depth. Preserve the original subject, pose, composition, and key identity details."
    ),
    "fantasy": (
        "Transform the image into fantasy-inspired artwork with enchanted mood, rich imaginative worldbuilding, elevated wonder, "
        "and stylized magical detail. Preserve the original subject, pose, composition, and key identity details."
    ),
    "meme": (
        "Transform the image into a playful meme-ready visual with comedic exaggeration, punchy framing, expressive energy, "
        "and internet-native humor. Preserve the original subject, pose, composition, and key identity details."
    )
}


def get_style_prompt(style: str) -> str:
    try:
        return STYLE_PROMPTS[style]
    except KeyError as error:
        supported = ", ".join(STYLE_PROMPTS.keys())
        raise ValueError(f"Unsupported style '{style}'. Supported styles: {supported}.") from error
