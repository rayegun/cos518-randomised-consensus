import random

from message import *
from enum import Enum


class UnknownVal:
    # False-y
    def __bool__(self):
        return False


UNKNOWN = UnknownVal()


def update_count(histogram, entry):
    if entry in histogram.keys():
        histogram[entry] += 1
    else:
        histogram[entry] = 1


def consensus_values(histogram, threshold):
    return [val for (val, count) in histogram.items() if count > threshold]


class State(Enum):
    INIT = 1
    REPORTS = 2
    POST_REPORTS = 3
    PROPOSALS = 4
    POST_PROPOSALS = 5
    DONE = 6
    WAITING = 7  # For a machine that is done, but in reactive mode -waiting for a message to decide if it should act


class AbstractServer:
    def __init__(
        self, network=None, id=-1, val=-1, n=0, f=0, randomness=None, *args, **kwargs
    ) -> None:
        pass

    @classmethod
    def from_server(cls, other): # -> AbstractServer
        return None

    def primitive_step(self) -> None:
        pass


class Server(AbstractServer):
    def __init__(
        self, network=None, id=-1, val=-1, n=0, f=0, randomness=None, possible_values=[0, 1], *args, **kwargs
    ):
        # Default args: A hack so that __init__() with no args works
        self.network = network
        self.id = id
        self.val = val
        self.x = val
        self.k = 1
        self.final_round = -1  # The round we finished in
        self.n = n
        self.f = f
        self.strong_agreement_threshold = (n + f) / 2
        self.weak_agreement_threshold = f + 1
        self.wait_threshold = n - f
        self.randomness = randomness

        self.message_log = []
        # For state tracking/history, essentially - track received messages

        self.done = False

        # Primitive step edition
        self.state = State.INIT
        self.seen = set()
        self.histogram = dict()

        # Hack FIXME
        self.possible_values = possible_values

        # debug info:
        self.dead_messages = 0

    @classmethod
    def from_server(cls, other):
        # Copy the state+attrs of another server (new server `cls` and old server `other` may have diff subclasses)
        # Motivation: The system can turn a server good or evil while preserving state,etc. via hotswapping
        s = cls()
        for k, v in other.__dict__.items():
            s.__setattr__(k, v)
        return s

    def random_val(self):
        return self.randomness.choice(self.possible_values)

    def read_message(self, msg_type):
        msg = self.network.poll(self.id)
        if (
            isinstance(msg, msg_type)
            and msg.k == self.k
            and msg.sender not in self.seen
        ):
            self.seen.add(msg.sender)
            update_count(self.histogram, msg.val)
            self.message_log.append(msg)
        else:
            self.dead_messages += 1

    def broadcast(self, msg_type, value):
        self.network.send_to_all(msg_type(self.id, self.k, value))

    def primitive_step(self):
        if self.state == State.INIT:
            self.message_log = []
            self.k += 1
            self.histogram = dict()
            self.seen = set()
            if self.done:
                self.state = State.WAITING
            else:
                self.broadcast(Report, self.x)
                self.state = State.REPORTS

        elif self.state == State.WAITING:
            # print(self.id, " WAITING")
            msg = self.network.poll(self.id)
            if msg:
                # Start sending messages, behave normally
                self.broadcast(Report, self.x)
                self.state = State.REPORTS

        elif self.state == State.REPORTS:
            if len(self.seen) < (self.wait_threshold):
                self.read_message(Report)
            else:
                self.state = State.POST_REPORTS

        elif self.state == State.POST_REPORTS:
            self.histogram[UNKNOWN] = (
                0  # Necessary for the state machine version, where some values are UNKNOWN and should be ignored
            )
            agreed = consensus_values(self.histogram, self.strong_agreement_threshold)
            self.histogram = dict()
            self.seen = set()
            # at most one such element
            # in the non-byzantine version, just n/2 rather than n+f/2
            if agreed:
                self.broadcast(Propose, agreed[0])
            else:
                self.broadcast(Propose, UNKNOWN)
            self.state = State.PROPOSALS

        elif self.state == State.PROPOSALS:
            if len(self.seen) < (self.wait_threshold):
                self.read_message(Propose)
            else:
                self.state = State.POST_PROPOSALS

        elif self.state == State.POST_PROPOSALS:
            self.histogram[UNKNOWN] = 0
            # We disregard these when choosing values, they're just there to pad numbers and get us to n-f
            agreed = consensus_values(self.histogram, self.weak_agreement_threshold)
            majority = consensus_values(self.histogram, self.strong_agreement_threshold)
            if not self.done:
                if majority:
                    self.decide(majority[0])
                elif agreed:
                    self.x = agreed[0]
                else:
                    self.x = self.random_val()
                    # self.x = self.id % 2
            self.state = State.INIT

    def decide(self, v):
        self.done = True
        self.x = v
        self.final_round = self.k
        # We can't quite /halt/ because that complicates things for other servers. So we just set a flag =done=, that can be observed by the system/supervisor/monitoring.


# Faulty servers for stress-tests


class SilentServer(Server):
    def broadcast(self, msg_type, value):
        # Fail to broadcast
        pass


class UnreliableServer(Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.fail_chance = kwargs.get("fail_chance", 0.5)

    def broadcast(self, msg_type, value):
        if self.randomness.random() < self.fail_chance:
            pass
        else:
            super().broadcast(msg_type, value)


class SemirandomServer(Server):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.fail_chance = kwargs.get("fail_chance", 0.5)

    def broadcast(self, msg_type, value):
        if self.randomness.random() < self.fail_chance:
            for i in range(self.n):
                self.network.send(i, msg_type(self.id, self.k, self.random_val()))
        else:
            super().broadcast(msg_type, value)


class EvilServer(Server):
    # We just need to modify the broadcast function; primitive_step takes care of the rest.
    def broadcast(self, msg_type, value):
        v = UNKNOWN
        if value == 0:
            v = 1
        elif value == 1:
            v = 0
        else:
            v = self.random_val()  # Handles UNKNOWN
        super().broadcast(msg_type, v)


class RandomServer(Server):
    # Idea: Keeps track of state transitions correctly, but broadcasts garbage
    # We just need to modify the broadcast function; primitive_step takes care of the rest.
    def broadcast(self, msg_type, value):
        for i in range(self.n):
            self.network.send(i, msg_type(self.id, self.k, self.random_val()))


class UnknownServer(Server):
    def broadcast(self, msg_type, value):
        return super().broadcast(msg_type, UNKNOWN)


def MysteryServerFactory(
    network=None, id=-1, val=-1, n=0, f=0, randomness=None, *args, **kwargs
):
    # Same signature as a server constructor
    # By the magic of python, we can call it on arguments and it instantiates+returns a server, so it's a drop-in replacement for actual constructors
    servers = [
        EvilServer,
        RandomServer,
        SilentServer,
        UnreliableServer,
        SemirandomServer,
        MysteryServerFactory
    ]
    constructor = randomness.choice(servers)
    return constructor(network, id, val, n, f, randomness, *args, **kwargs)
