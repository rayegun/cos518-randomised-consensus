from system import *
from server import *
from network import *
from scheduler import *
from json import dumps
from sys import stderr
import sys
import math


def scientific_notation(i, exp):
    return i * (10**exp)


def json_string(data):
    return dumps(data, indent=2)


def honest():
    print("Everything Honest")
    n = 6
    f = 1
    r = random.Random()
    sys = System(n, f, Network(n, r), Scheduler(n, r), r, cutoff=1000)
    sys.print_state()
    sys.run_undistributed()


def test_server_network_scheduler(
    servers, networks, schedulers, seed, num_servers, repeats=1, f=None, possible_values=[0, 1]
):
    flip_chance = 0.5
    n = num_servers
    f = f or math.ceil(n / 5) - 1
    cutoff_order = 4
    cutoff = scientific_notation(n, cutoff_order)

    def run_test(server, network, scheduler):
        print(f"{n}: {server}, {network}, {scheduler}", file=stderr)
        result = dict()
        result["server"] = server.__name__
        result["network"] = network.__name__
        result["scheduler"] = scheduler.__name__
        result["successes"] = 0
        result["failures"] = 0
        # result["base_seed"] = seed
        # result["dead_messages"] = 0
        result["rounds"] = 0
        result["messages"] = 0
        for i in range(repeats):
            randomness = random.Random(seed + i)
            sys = EvilHotswapSystem(
                # sys = EvilSystem(
                n,
                f,
                network(n, randomness),
                scheduler(n, randomness),
                randomness,
                cutoff,
                evil_class=server,
                flip_chance=flip_chance,
                possible_values=possible_values
            )

            x = sys.run_undistributed()
            # Rounds and dead_messages are averaged across repeats
            result["rounds"] += x["rounds"] / repeats
            result["messages"] += x["messages"] / repeats
            # result["dead_messages"] += x["dead_messages"] / repeats
            if x["success"]:
                result["successes"] = result["successes"] + 1
            else:
                result["failures"] = result["failures"] + 1
        return result

    results = []
    for server in servers:
        for network in networks:
            for scheduler in schedulers:
                results.append(run_test(server, network, scheduler))
    print(json_string(results))


def multitest(num, servers, networks, schedulers):
    seed = random.randint(1, 10000)
    test_server_network_scheduler(servers, networks, schedulers, seed, num)


servers = [
    Server,
    # EvilServer,
    # RandomServer,
    # SilentServer,
]

networks = [
    Network
]

schedulers = [Scheduler] # EvilFirstScheduler

# A smaller set of behaviours - the "interesting set", informally
servers_demo = [Server, EvilServer, RandomServer]
networks_demo = [Network, ApproximateNetwork]
schedulers_demo = [Scheduler, EvilFirstScheduler]
# 18 options

seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randint(0, 1000)


# A command for running a miniature test
# test_server_network_scheduler(servers, networks, schedulers, seed, 6, repeats=1)

# The command used to generate bigtest.json

for n in [[0, 1], [0,1,2], [0,1,2,3], [0,1,2,3,4]]:
    test_server_network_scheduler(servers, networks, schedulers, seed, 15, repeats=50, possible_values=n)
