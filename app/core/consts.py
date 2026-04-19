import re


STRING_COLUMN_255 = 255
POST_MAX_LENGTH = 10_000

PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Za-z0-9!-/:-@[-`{-~]{8,255}$")
