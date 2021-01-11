from src.wallet.puzzles.load_clvm import load_clvm

CC_MOD = load_clvm("cc.clisp", package_or_requirement=__name__)
LOCK_INNER_PUZZLE = load_clvm("lock.inner.puzzle.clisp", package_or_requirement=__name__)
