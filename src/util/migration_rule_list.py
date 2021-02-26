from src.util.migration_rules import Migration
from typing import List

schema_0 = [
    "CREATE TABLE full_blocks(header_hash text PRIMARY KEY, height bigint,  is_block tinyint, block blob)",
    "CREATE TABLE block_records(header_hash text PRIMARY KEY, prev_hash text, height bigint,block blob, sub_epoch_summary blob, is_peak tinyint, is_block tinyint)",
    "CREATE TABLE sub_epoch_segments(ses_height bigint PRIMARY KEY, challenge_segments blob)",
    "CREATE TABLE schema_version(version bigint PRIMARY KEY)",
    "CREATE INDEX full_block_height on full_blocks(height)",
    "CREATE INDEX is_block on full_blocks(is_block)",
    "CREATE INDEX height on block_records(height)",
    "CREATE INDEX hh on block_records(header_hash)",
    "CREATE INDEX peak on block_records(is_peak)",
    "CREATE TABLE coin_record(coin_name text PRIMARY KEY, confirmed_index bigint, spent_index bigint, spent int, coinbase int, puzzle_hash text, coin_parent text, amount blob, timestamp bigint)",
    "CREATE INDEX coin_confirmed_index on coin_record(confirmed_index)",
    "CREATE INDEX coin_spent_index on coin_record(spent_index)",
    "CREATE INDEX coin_spent on coin_record(spent)",
]


def migration_rules_0(old_connection, new_connection):
    return


mig0 = Migration(0, schema_0, migration_rules_0)

MIGRATION_RULES: List[Migration] = [mig0]
