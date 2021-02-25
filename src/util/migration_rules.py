from typing import Dict, List, Callable
import aiosqlite
from os import listdir

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
    await connection.commit()
    return


async def migrate(old_folder, new_folder, MIGRATION_UPDATES_LIST):
    current_chia_version = None
    for f in listdir(f"{old_folder}/db"):
        if f[0:12] == "blockchain_v":
            # We need to be careful and deliberate with db numbering
            current_chia_version = int(f.split("_")[1][1:-3])
    for mig in MIGRATION_UPDATES_LIST:
        if mig.version < current_chia_version:
            continue
        connection = await aiosqlite.connect(f"{new_folder}/db/blockchain_v{mig.version}.db")
        await create_tables_from_schemadict(connection, mig.schema)
        if current_chia_version is not None:
            old_connection = await aiosqlite.connect(f"{old_folder}/db/blockchain_v{current_chia_version}.db")
        else:
            old_connection = None
        await mig.migration_steps(old_connection, connection)
        await connection.close()
        if old_connection is not None:
            await old_connection.close()
        current_chia_version = mig.version
        old_folder = new_folder
    return
