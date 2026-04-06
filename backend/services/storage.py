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
    """基于 MinIO 的对象存储服务。"""

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

    # ── 默认 bucket 操作 ──

    def ensure_bucket(self) -> None:
        """创建 bucket（如不存在）。启动时调用。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """上传字节数据到 MinIO。"""
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )
        logger.info("文件上传 — 路径=%s, 大小=%d", object_name, len(data))

    def get_object(self, object_name: str) -> bytes:
        """下载对象内容为字节。"""
        response = self.client.get_object(self.bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_text(self, object_name: str, encoding: str = "utf-8") -> str:
        """下载对象内容为文本。"""
        return self.get_object(object_name).decode(encoding)

    def remove_object(self, object_name: str) -> None:
        """从 MinIO 删除单个对象。"""
        self.client.remove_object(self.bucket, object_name)

    def remove_objects(self, object_names: list[str]) -> None:
        """从 MinIO 批量删除对象。"""
        delete_list = [DeleteObject(name) for name in object_names]
        errors = list(self.client.remove_objects(self.bucket, delete_list))
        if errors:
            logger.warning("部分对象删除失败: %s", errors)

    def list_objects(self, prefix: str = "") -> list:
        """列出默认 bucket 中指定前缀下的对象。"""
        return list(self.client.list_objects(self.bucket, prefix=prefix))

    def presigned_get_url(self, object_name: str, expires: int = 3600) -> str:
        """为默认 bucket 生成预签名 GET URL。"""
        return self.client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(seconds=expires),
        )

    # ── 多 bucket 操作（备份等） ──

    def ensure_bucket_with_name(self, bucket_name: str) -> None:
        """创建指定名称的 bucket（如不存在）。"""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def put_object_to_bucket(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """上传字节数据到指定 bucket。"""
        self.client.put_object(
            bucket_name,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

    def list_objects_in_bucket(self, bucket_name: str, prefix: str = "") -> list:
        """列出指定 bucket 中的对象。"""
        return list(self.client.list_objects(bucket_name, prefix=prefix))

    def presigned_get_url_from_bucket(
        self, bucket_name: str, object_name: str, expires: int = 3600,
    ) -> str:
        """为指定 bucket 生成预签名 GET URL。"""
        return self.client.presigned_get_object(
            bucket_name, object_name, expires=timedelta(seconds=expires),
        )

    def remove_object_from_bucket(self, bucket_name: str, object_name: str) -> None:
        """从指定 bucket 删除对象。"""
        self.client.remove_object(bucket_name, object_name)

    def set_bucket_lifecycle(self, bucket_name: str, retention_days: int) -> None:
        """设置生命周期策略，N 天后自动过期对象。"""
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
