-- name: find_user
SELECT 
    * 
FROM users 
WHERE user_id = ?;


-- name: update_existing_user
UPDATE users SET 
    username = COALESCE(?, username),
    first_name = COALESCE(?, first_name),
    last_name = COALESCE(?, last_name),
    last_active_at = CURRENT_TIMESTAMP
WHERE user_id = ?;


-- name: add_new_user
INSERT INTO users 
    (user_id, username, first_name, last_name, access_level, remaining_free_queries)
VALUES (?, ?, ?, ?, 'free', 30);


-- name: validate_user
SELECT 
    access_level, 
    remaining_free_queries 
FROM users 
WHERE user_id = ?;

-- name: minus_free_query
UPDATE users SET 
    remaining_free_queries = remaining_free_queries - 1 
WHERE user_id = ?;


-- name: add_query_count
UPDATE users SET 
    total_queries = total_queries + 1,
    last_active_at = CURRENT_TIMESTAMP
WHERE user_id = ?;


--name: register_msg
INSERT INTO messages
    (user_id, provider, model_id, input_tokens, output_tokens, query_cost)
VALUES (?, ?, ?, ?, ?, ?);


-- name: update_provider_stats
UPDATE provider_stats SET
    total_messages = total_messages + 1,
    total_input_tokens = total_input_tokens + ?,
    total_output_tokens = total_output_tokens + ?,
    total_tokens = total_tokens + ?,
    total_cost = total_cost + ?
WHERE provider = ?;


-- name: get_users_count
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN access_level = 'free' THEN 1 ELSE 0 END) as free,
    SUM(CASE WHEN access_level = 'premium' THEN 1 ELSE 0 END) as premium,
    SUM(CASE WHEN access_level = 'admin' THEN 1 ELSE 0 END) as admin
FROM users;


-- name: get_active_users_count
SELECT 
    COUNT(DISTINCT user_id) as count
FROM users
WHERE last_active_at >= datetime('now', ?);


-- name: get_total_cost
SELECT 
    SUM(query_cost) as cost
FROM messages;


-- name: get_provider_stats
SELECT 
    *
FROM provider_stats
ORDER BY total_messages DESC;


-- name: get_daily_stats
SELECT
    date(m.created_at) as date,
    count(m.message_id) as total_messages,
    sum(case when u.access_level = "free" then 1 else 0 end) as free_user_messages,
    sum(case when u.access_level = "premium" then 1 else 0 end) as premium_user_messages,
    sum(case when u.access_level = "admin" then 1 else 0 end) as admin_user_messages,
    sum(m.query_cost) as total_cost
FROM messages as m
LEFT JOIN users as u ON
    u.user_id = m.user_id
WHERE created_at >= date('now') - ?
GROUP BY date(m.created_at);


-- name: get_recent_users
SELECT 
    user_id, username, first_name, last_name, 
    access_level, remaining_free_queries, total_queries,
    registered_at, last_active_at
FROM users
ORDER BY last_active_at DESC
LIMIT ?;


-- name: get_free_users
SELECT 
    user_id, username, first_name, last_name, 
    access_level, remaining_free_queries, total_queries,
    registered_at, last_active_at
FROM users
WHERE access_level == 'free'
ORDER BY last_active_at DESC
LIMIT ?;


-- name: admin_change_user_role
UPDATE users SET 
    access_level = ? 
WHERE user_id = ?;


-- name: admin_add_credit
UPDATE users SET 
    remaining_free_queries = ? 
WHERE user_id = ?;