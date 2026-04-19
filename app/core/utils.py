import datetime as dt


def utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)
