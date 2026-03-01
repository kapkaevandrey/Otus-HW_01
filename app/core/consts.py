import re


STRING_COLUMN_255 = 255

PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Za-z0-9!-/:-@[-`{-~]{8,255}$")
