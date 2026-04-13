STYLE_PROMPTS = {
    "magic": (
        "Transform the image with an ethereal magical atmosphere. Add luminous highlights, soft glowing auras, "
        "subtle floating spark particles, dreamy bloom, and whimsical depth. Preserve the original subject, pose, "
        "composition, and key identity details."
    ),
    "viral": (
        "Transform the image into a bold social-media-ready visual with ultra-crisp detail, vibrant saturated color, "
        "clean bright lighting, high contrast, and strong focal clarity. Preserve the original subject, pose, "
        "composition, and key identity details."
    ),
    "cinematic": (
        "Transform the image into a cinematic movie still with dramatic lighting, filmic color grading, refined depth, "
        "and shallow depth of field. Preserve the original subject, pose, composition, and key identity details."
    ),
    "fantasy": (
        "Transform the image into high-fantasy inspired artwork with a mystical atmosphere, rich jewel-tone color, "
        "enchanted ambient light, and stylized magical detail. Preserve the original subject, pose, composition, "
        "and key identity details."
    ),
    "meme": (
        "Transform the image into a playful meme-style visual with expressive reaction-image energy, punchy framing, "
        "clean hard-light clarity, bold contrast, and slight comedic exaggeration without distorting anatomy. "
        "Preserve the original subject, pose, composition, and key identity details."
    )
}


def get_style_prompt(style: str) -> str:
    try:
        return STYLE_PROMPTS[style]
    except KeyError as error:
        supported = ", ".join(STYLE_PROMPTS.keys())
        raise ValueError(f"Unsupported style '{style}'. Supported styles: {supported}.") from error
