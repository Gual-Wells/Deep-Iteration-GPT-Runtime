# ChatGPT local personalization

`PERSONALIZATION_TEMPLATE.txt` is the single editable source. Run `python tools/build_release.py --prepare-only` to generate:

- `CHATGPT_LOCAL_PERSONALIZATION.txt` (compact)
- `CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt` (byte-identical compact)
- `CHATGPT_LOCAL_PERSONALIZATION_FULL.txt` (expanded reference)
- root `CHATGPT_LOCAL_PERSONALIZATION.txt` (byte-identical standalone compact)

Every generated configuration ends with `<!-- DIGR_LOCAL_PERSONALIZATION_END -->`. The files remain version-neutral pinned-manifest routers: they enforce broad candidate capture, actual acquisition, immutable SHA pinning, manifest/VERSION/startup handoff and later manifest-navigated descriptor artifacts without copying DIGR execution semantics.
