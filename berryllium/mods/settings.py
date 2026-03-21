# Navigation configuration for upload form
#     name: Page title
#     url: Endpoint
#     icon: Icon name. See: https://icons.getbootstrap.com/
UPLOAD_NAVIGATION = [
    {"name": "Basic Information", "url": "upload_step1", "icon": "info-circle"},
    {"name": "Upload Files", "url": "upload_step2", "icon": "upload"},
    {"name": "Organize Files", "url": "upload_step3", "icon": "folder"},
    {"name": "Upload Pictures", "url": "upload_step4", "icon": "image"},
    {"name": "Details & Settings", "url": "upload_step4", "icon": "gear"},
    {"name": "Review & Submit", "url": "upload_step4", "icon": "check-circle"},
]

MIN_TEXTFIELD_LENGTH = 4
MAX_TEXTFIELD_LENGTH = 100

MIN_SUMMARY_LENGTH = 10
MAX_SUMMARY_LENGTH = 200

ALLOWED_EXTENSIONS = ["z2f", "ztd", "zip"]
ILLEGAL_CHARACTERS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

COLLAPSIBLE_WIDGET_ATTRS = {
    "@focus": "expand()",
    # if click away from field, collapse
    "@blur": "collapse(), updateTrimLength($el.offsetWidth), trimDisplayedContent()",
    ":rows": "focused ? 4 : 1",
    ":class": "focused ? 'h-32' : 'h-10'",
    "@keydown.escape": "$el.blur()",
    "@keydown.enter.prevent": "$el.blur()",
    # watch for changes to content and update content state
    ":value": "focused ? content : trimDisplayedContent()",
    "@input": "content = $el.value, updateTrimLength($el.offsetWidth)",
}

