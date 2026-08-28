#!/usr/bin/env python3
"""Live public-GitHub smoke check for the Berta1 transport boundary."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from runtime.invocation_surface import classify_surface
from runtime.repository_transport import RepositoryTransportSession, UrllibDirectFetcher, RouteAcquisitionError
from runtime.routing import load_route_metadata


def main(argv:list[str]) -> int:
    message=argv[1] if len(argv)>1 else 'DIGR/help'
    session=RepositoryTransportSession(UrllibDirectFetcher())
    try:
        bundle=session.acquire_startup(message)
    except RouteAcquisitionError as exc:
        print('ROUTE_ACQUISITION_FAILED')
        print(json.dumps([r.to_dict() for r in exc.receipts],ensure_ascii=False,indent=2))
        return 2
    manifest,version=load_route_metadata(bundle.route_receipt,bundle.manifest_bytes,bundle.version_bytes)
    surface=classify_surface(message)
    print(f'pinned_sha={bundle.resolution.commit_sha}')
    print(f'version={version}')
    print(f'startup_paths={list(bundle.discovery_plan.initial_paths)!r}')
    print(f'surface={surface.kind.value if surface else None}')
    print(f'attempts={len(bundle.attempts)}')
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))
