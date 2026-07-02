import logging

from config import config_manager
from database import db_manager

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, filename='log.txt', filemode='w')
    logger.info("Starting Application")
    config_manager.initialize()
    logger.debug("Starting Database")
    db_manager.initialize()


if __name__ == "__main__":
    main()
