from src.wallet.chialisp import (
    eval,
    sexp,
    sha256,
    args,
    make_if,
    iff,
    equal,
    quote,
    hexstr,
    fail,
    multiply,
    greater,
    make_list,
    subtract,
    add,
    cons,
    rest,
    string,
    first,
    sha256tree
)
from src.types.program import Program
from clvm_tools import binutils


def get_generator():
    # sha256tree = "((c (i (l 5) (q (sha256 (q 2) ((c 2 9)) (q 2) ((c 2 13)))) (q (sha256 (q 1) 2))) 1))"
    # ((c (i (l 5)
    #              (q (sha256 (q 2)
    #                         ((c 2 (c 2 (c 9 (q ())))))
    #                         ((c 2 (c 2 (c 13 (q ())))))))
    #              (q (sha256 (q 1) 5))) 1))) 2))

    #args0 is (generate_npc_pair_list, sha256tree), args1 is coin_solutions, args2 is output_list
    programs = args(0)
    coin_solutions = args(1)
    output_list = args(2)
    coin_solution = first(coin_solutions)
    coin_name = first(coin_solution)
    puzzle_solution_pair = first(rest(coin_solution))
    puzzle = first(puzzle_solution_pair)
    solution = first(rest(puzzle_solution_pair))

    # get_puzhash = eval(first(rest(programs)), make_list(first(rest(programs)), puzzle))
    get_npc = make_list(coin_name, sha256tree(puzzle), eval(puzzle, solution))

    recursive_call = eval(programs, make_list(programs, rest(coin_solutions), cons(get_npc, output_list)))

    generate_npc_pair_list = make_if(coin_solutions, recursive_call, output_list)

    # Run the block_program and enter loop over the results
    # args0 is generate_npc_pair_list, args1 is block_program being passed in

    programs = args(0)
    coin_solutions = args(1)
    execute_generate_npc_pair = eval(programs, make_list(programs, coin_solutions, quote(sexp())))

    # Bootstrap the execution by passing functions in as parameters before the actual data arguments
    get_coinsols = eval(1, quote(0))
    core = eval(quote(execute_generate_npc_pair), make_list(quote(generate_npc_pair_list), get_coinsols))
    ret = Program.to(binutils.assemble(core))
    return ret
