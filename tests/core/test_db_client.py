async def test_is_pg_recovery(context):
    assert (await context.db_client.is_master(context.db_client.master_engine)) is True
