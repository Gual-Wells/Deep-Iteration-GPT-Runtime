# Evolution State Tree (EST) as Reopenable Working Memory

EST is lightweight external working memory, not BFS/DFS/MCTS and not a score/controller. It compresses where work has reached so later evolution can continue without restarting from scratch.

Berta1 avoids anchoring labels such as immutable `stable_facts` or `important_decisions`. A snapshot may record currently supported facts, current decisions, superseded assumptions, open questions, active routes, dormant-but-reopenable routes, the latest meaningful change and references to current Strategy/Candidate revisions.

Every EST statement is current working state. New evidence, R, S, D, failures or counterexamples may revise or supersede it.
