"""Abstract protocol for platform adapters (Feishu, Discord, myserver, ...).

Any concrete adapter must provide two directions:

- **Inbound**: receive user messages from the platform and yield `InboundEvent`s.
- **Outbound**: render streaming relay output (text deltas, tool calls, final messages)
  back to the platform's UI (Feishu card, Discord message, ...).

The relay_core (claude CLI subprocess + stream-json parse) is adapter-agnostic and
consumes/produces the types below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class InboundEvent:
    """A message received from a platform adapter."""
    user_id: str
    chat_id: str
    text: str
    # Platform-opaque identifier for replying into the same thread/card.
    reply_context: object


@dataclass(frozen=True, slots=True)
class OutboundChunk:
    """A streaming chunk destined for the platform."""
    kind: str  # "text_delta" | "tool_use" | "tool_result" | "message_stop"
    payload: dict


@runtime_checkable
class RelayAdapter(Protocol):
    """Protocol every platform adapter must satisfy."""

    name: str  # "feishu", "discord", ...

    async def inbound(self) -> AsyncIterator[InboundEvent]:
        """Yield user messages. Long-running; typically WebSocket-backed."""
        ...

    async def send(self, reply_context: object, chunk: OutboundChunk) -> None:
        """Push a streaming chunk back to the platform (may batch internally)."""
        ...

    async def finalize(self, reply_context: object) -> None:
        """Mark the outbound stream complete (e.g., close Feishu card buffer)."""
        ...
