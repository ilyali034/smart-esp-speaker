import asyncio
import logging

from .app import amain
from .cli import parse_args

log = logging.getLogger("server")


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        log.info("Server stopped (Ctrl+C)")


if __name__ == "__main__":
    main()
