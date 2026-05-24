# Redis Procedures

## `send_message_to_user.lua`

This script implements the `send_message_to_user` domain operation in one Redis-side procedure call.

## What it does

1. Gets an existing direct conversation by key or creates it from the passed JSON candidate.
2. Adds sender and receiver to the participants set.
3. Adds message id into the conversation sorted set by `sent_at` score.
4. Stores the message payload by `message:{id}` key.

The script does not compute business values itself; it only uses keys and values passed from application code.

## KEYS

1. `direct_conversation_key` - `direct:conversation:{low_id}:{high_id}`
2. `participants_key` - `participants:{conversation_id}`
3. `messages_key` - `messages:{conversation_id}`
4. `message_key` - `message:{message_id}`

## ARGV

1. `conversation_json_candidate` - serialized `ConversationDto`
2. `sender_id`
3. `receiver_id`
4. `message_member` - message id placed into `ZSET`
5. `sent_at_score` - timestamp score for `ZADD`
6. `message_json` - serialized `MessageCreateSchema`

## Return value

Array with:

1. `final_conversation_json`
2. `added_participants_count`
3. `zadd_result`

## `get_dialog_with_users.lua`

Reads dialog messages for one conversation from Redis.

- Takes:
  - `messages:{conversation_id}` key
  - `message:` key prefix
  - pagination params (`offset`, `limit`) and `order`
- Reads message ids from `ZSET`, then fetches payloads via one `MGET`.
- Returns array of message JSON strings in requested order.
