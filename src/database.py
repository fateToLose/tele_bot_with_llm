import os
import logging
import sqlite3

from datetime import datetime

logger = logging.getLogger(__name__)
user_mgr = None


class UserManager:
    def __init__(self, db_path: str, query_path: str) -> None:
        self.db_path = db_path
        self.query_path = query_path

        self._check_db()

    def _connect_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _check_db(self):
        conn = self._connect_db()
        init_query_path = os.path.join(self.query_path, "init_db.sql")

        with open(init_query_path, "r") as file:
            query = file.read()

        try:
            conn.executescript(query)
            conn.commit()
        except Exception as e:
            logger.error(f"Error initialising database: {e}")
        finally:
            conn.close()

    def register_user(
        self, user_id: int, username: str | None = None, first_name: str | None = None, last_name: str | None = None
    ):
        conn = self._connect_db()

        try:
            user = conn.execute(
                """
                SELECT * FROM users WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if user:
                conn.execute(
                    """
                    UPDATE users SET 
                        username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name),
                        last_active_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (username, first_name, last_name, user_id),
                )

            else:
                conn.execute(
                    """
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, access_level, remaining_free_queries)
                    VALUES (?, ?, ?, ?, 'free', 30)
                    """,
                    (user_id, username, first_name, last_name),
                )
            conn.commit()

        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            conn.rollback()
            return {"user_id": user_id, "access_level": "free", "remaining_free_queries": 30}

        finally:
            conn.close()

    def validate_user(self, user_id: int) -> tuple[bool, str]:
        conn = self._connect_db()

        try:
            user = conn.execute(
                "SELECT access_level, remaining_free_queries FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

            access_level = user["access_level"]
            remaining = user["remaining_free_queries"]

            # Admin and premium users always have access
            if access_level in ("admin", "premium"):
                return True, access_level

            # Free users with remaining queries
            if access_level == "free" and remaining > 0:
                return True, f"free:{remaining}"

            # Free users with no remaining queries
            return False, "No queries remaining"

        except Exception as e:
            logging.error(f"Error checking user access for {user_id}: {e}")
            return False, f"Error: {str(e)}"

        finally:
            conn.close()

    def record_msg(
        self, user_id: int, provider: str, model_id: str, input_tokens: int, output_tokens: int, query_cost: float
    ):
        conn = self._connect_db()

        try:
            user = conn.execute(
                "SELECT access_level, remaining_free_queries FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

            if not user:
                logger.info(f"User {user_id} has no free queries available.")
                conn.rollback()
                return False

            if user["access_level"] == "free" and user["remaining_free_queries"] > 0:
                logger.info(f"User {user_id} - {user['access_level']} - Remaining: {user['remaining_free_queries']}")

                conn.execute(
                    "UPDATE users SET remaining_free_queries = remaining_free_queries - 1 WHERE user_id = ?", (user_id,)
                )

            conn.execute(
                """
                UPDATE users SET 
                    total_queries = total_queries + 1,
                    last_active_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )

            conn.execute(
                """
                INSERT INTO messages
                (user_id, provider, model_id, input_tokens, output_tokens, query_cost)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, provider, model_id, input_tokens, output_tokens, query_cost),
            )

            total_tokens = input_tokens + output_tokens
            conn.execute(
                """
                UPDATE provider_stats SET
                    total_messages = total_messages + 1,
                    total_input_tokens = total_input_tokens + ?,
                    total_output_tokens = total_output_tokens + ?,
                    total_tokens = total_tokens + ?,
                    total_cost = total_cost + ?
                WHERE provider = ?
                """,
                (input_tokens, output_tokens, total_tokens, query_cost, provider),
            )

            conn.commit()
            return True

        except Exception as e:
            logging.error(f"Error logging message for user {user_id}: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def get_user(self, user_id: int) -> dict | None:
        conn = self._connect_db()

        try:
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

            return dict(user) if user else None

        except Exception as e:
            logger.error(f"Error in getting user {user_id}: {e}")
            return None

        finally:
            conn.close()

    def get_user_count(self) -> dict[str, int]:
        conn = self._connect_db()
        try:
            result = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN access_level = 'free' THEN 1 ELSE 0 END) as free,
                    SUM(CASE WHEN access_level = 'premium' THEN 1 ELSE 0 END) as premium,
                    SUM(CASE WHEN access_level = 'admin' THEN 1 ELSE 0 END) as admin
                FROM users
                """
            ).fetchone()

            return dict(result)

        except Exception as e:
            logging.error(f"Error getting user count: {e}")
            return {"total": 0, "free": 0, "premium": 0, "admin": 0}
        finally:
            conn.close()

    def get_active_users(self, days: int = 7) -> int:
        conn = self._connect_db()
        try:
            result = conn.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count
                FROM users
                WHERE last_active_at >= datetime('now', ?)
                """,
                (f"-{days} days",),
            ).fetchone()

            return result["count"]

        except Exception as e:
            logging.error(f"Error getting active users: {e}")
            return 0
        finally:
            conn.close()

    def get_total_cost(self) -> float:
        conn = self._connect_db()
        try:
            result = conn.execute(
                """
                SELECT SUM(query_cost) as cost
                FROM messages
                """
            ).fetchone()

            return result["cost"]

        except Exception as e:
            logging.error(f"Error getting total cost: {e}")
            return 0.0
        finally:
            conn.close()

    def get_provider_stats(self) -> list[dict]:
        conn = self._connect_db()
        try:
            cursor = conn.execute(
                """
                SELECT *
                FROM provider_stats
                ORDER BY total_messages DESC
                """
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logging.error(f"Error getting provider stats: {e}")
            return []
        finally:
            conn.close()

    def get_daily_stats(self, days: int = 7) -> list[dict]:
        conn = self._connect_db()
        try:
            cursor = conn.execute(
                """
                SELECT *
                FROM messages
                WHERE date >= date('now', ?)
                ORDER BY date DESC
                """,
                (f"-{days} days",),
            )
            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logging.error(f"Error getting daily stats: {e}")
            return []
        finally:
            conn.close()

    def list_users(self, limit: int = 10) -> list[dict]:
        conn = self._connect_db()
        try:
            cursor = conn.execute(
                """
                SELECT 
                    user_id, username, first_name, last_name, 
                    access_level, remaining_free_queries, total_queries,
                    registered_at, last_active_at
                FROM users
                ORDER BY last_active_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logging.error(f"Error listing users: {e}")
            return []
        finally:
            conn.close()

    def list_free_user(self, limit: int = 5) -> list[dict]:
        conn = self._connect_db()
        try:
            cursor = conn.execute(
                """
                SELECT 
                    user_id, username, first_name, last_name, 
                    access_level, remaining_free_queries, total_queries,
                    registered_at, last_active_at
                FROM users
                WHERE access_level == 'free'
                ORDER BY last_active_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logging.error(f"Error listing users: {e}")
            return []
        finally:
            conn.close()

    def update_user_access(self, user_id: int, access_level: str) -> bool:
        if access_level not in ("free", "premium", "admin"):
            logger.error(f"Invalid access level: {access_level}")
            return False

        conn = self._connect_db()
        try:
            conn.execute("UPDATE users SET access_level = ? WHERE user_id = ?", (access_level, user_id))
            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating user access for {user_id}: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def reset_free_queries(self, user_id: int, count: int = 30) -> bool:
        conn = self._connect_db()
        try:
            conn.execute("UPDATE users SET remaining_free_queries = ? WHERE user_id = ?", (count, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error resetting free queries for {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


# Global Function to initalise UserManager
def init_user_mgr(db_path: str, query_path: str) -> UserManager | None:
    global user_mgr
    if user_mgr is None:
        try:
            user_mgr = UserManager(db_path, query_path)
            logger.info("Initalised UserManager")
            return user_mgr

        except Exception as e:
            RuntimeError(f"UserManager is not initialised - {e}")
    return user_mgr


def get_user_mgr() -> UserManager | None:
    if user_mgr is None:
        raise RuntimeError("UserManager is not initialised")
    return user_mgr
