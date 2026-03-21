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
