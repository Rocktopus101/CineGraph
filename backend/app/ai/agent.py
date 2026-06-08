import json
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.models.movie import Movie
from app.models.user_data import UserMovie
from app.retrieval.retrieval_service import RetrievalService
from app.schemas.recommendation import Citation
from app.services.observability_service import ObservabilityService
from app.services.recommendation_service import RecommendationService
from app.services.tmdb_service import TmdbService

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_movies",
            "description": "Search for movies by title",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_movie_details",
            "description": "Get details for a movie by ID",
            "parameters": {
                "type": "object",
                "properties": {"movie_id": {"type": "integer"}},
                "required": ["movie_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_history",
            "description": "Get user's watch history with optional filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "genre": {"type": "string"},
                    "min_rating": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_rated_movies",
            "description": "Get user's top rated movies",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                    "genre": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_similar_movies",
            "description": "Find movies similar to a given movie",
            "parameters": {
                "type": "object",
                "properties": {"movie_id": {"type": "integer"}},
                "required": ["movie_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_user_reviews",
            "description": "Semantic search over user's reviews",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_recommendations",
            "description": "Generate personalized recommendations",
            "parameters": {
                "type": "object",
                "properties": {"context": {"type": "string"}},
                "required": ["context"],
            },
        },
    },
]


def _normalize_tool_name(name: str) -> str:
    if name.startswith("default_api:"):
        return name.split(":", 1)[1]
    return name


class AgentService:
    MAX_TOOL_CALLS = 3

    def __init__(self, db: AsyncSession, obs: ObservabilityService):
        self.db = db
        self.obs = obs
        self.provider = get_llm_provider()
        self.retrieval = RetrievalService(db)
        self.recommendation = RecommendationService(db, obs)
        self.tmdb = TmdbService(db)

    async def chat(self, user_id: int, message: str) -> tuple[str, list[Citation], int]:
        query_id = await self.obs.start_query(user_id, message)

        if not self.provider.supports_chat:
            response, citations = await self.recommendation.generate(user_id, message)
            await self.obs.complete_query(response)
            return response, citations, query_id

        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are CineGraph, a movie recommendation agent. Use tools to ground answers in "
                    "the user's actual viewing history. Never hallucinate movies the user hasn't watched. "
                    "Always cite specific films from the user's history when making recommendations."
                ),
            },
            {"role": "user", "content": message},
        ]

        citations: list[Citation] = []
        tool_calls_count = 0

        while tool_calls_count < self.MAX_TOOL_CALLS:
            self.obs.start_timer("llm")
            try:
                resp = await self.provider.chat_completion(
                    messages=messages,
                    tools=TOOLS,
                    max_tokens=1000,
                )
            except Exception as exc:
                logger.warning("Agent chat failed (%s); falling back to recommendations", exc)
                response, citations = await self.recommendation.generate(user_id, message)
                await self.obs.complete_query(response)
                return response, citations, query_id
            await self.obs.log_event(
                "llm_call",
                {"provider": self.provider.name},
                latency_ms=self.obs.elapsed_ms("llm"),
                tokens_in=resp.usage.prompt_tokens if resp.usage else None,
                tokens_out=resp.usage.completion_tokens if resp.usage else None,
            )

            if not resp.tool_calls:
                response = resp.content or ""
                await self.obs.complete_query(response)
                return response, citations, query_id

            if resp.assistant_message:
                messages.append(resp.assistant_message)
            else:
                messages.append({"role": "assistant", "content": resp.content})

            for tool_call in resp.tool_calls:
                tool_calls_count += 1
                gemini_fn_name = tool_call.name
                fn_name = _normalize_tool_name(gemini_fn_name)
                args = json.loads(tool_call.arguments)
                self.obs.start_timer(f"tool_{fn_name}")
                result = await self._execute_tool(user_id, fn_name, args)
                await self.obs.log_event(
                    "tool_call",
                    {"name": fn_name, "args": args, "result_size": len(str(result))},
                    latency_ms=self.obs.elapsed_ms(f"tool_{fn_name}"),
                )
                if fn_name == "generate_recommendations" and isinstance(result, dict):
                    citations = [Citation(**c) for c in result.get("citations", [])]
                messages.append({
                    "role": "tool",
                    "name": gemini_fn_name,
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

        response = "I've analyzed your viewing history. Let me know if you'd like more specific recommendations."
        await self.obs.complete_query(response)
        return response, citations, query_id

    async def _execute_tool(self, user_id: int, name: str, args: dict) -> Any:
        if name == "search_movies":
            data = await self.tmdb.search_movie(args["query"])
            return [{"id": r["id"], "title": r["title"]} for r in data.get("results", [])[:10]]

        if name == "get_movie_details":
            result = await self.db.execute(select(Movie).where(Movie.id == args["movie_id"]))
            m = result.scalar_one_or_none()
            if not m:
                return {"error": "Movie not found"}
            return {"id": m.id, "title": m.title, "year": m.year, "overview": m.overview}

        if name == "get_user_history":
            query = (
                select(UserMovie, Movie)
                .join(Movie, UserMovie.movie_id == Movie.id)
                .where(UserMovie.user_id == user_id)
            )
            if args.get("days"):
                cutoff = date.today() - timedelta(days=args["days"])
                query = query.where(UserMovie.watched_date >= cutoff)
            if args.get("min_rating"):
                query = query.where(UserMovie.rating >= args["min_rating"])
            result = await self.db.execute(query.order_by(UserMovie.watched_date.desc()).limit(30))
            items = []
            for um, m in result.all():
                if args.get("genre"):
                    genres = (m.metadata_json or {}).get("genres", [])
                    if args["genre"] not in genres:
                        continue
                items.append({
                    "movie_id": m.id,
                    "title": m.title,
                    "rating": um.rating,
                    "watched_date": str(um.watched_date) if um.watched_date else None,
                })
            return items

        if name == "get_top_rated_movies":
            limit = args.get("limit", 10)
            result = await self.db.execute(
                select(UserMovie, Movie)
                .join(Movie, UserMovie.movie_id == Movie.id)
                .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
                .order_by(UserMovie.rating.desc())
                .limit(limit * 2)
            )
            items = []
            for um, m in result.all():
                if args.get("genre"):
                    genres = (m.metadata_json or {}).get("genres", [])
                    if args["genre"] not in genres:
                        continue
                items.append({"movie_id": m.id, "title": m.title, "rating": um.rating})
                if len(items) >= limit:
                    break
            return items

        if name == "find_similar_movies":
            docs = await self.retrieval.find_similar_movies(args["movie_id"])
            return [{"movie_id": d.movie_id, "title": d.citation_text, "score": d.score} for d in docs]

        if name == "search_user_reviews":
            docs = await self.retrieval.retrieve(args["query"], user_id, limit=10)
            return [{"movie_id": d.movie_id, "text": d.citation_text, "score": d.score} for d in docs]

        if name == "generate_recommendations":
            response, citations = await self.recommendation.generate(user_id, args["context"])
            return {"response": response, "citations": [c.model_dump() for c in citations]}

        return {"error": f"Unknown tool: {name}"}
