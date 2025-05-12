import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from rectools import Columns
from sqlalchemy import func, select, distinct
from sqlalchemy.exc import SQLAlchemyError

from recommender_service.config.external.models import (
    RawUsers, Bookmarks, Rating, UserTitleData,
    TitlesTitleRelation, Comments, UserBuys, 
    TitleChapter, TitlesSites, Titles, 
    TitlesCategories, TitlesGenres
)
from recommender_service.config.database import ExternalSession
import warnings
import os
import threadpoolctl

from recommender_service.utils.age_group import calculate_age_group
from recommender_service.utils.cat_chapters import categorize_chapters

warnings.filterwarnings('ignore')
os.environ["OPENBLAS_NUM_THREADS"] = "1"
threadpoolctl.threadpool_limits(1, "blas")

USERS_LIMIT = 1000000
DAYS = 1000000
test_users_ids = [34]

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def fetch_data_in_parallel():
    """Получение данных из внешней БД параллельно"""
    with ExternalSession() as session:
        with ThreadPoolExecutor() as executor:
            # Определяем задачи для параллельного выполнения
            titles_future = executor.submit(
                pd.read_sql_query,
                session.query(Titles).filter_by(is_erotic=0, is_yaoi=0, uploaded=1).order_by(None).statement,
                session.bind
            )
            categories_future = executor.submit(
                pd.read_sql_query,
                session.query(TitlesCategories).statement,
                session.bind
            )
            genres_future = executor.submit(
                pd.read_sql_query,
                session.query(TitlesGenres).statement,
                session.bind
            )
            relations_future = executor.submit(
                pd.read_sql_query,
                session.query(TitlesTitleRelation).statement,
                session.bind
            )

            titles_pd = titles_future.result()
            titles_categories_pd = categories_future.result()
            titles_genres_pd = genres_future.result()
            titles_relations_pd = relations_future.result()

    return titles_pd, titles_categories_pd, titles_genres_pd, titles_relations_pd

class DataPreparationService:
    @staticmethod
    async def boost_int_weights_by_paid(df: pd.DataFrame, boost_factor: float = 1.2) -> pd.DataFrame:
        """Усиление весов взаимодействий для платных глав"""
        if Columns.Weight not in df.columns or Columns.Item not in df.columns:
            return df

        black_list = await BlacklistManager.get_black_titles_ids()

        with ExternalSession() as session:
            paid_titles = session.query(
                distinct(TitleChapter.title_id)
            ).filter(
                TitleChapter.is_paid == True,
                TitleChapter.title_id.in_(df[Columns.Item].unique()),
                ~TitleChapter.title_id.in_(black_list)
            ).all()

            paid_title_ids = {t[0] for t in paid_titles}

        if paid_title_ids:
            paid_mask = df[Columns.Item].isin(paid_title_ids)
            df.loc[paid_mask, Columns.Weight] = df.loc[paid_mask, Columns.Weight] * boost_factor

        return df

    @staticmethod
    async def _get_user_title_data(black_list: set):
        with ExternalSession() as session:
            cur_date = datetime.now()
            user_title_data_pd = pd.read_sql_query(
                session.query(UserTitleData)
                .filter(
                    ~UserTitleData.title_id.in_(black_list))
                .statement, session.bind)
            user_title_data_pd.rename({"last_read_date": Columns.Datetime}, inplace=True)
            new_rows = []

            for index, row in user_title_data_pd.iterrows():
                chapter_votes = row['chapter_votes'] if 'chapter_votes' in row else []
                chapter_views = row['chapter_views'] if 'chapter_views' in row else []

                for _ in chapter_votes:
                    new_rows.append({
                        Columns.User: row[Columns.User],
                        Columns.Item: row["title_id"],
                        Columns.Weight: 6,
                        Columns.Datetime: row['last_read_date']
                    })

                for _ in chapter_views:
                    new_rows.append({
                        Columns.User: row[Columns.User],
                        Columns.Item: row["title_id"],
                        Columns.Weight: 3,
                        Columns.Datetime: row['last_read_date']
                    })

            final_df = pd.DataFrame(new_rows)
            final_df = final_df[[Columns.User, Columns.Item, Columns.Datetime, Columns.Weight]]
            return final_df

    @staticmethod
    async def _get_bookmarks(black_list: set):
        with ExternalSession() as session:
            bookmarks_pd = pd.read_sql_query(
                session.query(Bookmarks)
                .filter(
                    Bookmarks.is_default == 1,
                    ~Bookmarks.title_id.in_(black_list)
                )
                .limit(USERS_LIMIT)
                .statement,
                session.bind
            )
            bookmarks_pd.rename({
                "title_id": Columns.Item,
                "bookmark_type_id": Columns.Weight
            }, axis='columns', inplace=True)
            bookmarks_pd[Columns.Datetime] = pd.to_datetime("now")
            bookmarks_pd[Columns.Weight] = bookmarks_pd[Columns.Weight].apply(map_bookmark_type_id)
            bookmarks_pd.drop(columns=["id", "is_default"], inplace=True)
            bookmarks_pd = bookmarks_pd[[Columns.User, Columns.Item, Columns.Weight, Columns.Datetime]]
            return bookmarks_pd

    @staticmethod
    async def _get_comments(black_list: set):
        with ExternalSession() as session:
            try:
                query = session.query(Comments).filter(
                    Comments.title_id.isnot(None),
                    ~Comments.title_id.in_(black_list),
                    Comments.is_blocked == 0,
                    Comments.is_deleted == 0
                ).limit(USERS_LIMIT)

                comments_pd = pd.read_sql_query(query.statement, session.bind)

                if not comments_pd.empty:
                    comments_pd = (
                        comments_pd
                        .assign(**{Columns.Weight: 1.1})
                        .rename({
                            'user_id': Columns.User,
                            'title_id': Columns.Item,
                            'date': Columns.Datetime
                        }, axis='columns')
                    )
                else:
                    comments_pd = pd.DataFrame(columns=[
                        Columns.User,
                        Columns.Item,
                        Columns.Weight,
                        Columns.Datetime
                    ])
                comments_pd = comments_pd[[Columns.User, Columns.Item, Columns.Weight, Columns.Datetime]]

                return comments_pd

            except SQLAlchemyError as e:
                logger.error(f"Ошибка базы данных: {str(e)}")
                return pd.DataFrame()

    @staticmethod
    async def _get_user_buys(black_list: set):
        with ExternalSession() as session:
            query = session.query(
                UserBuys.user_id,
                UserBuys.date,
                TitleChapter.title_id
            ).join(
                TitleChapter,
                UserBuys.chapter_id == TitleChapter.id
            ).filter(
                ~TitleChapter.title_id.in_(black_list)
            ).limit(1000)

            user_buys_pd = pd.read_sql_query(query.statement, session.bind)
            user_buys_pd.rename({
                "date": Columns.Datetime,
                "title_id": Columns.Item,
                "user_id": Columns.User
            }, axis='columns', inplace=True)
            user_buys_pd[Columns.Weight] = 5
            return user_buys_pd

    @staticmethod
    async def _get_ratings(black_list: set):
        with ExternalSession() as session:
            cur_date = datetime.now()
            query = session.query(Rating).filter(
                ~Rating.title_id.in_(black_list)
            ).limit(1000).statement
            ratings_pd = pd.read_sql_query(query, session.bind)
            ratings_pd.rename({
                "date": Columns.Datetime,
                "title_id": Columns.Item,
                "rating": Columns.Weight
            }, axis='columns', inplace=True)
            ratings_pd.drop(columns=["id"], inplace=True)
            ratings_pd[Columns.Weight] = ratings_pd[Columns.Weight].apply(map_ratings)
            ratings_pd = ratings_pd[[Columns.User, Columns.Item, Columns.Weight, Columns.Datetime]]
            return ratings_pd

    @staticmethod
    async def get_users_features():
        with ExternalSession() as session:
            users_pd = pd.read_sql_query(
                session.query(RawUsers)
                .filter_by(is_banned=0)
                .limit(3000)
                .statement,
                session.bind
            )
            users_pd.fillna('Unknown', inplace=True)
            users_pd['birthday'] = pd.to_datetime(users_pd['birthday'], errors='coerce')
            users_pd["age_group"] = users_pd["birthday"].apply(calculate_age_group)

            user_features_frames = []
            for feature in ["sex", "age_group", "preference"]:
                feature_frame = users_pd.reindex(columns=["id", feature])
                feature_frame.columns = ["id", "value"]
                feature_frame["feature"] = feature
                user_features_frames.append(feature_frame)

            user_features = pd.concat(user_features_frames, ignore_index=True)
            user_features.to_pickle("data/user_features.pickle")
            return user_features 

    @staticmethod
    async def get_interactions():
        """Получение всех взаимодействий пользователей с тайтлами"""
        black_list = await BlacklistManager.get_black_titles_ids()
        
        # Получаем все типы взаимодействий
        user_title_data = await DataPreparationService._get_user_title_data(black_list)
        bookmarks = await DataPreparationService._get_bookmarks(black_list)
        comments = await DataPreparationService._get_comments(black_list)
        user_buys = await DataPreparationService._get_user_buys(black_list)
        ratings = await DataPreparationService._get_ratings(black_list)
        
        # Объединяем все взаимодействия
        interactions = pd.concat([
            user_title_data,
            bookmarks,
            comments,
            user_buys,
            ratings
        ], ignore_index=True)
        
        # Усиливаем веса для платных глав
        interactions = await DataPreparationService.boost_int_weights_by_paid(interactions)
        
        return interactions

    @staticmethod
    async def get_titles_features():
        """Получение признаков тайтлов"""
        titles_pd, titles_categories_pd, titles_genres_pd, titles_relations_pd = fetch_data_in_parallel()
        
        # Создаем признаки для категорий
        category_features = titles_categories_pd.rename(columns={
            "title_id": "id",
            "category_id": "value"
        })
        category_features["feature"] = "category"
        
        # Создаем признаки для жанров
        genre_features = titles_genres_pd.rename(columns={
            "title_id": "id",
            "genre_id": "value"
        })
        genre_features["feature"] = "genre"
        
        # Объединяем все признаки
        title_features = pd.concat([
            category_features,
            genre_features
        ], ignore_index=True)
        
        return title_features 