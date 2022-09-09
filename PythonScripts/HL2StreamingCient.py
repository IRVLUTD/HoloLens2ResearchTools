import sys, os
import socket
import struct
from collections import namedtuple
import numpy as np
import cv2
from multiprocessing import Process
import argparse
from datetime import datetime
import pandas as pd


HundredsOfNsToMilliseconds = 1e-4
MillisecondsToSeconds = 1e-3

# Define the viewer distance in meter for Depth image
VIEW_DEPTH_DISTANCE = 2.0
CV_ALPHA = 255 / (VIEW_DEPTH_DISTANCE * 1000)


class SensorStreamingClient:
    # Protocol Header Format
    # see https://docs.python.org/2/library/struct.html#format-characters
    SENSOR_FRAME_STRUCTURE = {
        "color": {
            "port": 10090,
            "header_format": "@qIIII20f",
            "header_data": namedtuple(
                "SensorFrameStreamHeader",
                "Timestamp ImageWidth ImageHeight PixelStride RowStride "
                "fx fy cx cy "
                "PV2WorldTransformM11 PV2WorldTransformM12 PV2WorldTransformM13 PV2WorldTransformM14 "
                "PV2WorldTransformM21 PV2WorldTransformM22 PV2WorldTransformM23 PV2WorldTransformM24 "
                "PV2WorldTransformM31 PV2WorldTransformM32 PV2WorldTransformM33 PV2WorldTransformM34 "
                "PV2WorldTransformM41 PV2WorldTransformM42 PV2WorldTransformM43 PV2WorldTransformM44 ",
            ),
        },
        "depth": {
            "port": 10091,
            "header_format": "@qIIII16f",
            "header_data": namedtuple(
                "SensorFrameStreamHeader",
                "Timestamp ImageWidth ImageHeight PixelStride RowStride "
                "Rig2WorldTransformM11 Rig2WorldTransformM12 Rig2WorldTransformM13 Rig2WorldTransformM14 "
                "Rig2WorldTransformM21 Rig2WorldTransformM22 Rig2WorldTransformM23 Rig2WorldTransformM24 "
                "Rig2WorldTransformM31 Rig2WorldTransformM32 Rig2WorldTransformM33 Rig2WorldTransformM34 "
                "Rig2WorldTransformM41 Rig2WorldTransformM42 Rig2WorldTransformM43 Rig2WorldTransformM44 ",
            ),
        },
    }

    def __init__(
        self, host, sensorType, output_folder, save_image=False, verbose=False
    ) -> None:
        assert sensorType.lower() in ["color", "depth", "all"], print(
            "Wrong sensorType!!!"
        )

        self.save_image = save_image
        self.verbose = verbose
        self.output_folder = output_folder
        self.sensor_type = sensorType
        self.host = host
        self.port = self.SENSOR_FRAME_STRUCTURE[self.sensor_type]["port"]
        self.header_format = self.SENSOR_FRAME_STRUCTURE[self.sensor_type][
            "header_format"
        ]
        self.header_data = self.SENSOR_FRAME_STRUCTURE[self.sensor_type]["header_data"]
        self.header_size = struct.calcsize(self.header_format)

        # define socket parameters
        self.socket = None
        self.default_timeout = 3.0
        socket.setdefaulttimeout(self.default_timeout)

        self.latest_header = None
        self.latest_image = None
        if self.save_image:
            os.makedirs(os.path.join(output_folder, self.sensor_type), exist_ok=True)
            self.camPose_file = os.path.join(
                self.output_folder,
                "pv2WorldTransform.csv"
                if self.sensor_type == "color"
                else "rig2worldTransform.csv",
            )
            self.camPose_dict = {}
            self.streamData = {}
            self.image_name_format = os.path.join(
                self.output_folder,
                self.sensor_type,
                "color_{}.jpg" if self.sensor_type == "color" else "depth_{}.png",
            )

        self.start()

    def create_tcp_socket(self):
        while True:
            try:
                self.socket = socket.socket(
                    family=socket.AF_INET, type=socket.SOCK_STREAM
                )
                break
            except socket.error as err:
                print("==> [ERROR] Create socket failed!!!")
                print(f"  *{err}")

    def close_tcp_socket(self):
        self.socket.close()
        print("==> [INFO] Socket close succeed...")

    def receive_data(self, data_size):
        data = bytes()
        while len(data) < data_size:
            remaining_bytes = data_size - len(data)
            try:
                data_chunk = self.socket.recv(remaining_bytes)
                data += data_chunk
            except Exception:
                break
        return data

    def parse_header(self, header_data):
        header = struct.unpack(self.header_format, header_data)
        self.latest_header = self.header_data(*header)

    def parse_image(self, image_data):
        if self.latest_header.PixelStride == 2:  # depth image
            img = np.frombuffer(image_data, dtype=np.uint16)
            img = img.reshape(
                (self.latest_header.ImageHeight, self.latest_header.ImageWidth, -1)
            )
            self.latest_image = cv2.applyColorMap(
                cv2.convertScaleAbs(img, alpha=CV_ALPHA),
                cv2.COLORMAP_JET,
            )
        if self.latest_header.PixelStride == 3:  # BGR8 image
            img = np.frombuffer(image_data, dtype=np.uint8)
            self.latest_image = img.reshape(
                (self.latest_header.ImageHeight, self.latest_header.ImageWidth, -1)
            )
        if self.latest_header.PixelStride == 4:  # BGRA8 image
            img = np.frombuffer(image_data, dtype=np.uint8)
            self.latest_image = img.reshape(
                (self.latest_header.ImageHeight, self.latest_header.ImageWidth, -1)
            )

    def get_pv2world_from_header(self, header):
        pv2world = np.array(header[9:26]).reshape((4, 4)).T
        return pv2world

    def get_rig2world_from_header(self, header):
        rig2world = np.array(header[5:22]).reshape((4, 4)).T
        return rig2world

    def get_intrinsics_from_header(self, header):
        intrinsics = np.array(
            [[header.fx, 0, header.cx], [0, header.fy, header.cy], [0, 0, 1]],
            dtype=np.float32,
        )
        return intrinsics

    def stop(self):
        cv2.destroyAllWindows()
        self.close_tcp_socket()
        if self.save_image:
            df_stream_data = pd.DataFrame.from_dict(
                self.streamData, orient="columns", dtype="str"
            )
            df_stream_data.to_html(
                os.path.join(self.output_folder, f"{self.sensor_type}_stream_data.html")
            )
        sys.exit()

    def start(self):
        timeout_counter = 0
        while True:
            self.create_tcp_socket()
            try:
                self.socket.connect((self.host, self.port))
                print(
                    f"==> [INFO] Connection create succeed... ({self.host}:{self.port})"
                )
            except Exception:
                self.socket.close()
                timeout_counter += 1
                print(
                    f"==> [ERROR] Connection create failed!!! ({self.host}:{self.port})"
                )
                print(f"  * Try to reconnect {self.default_timeout} seconds later...")
                continue

            while True:
                header_data = self.receive_data(self.header_size)
                if len(header_data) != self.header_size:
                    print("==> [ERROR] Failed to receive header data!!!")
                    break
                self.parse_header(header_data)
                if self.verbose:
                    print(self.latest_header)

                img_bytes_size = (
                    self.latest_header.ImageHeight * self.latest_header.RowStride
                )
                image_data = self.receive_data(img_bytes_size)
                if len(image_data) != img_bytes_size:
                    print("==> [ERROR] Failed to receive image data!!!")
                    break
                self.parse_image(image_data)

                if self.save_image:
                    cv2.imwrite(
                        self.image_name_format.format(self.latest_header.Timestamp),
                        self.latest_image,
                    )
                    if self.sensor_type == "color":
                        stream_data = {
                            "pv2world": self.get_pv2world_from_header(
                                self.latest_header
                            ).tolist(),
                            "intrinsics": self.get_intrinsics_from_header(
                                self.latest_header
                            ).tolist(),
                        }
                    if self.sensor_type == "depth":
                        stream_data = {
                            "rig2world": self.get_rig2world_from_header(
                                self.latest_header
                            ).tolist(),
                        }
                    self.streamData[str(self.latest_header.Timestamp)] = stream_data

                # Display image
                cv2.imshow(f"Hololen2 {self.sensor_type} Sensor", self.latest_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.stop()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", help="Host Address to connect", default="192.168.50.210"
    )
    parser.add_argument(
        "--sensor_type",
        help="Sensor type to subscribe, all/depth/color",
        choices=["color", "depth", "all"],
        default="all",
    )
    parser.add_argument(
        "--save_image", help="Save image to local", action="store_true", default=False
    )
    parser.add_argument(
        "--verbose", help="Print header information", action="store_true", default=False
    )
    parser.add_argument(
        "--output_folder",
        help="Output folder to save image",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "output",
            datetime.now().strftime("%Y%m%d_%H%M%S"),
        ),
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    host = args.host
    sensor_type = args.sensor_type
    save_image = args.save_image
    output_folder = args.output_folder

    process_pool = []

    if sensor_type == "color":
        process_pool.append(
            Process(
                target=SensorStreamingClient,
                args=(
                    host,
                    "color",
                    output_folder,
                    save_image,
                ),
                name="ColorViewer",
            )
        )

    if sensor_type == "depth":
        process_pool.append(
            Process(
                target=SensorStreamingClient,
                args=(
                    host,
                    "depth",
                    output_folder,
                    save_image,
                ),
                name="DepthViewer",
            )
        )

    if sensor_type == "all":
        process_pool.append(
            Process(
                target=SensorStreamingClient,
                args=(
                    host,
                    "color",
                    output_folder,
                    save_image,
                ),
                name="ColorViewer",
            )
        )
        process_pool.append(
            Process(
                target=SensorStreamingClient,
                args=(
                    host,
                    "depth",
                    output_folder,
                    save_image,
                ),
                name="DepthViewer",
            )
        )

    for p in process_pool:
        p.start()

    for p in process_pool:
        p.join()
