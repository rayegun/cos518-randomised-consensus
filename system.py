import random
from server import *
from network import *


class System:
    # The idea is that different systems will reimplement the `run_undistributed` and `spawn_servers` functions in more hostile ways; crashing servers, initialising weird values, etc.
    def __init__(
        self, n, f, network, scheduler, randomness, cutoff=0, possible_values=[0, 1], *args, **kwargs
    ) -> None:
        # assert 5 * f < n  # Threshold for correctness guarantee
        self.step_count = 0
        self.rounds = 0
        self.n = n
        self.f = f
        self.network = network
        self.scheduler = scheduler
        self.servers = [None] * n
        self.evil_ids = set()
        self.randomness = randomness
        self.cutoff = cutoff
        self.possible_values = possible_values
        self.spawn_servers()

    def print_state(self):
        print([s.x for s in self.servers])

    def finish(self):
        data = {
            # "steps": self.step_count,
            "messages": self.total_messages(),
            "rounds": self.rounds,
            "dead_messages": sum([s.dead_messages for s in self.servers]),
        }
        if self.verify_consensus():
            return {"success": True} | data
        elif self.cutoff and self.rounds >= self.cutoff:
            return {"success": False} | data

        else:
            # Should be unreachable
            raise Exception("Failed, but not due to cutoff - something is very wrong")
            self.print_state()
            return {
                "success": False,
                "steps": self.step_count,
                "rounds": self.rounds,
                "messages": self.total_messages(),
            } | data

    def run_undistributed(self):
        while self.should_keep_running():
            if self.step_count % self.n == 0:
                self.on_new_round()
            self.step_count += 1
            nxt = self.scheduler.next_server(self)
            self.servers[nxt].primitive_step()
        return self.finish()

    def spawn_servers(self):
        self.evil_ids = set()
        for i in range(self.n):
            # Only spawn honest servers - later implementations will have trickier behaviour
            self.servers[i] = Server(
                self.network,
                i,
                self.randomness.choice(self.possible_values)
                self.n,
                self.f,
                self.randomness,
                possible_values=self.possible_values
            )

    def on_new_round(self):
        self.rounds += 1
        self.scheduler.on_new_round(self)

    def get_honest_ids(self):
        return set(range(self.n)) - self.evil_ids

    def get_evil_ids(self):
        return self.evil_ids

    def verify_consensus(self):
        honest = self.get_honest_ids()
        idx = next(
            iter(honest)
        )  # Pick a random element without deleting it. Not great.
        expected = self.servers[idx].x
        for i in honest:
            if self.servers[i].x != expected:
                return False
        self.decided_value = expected
        return True

    def should_keep_running(self):
        return not (self.is_completed() or (self.cutoff and self.rounds >= self.cutoff))

    def is_completed(self):
        for i in self.get_honest_ids():
            if not self.servers[i].done:
                return False
        return True

    def total_rounds(self):
        return max(self.get_honest_ids(), key=lambda i: self.servers[i].final_round)

    def total_messages(self):
        return self.network.message_count


class EvilSystem(System):
    def __init__(self, *args, **kwargs) -> None:
        self.evil_class = kwargs.get("evil_class", Server)
        super().__init__(*args, **kwargs)

    def spawn_servers(self):
        self.evil_ids = set(self.randomness.sample(range(self.n), self.f))
        for i in range(self.n):
            if i in self.evil_ids:
                self.servers[i] = self.evil_class(
                    self.network,
                    i,
                    self.randomness.randint(0, 1),
                    self.n,
                    self.f,
                    self.randomness,
                    possible_values=self.possible_values
                )

            else:
                self.servers[i] = Server(
                    self.network,
                    i,
                    self.randomness.randint(0, 1),
                    self.n,
                    self.f,
                    self.randomness,
                    possible_values=self.possible_values
                )


class EvilHotswapSystem(EvilSystem):
    # Every time we step a server, we have a `flip_chance` probability to change it from good to evil (or vice versa) , and also of some other server (to maintain balance)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flip_chance = kwargs.get("flip_chance", 0.5)

    def find_flippable(self, options):
        # Pick a server from `options` that is not done (if one exists), and hotswap it with new_constructor
        still_running = [i for i in options if not self.servers[i].done]
        if still_running:
            flipped = self.randomness.choice(still_running)
            return flipped  # We should flip this server
        return None

    def swap_servers(self, good_id, evil_id):
        # Turns good_id into an evil server, and evil_id into a good server, preserving state of both
        self.servers[good_id] = self.evil_class.from_server(self.servers[good_id])
        self.evil_ids.add(good_id)

        self.servers[evil_id] = Server.from_server(self.servers[evil_id])
        self.evil_ids.remove(evil_id)

    def on_new_round(self):
        super().on_new_round()
        if self.randomness.random() < self.flip_chance:
            swaps_this_round = self.randomness.randint(0, self.f)
            for _ in range(swaps_this_round):
                currently_good = self.find_flippable(self.get_honest_ids())
                currently_evil = self.find_flippable(self.get_evil_ids())
                if currently_evil and currently_good:  # both exist to be flipped
                    self.swap_servers(currently_good, currently_evil)
