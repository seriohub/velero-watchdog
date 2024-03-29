from utils.printer import PrintHelper
from utils.handle_error import handle_exceptions_method

from config.config import Config


config_app = Config()

# class syntax
class ClassString:
    def __init__(self):
        self.print_helper = PrintHelper('[utils.strings]',
                                        level=config_app.get_internal_log_level())

    @handle_exceptions_method
    def split_string(self,
                     input_string,
                     chunk_length,
                     separator='\n'):
        try:
            self.print_helper.debug(f"telegram new receive element")

            if chunk_length <= 0:
                # raise ValueError("Chunk length must be greater than 0")
                self.print_helper.error(f"split_string. Chunk length must be greater than 0")

            if chunk_length >= len(input_string) or chunk_length == 0:
                return [input_string]

            result = []
            current_chunk = ""
            current_length = 0

            for char in input_string:
                if current_length < chunk_length:
                    current_chunk += char
                    current_length += 1
                else:
                    if char == separator:
                        result.append(current_chunk.strip())
                        current_chunk = ""
                        current_length = 0
                    else:
                        last_separator = current_chunk.rfind(separator)
                        if last_separator != -1:
                            result.append(current_chunk[:last_separator].strip())
                            current_chunk = current_chunk[last_separator + 1:]
                        else:
                            result.append(current_chunk.strip())
                            current_chunk = ""
                        current_chunk += char
                        current_length = 1

            if current_chunk:
                result.append(current_chunk.strip())

            return result
        except Exception as err:
            self.print_helper.error_and_exception(f"split_string", err)
            return [input_string]
