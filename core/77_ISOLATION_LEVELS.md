# L — D Isolation as Actual Information Flow

Keep three distinct facts: `L_target` (requested contract mode), `L_cap` (maximum host capability evidenced), and `L_actual` (mode actually selected for a D isolation receipt). Capability never automatically becomes actual. Normally actual mode is target-bounded by capability.

L1: same-context semantic firewall/sparse D state and exclusive D work. It cannot honestly claim physical/context isolation or background execution.

L2 uses a temporal packet boundary:

`Main → controlled Input Packet → isolated D context/private D state → Output Packet → Main reintegration`.

The **Input Packet exists and is indexed before isolated execution starts**. The **Output Packet is produced by that execution**, is indexed afterwards and is bound to a D Result revision; it cannot be required before the isolated work has run. Full Main history is not simply handed across. L2 may be exclusive or supported background work; background D time itself is not T/t while foreground Main/SOURCE can continue.

L3 preserves the L2 packet boundary and additionally requires independently evidenced agent identity, instructions, execution loop and tool lifecycle.

Input/output packets are immutable workspace artifacts. Every counted D intervention references its actual IsolationReceipt, so a global host capability fact cannot falsely upgrade unrelated interventions. If completed interventions use different actual modes, proof reports the conservative actual level rather than overstating isolation. L mismatch is visible but blocks delivery only when U0 separately makes exact L a hard condition. D=0 leaves L visible/configured and non-blocking.
