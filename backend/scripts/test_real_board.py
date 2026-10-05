"""Read real hardware using Gravia's pinned API; never use the wiibalance CLI."""

import argparse
import json
import sys
import time

from app.balance_board.real_board import describe_connection_error, map_board_state
from app.balance_board.wiibalance_client import WiibalanceClient
from app.configuration import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20)
    arguments = parser.parse_args()
    if arguments.samples < 1 or arguments.timeout <= 0:
        parser.error("--samples and --timeout must be positive")
    connection = None
    try:
        settings = Settings()
        if not settings.board_mac:
            raise ValueError("Configura GRAVIA_BOARD_MAC prima di eseguire la diagnostica.")
        print(f"Connecting to Wii Balance Board {settings.board_mac}...", flush=True)
        connection = WiibalanceClient(settings.board_mac)
        print("Balance Board connected", flush=True)
        started = time.monotonic()
        previous_weights = None
        printed = 0
        while printed < arguments.samples:
            if time.monotonic() - started > arguments.timeout:
                raise TimeoutError("No fresh samples during diagnostic")
            state = connection.read_state()
            if not state.connected:
                raise RuntimeError("Balance Board disconnected during diagnostic")
            if state.weights is not previous_weights:
                sample = map_board_state(state, time.monotonic() - started)
                print(
                    json.dumps(
                        {
                            "weight": sample.weight,
                            "sensors": {
                                "frontLeft": sample.front_left,
                                "frontRight": sample.front_right,
                                "rearLeft": sample.rear_left,
                                "rearRight": sample.rear_right,
                            },
                            "centerOfPressure": {"x": sample.center_x, "y": sample.center_y},
                            "battery": state.battery_percent if state.battery_raw >= 0 else None,
                        }
                    ),
                    flush=True,
                )
                previous_weights = state.weights
                printed += 1
            time.sleep(0.5)
        return 0
    except KeyboardInterrupt:
        print("Diagnostica interrotta.", file=sys.stderr)
        return 130
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else describe_connection_error(error)
        print(f"Diagnostica fallita: {message} ({error})", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()
            print("Balance Board disconnected", flush=True)


if __name__ == "__main__":
    sys.exit(main())
