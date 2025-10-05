import os
import sys
import threading
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def start_scheduler():
    """Start the pipeline scheduler in a separate thread"""
    try:
        from scheduler import DustPipelineScheduler
        scheduler = DustPipelineScheduler()
        print("🚀 Starting pipeline scheduler...")
        scheduler.start_scheduler()
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")
        import traceback
        traceback.print_exc()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port_str = os.getenv("PORT", "8000")
    reload_flag = os.getenv("RELOAD", "true").lower() in ("1", "true", "yes")
    start_scheduler_flag = os.getenv("START_SCHEDULER", "true").lower() in ("1", "true", "yes")

    try:
        port = int(port_str)
    except ValueError:
        port = 8000

    # Start scheduler in background thread if enabled
    if start_scheduler_flag:
        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()
        print("✅ Pipeline scheduler started in background")
        
        # Give scheduler time to initialize
        time.sleep(2)
    else:
        print("⚠️  Pipeline scheduler disabled (set START_SCHEDULER=true to enable)")

    # Delayed import so that missing optional deps don't block script import
    import uvicorn  # type: ignore

    print(f"🌐 Starting API server on {host}:{port}")
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=reload_flag,
    )


if __name__ == "__main__":
    main()


