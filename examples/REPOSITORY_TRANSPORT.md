# Repository transport example

For a candidate `DIGR/help`, the Alpha 3 host bridge has this shape:

```text
stable_ref_primary      GET api.github.com/.../git/ref/heads/stable
stable_ref_corroboration GET api.github.com/.../branches/stable
                         require same 40-char SHA
pinned:manifest.json    GET raw.githubusercontent.com/.../{SHA}/manifest.json
pinned:VERSION          GET raw.githubusercontent.com/.../{SHA}/VERSION
                         require manifest.version == VERSION
pinned:<startup path>   GET raw.githubusercontent.com/.../{SHA}/...
                         then repository surface classification
```

Every line above produces an acquisition receipt. Search snippets never stand in for the first two lines. If the raw pinned request fails, Contents API fallback must yield raw file bytes or be base64-decoded before validation.
