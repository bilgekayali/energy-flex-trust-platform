"""Hugging Face Spaces and local entry point for the read-only dashboard."""

from energy_flex_trust.dashboard import build_dashboard


if __name__ == "__main__":
    build_dashboard().launch(server_name="0.0.0.0", server_port=7860)
