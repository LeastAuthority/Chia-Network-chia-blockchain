from typing import List, Callable
import aiosqlite
from os import listdir, unlink
from shutil import copyfile


# backwards migration not supported
# list of python functions for transforming the previous SQL DB to the next version
# Indexed by version number
# Separationg between chia version num and database version num
# Run every migration set of steps that exist since the old version


class Migration:
    version: int
    schema: List[str]  # List of strings
    migration_steps: Callable

    def __init__(self, vers, sch, mig_steps):
        self.version = vers
        self.schema = sch
        self.migration_steps = mig_steps


async def create_tables_from_schemadict(connection, schema, version):
    for command in schema:
        await connection.execute(command)
    await connection.commit()
    cursor = await connection.executemany(
        "INSERT OR REPLACE INTO schema_version VALUES(?, ?)",
        [("version", version)],
    )
    await cursor.close()
    await connection.commit()
    return


async def migrate(old_folder, new_folder, MIGRATION_UPDATES_LIST):
    current_chia_version = None
    for f in listdir(f"{old_folder}/db"):
        if f[0:12] == "blockchain_v":
            split_f = f.split("_")
            # We need to be careful and deliberate with db numbering
            current_chia_version = int(split_f[1][1:])
            genesis_block_str = split_f[2][:-7]

    if current_chia_version is None:
        connection = await aiosqlite.connect(
            f"{new_folder}/db/blockchain_v{MIGRATION_UPDATES_LIST[-1].version}_{genesis_block_str}.sqlite"
        )
        create_tables_from_schemadict(connection, MIGRATION_UPDATES_LIST[-1].schema, MIGRATION_UPDATES_LIST[-1].version)
        connection.close()
        return

    if current_chia_version >= MIGRATION_UPDATES_LIST[-1].version:
        copyfile(
            f"{old_folder}/db/blockchain_v{current_chia_version}_{genesis_block_str}.sqlite",
            f"{new_folder}/db/blockchain_v{current_chia_version}_{genesis_block_str}.sqlite",
        )
        return

    for mig in MIGRATION_UPDATES_LIST:
        if mig.version < current_chia_version:
            continue
        connection = await aiosqlite.connect(f"{new_folder}/db/blockchain_v{mig.version}_{genesis_block_str}.sqlite")
        await create_tables_from_schemadict(connection, mig.schema, mig.version)
        old_connection = await aiosqlite.connect(
            f"{old_folder}/db/blockchain_v{current_chia_version}_{genesis_block_str}.sqlite"
        )
        await mig.migration_steps(old_connection, connection)
        await connection.close()
        await old_connection.close()
        current_chia_version = mig.version
        old_folder = new_folder

    for f in listdir(f"{old_folder}/db"):
        if f[0:12] == "blockchain_v" and int(f.split("_")[1][1:]) != mig.version:
            unlink(f"{old_folder}/db/{f}")
    return
