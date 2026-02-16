from __future__ import annotations

"""
Minimal Telegram Bot API client (production-oriented).

Used for:
- channel verification on webhook events
- checking bot permissions / admin list
- sending confirmation message to channel

No business logic here; just HTTP calls.
"""

from dataclasses import dataclass
import json
import logging
from typing import Any, Optional, Union, List

import httpx

logger = logging.getLogger(__name__)

# HTTP timeout constants
DEFAULT_TIMEOUT_SEC = 15
LONG_POLL_BASE_TIMEOUT_SEC = 30
LONG_POLL_EXTRA_SEC = 5


@dataclass(frozen=True)
class TelegramApiError(Exception):
    message: str
    payload: dict[str, Any] | None = None


class TelegramBotClient:
    def __init__(self, token: str, base_url: str = "https://api.telegram.org") -> None:
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        self._token = token
        self._base = f"{base_url}/bot{token}"
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Initialize persistent HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SEC)

    async def stop(self) -> None:
        """Close persistent HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "TelegramBotClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @staticmethod
    def _bool_to_str(value: bool) -> str:
        """Convert Python bool to Telegram API string format."""
        return "true" if value else "false"

    def _check_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check Telegram API response and raise error if not ok."""
        if not payload.get("ok"):
            error_msg = str(payload.get("description") or "Telegram API error")
            logger.error(f"Telegram API error: {error_msg}", extra={"payload": payload})
            raise TelegramApiError(message=error_msg, payload=payload)
        return payload["result"]

    async def _call(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}/{method}"
        if self._client:
            r = await self._client.post(url, data=data)
            payload = r.json()
            return self._check_response(payload)
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SEC) as client:
                r = await client.post(url, data=data)
                payload = r.json()
                return self._check_response(payload)

    async def _call_json(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Call Telegram API using JSON body.
        Some methods with array params (e.g. copyMessages) are more reliable with JSON.
        """
        url = f"{self._base}/{method}"
        if self._client:
            r = await self._client.post(url, json=data)
            payload = r.json()
            return self._check_response(payload)
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SEC) as client:
                r = await client.post(url, json=data)
                payload = r.json()
                return self._check_response(payload)

    async def get_chat(self, chat_id: Union[str, int]) -> dict[str, Any]:
        return await self._call("getChat", {"chat_id": str(chat_id)})

    async def get_chat_administrators(self, chat_id: Union[str, int]) -> list[dict[str, Any]]:
        return await self._call("getChatAdministrators", {"chat_id": str(chat_id)})

    async def export_chat_invite_link(self, chat_id: Union[str, int]) -> str:
        """
        Generate a new primary invite link for a chat.
        """
        return str(await self._call("exportChatInviteLink", {"chat_id": str(chat_id)}))

    async def create_chat_invite_link(self, chat_id: Union[str, int], member_limit: int = 1) -> str:
        """
        Create a fresh additional invite link (does not revoke the primary one).
        """
        result = await self._call("createChatInviteLink", {
            "chat_id": str(chat_id),
            "member_limit": member_limit,
        })
        return result["invite_link"]

    async def promote_chat_member(
        self,
        chat_id: Union[str, int],
        user_id: int,
        can_post_messages: bool = True,
        can_edit_messages: bool = True,
        can_delete_messages: bool = True,
        can_invite_users: bool = True,
        can_restrict_members: bool = False,
        can_promote_members: bool = False,
        can_change_info: bool = False,
        can_pin_messages: bool = False,
        can_manage_video_chats: bool = False,
    ) -> bool:
        """
        Promote or demote a user in a supergroup or a channel.
        """
        data = {
            "chat_id": str(chat_id),
            "user_id": user_id,
            "can_post_messages": self._bool_to_str(can_post_messages),
            "can_edit_messages": self._bool_to_str(can_edit_messages),
            "can_delete_messages": self._bool_to_str(can_delete_messages),
            "can_invite_users": self._bool_to_str(can_invite_users),
            "can_restrict_members": self._bool_to_str(can_restrict_members),
            "can_promote_members": self._bool_to_str(can_promote_members),
            "can_change_info": self._bool_to_str(can_change_info),
            "can_pin_messages": self._bool_to_str(can_pin_messages),
            "can_manage_video_chats": self._bool_to_str(can_manage_video_chats),
        }
        return bool(await self._call("promoteChatMember", data))

    async def get_chat_member(self, chat_id: Union[str, int], user_id: int) -> dict[str, Any]:
        return await self._call("getChatMember", {"chat_id": str(chat_id), "user_id": user_id})

    async def get_chat_member_count(self, chat_id: Union[str, int]) -> int:
        res = await self._call("getChatMemberCount", {"chat_id": str(chat_id)})
        return int(res)

    async def send_message(
        self,
        chat_id: Union[str, int],
        text: str,
        reply_markup: Optional[dict[str, Any]] = None,
        parse_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"chat_id": str(chat_id), "text": text}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        if parse_mode:
            data["parse_mode"] = parse_mode
        return await self._call("sendMessage", data)

    async def edit_message_text(
        self,
        *,
        chat_id: Union[str, int],
        message_id: int,
        text: str,
        reply_markup: Optional[dict[str, Any]] = None,
        parse_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Edit a text message.
        """
        data: dict[str, Any] = {"chat_id": str(chat_id), "message_id": message_id, "text": text}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        if parse_mode:
            data["parse_mode"] = parse_mode
        return await self._call("editMessageText", data)

    async def delete_message(self, *, chat_id: Union[str, int], message_id: int) -> bool:
        """
        Delete a message.
        """
        result = await self._call("deleteMessage", {"chat_id": str(chat_id), "message_id": message_id})
        return bool(result)

    async def copy_message(
        self,
        *,
        chat_id: Union[str, int],
        from_chat_id: Union[str, int],
        message_id: int,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        reply_markup: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Copy a message without forward header.
        """
        data: dict[str, Any] = {
            "chat_id": str(chat_id),
            "from_chat_id": str(from_chat_id),
            "message_id": int(message_id),
        }
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        return await self._call("copyMessage", data)

    async def copy_messages(self, *, chat_id: Union[str, int], from_chat_id: Union[str, int], message_ids: List[int]) -> List[int]:
        """
        Copy multiple messages at once.
        """
        if not message_ids:
            return []
        res = await self._call_json(
            "copyMessages",
            {
                "chat_id": str(chat_id),
                "from_chat_id": str(from_chat_id),
                "message_ids": [int(x) for x in message_ids],
            },
        )
        if isinstance(res, list):
            try:
                return [
                    int(x["message_id"]) if isinstance(x, dict) else int(x)
                    for x in res
                ]
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to parse copyMessages result: {e}", extra={"result": res})
                return []
        return []

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """
        Get file path for downloading.
        """
        return await self._call("getFile", {"file_id": file_id})

    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe", {})

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 25) -> List[dict[str, Any]]:
        """
        Long polling updates from Telegram.
        """
        url = f"{self._base}/getUpdates"
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        client_timeout = max(LONG_POLL_BASE_TIMEOUT_SEC, timeout + LONG_POLL_EXTRA_SEC)
        
        if self._client:
            # Persistent client request with specific timeout
            r = await self._client.get(url, params=params, timeout=client_timeout)
            payload = r.json()
            return self._check_response(payload)
        else:
            # Fallback client
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                r = await client.get(url, params=params)
                payload = r.json()
                return self._check_response(payload)

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        result = await self._call(
            "deleteWebhook",
            {"drop_pending_updates": self._bool_to_str(drop_pending_updates)},
        )
        return bool(result)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> bool:
        """
        Answer a callback query.
        """
        data: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        if show_alert:
            data["show_alert"] = self._bool_to_str(show_alert)
        result = await self._call("answerCallbackQuery", data)
        return bool(result)
