import io
import logging
from datetime import timedelta

from minio import Minio
from minio.commonconfig import Filter, ENABLED
from minio.deleteobjects import DeleteObject
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO-backed object storage service."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ):
        self.client = Minio(endpoint, access_key, secret_key, secure=secure)
        self.bucket = bucket

    # ── Default bucket operations ──

    def ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist. Called at startup."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload bytes to MinIO."""
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

    def get_object(self, object_name: str) -> bytes:
        """Download object content as bytes."""
        response = self.client.get_object(self.bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_text(self, object_name: str, encoding: str = "utf-8") -> str:
        """Download object content as text."""
        return self.get_object(object_name).decode(encoding)

    def remove_object(self, object_name: str) -> None:
        """Delete an object from MinIO."""
        self.client.remove_object(self.bucket, object_name)

    def remove_objects(self, object_names: list[str]) -> None:
        """Delete multiple objects from MinIO."""
        delete_list = [DeleteObject(name) for name in object_names]
        errors = list(self.client.remove_objects(self.bucket, delete_list))
        if errors:
            logger.warning("Failed to delete some objects: %s", errors)

    def list_objects(self, prefix: str = "") -> list:
        """List objects under the given prefix in the default bucket."""
        return list(self.client.list_objects(self.bucket, prefix=prefix))

    def presigned_get_url(self, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned GET URL for the default bucket."""
        return self.client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(seconds=expires),
        )

    # ── Multi-bucket operations (for backups etc.) ──

    def ensure_bucket_with_name(self, bucket_name: str) -> None:
        """Create a named bucket if it doesn't exist."""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def put_object_to_bucket(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload bytes to a specific bucket."""
        self.client.put_object(
            bucket_name,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

    def list_objects_in_bucket(self, bucket_name: str, prefix: str = "") -> list:
        """List objects in a specific bucket."""
        return list(self.client.list_objects(bucket_name, prefix=prefix))

    def presigned_get_url_from_bucket(
        self, bucket_name: str, object_name: str, expires: int = 3600,
    ) -> str:
        """Generate a presigned GET URL from a specific bucket."""
        return self.client.presigned_get_object(
            bucket_name, object_name, expires=timedelta(seconds=expires),
        )

    def remove_object_from_bucket(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from a specific bucket."""
        self.client.remove_object(bucket_name, object_name)

    def set_bucket_lifecycle(self, bucket_name: str, retention_days: int) -> None:
        """Set lifecycle policy to auto-expire objects after N days."""
        config = LifecycleConfig(
            [
                Rule(
                    ENABLED,
                    rule_filter=Filter(prefix=""),
                    rule_id="auto-expire",
                    expiration=Expiration(days=retention_days),
                ),
            ],
        )
        self.client.set_bucket_lifecycle(bucket_name, config)


storage_service = StorageService(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    bucket=MINIO_BUCKET,
    secure=MINIO_SECURE,
)
