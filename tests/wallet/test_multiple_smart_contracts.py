import asyncio
from typing import List

import pytest

from src.simulator.simulator_protocol import FarmNewBlockProtocol
from src.types.peer_info import PeerInfo
from src.util.ints import uint16, uint32, uint64
from src.wallet.wallet_coin_record import WalletCoinRecord
from tests.setup_nodes import setup_simulators_and_wallets
from src.consensus.block_rewards import calculate_pool_reward, calculate_base_farmer_reward
from src.wallet.cc_wallet.cc_wallet import CCWallet
from src.wallet.rl_wallet.rl_wallet import RLWallet
from tests.time_out_assert import time_out_assert


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


class TestCCWallet:
    @pytest.fixture(scope="function")
    async def wallet_node(self):
        async for _ in setup_simulators_and_wallets(1, 1, {}):
            yield _

    @pytest.fixture(scope="function")
    async def two_wallet_nodes(self):
        async for _ in setup_simulators_and_wallets(1, 2, {}):
            yield _

    @pytest.fixture(scope="function")
    async def three_wallet_nodes(self):
        async for _ in setup_simulators_and_wallets(1, 3, {}):
            yield _

    @pytest.mark.asyncio
    async def test_multiple_smart_spend(self, two_wallet_nodes):
        num_blocks = 3
        full_nodes, wallets = two_wallet_nodes
        full_node_api = full_nodes[0]
        full_node_server = full_node_api.server
        wallet_node, server_2 = wallets[0]
        wallet_node_2, server_3 = wallets[1]
        wallet = wallet_node.wallet_state_manager.main_wallet
        wallet2 = wallet_node_2.wallet_state_manager.main_wallet

        # get funds for the two main wallets
        ph = await wallet.get_new_puzzlehash()

        await server_2.start_client(PeerInfo("localhost", uint16(full_node_server._port)), None)
        await server_3.start_client(PeerInfo("localhost", uint16(full_node_server._port)), None)

        for i in range(1, num_blocks):
            await full_node_api.farm_new_block(FarmNewBlockProtocol(ph))

        funds = sum(
            [
                calculate_pool_reward(uint32(i)) + calculate_base_farmer_reward(uint32(i))
                for i in range(1, num_blocks - 1)
            ]
        )

        await time_out_assert(15, wallet.get_confirmed_balance, funds)

        ph = await wallet2.get_new_puzzlehash()
        for i in range(1, num_blocks):
            await full_node_api.farm_new_block(FarmNewBlockProtocol(ph))

        funds = sum(
            [
                calculate_pool_reward(uint32(i)) + calculate_base_farmer_reward(uint32(i))
                for i in range(1, num_blocks - 1)
            ]
        )

        await time_out_assert(15, wallet2.get_confirmed_balance, funds)

        # Create the smart wallets
        cc_wallet: CCWallet = await CCWallet.create_new_cc(wallet_node.wallet_state_manager, wallet, uint64(100))

        for i in range(1, num_blocks):
            await full_node_api.farm_new_block(FarmNewBlockProtocol(32 * b"0"))

        await time_out_assert(15, cc_wallet.get_confirmed_balance, 100)
        await time_out_assert(15, cc_wallet.get_unconfirmed_balance, 100)

        assert cc_wallet.cc_info.my_genesis_checker is not None

        rl_admin: RLWallet = await RLWallet.create_rl_admin(wallet_node.wallet_state_manager)

        rl_user: RLWallet = await RLWallet.create_rl_user(wallet_node_2.wallet_state_manager)
        interval = uint64(2)
        limit = uint64(1)
        amount = uint64(100)
        await rl_admin.admin_create_coin(interval, limit, rl_user.rl_info.user_pubkey.hex(), amount, 0)
        origin = rl_admin.rl_info.rl_origin
        admin_pubkey = rl_admin.rl_info.admin_pubkey

        await rl_user.set_user_info(
            interval,
            limit,
            origin.parent_coin_info.hex(),
            origin.puzzle_hash.hex(),
            origin.amount,
            admin_pubkey.hex(),
        )

        for i in range(0, num_blocks):
            await full_node_api.farm_new_block(FarmNewBlockProtocol(32 * b"\0"))

        # Here we generate all the transactions for a big block

        # Standard tx
        ph2 = await wallet.get_new_puzzlehash()
        tx = await wallet2.generate_signed_transaction(uint64(150), ph2)
        await wallet2.push_transaction(tx)

        # Coloured coin spend
        cc_hash = await cc_wallet.get_new_inner_hash()
        tx_record = await cc_wallet.generate_signed_transaction([uint64(15)], [cc_hash])
        await wallet.wallet_state_manager.add_pending_transaction(tx_record)

        # RL spend
        tx = await rl_user.generate_signed_transaction(1, 32 * b"\0")
        await wallet.wallet_state_manager.main_wallet.push_transaction(tx)

        # Farm all the transactions
        breakpoint()
        for i in range(1, num_blocks):
            await full_node_api.farm_new_block(FarmNewBlockProtocol(ph))
