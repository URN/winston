import queue
import re
import socket
import subprocess
import threading

import httpx
from loguru import logger

from winston.config import AudioConfig, GeneralConfig, NotificationsConfig, ZettaConfig

# FFMPeg outputs some weird stuff, but this will contain the volume data
FFMPEG_REGEX = re.compile("(\\w+): (.+)$")

# Create a queue for notifications from loudness monitor -> Zetta
NOTIF_QUEUE = queue.Queue()


class FFMPEGListener(threading.Thread):
    def run(self):
        samples = []

        while True:
            p = subprocess.Popen(
                [
                    "ffmpeg",
                    "-t",
                    str(AudioConfig.sample_dur),
                    "-i",
                    GeneralConfig.stream_url,
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "/dev/null",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                _, errs = p.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()
                _, errs = p.communicate()

            data = {}

            for line in errs.split(b"\n"):
                if b"volumedetect" in line:
                    line_matched = FFMPEG_REGEX.search(line.decode())
                    if line_matched:
                        data[line_matched.group(1)] = line_matched.group(2)

            if "mean_volume" not in data:
                logger.debug(data)
                continue

            max_vol = float(data["max_volume"].split(" ")[0])
            mean_vol = float(data["mean_volume"].split(" ")[0])

            samples.append((max_vol, mean_vol))

            if len(samples) > AudioConfig.samples:
                samples.pop(0)

            quiet_samps = 0

            for max_vol, mean_vol in samples:
                if max_vol < AudioConfig.ambient_db:
                    quiet_samps += 1

            logger.debug(f"Quiet samps: {quiet_samps}")

            if quiet_samps > AudioConfig.samples * AudioConfig.threshold:
                logger.warning("SILENCE DETECTED! Instructing Zetta to switch to Auto!")
                NOTIF_QUEUE.put(ZettaConfig.silence_message)

                httpx.post(
                    NotificationsConfig.discord,
                    json={
                        "content": (
                            f":warning: SILENCE DETECTED! Instructing Zetta "
                            f"to switch to Auto! Last detected max volume was {max_vol}"
                            f" dB, mean volume was {mean_vol} dB."
                        )
                    },
                )

                samples.clear()


class ZettaSocket(threading.Thread):
    def run(self):
        logger.info("Opening socket to Zetta")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ZettaConfig.host, ZettaConfig.port))

        while True:
            msg = NOTIF_QUEUE.get()
            logger.debug(f"Sending message: {msg}")
            sock.sendall(msg.encode() + b"\n")
            NOTIF_QUEUE.task_done()


if __name__ == "__main__":
    logger.info("Starting Winston...")

    httpx.post(
        NotificationsConfig.discord,
        json={
            "content": ":green_circle: Winston is now online, listening into stream."
        },
    )

    listener = FFMPEGListener()
    listener.start()

    zetta = ZettaSocket()
    zetta.start()

    listener.join()
