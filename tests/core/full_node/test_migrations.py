import pytest
import asyncio
import os
import shutil
from src.util.migration_rules import (
    create_tables_from_schemadict,
    migrate,
)


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
        folder = "tests/temp"
        delete_temp_folder(folder)
        assert count_files_in_folder(folder) == 0
        await migrate(folder, -1)
        assert count_files_in_folder(folder) == 3
        # TODO: check that the final version has undergone all transformations
