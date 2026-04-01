# Navigation configuration for upload form
#     name: Page title
#     url: Endpoint
#     icon: Icon name. See: https://icons.getbootstrap.com/
UPLOAD_NAVIGATION = [
    {"name": "General", "url": "mod_create_categorization", "icon": "info-circle"},
    {"name": "Categorization", "url": "mod_create_step2", "icon": "tags"},
    {"name": "Upload Files", "url": "mod_create_files", "icon": "upload"},
    {"name": "Upload Images", "url": "mod_create_images", "icon": "image"},
    {"name": "Description", "url": "mod_create_description", "icon": "file-text"},
    {"name": "Details & Settings", "url": "upload_step3", "icon": "gear"},
    {"name": "Review & Submit", "url": "upload_step3", "icon": "check-circle"},
]

MIN_TEXTFIELD_LENGTH = 4
MAX_TEXTFIELD_LENGTH = 100

MIN_SUMMARY_LENGTH = 10
MAX_SUMMARY_LENGTH = 200

ALLOWED_EXTENSIONS = ["z2f", "ztd", "zip"]
ILLEGAL_CHARACTERS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

COLLAPSIBLE_WIDGET_ATTRS = {
    "@focus": "expand()",
    # if click away from field, collapse
    "@blur": "collapse()",
    ":rows": "focused ? 4 : 1",
    ":class": "focused ? 'h-32' : 'h-10'",
    "@keydown.escape": "$el.blur()",
    "@keydown.enter.prevent": "$el.blur()",
}

DISABLE_SUBMIT_BUTTON_ATTRS = {
    "autocomplete": "off",
    "@keydown.escape": "$el.blur()",
    "@keydown.enter.prevent": "$el.blur()",
}

MOD_CATEGORIES = [
    ("animals", "Animals"),
    ("animal_needs", "Animal Needs"),
    ("props_and_structures", "Props & Structures"),
    ("packs", "Packs"),
    ("utilities", "Utilities"),
    ("texture_variants", "Texture Variants"),
    ("texture_replacements", "Texture Replacements"),
    ("gameplay_tweaks", "Gameplay Tweaks"),
    ("remakes", "Remakes"),
    ("scripts", "Scripts"),
    ("zoos_and_saves", "Zoos & Saves"),
    ("assets", "Assets"),
]

GAME_OPTIONS = [
    ("na", "Not Applicable"),
    ("zt1", "Zoo Tycoon 1"),
    ("zt2", "Zoo Tycoon 2"),
]

EXPANSION_REQUIREMENTS = [
    ("none", "None"),
    ("mm1", "Marine Mania"),
    ("dd", "Dinosaur Digs"),
    ("aa", "African Adventure"),
    ("es", "Endangered Species"),
    ("mm2", "Marine Mania 2"),
    ("ea", "Extinct Animals"),
]
