"""ServiceNow Attachment API client for extracting files from ServiceNow instances."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth


@dataclass
class AttachmentMetadata:
    """Metadata for a ServiceNow attachment."""

    sys_id: str
    file_name: str
    content_type: str
    size_bytes: int
    table_name: str
    table_sys_id: str
    download_link: str
    sys_created_on: str
    sys_updated_on: str
    compressed: bool = False
    size_compressed: int | None = None


class ServiceNowClient:
    """Client for ServiceNow Attachment REST API.

    Supports listing, downloading, and uploading attachments.

    Example:
        client = ServiceNowClient(
            instance_url="https://instance.servicenow.com",
            username="admin",
            password="password"
        )

        for attachment in client.list_attachments(table_name="kb_knowledge"):
            content = client.download_attachment(attachment.sys_id)
            print(f"Downloaded {attachment.file_name}: {len(content)} bytes")
    """

    def __init__(
        self,
        instance_url: str,
        username: str | None = None,
        password: str | None = None,
    ):
        self.instance_url = instance_url.rstrip("/")
        self.username = username or os.environ.get("SERVICENOW_USERNAME")
        self.password = password or os.environ.get("SERVICENOW_PASSWORD")

        if not self.username or not self.password:
            raise ValueError("ServiceNow credentials required. Provide username/password or set SERVICENOW_USERNAME and SERVICENOW_PASSWORD environment variables.")

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.username, self.password)
        self._session.headers.update({"Accept": "application/json"})

    @property
    def _base_url(self) -> str:
        return f"{self.instance_url}/api/now/attachment"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        headers: dict | None = None,
        **kwargs,
    ) -> requests.Response:
        url = urljoin(self._base_url + "/", endpoint.lstrip("/"))
        response = self._session.request(method, url, params=params, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def list_attachments(
        self,
        table_name: str | None = None,
        table_sys_id: str | None = None,
        query: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
    ) -> Iterator[AttachmentMetadata]:
        """List attachments with optional filtering.

        Args:
            table_name: Filter by table name (e.g., 'kb_knowledge', 'incident')
            table_sys_id: Filter by specific record sys_id
            query: Encoded query string for advanced filtering
            limit: Maximum records per request (default 1000)
            offset: Starting offset for pagination
            order_by: Field to order by (prefix with DESC for descending)

        Yields:
            AttachmentMetadata objects for each matching attachment
        """
        query_parts = []
        if table_name:
            query_parts.append(f"table_name={table_name}")
        if table_sys_id:
            query_parts.append(f"table_sys_id={table_sys_id}")
        if query:
            query_parts.append(query)
        if order_by:
            if order_by.startswith("DESC"):
                query_parts.append(f"ORDERBYDESC{order_by[4:]}")
            else:
                query_parts.append(f"ORDERBY{order_by}")

        sysparm_query = "^".join(query_parts) if query_parts else None

        while True:
            params = {"sysparm_limit": limit, "sysparm_offset": offset}
            if sysparm_query:
                params["sysparm_query"] = sysparm_query

            response = self._request("GET", "", params=params)
            data = response.json()
            results = data.get("result", [])

            if not results:
                break

            for item in results:
                yield self._parse_attachment_metadata(item)

            if len(results) < limit:
                break

            offset += limit

    def get_attachment_metadata(self, sys_id: str) -> AttachmentMetadata:
        """Get metadata for a specific attachment.

        Args:
            sys_id: The sys_id of the attachment

        Returns:
            AttachmentMetadata object
        """
        response = self._request("GET", sys_id)
        data = response.json()
        return self._parse_attachment_metadata(data["result"])

    def download_attachment(self, sys_id: str) -> bytes:
        """Download the binary content of an attachment.

        Args:
            sys_id: The sys_id of the attachment

        Returns:
            Binary content of the attachment
        """
        response = self._request("GET", f"{sys_id}/file", headers={"Accept": "*/*"})
        return response.content

    def download_attachment_stream(self, sys_id: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Stream download an attachment in chunks.

        Args:
            sys_id: The sys_id of the attachment
            chunk_size: Size of each chunk in bytes

        Yields:
            Chunks of binary data
        """
        url = f"{self._base_url}/{sys_id}/file"
        with self._session.get(url, headers={"Accept": "*/*"}, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk

    def upload_attachment(
        self,
        table_name: str,
        table_sys_id: str,
        file_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> AttachmentMetadata:
        """Upload a binary file as an attachment to a record.

        Args:
            table_name: Name of the table to attach to
            table_sys_id: Sys_id of the record to attach to
            file_name: Name for the attachment
            content: Binary content to upload
            content_type: MIME type of the content

        Returns:
            AttachmentMetadata of the created attachment
        """
        params = {
            "table_name": table_name,
            "table_sys_id": table_sys_id,
            "file_name": file_name,
        }
        headers = {"Content-Type": content_type}

        response = self._request("POST", "file", params=params, headers=headers, data=content)
        data = response.json()
        return self._parse_attachment_metadata(data["result"])

    def delete_attachment(self, sys_id: str) -> None:
        """Delete an attachment.

        Args:
            sys_id: The sys_id of the attachment to delete
        """
        self._request("DELETE", sys_id)

    def _parse_attachment_metadata(self, data: dict) -> AttachmentMetadata:
        return AttachmentMetadata(
            sys_id=data["sys_id"],
            file_name=data["file_name"],
            content_type=data["content_type"],
            size_bytes=int(data.get("size_bytes", 0)),
            table_name=data["table_name"],
            table_sys_id=data["table_sys_id"],
            download_link=data.get("download_link", ""),
            sys_created_on=data.get("sys_created_on", ""),
            sys_updated_on=data.get("sys_updated_on", ""),
            compressed=data.get("compressed", "false").lower() == "true",
            size_compressed=int(data["size_compressed"]) if data.get("size_compressed") else None,
        )


def extract_kb_attachments(
    instance_url: str,
    username: str | None = None,
    password: str | None = None,
    output_dir: str = "./attachments",
    table_name: str = "kb_knowledge",
) -> list[tuple[AttachmentMetadata, str]]:
    """Extract all attachments from a ServiceNow knowledge base.

    Args:
        instance_url: ServiceNow instance URL
        username: ServiceNow username (or set SERVICENOW_USERNAME env var)
        password: ServiceNow password (or set SERVICENOW_PASSWORD env var)
        output_dir: Directory to save downloaded files
        table_name: Table to extract from (default: kb_knowledge)

    Returns:
        List of (metadata, file_path) tuples for downloaded files
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    client = ServiceNowClient(instance_url, username, password)
    downloaded = []

    for attachment in client.list_attachments(table_name=table_name):
        safe_name = attachment.file_name.replace("/", "_").replace("\\", "_")
        file_path = os.path.join(output_dir, f"{attachment.sys_id}_{safe_name}")

        content = client.download_attachment(attachment.sys_id)
        with open(file_path, "wb") as f:
            f.write(content)

        downloaded.append((attachment, file_path))
        print(f"Downloaded: {attachment.file_name} ({attachment.size_bytes} bytes)")

    return downloaded
