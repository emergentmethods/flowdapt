from flowdapt.lib.logger import get_logger

logger = get_logger("test_workflow")

def test_stage_one():
    logger.info("test_stage_one: Success")
    return None

def test_stage_two():
    logger.info("test_stage_two: Success")
    return None

def test_stage_error():
    raise Exception("test_stage_error: Failure")