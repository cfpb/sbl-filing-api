from http import HTTPStatus
from fastapi import HTTPException
import logging
from fsspec import AbstractFileSystem, filesystem
from config import settings, FsProtocol

log = logging.getLogger(__name__)


async def upload_to_storage(lei: str, submission_id: str, content: bytes, extension: str = "csv"):
    try:
        fs: AbstractFileSystem = filesystem(settings.upload_fs_protocol.value)
        if settings.upload_fs_protocol == FsProtocol.FILE:
            fs.mkdirs(f"{settings.upload_fs_root}/{lei}", exist_ok=True)
        with fs.open(f"{settings.upload_fs_root}/{lei}/{submission_id}.{extension}", "wb") as f:
            f.write(content)
    except Exception as e:
        log.error("Failed to upload file", e, exc_info=True, stack_info=True)
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to upload file")


async def validate_submission(lei: str, submission_id: str, content: bytes):
    # implement validation process here
    pass
