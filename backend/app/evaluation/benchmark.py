"""
ALIGN Academic Benchmark Entrypoint.

Forwards to app.evaluation.run_all for comprehensive evaluation.
"""

from app.evaluation.run_all import run_evaluation_pipeline

if __name__ == "__main__":
    run_evaluation_pipeline()
