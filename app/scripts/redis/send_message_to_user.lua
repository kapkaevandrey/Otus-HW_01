-- KEYS:
-- 1 = direct_conversation_key    (direct:conversation:{low_id}:{high_id})
-- 2 = participants_key           (participants:{conversation_id})
-- 3 = messages_key               (messages:{conversation_id})
-- 4 = message_key                (message:{message_id})
--
-- ARGV:
-- 1 = conversation_json_candidate
-- 2 = sender_id
-- 3 = receiver_id
-- 4 = message_member             (message_id)
-- 5 = sent_at_score
-- 6 = message_json
--
-- Returns:
-- { final_conversation_json, added_participants_count, zadd_result }

local direct_conversation_key = KEYS[1]
local participants_key = KEYS[2]
local messages_key = KEYS[3]
local message_key = KEYS[4]

local conversation_json_candidate = ARGV[1]
local sender_id = ARGV[2]
local receiver_id = ARGV[3]
local message_member = ARGV[4]
local sent_at_score = tonumber(ARGV[5])
local message_json = ARGV[6]

local final_conversation_json = redis.call("GET", direct_conversation_key)
if not final_conversation_json then
  redis.call("SET", direct_conversation_key, conversation_json_candidate)
  final_conversation_json = conversation_json_candidate
end

local added_participants_count = redis.call("SADD", participants_key, sender_id, receiver_id)
local zadd_result = redis.call("ZADD", messages_key, sent_at_score, message_member)
redis.call("SET", message_key, message_json)

return { final_conversation_json, tostring(added_participants_count), tostring(zadd_result) }
