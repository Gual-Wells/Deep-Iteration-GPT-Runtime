# D with L2 — controlled context packet

Invocation: `DIGR（D（1），L（2））：任务`

An honest L2 intervention has a real information-flow boundary:

1. Main writes an indexed controlled **Input Packet** containing only what isolated D work needs.
2. The L2 isolation receipt references that input and evidences an isolated context/private D state.
3. The decreed D intervention executes in `D_EXCLUSIVE` or an explicitly supported background mode and records its clock-state binding.
4. Isolated work writes an indexed **Output Packet**; the D Result revision references it.
5. Main returns to `MAIN`, independently evaluates the output, and writes a clock-bound ReintegrationReceipt with accepted/rejected material and the concrete Main consequence.

The Output Packet cannot be required at isolation creation time because it does not exist until the isolated work has produced a result.
