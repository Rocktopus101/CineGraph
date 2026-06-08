from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.user_data import UserList, UserListItem, UserMovie, WatchlistItem


class ListGeneratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_lists(self, user_id: int) -> list[UserList]:
        await self.db.execute(delete(UserList).where(UserList.user_id == user_id))
        lists = []

        # Highest Rated
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
            .order_by(UserMovie.rating.desc())
            .limit(20)
        )
        rows = result.all()
        if rows:
            lst = UserList(
                user_id=user_id,
                name="Highest Rated",
                list_type="taste_generated",
                description="Your top-rated films",
            )
            self.db.add(lst)
            await self.db.flush()
            for rank, (um, movie) in enumerate(rows):
                self.db.add(UserListItem(list_id=lst.id, movie_id=movie.id, rank=rank))
            lists.append(lst)

        # Top genres
        from app.services.taste_profile_service import TasteProfileService

        taste = TasteProfileService(self.db)
        profile = await taste.get_profile(user_id)
        top_genres = (profile.insights_json or {}).get("top_genres", [])[:3] if profile else []

        if top_genres:
            result = await self.db.execute(
                select(UserMovie, Movie)
                .join(Movie, UserMovie.movie_id == Movie.id)
                .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
            )
            rated_rows = result.all()

        for genre_info in top_genres:
            genre = genre_info["genre"]
            genre_movies = [
                (um, movie)
                for um, movie in rated_rows
                if genre in (movie.metadata_json or {}).get("genres", [])
            ]
            genre_movies.sort(key=lambda x: x[0].rating or 0, reverse=True)
            genre_movies = genre_movies[:15]
            if genre_movies:
                lst = UserList(
                    user_id=user_id,
                    name=f"Top {genre}",
                    list_type="taste_generated",
                    description=f"Your highest-rated {genre} films",
                )
                self.db.add(lst)
                await self.db.flush()
                for rank, (_, movie) in enumerate(genre_movies):
                    self.db.add(UserListItem(list_id=lst.id, movie_id=movie.id, rank=rank))
                lists.append(lst)

        # Recently Loved (5-star last 90 days)
        cutoff = date.today() - timedelta(days=90)
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(
                UserMovie.user_id == user_id,
                UserMovie.rating >= 4.5,
                UserMovie.watched_date >= cutoff,
            )
            .order_by(UserMovie.watched_date.desc())
            .limit(10)
        )
        recent = result.all()
        if recent:
            lst = UserList(
                user_id=user_id,
                name="Recently Loved",
                list_type="taste_generated",
                description="Films you loved in the last 90 days",
            )
            self.db.add(lst)
            await self.db.flush()
            for rank, (_, movie) in enumerate(recent):
                self.db.add(UserListItem(list_id=lst.id, movie_id=movie.id, rank=rank))
            lists.append(lst)

        # Watch Next
        result = await self.db.execute(
            select(WatchlistItem, Movie)
            .join(Movie, WatchlistItem.movie_id == Movie.id)
            .where(WatchlistItem.user_id == user_id)
            .limit(20)
        )
        watchlist = result.all()
        if watchlist:
            lst = UserList(
                user_id=user_id,
                name="Watch Next",
                list_type="taste_generated",
                description="Films on your watchlist",
            )
            self.db.add(lst)
            await self.db.flush()
            for rank, (_, movie) in enumerate(watchlist):
                self.db.add(UserListItem(list_id=lst.id, movie_id=movie.id, rank=rank))
            lists.append(lst)

        await self.db.flush()
        return lists

    async def get_lists(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(UserList).where(UserList.user_id == user_id)
        )
        lists = result.scalars().all()
        output = []
        for lst in lists:
            count_result = await self.db.execute(
                select(UserListItem).where(UserListItem.list_id == lst.id)
            )
            output.append({
                "id": lst.id,
                "name": lst.name,
                "list_type": lst.list_type,
                "description": lst.description,
                "item_count": len(count_result.scalars().all()),
            })
        return output

    async def get_list_detail(self, user_id: int, list_id: int) -> dict | None:
        result = await self.db.execute(
            select(UserList).where(UserList.id == list_id, UserList.user_id == user_id)
        )
        lst = result.scalar_one_or_none()
        if not lst:
            return None
        items_result = await self.db.execute(
            select(UserListItem, Movie)
            .join(Movie, UserListItem.movie_id == Movie.id)
            .where(UserListItem.list_id == list_id)
            .order_by(UserListItem.rank)
        )
        items = [movie for _, movie in items_result.all()]
        return {
            "id": lst.id,
            "name": lst.name,
            "list_type": lst.list_type,
            "description": lst.description,
            "items": items,
        }
