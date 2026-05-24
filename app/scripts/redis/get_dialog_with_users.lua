-- KEYS:
-- 1 = messages_key          (messages:{conversation_id})
-- 2 = message_key_prefix    (message:)
--
-- ARGV:
-- 1 = offset
-- 2 = limit
-- 3 = order ("desc" | "asc")
--
-- Returns:
-- array of message JSON strings

local messages_key = KEYS[1]
local message_key_prefix = KEYS[2]

local offset = tonumber(ARGV[1]) or 0
local limit = tonumber(ARGV[2]) or 1000
local order = ARGV[3] or "desc"

local from_index = offset
local to_index = offset + limit - 1

local message_ids
if order == "asc" then
  message_ids = redis.call("ZRANGE", messages_key, from_index, to_index)
else
  message_ids = redis.call("ZREVRANGE", messages_key, from_index, to_index)
end

if #message_ids == 0 then
  return {}
end

local message_keys = {}
for _, message_id in ipairs(message_ids) do
  message_keys[#message_keys + 1] = message_key_prefix .. message_id
end

local raw_messages = redis.call("MGET", unpack(message_keys))
local result = {}
for _, raw_message in ipairs(raw_messages) do
  if raw_message then
    result[#result + 1] = raw_message
  end
end

return result
