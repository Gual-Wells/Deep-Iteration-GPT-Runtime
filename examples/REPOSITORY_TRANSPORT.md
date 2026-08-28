# Stable pinned-manifest transport

Connector candidate startup:

```text
1. connector/direct REST stable branch HEAD → full SHA
2. pinned manifest.json + pinned VERSION → require version agreement
3. pinned manifest.startup_slice (Berta1: entry/STARTUP.md)
4. pinned STARTUP classifies the untouched original message
```

Direct REST performs both current branch and Git-ref reads in the same bounded attempt and requires identical full SHAs; the legacy `paranoid` argument cannot weaken or strengthen this invariant. Search/index/crawl material is never ref authority.

After classification, HELP fetches same-SHA `manifest.help`. EXECUTING resolves deterministic parameters and capabilities; READY then fetches the manifest-navigated descriptor and verified execution bundle before Genesis. NATIVE/INVALID/correction need no additional artifact fetch, but their startup acquisition has already occurred.
