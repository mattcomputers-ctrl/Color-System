"""Secure file upload handling."""

import hashlib
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'cxf', 'xml'}
MAX_FILENAME_LENGTH = 200


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage, purpose: str = 'general') -> dict:
    """Save an uploaded file securely.

    Args:
        file_storage: Werkzeug FileStorage object.
        purpose: Category for organizing uploads.

    Returns:
        Dict with file metadata (stored_filename, original_filename, etc.)
    """
    original_filename = secure_filename(file_storage.filename or 'unnamed')
    if len(original_filename) > MAX_FILENAME_LENGTH:
        ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        original_filename = original_filename[:MAX_FILENAME_LENGTH - len(ext) - 1] + '.' + ext

    # Generate a unique stored filename
    ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'bin'
    stored_filename = f'{purpose}/{uuid.uuid4().hex}.{ext}'

    # Ensure subdirectory exists
    full_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], purpose)
    os.makedirs(full_dir, exist_ok=True)

    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)

    # Read content for hashing, then save
    content = file_storage.read()
    checksum = hashlib.sha256(content).hexdigest()

    with open(full_path, 'wb') as f:
        f.write(content)

    return {
        'original_filename': original_filename,
        'stored_filename': stored_filename,
        'file_type': ext,
        'file_size': len(content),
        'mime_type': file_storage.content_type,
        'checksum_sha256': checksum,
        'full_path': full_path,
        'content': content,
    }


def get_upload_path(stored_filename: str) -> str:
    """Get the full filesystem path for a stored file."""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
