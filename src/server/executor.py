import functools
import logging
import json
from .timer import Timer
from .utils import rounding_dumps

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BlenderExecutor")


class BlenderExecutor:
    instance = None

    @classmethod
    def get(cls) -> "BlenderExecutor":
        return cls.instance or cls()

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def send_function_call(self, func, params):
        command = {"func": func, "params": params or {}}

        logger.info(f"发送命令: {func} 参数: {params}")
        response = Timer.wait_run_with_context(self.execute_function)(command)
        logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")

        if response.get("status") == "error":
            logger.error(f"Blender error: {response.get('message')}")
            raise Exception(response.get("message", "Unknown error from Blender"))
        result_str = rounding_dumps(response.get("result", {}), ensure_ascii=False)
        print(f"-----------------------------\n所选工具: {func.__name__}\n执行结果: {result_str}\n-----------------------------")
        return result_str

    def execute_function(self, command):
        logger.info(f"命令执行: {command}")
        func = command.get("func")
        try:
            params = command.get("params", {})
            result = func(**params)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error execute {func.__name__}: {str(e)}")
            return {"status": "error", "message": str(e)}
