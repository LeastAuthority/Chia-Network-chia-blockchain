from typing import Dict, List, Callable
import aiosqlite
from src.util.hash import std_hash
import copy


# backwards migration not supported
# list of python functions for transforming the previous SQL DB to the next version
# indexed by version number
# version for chia, version for database, version for database
# run every migration set of steps that exist since the old version


class Migration():
    version: int
    schema: Dict
    migration_steps: List[Callable]

    def __init__(self, vers, sch, mig_steps):
        self.version = vers
        self.schema = sch
        self.migration_steps = mig_steps


# tablename: [(fieldname, type, Primary Key, index)]
DEFAULT_TABLES = {
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
        ("ses_height", "bigint", True, None),
        ("challenge_segments", "blob", False, None)
    ],
}

MODIFIED_TABLES = copy.deepcopy(DEFAULT_TABLES)
MODIFIED_TABLES["full_blocks"].append(("names", "text", False, None))
MODIFIED_TABLES["sub_epoch_segments"][0] = ("ses_height", "bigint", True, "height")


async def test_migration_steps_0(old_connection, new_connection):
    # populate table with data for test purposes
    sql_records = [
        (std_hash(0), 0, 1, 0xcafef00d),
        (std_hash(1), 1, 0, 0xcafed00d),
        (std_hash(2), 2, 1, 0xfadeddab),
        (std_hash(3), 0, 0, 0x12341234),
    ]
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO full_blocks VALUES(?, ?, ?, ?)",
        sql_records,
    )

    await cursor.close()
    await new_connection.commit()

    sql_records = [
        (std_hash(0), std_hash(0xdeadb33f), 0, 0xcafef00d, None, 0, 1),
        (std_hash(1), std_hash(0), 1, 0xcafed00d, None, 0, 0),
        (std_hash(2), std_hash(1), 2, 0xfadeddab, None, 0, 1),
        (std_hash(3), std_hash(2), 3, 0x12341234, None, 1, 1),
    ]
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO block_records VALUES(?, ?, ?, ?, ?, ?, ?)",
        sql_records,
    )

    await cursor.close()
    await new_connection.commit()

    sql_records = [
        (0, 0xdeadbeef),
        (3, 0xd3adb33f),
    ]
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO sub_epoch_segments VALUES(?, ?)",
        sql_records,
    )

    await cursor.close()
    await new_connection.commit()
    return


async def test_migration_steps_1(old_connection, new_connection):
    # all heights +5 - incase we decide to start indexing from 1 :^)
    cursor = await old_connection.execute('SELECT * FROM full_blocks')
    rows = await cursor.fetchall()
    sql_records = []
    for row in rows:
        new_value = row[1] + 5
        sql_records.append(
            (
                row[0],
                new_value,
                row[2],
                row[3],
            ),
        )
    await cursor.close()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO full_blocks VALUES(?, ?, ?, ?)",
        sql_records,
    )

    await cursor.close()
    await new_connection.commit()
    cursor = await old_connection.execute('SELECT * FROM block_records')
    rows = await cursor.fetchall()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO block_records VALUES(?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    await cursor.close()
    await new_connection.commit()
    cursor = await old_connection.execute('SELECT * FROM sub_epoch_segments')
    rows = await cursor.fetchall()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO sub_epoch_segments VALUES(?, ?)",
        rows,
    )

    await cursor.close()
    await new_connection.commit()
    return


async def test_migration_steps_2(old_connection, new_connection):
    # add index for ses_height
    # add new column to full_blocks, populate it with placeholder info for old data
    cursor = await old_connection.execute('SELECT * FROM full_blocks')
    rows = await cursor.fetchall()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO full_blocks VALUES(?, ?, ?, ?, \"test\")",
        rows,
    )
    await cursor.close()
    await new_connection.commit()
    cursor = await old_connection.execute('SELECT * FROM block_records')
    rows = await cursor.fetchall()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO block_records VALUES(?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    await cursor.close()
    await new_connection.commit()
    cursor = await old_connection.execute('SELECT * FROM sub_epoch_segments')
    rows = await cursor.fetchall()
    cursor = await new_connection.executemany(
        "INSERT OR REPLACE INTO sub_epoch_segments VALUES(?, ?)",
        rows,
    )

    await cursor.close()
    await new_connection.commit()

    return

mig_0 = Migration(0, DEFAULT_TABLES, test_migration_steps_0)
mig_1 = Migration(1, DEFAULT_TABLES, test_migration_steps_1)
mig_2 = Migration(2, MODIFIED_TABLES, test_migration_steps_2)

MIGRATION_UPDATES: List[Migration] = [mig_0, mig_1, mig_2]


async def create_tables_from_schemadict(connection, schema):
    index_creations = []
    for tablename, values in schema.items():
        params = f"CREATE TABLE IF NOT EXISTS {tablename}("
        for tuple in values:
            params = params + f"{tuple[0]} {tuple[1]}"
            if tuple[2]:
                params = params + " PRIMARY KEY"
            if tuple[3] is not None:
                # full_block_height on full_blocks(height)
                index_creations.append(f"{tuple[3]} on {tablename}({tuple[0]})")
            params = params + ", "
        params = params[:-2] + ")"
        await connection.execute(
            params
        )
    for creation in index_creations:
        await connection.execute(f"CREATE INDEX IF NOT EXISTS {creation}")
    return


async def migrate(folder, current_chia_version):
    for mig in MIGRATION_UPDATES:
        if mig.version < current_chia_version:
            continue
        connection = await aiosqlite.connect(f"{folder}/db_{mig.version}.db")
        await create_tables_from_schemadict(connection, mig.schema)
        if current_chia_version >= 0:
            old_connection = await aiosqlite.connect(f"{folder}/db_{current_chia_version}.db")
        else:
            old_connection = None
        await mig.migration_steps(old_connection, connection)
        await connection.close()
        if old_connection is not None:
            await old_connection.close()
        current_chia_version = mig.version
    return
