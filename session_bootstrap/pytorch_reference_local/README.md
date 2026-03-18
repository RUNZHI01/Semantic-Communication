# PyTorch Reference Local Workspace

This directory is an isolated local work area for iterating on the current
PyTorch reference reconstruction flow without editing the mainline copies under
`session_bootstrap/scripts/`.

Copied on 2026-03-18 from:

- `session_bootstrap/scripts/pytorch_reference_reconstruction.py`
- `session_bootstrap/scripts/run_remote_pytorch_reference_reconstruction.sh`

Files in this folder:

- `pytorch_reference_reconstruction.py`: Python helper that generates
  reproducible PyTorch JSCC reference reconstructions from latent inputs.
- `run_remote_pytorch_reference_reconstruction.sh`: Bash wrapper that resolves
  env/config inputs and invokes the Python helper for remote or local runs.

Intended use:

- Make local experimental edits here first.
- Keep the originals in `session_bootstrap/scripts/` unchanged until any
  follow-up work is ready to be promoted deliberately.
