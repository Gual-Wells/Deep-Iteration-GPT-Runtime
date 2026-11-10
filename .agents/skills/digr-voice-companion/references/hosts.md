# Host guidance

This is deployment and troubleshooting material, not a script to speak during practice. These notes were checked against the official pages on 2026-11-10. A capability described by a vendor is not proof that this account or conversation has loaded the companion.

## One companion, two ways to carry it

The small resident is self-sufficient. It keeps help available if the full skill or a source tool cannot be read. The full skill supplies richer behavior; examples and professional worlds are optional material. Do not force a repository fetch before every spoken reply.

For a local host that discovers skills, install `digr-voice-companion` with its `SKILL.md` and `references` folder in a supported discovery location. Current [skill documentation](https://learn.chatgpt.com/docs/build-skills) describes standalone skills in the desktop app, Codex CLI and IDE extension; user-scope discovery includes `$HOME/.agents/skills`, and symbolic links are supported. A matching name in metadata means discoverable, not necessarily selected or fully read. Use the host's skill selection controls if it does not select the skill naturally; restart a stale host if necessary.

For ChatGPT web/mobile without that local file access, use the exported, self-contained project file. Upload or connect it as a project source and add the resident to the project's instructions, or to existing account custom instructions for global readiness. Preserve existing user instructions and the explicit DIGR router. The file contains the behavior and material, so a phone does not need to open a D-drive path or follow repository links to get it.

The [project documentation](https://learn.chatgpt.com/docs/projects) distinguishes shared project instructions/sources from access to a local folder. [Current release notes](https://learn.chatgpt.com/docs/whats-new) describe Voice using project context and uploaded files. Actual retrieval and use still depend on the host and session. The same content can be pasted into a conversation when that is the available route; an attachment alone does not compel the model to read it.

## Global guidance and account guidance are different locations

[Personalization](https://learn.chatgpt.com/docs/personalize) provides cross-chat custom instructions. In Codex, the corresponding global file is `AGENTS.md` under the active `CODEX_HOME`; [discovery rules](https://learn.chatgpt.com/docs/agent-configuration/agents-md) explain override precedence and new-session loading. Editing that local file is not evidence that ChatGPT's web account custom instructions changed.

For this user's Windows setup, actual added data must live on D. A user-scope discovery junction under `C:\Users\huawei\.agents\skills` may point to the D-hosted skill. The configured `CODEX_HOME` is `D:\CodexData`. These are deployment locations, not paths a phone can read. Do not move user data or change global HOME/APPDATA as part of installing this small skill.

## Ready does not mean an exercise has started

Use reliable live-Voice metadata when it is supplied. If it is not supplied, “Start voice rehearsal” or “进入语音陪练” is enough to choose the activity for the conversation. That is an intention, not evidence of a microphone. A transcript, a voice-related filename or the word “voice” does not identify the input channel.

Within that activity, an ordinary short continuation remains relevant without a new activation ritual. A reliable switch to an ordinary text channel, a request to stop, or a genuine ordinary work task suspends automatic rehearsal. Do not hijack unrelated work because Voice is available. Explicit written rehearsal can still be requested. Quoted rescue phrases and ordinary turn-taking are not help commands.

If no scene exists, offer a light, concrete beginning rather than a level questionnaire. For example, start a colleague conversation about an offline note assistant. Do not announce that any future project has really been completed. Once a simulation is agreed, keep it usable without repeated disclaimers.

## What the stronger host can actually add

The [Voice overview](https://learn.chatgpt.com/docs/features/voice) describes GPT-Live working with the task's conversation and selected model. Do not assume every Voice session is a fixed weak model, and do not claim this instruction changes model weights or reasoning settings.

The [GPT-Live API prompting guide](https://developers.openai.com/api/docs/guides/live-prompting) separates concise front-end conversation from detailed background work. This companion borrows that division of attention. API control tokens, configured tools and `session.instructions` are not a ready-made ChatGPT backend. Only call native tools or independent work that really exists and fits the user's request. Immediate help should continue without them.

## Verify the observation you can make

Keep the following statements separate: files exported; files installed in a discovery location; metadata actually discovered; full instructions actually read; the target Voice session behaving accordingly. Test the last one in that actual host. A useful short check is: enter rehearsal, ask a question with no idea for an answer, request help twice, then change one detail. Observe whether the companion contributes content, changes the second help and follows the new detail. Also try a quoted cue and an ordinary work request.

Text rehearsal can reveal content and instruction failures. It does not establish live audio loading, pronunciation, interruption behavior, latency or learning gains. Do not report a behavior as observed merely because the files prescribe it.
