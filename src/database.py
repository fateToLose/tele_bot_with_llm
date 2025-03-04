import os
import logging
import sqlite3

from datetime import datetime

logger = logging.getLogger(__name__)


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
