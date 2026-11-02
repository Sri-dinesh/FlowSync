"""Research candidate: pressure shares, allocation debt and executed green batches.

Combines established pressure control and deficit/fair scheduling ideas. This is
not a learned DQN, a global novelty claim or a traffic-improvement guarantee.
Only delivered Counts and authoritative physical Clock feedback enter the policy.
"""
from dataclasses import asdict, dataclass
from types import MappingProxyType

from research.audits.sumo_branch_feasibility import Signal
from research.policies.sumo_classical import Clock, Counts, choose_action, phase_pressures

VERSION = "sumo_service_ledger_v1"
DECISION_TICKS = 20
QUANTUM_TICKS = 80
SHARE_SCALE = 1_048_576  # 2**20 fixed-point units per green-opportunity tick
MAX_BATCH_TICKS = 3 * QUANTUM_TICKS


@dataclass(frozen=True)
class Rule:
    debt_priority: bool = True
    debt_budget: bool = True

    def __post_init__(self):
        if type(self.debt_priority) is not bool or type(self.debt_budget) is not bool:
            raise ValueError("Ledger ablations require explicit boolean rules")


RULES = MappingProxyType({
    "ledger": Rule(),
    "pressure_budget": Rule(False, True),
    "pressure_batch": Rule(False, False),
    "debt_batch": Rule(True, False),
})


@dataclass(frozen=True)
class Batch:
    identifier: int
    target: int
    budget: int
    received: int = 0

    @property
    def remaining(self):
        return self.budget - self.received


@dataclass(frozen=True)
class Proposal:
    interval: int
    phase: int
    reference: int
    reason: str
    pressures: tuple[int, int]
    share_ns_units: int | None
    debt_ns_units: int
    batch: Batch | None


@dataclass(frozen=True)
class Receipt:
    interval: int
    executed: Clock
    debt_ns_units: int
    credited_batch: int | None
    batch: Batch | None
    completed: Batch | None


@dataclass(frozen=True)
class _Transaction:
    proposal: Proposal
    expected: Signal
    created_batch: bool


def _clock(signal):
    return Clock(signal.phase, signal.stage, signal.age)


def _pressure_share(pressures):
    """Exact nearest/even quantization; opposite share is SHARE_SCALE - result."""
    total = sum(pressures)
    if total == 0:
        return None
    quotient, remainder = divmod(SHARE_SCALE * pressures[0], total)
    return quotient + int(2 * remainder > total or (2 * remainder == total and quotient % 2))


def _settle(debt, share, executed):
    if executed.stage != "green":
        return debt
    if share is not None:
        return debt + share - (SHARE_SCALE if executed.phase == 0 else 0)
    if executed.phase == 0 and debt > 0:
        return max(0, debt - SHARE_SCALE)
    if executed.phase == 1 and debt < 0:
        return min(0, debt + SHARE_SCALE)
    return debt


def _budget_ticks(selected_debt, rule):
    divisor = SHARE_SCALE * DECISION_TICKS
    extra = (DECISION_TICKS * ((max(0, selected_debt) + divisor - 1) // divisor)
             if rule.debt_budget else 0)
    return min(MAX_BATCH_TICKS, QUANTUM_TICKS + extra)


class ServiceLedgerPolicy:
    """One owner per episode; begin -> actual execution -> finish on every tick.

    Initialize at an empty-run green clock of age zero. The proposal object is
    the interval receipt token and belongs to this owner. Failed boundary checks
    leave committed state unchanged. Replay into a fresh owner is recovery;
    duplicate or out-of-order transactions are rejected rather than re-credited.
    """

    def __init__(self, rule=Rule()):
        if not isinstance(rule, Rule):
            raise ValueError("Expected a validated ledger rule")
        self._rule = rule
        self._interval = self._next_batch = self._debt = 0
        self._batch = self._expected = self._open = None

    @property
    def rule(self):
        return self._rule

    def snapshot(self):
        """Committed state only; pending interval details belong to its Proposal."""
        return dict(interval=self._interval, debt_ns_units=self._debt,
                    batch=None if self._batch is None else asdict(self._batch),
                    next_batch=self._next_batch, interval_open=self._open is not None)

    def begin_interval(self, counts: Counts, before: Clock) -> Proposal:
        if self._open is not None:
            raise ValueError("Finish the current ledger interval before opening another")
        if not isinstance(counts, Counts) or not isinstance(before, Clock):
            raise ValueError("Ledger policy accepts delivered Counts and a physical Clock")
        if self._expected is None:
            if before.stage != "green" or before.age != 0:
                raise ValueError("A fresh ledger episode must start at green age zero")
            predicted = Signal(phase=before.phase, pending=before.phase)
        else:
            if before != _clock(self._expected):
                raise ValueError("Pre-request clock does not follow recorded execution")
            predicted = Signal(**asdict(self._expected))

        pressures = phase_pressures(counts)
        share = _pressure_share(pressures)
        reference = choose_action("max_pressure", counts, before)
        phase, reason, batch = before.phase, "off_gate", self._batch
        created = False
        if self._interval % DECISION_TICKS == 0:
            if before.stage != "green" or before.age < QUANTUM_TICKS:
                reason = "physical_guard"
            elif batch is not None:
                phase, reason = batch.target, "committed_batch"
            elif share is None and abs(self._debt) < QUANTUM_TICKS * SHARE_SCALE:
                reason = "idle"
            else:
                phase, reason = reference, "pressure"
                if self.rule.debt_priority and abs(self._debt) >= QUANTUM_TICKS * SHARE_SCALE:
                    phase, reason = int(self._debt < 0), "allocation_debt"
                budget = _budget_ticks(self._debt if phase == 0 else -self._debt, self.rule)
                batch = Batch(self._next_batch, phase, budget)
                created = True
            predicted.request(phase)

        proposal = Proposal(self._interval, phase, reference, reason, pressures, share, self._debt, batch)
        self._open = _Transaction(proposal, predicted, created)
        return proposal

    def finish_interval(self, proposal: Proposal, executed: Clock) -> Receipt:
        transaction = self._open
        if transaction is None or proposal is not transaction.proposal:
            raise ValueError("Unknown, stale or foreign ledger interval receipt")
        if not isinstance(executed, Clock) or executed != _clock(transaction.expected):
            raise ValueError("Executed clock differs from the physical request transition")
        debt = _settle(self._debt, proposal.share_ns_units, executed)
        if self.rule.debt_priority and abs(debt) > 2 * QUANTUM_TICKS * SHARE_SCALE:
            raise ArithmeticError("Allocation debt bound violated; do not clamp the evidence")

        batch, credited, completed = proposal.batch, None, None
        if batch is not None and executed.stage == "green" and executed.phase == batch.target:
            credited = batch.identifier
            batch = Batch(batch.identifier, batch.target, batch.budget, batch.received + 1)
            if batch.received == batch.budget:
                completed, batch = batch, None

        receipt = Receipt(self._interval, executed, debt, credited, batch, completed)
        following = Signal(**asdict(transaction.expected))
        following.advance()
        self._debt, self._batch, self._expected = debt, batch, following
        self._next_batch += int(transaction.created_batch)
        self._interval += 1
        self._open = None
        return receipt
