import hashlib

def calculate_file_hash(file):
    """
    Calculates a hash for the given file.
    """

    hasher = hashlib.md5()
    for chunk in file.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()
