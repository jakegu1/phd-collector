"""Main entry point for PhD Project Collector.

Usage:
    python main.py scrape      - Run a one-time scrape
    python main.py scheduler   - Start the daily scheduler
    python main.py dashboard   - Launch the Streamlit dashboard
"""

import sys
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("phd_collector.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("请选择一个命令: scrape / scheduler / dashboard")
        return

    command = sys.argv[1].lower()

    if command == "scrape":
        from collector import run_collection
        stats = run_collection()
        print(f"\n采集完成！统计: {stats}")

    elif command == "scheduler":
        from scheduler import create_scheduler
        scheduler = create_scheduler()
        scheduler.start()
        print(f"定时任务已启动，每天自动采集。按 Ctrl+C 停止。")
        try:
            import time
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            print("定时任务已停止。")

    elif command == "dashboard":
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.headless", "true",
            "--server.port", "8501",
        ])

    else:
        print(f"未知命令: {command}")
        print("可用命令: scrape / scheduler / dashboard")


if __name__ == "__main__":
    main()
