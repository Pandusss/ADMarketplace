import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union, TypeAlias, TypedDict

from telethon import TelegramClient, functions, types, errors
from telethon.sessions import StringSession

from app.core.config import settings
from app.utils.dt import ensure_utc, utcnow

logger = logging.getLogger(__name__)

# --- Type Aliases ---
ChannelIdentifier: TypeAlias = Union[str, int]

# --- Constants ---
METRICS_POST_LIMIT = 50
DEFAULT_SCAN_LIMIT = 200
DEFAULT_CONNECTION_RETRIES = 3
DEFAULT_RETRY_DELAY = 5

# Sampling thresholds for detailed stats
MAX_FETCH_LIMIT_SMALL = 500
MAX_FETCH_LIMIT_MEDIUM = 1_000
MAX_FETCH_LIMIT_LARGE = 2_000
CHANNEL_SIZE_SMALL = 10_000
CHANNEL_SIZE_MEDIUM = 100_000

# Graph parsing windows
GRAPH_WINDOW_DAYS = 7
GRAPH_DAYS_MONTH = 30
GRAPH_DAYS_WEEK = 7


# --- DTOs ---

class DetailedStats(TypedDict):
    """Summary of premium / region audience breakdown."""

    total_processed: int
    premium_count: int
    premium_percentage: float
    region_stats: Dict[str, int]


class ChannelStats(TypedDict):
    """Raw snapshot returned by :meth:`ChannelAnalyticsService.fetch_channel_stats`."""

    channel_id: int
    username: Optional[str]
    subscribers: int
    fetched_at: str
    telegram_metrics: Dict[str, Any]
    calculated_metrics: Optional[Dict[str, Any]]


@dataclass(slots=True)
class PostDTO:
    """Internal representation of a channel post for analytics."""

    post_id: int
    date: datetime
    views: int
    forwards: int
    replies: int
    reactions: Dict[str, int]
    content_type: str
    has_links: bool
    grouped_id: Optional[Union[int, str]] = None


class PostAnalytics:
    """Calculates engagement & activity metrics from raw channel posts."""

    # -- public API ----------------------------------------------------------

    @staticmethod
    def calculate(posts: List[Dict[str, Any]], subscribers: int = 0) -> Dict[str, Any]:
        """Return a dict with ``calculated_metrics`` key."""
        if not posts:
            return PostAnalytics._get_empty_metrics()

        unique_posts = PostAnalytics._prepare_posts(posts)
        recent_posts = unique_posts[:METRICS_POST_LIMIT]
        count = len(recent_posts)

        avg_views = PostAnalytics._calculate_avg_views(recent_posts)
        engagement_rate = PostAnalytics._calculate_er(avg_views, subscribers)
        stability_score = PostAnalytics._calculate_stability_score(recent_posts)

        ad_reach = PostAnalytics._calculate_median_views(recent_posts)
        median_views_all = PostAnalytics._calculate_median_views(unique_posts)

        interaction = PostAnalytics._calculate_interaction_metrics(recent_posts)
        time_info = PostAnalytics._calculate_time_metrics(recent_posts, subscribers)
        posts_per_day = PostAnalytics._calculate_posts_per_day(recent_posts)

        return {
            "calculated_metrics": {
                "engagement_rate": round(engagement_rate, 2),
                "median_er": round(interaction["median_er"], 2),
                "err_24h_percent": round(time_info["err_24h"], 2),
                "posts_per_day": round(posts_per_day, 1),
                "ad_reach_estimate": ad_reach,
                "median_views": median_views_all,
                "stability_score": stability_score,
                "avg_views_24h": int(time_info["avg_views_24h"]),
                "avg_views_7d": int(time_info["avg_views_7d"]),
                "posts_total": count,
                "posts_yesterday": time_info["posts_24h_count"],
                "posts_week": time_info["posts_7d_count"],
                "posts_month": time_info["posts_30d_count"],
                "avg_reactions": round(interaction["avg_reactions"], 1),
                "avg_forwards": round(interaction["avg_forwards"], 1),
                "avg_replies": round(interaction["avg_replies"], 1),
            },
        }

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _get_empty_metrics() -> Dict[str, Any]:
        return {
            "calculated_metrics": {
                "engagement_rate": 0.0,
                "median_er": 0.0,
                "err_24h_percent": 0.0,
                "posts_per_day": 0.0,
                "ad_reach_estimate": 0,
                "median_views": 0,
                "stability_score": 0.0,
                "avg_views_24h": 0,
                "avg_views_7d": 0,
                "posts_total": 0,
                "posts_yesterday": 0,
                "posts_week": 0,
                "posts_month": 0,
                "avg_reactions": 0.0,
                "avg_forwards": 0.0,
                "avg_replies": 0.0,
            },
        }

    @staticmethod
    def _prepare_posts(posts: List[Dict[str, Any]]) -> List[PostDTO]:
        """Convert raw dicts → sorted, de-duplicated ``PostDTO`` list."""
        dto_list: List[PostDTO] = []

        for p in posts:
            date_val = p["date"]
            if isinstance(date_val, str):
                date_val = datetime.fromisoformat(date_val)
            date_val = ensure_utc(date_val)

            reactions = p.get("reactions", {})
            if isinstance(reactions, str):
                try:
                    reactions = json.loads(reactions)
                except json.JSONDecodeError:
                    reactions = {}
            if not isinstance(reactions, dict):
                reactions = {}

            dto_list.append(
                PostDTO(
                    post_id=p.get("post_id", 0),
                    date=date_val,
                    views=p.get("views", 0),
                    forwards=p.get("forwards", 0),
                    replies=p.get("replies", 0) if isinstance(p.get("replies"), int) else 0,
                    reactions=reactions,
                    content_type=p.get("content_type", "text"),
                    has_links=bool(p.get("has_links", False)),
                    grouped_id=p.get("grouped_id"),
                )
            )

        # Newest first, then deduplicate by grouped_id
        dto_list.sort(key=lambda x: x.date, reverse=True)

        unique: List[PostDTO] = []
        seen_groups: Set[Union[str, int]] = set()
        for dto in dto_list:
            if dto.grouped_id:
                if dto.grouped_id in seen_groups:
                    continue
                seen_groups.add(dto.grouped_id)
            unique.append(dto)

        return unique

    @staticmethod
    def _calculate_avg_views(posts: List[PostDTO]) -> float:
        if not posts:
            return 0.0
        return sum(p.views for p in posts) / len(posts)

    @staticmethod
    def _calculate_er(avg_views: float, subscribers: int) -> float:
        return (avg_views / subscribers * 100) if subscribers > 0 else 0.0

    @staticmethod
    def _calculate_stability_score(posts: List[PostDTO]) -> float:
        """Coefficient of variation inverted to 0‑1 range."""
        if len(posts) <= 1:
            return 0.0
        views = [p.views for p in posts]
        mean = statistics.mean(views)
        if mean <= 0:
            return 0.0
        score = 1.0 - (statistics.stdev(views) / mean)
        return max(0.0, min(1.0, round(score, 2)))

    @staticmethod
    def _calculate_median_views(posts: List[PostDTO]) -> int:
        if not posts:
            return 0
        return int(statistics.median([p.views for p in posts]))

    @staticmethod
    def _calculate_interaction_metrics(posts: List[PostDTO]) -> Dict[str, float]:
        if not posts:
            return {
                "median_er": 0.0,
                "avg_reactions": 0.0,
                "avg_forwards": 0.0,
                "avg_replies": 0.0,
            }

        er_values: list[float] = []
        sum_reacts = sum_forwards = sum_replies = 0

        for p in posts:
            r_count = sum(p.reactions.values())
            sum_reacts += r_count
            sum_forwards += p.forwards
            sum_replies += p.replies
            if p.views > 0:
                er_values.append((r_count + p.forwards + p.replies) / p.views)

        median_er = (statistics.median(er_values) * 100) if er_values else 0.0
        n = len(posts)
        return {
            "median_er": median_er,
            "avg_reactions": sum_reacts / n,
            "avg_forwards": sum_forwards / n,
            "avg_replies": sum_replies / n,
        }

    @staticmethod
    def _calculate_time_metrics(posts: List[PostDTO], subscribers: int) -> Dict[str, Any]:
        if not posts:
            return {
                "avg_views_24h": 0,
                "err_24h": 0.0,
                "posts_24h_count": 0,
                "avg_views_7d": 0,
                "posts_7d_count": 0,
                "posts_30d_count": 0,
            }

        now = utcnow()
        posts_24h = [p for p in posts if p.date > now - timedelta(hours=24)]
        posts_7d = [p for p in posts if p.date > now - timedelta(days=7)]
        posts_30d_count = len([p for p in posts if p.date > now - timedelta(days=30)])

        avg_views_24h = sum(p.views for p in posts_24h) / len(posts_24h) if posts_24h else 0
        avg_views_7d = sum(p.views for p in posts_7d) / len(posts_7d) if posts_7d else 0

        return {
            "avg_views_24h": avg_views_24h,
            "err_24h": (avg_views_24h / subscribers * 100) if subscribers > 0 else 0.0,
            "posts_24h_count": len(posts_24h),
            "avg_views_7d": avg_views_7d,
            "posts_7d_count": len(posts_7d),
            "posts_30d_count": posts_30d_count,
        }

    @staticmethod
    def _calculate_posts_per_day(posts: List[PostDTO]) -> float:
        if len(posts) <= 1:
            return 0.0
        span_days = max(
            (posts[0].date - posts[-1].date).total_seconds() / 86_400.0,
            1.0,
        )
        return round(len(posts) / span_days, 1)


class TelegramStatsParser:
    """Parses ``stats.GetBroadcastStats`` response into a flat dict."""

    def __init__(self, client: TelegramClient):
        self.client = client

    # -- public --------------------------------------------------------------

    async def parse(self, stats: Any, full_channel: Any) -> Dict[str, Any]:
        """Return ``{"telegram_metrics": {...}}``."""
        vpp_abs = getattr(stats, "views_per_post", None)
        avg_vpp = int(vpp_abs.current) if vpp_abs and hasattr(vpp_abs, "current") else 0

        grow_graph = await self._resolve_graph(
            getattr(stats, "growth_graph", None)
            or getattr(stats, "followers_graph", None)
        )
        nf_graph = await self._resolve_graph(getattr(stats, "new_followers_graph", None))
        lang_graph = await self._resolve_graph(getattr(stats, "languages_graph", None))

        return {
            "telegram_metrics": {
                "followers": full_channel.full_chat.participants_count,
                "avg_views_per_post": avg_vpp,
                "followers_trend_percent": self._calculate_followers_trend(grow_graph),
                "official_languages": self._calculate_languages(lang_graph),
                **self._calculate_detailed_deltas(grow_graph),
                **self._calculate_joins_leaves(nf_graph),
            },
        }

    # -- graph resolution ----------------------------------------------------

    async def _resolve_graph(self, graph: Any) -> Any:
        """Fetch async graph data if needed."""
        if not graph or not isinstance(graph, types.StatsGraphAsync):
            return graph
        try:
            return await self.client(
                functions.stats.LoadAsyncGraphRequest(token=graph.token)
            )
        except errors.RPCError as e:
            logger.warning("Failed to resolve graph: %s", e)
            return None

    def _extract_graph_data(self, graph: Any) -> Optional[Dict[str, Any]]:
        """Extract parsed JSON payload from a graph object."""
        if not graph or not hasattr(graph, "json"):
            return None
        try:
            return json.loads(graph.json.data)
        except (json.JSONDecodeError, AttributeError):
            return None

    # -- metric calculators --------------------------------------------------

    def _calculate_followers_trend(self, chart: Any) -> float:
        """Percentage growth over the last ``GRAPH_WINDOW_DAYS``."""
        data = self._extract_graph_data(chart)
        if not data:
            return 0.0
        try:
            cols = [col for col in data.get("columns", []) if col[0] != "x"]
            if not cols:
                return 0.0
            vals = cols[0][1:]
            if len(vals) < 2:
                return 0.0
            idx = -(GRAPH_WINDOW_DAYS + 1)
            start = vals[idx] if len(vals) >= abs(idx) else vals[0]
            return round(((vals[-1] - start) / start) * 100, 2) if start > 0 else 0.0
        except (KeyError, IndexError, ZeroDivisionError, TypeError):
            return 0.0

    def _calculate_detailed_deltas(self, graph: Any) -> Dict[str, int]:
        """Subscriber deltas: today / week / month from growth graph."""
        default = {"subs_today": 0, "subs_week": 0, "subs_month": 0}
        data = self._extract_graph_data(graph)
        if not data:
            return default
        try:
            y_cols = [col for col in data.get("columns", []) if col[0].startswith("y")]
            if not y_cols or not y_cols[0][1:]:
                return default
            vals = y_cols[0][1:]
            curr = vals[-1]
            week_idx = -(GRAPH_DAYS_WEEK + 1)
            month_idx = -(GRAPH_DAYS_MONTH + 1)
            return {
                "subs_today": int(curr - vals[-2]) if len(vals) >= 2 else 0,
                "subs_week": (
                    int(curr - vals[week_idx])
                    if len(vals) >= abs(week_idx)
                    else int(curr - vals[0])
                ),
                "subs_month": (
                    int(curr - vals[month_idx])
                    if len(vals) >= abs(month_idx)
                    else int(curr - vals[0])
                ),
            }
        except (KeyError, IndexError, ZeroDivisionError, TypeError):
            return default

    def _calculate_joins_leaves(self, graph: Any) -> Dict[str, int]:
        """Joins / leaves for the last data-point from new-followers graph."""
        data = self._extract_graph_data(graph)
        if not data:
            return {"joins_24h": 0, "leaves_24h": 0}

        cols = data.get("columns", [])
        joins = [c for c in cols if c[0] == "y0"]
        leaves = [c for c in cols if c[0] == "y1"]
        return {
            "joins_24h": int(joins[0][-1]) if joins else 0,
            "leaves_24h": int(leaves[0][-1]) if leaves else 0,
        }

    def _calculate_languages(self, graph: Any) -> Dict[str, float]:
        """Language distribution (%) from the languages graph."""
        data = self._extract_graph_data(graph)
        if not data:
            return {}
        try:
            cols = data.get("columns", [])
            names = data.get("names", {})
            raw: Dict[str, int] = {}
            total = 0
            for col in cols:
                if col[0] == "x":
                    continue
                label = names.get(col[0], col[0])
                val = int(col[-1]) if len(col) > 1 else 0
                if val > 0:
                    raw[label] = val
                    total += val
            if total <= 0:
                return {}
            return {label: round((cnt / total) * 100, 1) for label, cnt in raw.items()}
        except (KeyError, IndexError, ZeroDivisionError, TypeError):
            return {}


class ChannelAnalyticsService:
    """High-level service: connects to Telegram user-bot and collects stats."""

    def __init__(self):
        self.api_id = settings.telegram_api_id
        self.api_hash = settings.telegram_api_hash
        self.session_str = settings.telegram_user_session
        self.client: Optional[TelegramClient] = None

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> "ChannelAnalyticsService":
        """Connect the Telethon client (idempotent)."""
        if not self.client:
            self.client = TelegramClient(
                StringSession(self.session_str),
                self.api_id,
                self.api_hash,
                connection_retries=DEFAULT_CONNECTION_RETRIES,
                retry_delay=DEFAULT_RETRY_DELAY,
            )
            await self.client.connect()
        return self

    async def stop(self):
        """Disconnect the Telethon client."""
        if self.client:
            await self.client.disconnect()
            self.client = None

    def _ensure_client(self) -> TelegramClient:
        if not self.client:
            raise RuntimeError("Client not started")
        return self.client

    # -- public API ----------------------------------------------------------

    async def get_me(self) -> types.User:
        """Get info about the current user-bot session."""
        return await self._ensure_client().get_me()

    async def join_channel(self, link_or_handle: str) -> None:
        """Join a channel by invite link or public handle."""
        client = self._ensure_client()
        try:
            if "t.me/+" in link_or_handle or "t.me/joinchat/" in link_or_handle:
                invite_hash = link_or_handle.split("/")[-1].replace("+", "")
                await client(functions.messages.ImportChatInviteRequest(hash=invite_hash))
            else:
                entity = await client.get_entity(link_or_handle)
                await client(functions.channels.JoinChannelRequest(channel=entity))
        except errors.UserAlreadyParticipantError:
            pass
        except Exception as e:
            logger.error("Join failed: %s", e)

    async def fetch_channel_stats(self, identifier: ChannelIdentifier) -> ChannelStats:
        """Fetch official Telegram broadcast stats + basic channel info."""
        client = self._ensure_client()
        entity = await client.get_entity(identifier)
        full = await client(functions.channels.GetFullChannelRequest(channel=entity))

        # Try official stats; fall back to manual view sampling
        try:
            stats_raw = await client(
                functions.stats.GetBroadcastStatsRequest(channel=entity, dark=False)
            )
            stats_data = await TelegramStatsParser(client).parse(stats_raw, full)
        except (errors.ChatAdminRequiredError, errors.RPCError):
            messages = await client.get_messages(entity, limit=50)
            views = [m.views for m in messages if hasattr(m, "views") and m.views is not None]
            stats_data = {
                "telegram_metrics": {
                    "followers": full.full_chat.participants_count,
                    "avg_views_per_post": sum(views) // len(views) if views else 0,
                },
            }

        # Channel creation date
        first_msg = await client.get_messages(entity, limit=1, reverse=True)
        stats_data["telegram_metrics"]["channel_created_at"] = (
            ensure_utc(first_msg[0].date) if first_msg else ensure_utc(entity.date)
        )

        return {
            "channel_id": entity.id,
            "username": getattr(entity, "username", None),
            "subscribers": full.full_chat.participants_count,
            "fetched_at": utcnow().isoformat(),
            "telegram_metrics": stats_data.get("telegram_metrics", {}),
            "calculated_metrics": None,
        }

    async def scan_channel(
        self,
        identifier: ChannelIdentifier,
        limit: int = DEFAULT_SCAN_LIMIT,
    ) -> List[Dict[str, Any]]:
        """Scan recent posts and return a list of post dicts."""
        client = self._ensure_client()
        entity = await client.get_entity(identifier)
        messages = await client.get_messages(entity, limit=limit)

        result: list[Dict[str, Any]] = []
        for m in messages:
            if (
                not m.date
                or not isinstance(m, types.Message)
                or m.views is None
                or getattr(m, "action", None)
            ):
                continue

            reactions: Dict[str, int] = {}
            if m.reactions and m.reactions.results:
                for r in m.reactions.results:
                    reactions[getattr(r.reaction, "emoticon", "custom")] = r.count

            result.append({
                "post_id": m.id,
                "date": ensure_utc(m.date),
                "views": m.views,
                "forwards": m.forwards or 0,
                "replies": m.replies.replies if (m.replies and m.replies.replies) else 0,
                "reactions": reactions,
                "content_type": (
                    "photo" if m.photo
                    else "video" if m.video
                    else "document" if m.document
                    else "voice" if m.voice
                    else "text"
                ),
                "has_links": any(
                    isinstance(e, (types.MessageEntityTextUrl, types.MessageEntityUrl))
                    for e in (m.entities or [])
                ),
                "grouped_id": getattr(m, "grouped_id", None),
            })

        return result

    async def get_detailed_stats(
        self,
        identifier: ChannelIdentifier,
        limit: Optional[int] = None,
    ) -> DetailedStats:
        """Iterate participants to compute premium share & language breakdown."""
        client = self._ensure_client()
        entity = await client.get_entity(identifier)
        full = await client(functions.channels.GetFullChannelRequest(entity))
        total = full.full_chat.participants_count or 0

        # Select fetch limit based on channel size
        if limit:
            fetch_limit = min(limit, total)
        elif total > CHANNEL_SIZE_MEDIUM:
            fetch_limit = min(MAX_FETCH_LIMIT_LARGE, total)
        elif total > CHANNEL_SIZE_SMALL:
            fetch_limit = min(MAX_FETCH_LIMIT_MEDIUM, total)
        else:
            fetch_limit = min(MAX_FETCH_LIMIT_SMALL, total)

        stats: DetailedStats = {
            "total_processed": 0,
            "premium_count": 0,
            "premium_percentage": 0.0,
            "region_stats": {},
        }
        processed: set[int] = set()

        async for p in client.iter_participants(entity, limit=fetch_limit):
            if p.id in processed:
                continue
            processed.add(p.id)

            stats["total_processed"] += 1

            is_premium = (
                getattr(p, "premium", False)
                or getattr(p, "premium_first_sent_date", None)
                or "premium" in str(getattr(p, "status", "")).lower()
            )
            if is_premium:
                stats["premium_count"] += 1

            lang_code = getattr(p, "lang_code", None)
            if lang_code:
                stats["region_stats"][lang_code] = stats["region_stats"].get(lang_code, 0) + 1

        if stats["total_processed"] > 0:
            stats["premium_percentage"] = round(
                stats["premium_count"] / stats["total_processed"] * 100, 2
            )

        return stats

    def calculate_stats(self, posts: List[Dict[str, Any]], subscribers: int = 0) -> Dict[str, Any]:
        """Shortcut to :meth:`PostAnalytics.calculate`."""
        return PostAnalytics.calculate(posts, subscribers)
