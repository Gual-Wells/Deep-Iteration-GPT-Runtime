---
name: digr-delivery
description: Send final DIGR/DIGRP files to the authenticated Gmail self mailbox when the task selects X, and verify sent attachments through the native Gmail connection. Does not enable X or send for tasks without X.
---

# Deliver final files to Gmail

Follow the acquired pinned profile and [delivery contract](../../../codex/DELIVERY.md). This skill is an operation aid, not a router or new authorization. An installed alias locates the matching distribution through CODEX_HOME/digr-codex/toolchain.json.

For Codex pins from 1.5.0, binary X belongs to the formal parameter group. X=0 selects the current chat and an explicit X=1 selects the authenticated Gmail self mailbox. Bare (X) and (X=Gmail) remain compatible. Earlier pins retain their separate final X group. Without final files, skip and create no extra attachment. Body mentions do not enable X. Reject empty, duplicate, conflicting or unsupported selections. Continue the same task's frozen account and actual selection. A new task resets the choice. Revoking X stops further external sends while preserving prior outcomes. For Max tasks, the actual final bytes pass the source-bound court before sending; the verdict and real Gmail readback each retain their own responsibility.

Read native Gmail get_profile and compare the actual address to the task's frozen account and recipient. Select only actual final files. Use one original file per email and transaction, preserving each whole PDF; freeze its name, bytes and SHA256 with delivery prepare. Record fresh profile-based identity and reserve the attempt with mark-sending before the external action. Send once only after the new transition returns send_allowed:true; replays and resume grant no second send.

Use the existing native Gmail send_email with to set to the verified self address, attachment_files as one Windows absolute path string, and no CC/BCC. Do not guess a multi-attachment encoding. Save the real send response and message ID. Read that exact ID with read_email(format=full), checking From/To/SENT and all attachment names/sizes. Total message size_estimate is not attachment bytes. Save the actual profile/send/full-readback outputs privately and reconcile the matching receipt; see the contract for exact JSON and CLI parameters.

After a timeout or interruption, inspect and reconcile the same message before retrying. Search absence is insufficient proof of non-send. Reuse verified file receipts instead of sending again. Lost current evidence can be refreshed by re-reading the same message with a new operation ID; that is not another send. Report actual metadata confirmation, and claim byte equality only after retrieving the original attachment and matching its hash.

For DIGRP, keep one complete PDF per paper. Use the parent task_root for delivery operations and the reviewed per-paper candidate ID. After verification, paper delivery only links candidate_id/delivery_id; do not resend or create a separate outbox. No-X READY_LOCAL goes directly to paper return. The parent final return reuses the same actual files and records. Keep the answer and file entry in the current chat.
