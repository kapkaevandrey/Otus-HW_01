import asyncio
import datetime as dt
import json
import random
import uuid
from pathlib import Path

import asyncpg
from faker import Faker


DB_CONFIG = {
    "user": "postgres",
    "password": "app_pswd",
    "database": "app_db",
    "host": "localhost",
    "port": 5432,
}

TABLE_NAME = "users"
BATCH_SIZE = 5000
TOTAL_RECORDS = 1_000_000

K6_IDS_COUNT = 100_000
K6_SEARCH_COUNT = 50_000

PATH = Path(__file__).parent.resolve()

fake = Faker(["ru_RU", "en_US"])  # русские и английские имена

# Генерация 1000 уникальных first_name и second_name
FIRST_NAMES = list({fake.first_name() for _ in range(25_000)})[:1000]
LAST_NAMES = list({fake.last_name() for _ in range(25_000)})[:1000]

print(len(FIRST_NAMES), len(LAST_NAMES))

IDS = [str(uuid.uuid4()) for _ in range(TOTAL_RECORDS)]
ALL_PAIRS = [(fn, ln) for fn in FIRST_NAMES for ln in LAST_NAMES]
random.shuffle(ALL_PAIRS)


async def main():
    conn = await asyncpg.connect(**DB_CONFIG)

    print("Cleaning table...")
    await conn.execute(f"TRUNCATE {TABLE_NAME} RESTART IDENTITY;")

    print("Generating and inserting records...")
    batch = []
    for i, (fn, ln) in enumerate(ALL_PAIRS, start=1):
        if i > TOTAL_RECORDS:
            break
        record = (
            IDS[i - 1],
            fn,
            ln,
            fake.date_of_birth(minimum_age=18, maximum_age=80),
            fake.text(max_nb_chars=200),
            "load_test",
            fake.password(length=10),
            dt.datetime.now(dt.UTC),
        )
        batch.append(record)
        if len(batch) >= BATCH_SIZE:
            await conn.executemany(
                f"""
                INSERT INTO {TABLE_NAME}
                (id, first_name, second_name, birthdate, biography, city, password, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                batch,
            )
            batch = []
            print(f"Inserted {i} records...")

    if batch:
        await conn.executemany(
            f"""
            INSERT INTO {TABLE_NAME}
            (id, first_name, second_name, birthdate, biography, city, password, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            batch,
        )

    await conn.close()
    print("Done inserting!")

    # 1. Генерация списка id для нагрузки
    k6_ids = random.sample(IDS, K6_IDS_COUNT)
    with open(PATH / "user_ids.json", "w") as f:
        json.dump(k6_ids, f)
    print(f"user_ids.json: {len(k6_ids)}")

    # 2. search пары
    search_pairs = random.sample(ALL_PAIRS, K6_SEARCH_COUNT)
    k6_pairs = [{"first_name": fn, "last_name": ln} for fn, ln in search_pairs]
    with open(PATH / "search_pairs.json", "w") as f:
        json.dump(k6_pairs, f)
    print(f"search_pairs.json: {len(k6_pairs)}")


if __name__ == "__main__":
    asyncio.run(main())
