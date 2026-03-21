from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from config import get_settings
from storage.models import ChatMessage, PaginatedResult, Session, ToolResult, ToolResultMetadata

logger = logging.getLogger(__name__)


class DynamoDBStore:
    """DynamoDB-backed storage for sessions, messages, and tool results.

    Uses a single-table design with PK/SK patterns:
      - Session:     PK=SESSION#{session_id}  SK=META
      - Message:     PK=SESSION#{session_id}  SK=MSG#{timestamp}#{message_id}
      - ToolResult:  PK=SESSION#{session_id}  SK=RESULT#{result_id}
    """

    def __init__(self) -> None:
        settings = get_settings()
        kwargs: dict[str, Any] = {"region_name": settings.aws_region}
        if settings.dynamodb_endpoint_url:
            kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        self._resource = boto3.resource("dynamodb", **kwargs)
        self._table_name = settings.dynamodb_table_name
        self._table = self._resource.Table(self._table_name)

    # ── Table bootstrap (local dev / testing) ──────────────────────────

    def create_table_if_not_exists(self) -> None:
        try:
            self._resource.meta.client.describe_table(TableName=self._table_name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                self._resource.create_table(
                    TableName=self._table_name,
                    KeySchema=[
                        {"AttributeName": "PK", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"},
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "PK", "AttributeType": "S"},
                        {"AttributeName": "SK", "AttributeType": "S"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
                self._resource.meta.client.get_waiter("table_exists").wait(
                    TableName=self._table_name
                )
                logger.info("Created DynamoDB table %s", self._table_name)
            else:
                raise

    # ── Sessions ───────────────────────────────────────────────────────

    def create_session(self, title: str = "New Chat") -> Session:
        session = Session(session_id=str(uuid.uuid4()), title=title)
        self._table.put_item(
            Item={
                "PK": f"SESSION#{session.session_id}",
                "SK": "META",
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        )
        return session

    def get_session(self, session_id: str) -> Session | None:
        resp = self._table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "META"})
        item = resp.get("Item")
        if not item:
            return None
        return Session(
            session_id=item["session_id"],
            title=item["title"],
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )

    def list_sessions(
        self,
        limit: int = 20,
        cursor: str | None = None,
    ) -> PaginatedResult[Session]:
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": "SK = :sk",
            "ExpressionAttributeValues": {":sk": "META"},
            "Limit": limit * 3,
        }
        if cursor:
            scan_kwargs["ExclusiveStartKey"] = json.loads(base64.urlsafe_b64decode(cursor).decode())

        resp = self._table.scan(**scan_kwargs)
        sessions = [
            Session(
                session_id=item["session_id"],
                title=item["title"],
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )
            for item in resp.get("Items", [])
        ]
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        next_cursor: str | None = None
        last_key = resp.get("LastEvaluatedKey")
        if last_key:
            next_cursor = base64.urlsafe_b64encode(json.dumps(last_key).encode()).decode()

        return PaginatedResult(items=sessions[:limit], next_cursor=next_cursor)

    def update_session_timestamp(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._table.update_item(
            Key={"PK": f"SESSION#{session_id}", "SK": "META"},
            UpdateExpression="SET updated_at = :ts",
            ExpressionAttributeValues={":ts": now},
        )

    def update_session_title(self, session_id: str, title: str) -> Session | None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            resp = self._table.update_item(
                Key={"PK": f"SESSION#{session_id}", "SK": "META"},
                UpdateExpression="SET title = :t, updated_at = :ts",
                ExpressionAttributeValues={":t": title, ":ts": now},
                ConditionExpression="attribute_exists(PK)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
        item = resp["Attributes"]
        return Session(
            session_id=item["session_id"],
            title=item["title"],
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )

    def delete_session(self, session_id: str) -> bool:
        pk = f"SESSION#{session_id}"
        resp = self._table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
            ProjectionExpression="PK, SK",
        )
        items = resp.get("Items", [])
        if not items:
            return False
        with self._table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        return True

    # ── Messages ───────────────────────────────────────────────────────

    def store_message(self, message: ChatMessage) -> None:
        ts = message.created_at.isoformat()
        item: dict[str, Any] = {
            "PK": f"SESSION#{message.session_id}",
            "SK": f"MSG#{ts}#{message.message_id}",
            "message_id": message.message_id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": ts,
        }
        if message.tool_name:
            item["tool_name"] = message.tool_name
        if message.tool_call_id:
            item["tool_call_id"] = message.tool_call_id
        self._table.put_item(Item=item)

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        resp = self._table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"SESSION#{session_id}",
                ":prefix": "MSG#",
            },
        )
        messages = []
        for item in resp.get("Items", []):
            messages.append(
                ChatMessage(
                    session_id=item["session_id"],
                    message_id=item["message_id"],
                    role=item["role"],
                    content=item["content"],
                    tool_name=item.get("tool_name"),
                    tool_call_id=item.get("tool_call_id"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
            )
        messages.sort(key=lambda m: m.created_at)
        return messages

    # ── Tool Results ───────────────────────────────────────────────────

    def store_tool_result(self, result: ToolResult) -> None:
        item: dict[str, Any] = {
            "PK": f"SESSION#{result.session_id}",
            "SK": f"RESULT#{result.result_id}",
            "session_id": result.session_id,
            "result_id": result.result_id,
            "tool_name": result.tool_name,
            "summary": result.summary,
            "full_result": result.full_result,
            "metadata": json.dumps(result.metadata),
            "created_at": result.created_at.isoformat(),
            "size_bytes": result.size_bytes,
        }
        if result.s3_key:
            item["s3_key"] = result.s3_key
        self._table.put_item(Item=item)

    def get_tool_result(self, session_id: str, result_id: str) -> ToolResult | None:
        resp = self._table.get_item(
            Key={"PK": f"SESSION#{session_id}", "SK": f"RESULT#{result_id}"}
        )
        item = resp.get("Item")
        if not item:
            return None
        return ToolResult(
            session_id=item["session_id"],
            result_id=item["result_id"],
            tool_name=item["tool_name"],
            summary=item["summary"],
            full_result=item.get("full_result", ""),
            s3_key=item.get("s3_key"),
            metadata=json.loads(item.get("metadata", "{}")),
            created_at=datetime.fromisoformat(item["created_at"]),
            size_bytes=int(item["size_bytes"]),
        )

    def list_tool_results(self, session_id: str) -> list[ToolResultMetadata]:
        resp = self._table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"SESSION#{session_id}",
                ":prefix": "RESULT#",
            },
            ProjectionExpression=(
                "session_id, result_id, tool_name, summary, s3_key, metadata,"
                " created_at, size_bytes"
            ),
        )
        results = []
        for item in resp.get("Items", []):
            results.append(
                ToolResultMetadata(
                    session_id=item["session_id"],
                    result_id=item["result_id"],
                    tool_name=item["tool_name"],
                    summary=item["summary"],
                    s3_key=item.get("s3_key"),
                    metadata=json.loads(item.get("metadata", "{}")),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    size_bytes=int(item["size_bytes"]),
                )
            )
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results
