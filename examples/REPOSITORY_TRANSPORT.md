# Repository transport example

For a candidate `DIGR/help` or executing invocation, Alpha 4 has two admissible mutable-ref modes.

Connected GitHub connector:

```text
stable_branch_primary_r1   connector repository branch `stable`
                           → current full 40-char HEAD SHA
pinned:manifest.json       same SHA
pinned:VERSION             same SHA
pinned:<startup path>      same SHA
```

Direct REST client:

```text
stable_branch_primary_r1       GET api.github.com/.../branches/stable
stable_ref_corroboration_r1    GET api.github.com/.../git/ref/heads/stable
                               require same full 40-char SHA
                               (one bounded r2 re-observation if a live push races the pair)
pinned:manifest.json           GET raw.githubusercontent.com/.../{SHA}/manifest.json
pinned:VERSION                 GET raw.githubusercontent.com/.../{SHA}/VERSION
                               require manifest.version == VERSION
pinned:<startup path>          GET raw.githubusercontent.com/.../{SHA}/...
```

After the startup slice classifies an EXECUTING invocation and Clock Genesis succeeds, the current Alpha 4 manifest declares:

```text
pinned:bundle/EXECUTION_PROTOCOL.json
    → exactly entrypoint + 17 core logical members
    → verify order, length and SHA-256 for every member
    → ExecutingProtocolLoadReceipt
    → only then parameter resolution
```

Thus a connector EXECUTING startup uses 5 repository acquisitions before Clock Genesis and 1 post-genesis execution-bundle acquisition, rather than 18 separate entrypoint/core reads. This changes physical transport only; logical protocol authority remains the manifest-declared source files.

Every acquisition produces a receipt. Search snippets/indexed snapshots never substitute for mutable-ref authority. If raw pinned retrieval fails, Contents API fallback must yield raw file bytes or be base64-decoded before validation. Mandatory execution-protocol load failure after genesis aborts the born run.
