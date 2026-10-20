LINK_PRESETS = {
    "website": {"label": "Website", "icon": "bi-globe2", "domains": []},
    "mirror": {"label": "Mirror / Download", "icon": "bi-cloud-arrow-down", "domains": []},
    "forum": {"label": "Forum thread", "icon": "bi-chat-square-text", "domains": []},
    "github": {"label": "GitHub", "icon": "bi-github", "domains": ["github.com"]},
    "discord": {"label": "Discord", "icon": "bi-discord", "domains": ["discord.gg", "discord.com"]},
    "youtube": {"label": "YouTube", "icon": "bi-youtube", "domains": ["youtube.com", "youtu.be"]},
    "twitch": {"label": "Twitch", "icon": "bi-twitch", "domains": ["twitch.tv"]},
    "twitter": {"label": "X / Twitter", "icon": "bi-twitter-x", "domains": ["x.com", "twitter.com"]},
    "bluesky": {"label": "Bluesky", "icon": "bi-bluesky", "domains": ["bsky.app"]},
    "facebook": {"label": "Facebook", "icon": "bi-facebook", "domains": ["facebook.com", "fb.com"]},
    "instagram": {"label": "Instagram", "icon": "bi-instagram", "domains": ["instagram.com"]},
    "patreon": {"label": "Patreon", "icon": "bi-heart-fill", "domains": ["patreon.com"]},
    "kofi": {"label": "Ko-fi", "icon": "bi-cup-hot-fill", "domains": ["ko-fi.com"]},
    "donate": {"label": "Donate", "icon": "bi-gift-fill", "domains": []},
    "other": {"label": "Other", "icon": "bi-link-45deg", "domains": []},
}

DEFAULT_LINK_PRESET = "website"

LINK_PRESET_CHOICES = [(key, preset["label"]) for key, preset in LINK_PRESETS.items()]


def link_preset(kind):
    return LINK_PRESETS.get(kind, LINK_PRESETS["other"])
