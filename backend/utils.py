import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    """Generate a UUID v7 (time-ordered), returned as a stdlib uuid.UUID."""
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
