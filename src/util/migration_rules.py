from typing import Dict, List, Callable
import aiosqlite

# backwards migration not supported
# list of python functions for transforming the previous SQL DB to the next version
# indexed by version number
# version for chia, version for database, version for database
# run every migration set of steps that exist since the old version


class Migration:
    version: int
    schema: Dict
    migration_steps: List[Callable]


# tablename: [(fieldname, type, Primary Key, index)]
tables = {
    "full_blocks": [
        ("header_hash", "text", True, None),
        ("height", "bigint", False, "full_block_height"),
        ("is_block", "tinyint", False, "is_block"),
        ("block", "blob", False, None)
    ],

    "block_records": [
        ("header_hash", "text", True, "hh"),
        ("prev_hash", "text", False, None),
        ("height", "bigint", False, "height"),
        ("block", "blob", False, None),
        ("sub_epoch_summary", "blob", False, None),
        ("is_peak", "tinyint", False, "peak"),
        ("is_block", "tinyint", False, "is_block")
    ],

    "sub_epoch_segments": [
        ("ses_height", "bigint", True),
        ("challenge_segments", "blob", False)
    ],
}


def test_migration_steps_1(old_db, new_db):

    return


mig_1 = Migration(1, tables, test_migration_steps)
MIGRATION_UPDATES: List[Migration] = [mig_1]


async def create_tables_from_schemadict(connection, schema):
    index_creations = []
    for tablename, values in schema:
        params = f"("
        for tuple in values:
            params = params + f"{tuple[0] tuple[1]}"
            if tuple[2]:
                params = params + "PRIMARY KEY"
            if tuple[3] is not None:
                # full_block_height on full_blocks(height)
                index_creations.append(f"{tuple[3]} on {tablename}({tuple[0]})")
            params = params + ","
        params = params[:-1] + ")"
        await connection.execute(
            params
        )
    for creation in index_creations:
        await connection.execute(f"CREATE INDEX IF NOT EXISTS {creation}")
    return


async def migrate(old_db, current_chia_version):
    for mig in MIGRATION_UPDATES:
        if mig.version < current_chia_version:
            continue
        connection = await aiosqlite.connect(f"temp/{mig.version}.db")
        await create_tables_from_schemadict(connection, mig.schema)
    return
