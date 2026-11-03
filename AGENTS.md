# Working agreement

Before implementing, read `docs/PROJECT.md` and the local handoff in `.scratch/arabic-transcriber/HANDOFF.md`. If local scratch files are unavailable, use the tracked project specification as the source of product requirements.

The user authorizes autonomous implementation, routine dependency setup, meaningful tests and Conventional Commits. They explicitly waive additional approval of test seams, ticket granularity and routine implementation decisions. Record the selected public test boundaries and proceed with short red-to-green cycles covering the main behaviors.

Keep `.scratch/` ignored and untracked. Work on tickets whose blockers are complete and update their local status. Use an ImageGen sub-agent for the requested minimalist visual direction. Read the applicable TDD and image-generation skills; use the document and PDF skills for export creation and visual verification when available.

Use only Cohere Transcribe Arabic for speech transcription. Treat model access and hardware support as real prerequisites; report any unverified model execution or platform packaging honestly. Never embed access tokens, model weights, downloaded media or signing secrets in Git.

Finish with verified local start and packaging commands, checks performed, platform limitations and any signing credentials still required. Public publishing requires a concrete target repository; configuring release workflows does not imply that a repository or release is already published.
