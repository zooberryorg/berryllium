import hashlib


def calculate_file_hash(file):
    """
    Calculates a hash for the given file.
    Note: This is not ideal for security, only used for
    simple duplicate detection
    """

    hasher = hashlib.md5()
    for chunk in file.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()
