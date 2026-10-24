# Navigation configuration for upload form
#     name: Page title
#     url: Endpoint
#     icon: Icon name. See: https://icons.getbootstrap.com/
UPLOAD_NAVIGATION = [
    {"name": "General", "url": "mod_create_general", "icon": "info-circle"},
    {"name": "Categorization", "url": "mod_create_categorization", "payload": "mod_id", "icon": "tags"},
    {"name": "Upload Files", "url": "mod_create_files", "icon": "upload"},
    {"name": "Upload Images", "url": "mod_create_images", "icon": "image"},
    {"name": "Description", "url": "mod_create_description", "icon": "file-text"},
    {"name": "Resources & Credits", "url": "mod_create_resources", "icon": "diagram-3"},
    {"name": "Review & Submit", "url": "mod_create_review", "icon": "check-circle"},
]

MIN_TEXTFIELD_LENGTH = 4
MAX_TEXTFIELD_LENGTH = 100

MIN_SUMMARY_LENGTH = 10
MAX_SUMMARY_LENGTH = 200

ALLOWED_EXTENSIONS = ["z2f", "ztd", "zip"]
ILLEGAL_CHARACTERS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

GALLERY_RATIO = "16 / 9"
GALLERY_RATIO_LABEL = "16:9"
GALLERY_RECOMMENDED_SIZE = "1920 × 1280"

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
