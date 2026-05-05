from tool.tools import tool
import time

@tool
def test_tool() -> str:
    '''
    A test tool

    '''
    print("start sleep")
    time.sleep(60)
    print("end sleep")
    return "sleep ok"
