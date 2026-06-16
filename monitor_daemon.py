#!/usr/bin/env python3
"""
Continuous apartment monitor daemon.
Runs rental_watch.py every N seconds in a loop.
Can run on PythonAnywhere, Replit, or any server.
"""

import time
import sys
import subprocess
import logging
from datetime import datetime

# Configuration
INTERVAL_SECONDS = 60  # Run every 60 seconds
LOG_FILE = "monitor_daemon.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_check():
    """Run the rental watch check once."""
    try:
        logger.info("=" * 60)
        logger.info("Starting apartment monitor check...")
        result = subprocess.run(
            [sys.executable, "rental_watch.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("✓ Check completed successfully")
        else:
            logger.error(f"✗ Check failed with exit code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error("✗ Check timed out (exceeded 5 minutes)")
        return False
    except Exception as e:
        logger.error(f"✗ Exception during check: {e}")
        return False

def main():
    """Main daemon loop."""
    logger.info("=" * 60)
    logger.info(f"Apartment Monitor Daemon started")
    logger.info(f"Check interval: {INTERVAL_SECONDS} seconds")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 60)
    
    run_count = 0
    success_count = 0
    
    try:
        while True:
            run_count += 1
            logger.info(f"\n[Run #{run_count}] {datetime.now().isoformat()}")
            
            if run_check():
                success_count += 1
            
            logger.info(f"Stats: {success_count}/{run_count} successful")
            logger.info(f"Sleeping for {INTERVAL_SECONDS} seconds...")
            
            time.sleep(INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("Daemon stopped by user")
        logger.info(f"Final stats: {success_count}/{run_count} successful runs")
        logger.info("=" * 60)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
