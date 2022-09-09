# from copy import copy
import os, sys, struct
import socket
from collections import namedtuple
import yaml
import numpy as np
from scipy.spatial.transform import Rotation as Rot
import argparse
import rospy, cv_bridge, tf2_ros
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from geometry_msgs.msg import TransformStamped


class HoloLensMessagePublisher:
    UNIX_EPOCH = 11644473600
    # Set Header infomation
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

    # Rotate the HoloLens World coordinate system to match ROS World coordinate system
    # HoloLens World coordinate system: x left, y up, z backward
    # ROS World coordinate system: x forward, y left, z up
    HoloWorld2RosWorld = np.array(
        [[0, 0, -1, 0], [-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
        dtype=np.float32,
    )
    # Rotate the HoloLens Camera coordinate system to match ROS Camera coordinate system
    # HoloLens Camera coordinate system: x left, y up, z backward
    # ROS Camera coordinate system: x left, y down, z forward
    HoloPV2RosCam = np.array(
        [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]],
        dtype=np.float32,
    )

    def __init__(self, sensor_type, host, rig2depth, holo_serial="hololens2") -> None:
        self.serial = holo_serial
        self.sensor_type = sensor_type
        self.preTimeStamp = 0
        # Initialize CvBridge
        self.bridge = cv_bridge.CvBridge()
        # Calibration information
        self.pv2world = None
        self.rig2world = None
        self.depth2rig = np.linalg.inv(rig2depth)
        # Streaming Frame Header
        self.stream_header_format = self.SENSOR_FRAME_STRUCTURE[self.sensor_type][
            "header_format"
        ]
        self.stream_header = self.SENSOR_FRAME_STRUCTURE[self.sensor_type][
            "header_data"
        ]
        self.header_size = struct.calcsize(self.stream_header_format)
        # Varialbles for TCP stream socket
        self.host = host
        self.port = self.SENSOR_FRAME_STRUCTURE[self.sensor_type]["port"]
        # Set Publisher topic names
        self.node_id = f"hololens2_publisher_{self.serial}_{self.sensor_type}"
        self.world_frame_id = f"{self.serial}_world"
        self.frame_id = f"{self.serial}_{self.sensor_type}_optical_frame"
        self.imageTopic = f"/{self.serial}/sensor_{self.sensor_type}/image_raw"
        self.camInfoTopic = (
            f"/{self.serial}/sensor_{self.sensor_type}/camera_info"
            if self.sensor_type == "color"
            else None
        )

        # Initialize node
        try:
            rospy.init_node(name=self.node_id, anonymous=False)
            rospy.loginfo_once("Node '{}' initialized success...".format(self.node_id))
        except:
            rospy.loginfo_once("Node '{}' initialized failed!!!".format(self.node_id))
            sys.exit(0)

        # Create message Publishers
        self.imagePub = rospy.Publisher(self.imageTopic, Image, queue_size=2)
        self.tfBroadcaster = tf2_ros.TransformBroadcaster()
        self.camInfoPub = (
            rospy.Publisher(self.camInfoTopic, CameraInfo, queue_size=2)
            if self.sensor_type == "color"
            else None
        )

    def run(self):
        socket.setdefaulttimeout(3)
        timeout_counter = 0
        try:
            while not rospy.is_shutdown():
                # Initialize the TCP stream socket
                self.socket = self.create_tcp_stream_socket()
                # Connect to (host, port)
                try:
                    self.socket.connect((self.host, self.port))
                    rospy.loginfo('Connected to "{}:{}"'.format(self.host, self.port))
                except Exception:
                    self.socket.close()
                    timeout_counter += 1
                    rospy.logerr(
                        "Connection failed {}!!! ({}:{}). Try again 3 seconds later...".format(
                            timeout_counter, self.host, self.port
                        )
                    )
                    continue

                while not rospy.is_shutdown():
                    # Receive header
                    try:
                        reply = self.receive_data_in_chunks(self.header_size)
                    except Exception:
                        self.socket.close()
                        rospy.logerr("Cannot receive Header")
                        break

                    # Compute camera_to_world matrix
                    # for ROS coordinate system
                    #   ref: https://www.ros.org/reps/rep-0103.html
                    # for HoloLens coordinate system [x:right,y:up,z:backward]
                    #   ref: https://docs.microsoft.com/en-us/windows/mixed-reality/design/coordinate-systems
                    if self.sensor_type == "color":
                        self.latest_header, self.pv2world = self.color_header_parser(
                            reply
                        )
                        cam2world = np.matmul(
                            self.HoloWorld2RosWorld,
                            np.matmul(self.pv2world, self.HoloPV2RosCam),
                        )

                    if self.sensor_type == "depth":
                        self.latest_header, self.rig2world = self.depth_header_parser(
                            reply
                        )
                        cam2world = np.matmul(
                            self.HoloWorld2RosWorld,
                            np.matmul(self.rig2world, self.depth2rig),
                        )

                    rospy.logdebug("Header:\n", self.latest_header)

                    # Receive the image
                    img_bytes_size = (
                        self.latest_header.ImageHeight * self.latest_header.RowStride
                    )
                    try:
                        image_data = self.receive_data_in_chunks(img_bytes_size)
                    except Exception:
                        self.socket.close()
                        rospy.logerr("Cannot receive Image data...")
                        break

                    # Prepare messages for publishing
                    rospy.loginfo_once("Start publishing messages...")

                    # Create Timestamp
                    self.msgTimestamp = rospy.Time.from_sec(
                        self.latest_header.Timestamp / 1e7 - self.UNIX_EPOCH
                    )
                    rospy.logdebug("msgTimestamp={}".format(self.msgTimestamp))

                    # publish camera pose
                    self.publish_stamped_transformation_message(
                        cam2world,
                        self.world_frame_id,
                        self.frame_id,
                    )
                    # publish image message
                    image_array, encoding = self.image_data_parser(image_data)
                    self.publish_stamped_image_message(image_array, encoding)

                    # publish camera info message with camInfo publisher
                    if self.camInfoPub is not None:
                        self.publish_stamped_camera_info_message(
                            self.latest_header.fx,
                            self.latest_header.fy,
                            self.latest_header.cx,
                            self.latest_header.cy,
                        )

        except KeyboardInterrupt:
            rospy.signal_shutdown("Node shutdown by user...")
            self.socket.close()
            sys.exit()

    def color_header_parser(self, reply):
        header_data = struct.unpack(self.stream_header_format, reply)
        header = self.stream_header(*header_data)
        pv2world = np.array(header[9:26], dtype=np.float32).reshape((4, 4)).transpose()
        return header, pv2world

    def depth_header_parser(self, reply):
        header_data = struct.unpack(self.stream_header_format, reply)
        header = self.stream_header(*header_data)
        rig2world = np.array(header[5:22], dtype=np.float32).reshape((4, 4)).transpose()
        return header, rig2world

    def image_data_parser(self, reply):
        if self.latest_header.PixelStride == 2:  # depth image: 'Gray16'
            image_array = np.frombuffer(reply, dtype=np.uint16).reshape(
                (
                    self.latest_header.ImageHeight,
                    self.latest_header.ImageWidth,
                    -1,
                )
            )
            encoding = "16UC1"
        if self.latest_header.PixelStride == 3:  # color image 'Bgr8'
            image_array = np.frombuffer(reply, dtype=np.uint8).reshape(
                (
                    self.latest_header.ImageHeight,
                    self.latest_header.ImageWidth,
                    -1,
                )
            )
            encoding = "bgr8"
        if self.latest_header.PixelStride == 4:  # color image 'Bgra8'
            image_array = np.frombuffer(reply, dtype=np.uint8).reshape(
                (
                    self.latest_header.ImageHeight,
                    self.latest_header.ImageWidth,
                    -1,
                )
            )
            encoding = "bgra8"
        return image_array, encoding

    def receive_data_in_chunks(self, data_size):
        """
        Function to receive data in chunks.
        Especially useful for large datagrams
        """
        data = bytes()
        while len(data) < data_size:
            remaining_bytes = data_size - len(data)
            data_chunk = self.socket.recv(remaining_bytes)
            data += data_chunk
        return data

    def publish_stamped_image_message(self, image_array, encoding):
        msgImage = self.create_msgImage(image_array, encoding)
        self.imagePub.publish(msgImage)

    def publish_stamped_transformation_message(
        self, transform_mat, reference_frame, child_frame
    ):
        trans = transform_mat[:3, 3]
        quat = Rot.from_matrix(transform_mat[:3, :3]).as_quat()

        # Create & publish stamped transformation message
        self.msgTransformStamped = self.create_msgTransformStamped(
            timestamp=self.msgTimestamp,
            reference_frame=reference_frame,
            child_frame=child_frame,
            translation=trans,
            quaternion=quat,
        )
        self.tfBroadcaster.sendTransform(self.msgTransformStamped)

    def publish_stamped_camera_info_message(self, fx, fy, ppx, ppy):
        projection_matrix = [fx, 0, ppx, 0, 0, fy, ppy, 0, 0, 0, 1, 0]
        # create camera info message
        msgCamInfo = self.create_msgCamInfo(P=projection_matrix)
        self.camInfoPub.publish(msgCamInfo)

    def create_msgImage(self, image_array, encoding):
        """
        ref: http://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/Image.html
        ref: http://wiki.ros.org/cv_bridge/Tutorials/ConvertingBetweenROSImagesAndOpenCVImagesPython
        :param image_array
            numpy array of the image
        :param encoding
            encoding type of the image ()

        :returns msgImage
        """
        msg = self.bridge.cv2_to_imgmsg(image_array, encoding=encoding)
        msg.header.stamp = self.msgTimestamp
        msg.header.frame_id = self.frame_id
        return msg

    def create_msgTransformStamped(
        self, timestamp, translation, quaternion, reference_frame, child_frame
    ):
        """
        Creates a new stamped transform from translation and quaternion
        :param timestamp: assigned timestamp
        :param translation: assigned translation
        :param quaternion: assigned quaternion
        :param reference_frame: transform from this frame
        :param child_frame: transform to this frame

        :returns: TransformStamped
        """
        msg = TransformStamped()
        msg.header.stamp = timestamp
        msg.header.frame_id = reference_frame
        msg.child_frame_id = child_frame
        msg.transform.translation.x = translation[0]
        msg.transform.translation.y = translation[1]
        msg.transform.translation.z = translation[2]
        msg.transform.rotation.x = quaternion[0]
        msg.transform.rotation.y = quaternion[1]
        msg.transform.rotation.z = quaternion[2]
        msg.transform.rotation.w = quaternion[3]
        return msg

    def create_msgCamInfo(self, D=None, K=None, R=None, P=None):
        """
        ref: http://docs.ros.org/en/noetic/api/sensor_msgs/html/msg/CameraInfo.html
        :param D: float64[5]
            distortion parameters, For "plumb_bob", the 5 parameters are: (k1, k2, t1, t2, k3)
        :param K: float64[9]
            Intrinsic camera matrix for the raw (distorted) images
                [fx  0 cx]
            K = [ 0 fy cy]
                [ 0  0  1]
        :param R: float[9]
            Rectification matrix (stereo cameras only)
            # default: [1, 0, 0, 0, 1, 0, 0, 0, 1]
        :param P: float64[12]
            Intrinsic camera matrix of the processed (rectified) image
                [fx'  0  cx' Tx]
            P = [ 0  fy' cy' Ty]
                [ 0   0   1   0]
        """

        msg = CameraInfo()
        msg.header.stamp = self.msgTimestamp
        msg.header.frame_id = self.frame_id
        msg.width = self.latest_header.ImageWidth
        msg.height = self.latest_header.ImageHeight
        msg.distortion_model = "plumb_bob"
        if D is not None:
            msg.D = D
        if K is not None:
            msg.K = K
        if R is not None:
            msg.R = R
        if P is not None:
            msg.P = P
        return msg

    def create_tcp_stream_socket(self):
        try:
            ss = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            return ss
        except:
            rospy.logerr("TCP stream socket initialization failed... ")
            sys.exit()

    @staticmethod
    def load_depth_extrinsics_from_yaml(file_path):
        with open(file_path, "r") as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        extr = np.array(data["extrinsics"], dtype=np.float32).reshape((4, 4))
        return extr


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", help="IP address of HoloLens.", default="192.168.50.210", type=str
    )
    parser.add_argument(
        "--sensor_type",
        help='Publishing sensor type ["color" or "depth"]',
        choices=["color", "depth"],
        default="depth",
        type=str,
    )
    parser.add_argument(
        "--holo_serial", help="HoloLens serial", default="hololens2", type=str
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    host = args.host
    sensor_type = args.sensor_type.lower()
    holo_serial = args.holo_serial.lower()

    rig2depth = np.array(
        [
            0.022715600207448006,
            -0.9995700120925903,
            -0.018523599952459335,
            -0.05916620045900345,
            0.9609990119934082,
            0.026939600706100464,
            -0.27523499727249146,
            -0.015487399883568287,
            0.27561599016189575,
            -0.011549100279808044,
            0.9611979722976685,
            -0.01788480021059513,
            0.0,
            0.0,
            0.0,
            1.0,
        ],
        dtype=np.float32,
    ).reshape((4, 4))

    holo_publisher = HoloLensMessagePublisher(
        holo_serial=holo_serial,
        sensor_type=sensor_type,
        host=host,
        rig2depth=rig2depth,
    )

    holo_publisher.run()
