import pytest
import asyncio
import os
import shutil
from src.util.migration_rules import (
    create_tables_from_schemadict,
    migrate,
    Migration
)
from src.util.hash import std_hash
from typing import List
import aiosqlite


# tablename: [(fieldname, type, Primary Key, index)]
DEFAULT_TABLES = [
    "CREATE TABLE full_blocks(header_hash text PRIMARY KEY, height bigint, is_block tinyint, block bloba)",
    "CREATE TABLE block_records(header_hash text PRIMARY KEY, prev_hash text, height bigint, block blob, sub_epoch_summary blob, is_peak tinyint, is_block tinyint)",
    "CREATE TABLE sub_epoch_segments(ses_height bigint PRIMARY KEY, challenge_segments blob)",
    "CREATE INDEX full_block_height on full_blocks(height)",
    "CREATE INDEX is_block on full_blocks(is_block)",
    "CREATE INDEX hh on block_records(header_hash)",
    "CREATE INDEX height on block_records(height)",
    "CREATE INDEX peak on block_records(is_peak)",
]

MODIFIED_TABLES = DEFAULT_TABLES.copy()
MODIFIED_TABLES[0] = "CREATE TABLE full_blocks(header_hash text PRIMARY KEY, height bigint, is_block tinyint, block blob, names text)"


async def fake_migration_steps_0(old_connection, new_connection):
    # populate table with data for test purposes
    sql_records = [
        (std_hash(0), 0, 1, 0xcafef00d),
        (std_hash(1), 1, 0, 0xcafed00d),
        (std_hash(2), 2, 1, 0xfadeddab),
        (std_hash(3), 3, 0, 0x12341234),
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


async def fake_migration_steps_1(old_connection, new_connection):
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


async def fake_migration_steps_2(old_connection, new_connection):
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

mig_0 = Migration(1, DEFAULT_TABLES, fake_migration_steps_0)
mig_1 = Migration(2, DEFAULT_TABLES, fake_migration_steps_1)
mig_2 = Migration(3, MODIFIED_TABLES, fake_migration_steps_2)

fake_migration_updates: List[Migration] = [mig_0, mig_1, mig_2]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


def count_files_in_folder(foldername):
    count = 0
    for filename in os.listdir(foldername):
        count = count + 1
    return count


def delete_temp_folder(folder):
    # delete temp folder
    # taken from stack overflow
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


class TestMigrations:
    @pytest.mark.asyncio
    async def test_migration(self):
        old_folder = "tests/util/old_temp"
        new_folder = "tests/util/new_temp"

        delete_temp_folder(f"{new_folder}/db")
        assert count_files_in_folder(f"{new_folder}/db") == 0
        delete_temp_folder(f"{old_folder}/db")
        assert count_files_in_folder(f"{old_folder}/db") == 0

        connection = await aiosqlite.connect(f"{old_folder}/db/blockchain_v0.db")
        await create_tables_from_schemadict(connection, DEFAULT_TABLES)
        await connection.close()
        await migrate(old_folder, new_folder, fake_migration_updates)
        assert count_files_in_folder(f"{new_folder}/db") == 1
        # TODO: check that the final version has undergone all transformations
        connection = await aiosqlite.connect(f"{new_folder}/db/blockchain_v3.db")
        cursor = await connection.execute('SELECT * FROM full_blocks')
        row = await cursor.fetchone()
        await connection.close()
        assert row[1] == 5
        assert row[4] == "test"

        # Test migration back to old_temp using copy feature
        delete_temp_folder(f"{old_folder}/db")
        assert count_files_in_folder(f"{old_folder}/db") == 0
        await migrate(new_folder, old_folder, fake_migration_updates)
        connection = await aiosqlite.connect(f"{old_folder}/db/blockchain_v3.db")
        cursor = await connection.execute('SELECT * FROM full_blocks')
        row = await cursor.fetchone()
        await connection.close()
        assert row[1] == 5
        assert row[4] == "test"
