from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath

_SAFE_FILENAME_SUFFIX = re.compile(r"^\.[a-z0-9]{1,16}$", re.IGNORECASE)


def knowledge_file_object_key(
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID,
    file_id: uuid.UUID,
    original_filename: str | None = None,
) -> str:
    suffix = ""
    if original_filename:
        ext = PurePosixPath(original_filename).suffix
        if ext and _SAFE_FILENAME_SUFFIX.match(ext):
            suffix = ext.lower()
    return f"v1/knowledge/owners/{owner_id}/bots/{bot_id}/files/{file_id}{suffix}"
