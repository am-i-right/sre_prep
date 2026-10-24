import argparse
import time

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PATHS = {
    "normal": "/counter",
    "errors": "/lab/error",
    "slow": "/slow?seconds=1",
}


def send_request(url):
    try:
        with urlopen(url, timeout=15) as response:
            return response.status

    except HTTPError as error:
        return error.code

    except (URLError, TimeoutError):
        return "network_error"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=PATHS.keys(),
        required=True,
    )

    parser.add_argument(
        "--seconds",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--rps",
        type=float,
        default=3.0,
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080",
    )

    args = parser.parse_args()

    if args.seconds <= 0 or args.rps <= 0:
        parser.error(
            "--seconds and --rps must be positive"
        )

    url = args.base_url + PATHS[args.mode]

    print(f"Mode: {args.mode}")
    print(f"Target: {url}")
    print(f"Duration: {args.seconds} s")
    print(f"Target RPS: {args.rps}")

    deadline = time.monotonic() + args.seconds
    futures = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        while time.monotonic() < deadline:
            futures.append(
                pool.submit(send_request, url)
            )

            time.sleep(1 / args.rps)

        results = Counter(
            future.result() for future in futures
        )

    print("\nResults:")

    for status, count in sorted(
        results.items(),
        key=lambda item: str(item[0]),
    ):
        print(f"{status}: {count}")


if __name__ == "__main__":
    main()

