-- check_existing
SELECT
    *
FROM users
WHERE
    user_id = ?;