import uvicorn
import sys

from config.config import Config

from utils.printer import PrintHelper

config_app = Config()
print_ls = PrintHelper('[main]',
                       level=config_app.get_internal_log_level())
print_ls.info('start')
print_ls.info('load config')

if __name__ == '__main__':
    daemon = False
    if len(sys.argv) > 1 and '--daemon' in sys.argv:
        daemon = True

    endpoint_url = config_app.get_endpoint_url()
    endpoint_port = config_app.get_endpoint_port()

    print_ls.info(f"run server at url:{endpoint_url}-port={endpoint_port}")

    uvicorn.run('app:app',
                host=endpoint_url,
                port=int(endpoint_port),
                reload=True,
                # log_level=log_level,
                workers=2,
                )
