"""
Wellness Outreach Scheduler

This module provides a continuous scheduler service that runs wellness outreach
at configured intervals. Designed to run as a long-lived service in Docker.

Usage:
    docker-compose exec backend python -m app.wellness_scheduler
    
Or add as a service in docker-compose.yml for automatic startup.
"""

import asyncio
import schedule
import time
from datetime import datetime
import logging

from .wellness_outreach import main as run_wellness_outreach

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration
SCHEDULE_DAY = "monday"      # Day of week to run
SCHEDULE_TIME = "08:00"      # Time to run (24-hour format)


async def scheduled_job():
    """
    Wrapper for the wellness outreach job.
    Handles errors and logs execution.
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting scheduled wellness outreach job")
        logger.info("=" * 80)
        
        await run_wellness_outreach()
        
        logger.info("=" * 80)
        logger.info("Scheduled wellness outreach job completed successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in scheduled wellness outreach: {str(e)}", exc_info=True)


def run_job_sync():
    """Synchronous wrapper to run async job in schedule."""
    asyncio.run(scheduled_job())


def main():
    """
    Main scheduler loop.
    Runs continuously and executes wellness outreach on schedule.
    """
    logger.info("🏥 Interpaws Wellness Outreach Scheduler Starting")
    logger.info(f"📅 Schedule: Every {SCHEDULE_DAY.capitalize()} at {SCHEDULE_TIME}")
    logger.info("=" * 80)
    
    # Schedule the job
    schedule_method = getattr(schedule.every(), SCHEDULE_DAY)
    schedule_method.at(SCHEDULE_TIME).do(run_job_sync)
    
    # Also log next run time
    next_run = schedule.next_run()
    if next_run:
        logger.info(f"⏰ Next run scheduled for: {next_run}")
    
    logger.info("✅ Scheduler is running. Press Ctrl+C to stop.")
    logger.info("=" * 80)
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("\n⏹  Scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
