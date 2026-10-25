#!/usr/bin/env python3
import csv
import os

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from geometry_msgs.msg import Pose
from cv_bridge import CvBridge
from ultralytics import YOLO


CSV_HEADER = [
    'timestamp', 'robot_x', 'robot_y', 'robot_z',
    'robot_qx', 'robot_qy', 'robot_qz', 'robot_qw',
    'track_id', 'class_name', 'confidence',
    'box_x1', 'box_y1', 'box_x2', 'box_y2',
]


class CoralDetectorNode(Node):
    def __init__(self):
        super().__init__('coral_detector_node')

        self.declare_parameter('model_path', '/ws/src/bluerov2/bluerov2_integration/src/runs/detect/runs_coral/yolov8_coral/weights/best.pt')
        self.declare_parameter('csv_path', 'coral_detections.csv')
        self.declare_parameter('conf_threshold', 0.5)
        self.declare_parameter('image_topic', '/bluerov2/image')
        self.declare_parameter('pose_topic', '/bluerov2/pose_gt')
        self.declare_parameter('device', 'cpu')  # 'cuda:0' se tiver GPU

        model_path = self.get_parameter('model_path').value
        csv_path = self.get_parameter('csv_path').value
        self.conf = float(self.get_parameter('conf_threshold').value)
        self.device = self.get_parameter('device').value

        self.get_logger().info(f'Carregando modelo: {model_path}')
        self.model = YOLO(model_path)
        self.class_names = self.model.names  # dict {0: 'nome', 1: 'nome', ...}
        self.get_logger().info(f'Classes do modelo: {self.class_names}')

        self.bridge = CvBridge()
        self.latest_pose = None

        self.create_subscription(
            Pose, self.get_parameter('pose_topic').value, self.pose_callback, 10)
        self.create_subscription(
            Image, self.get_parameter('image_topic').value, self.image_callback,
            qos_profile_sensor_data)

        new_file = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
        self.csv_file = open(csv_path, 'a', newline='')
        self.writer = csv.writer(self.csv_file)
        if new_file:
            self.writer.writerow(CSV_HEADER)
            self.csv_file.flush()

        self.get_logger().info(f'Salvando detecções em: {csv_path}')

    def pose_callback(self, msg: Pose):
        self.latest_pose = msg

    def image_callback(self, msg: Image):
        if self.latest_pose is None:
            self.get_logger().warn(
                'Aguardando a primeira pose do robô...', throttle_duration_sec=2.0)
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        results = self.model.track(
            frame,
            persist=True,
            conf=self.conf,
            device=self.device,
            tracker='bytetrack.yaml',
            verbose=False,
        )
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return

        timestamp = self.get_clock().now().nanoseconds * 1e-9
        p = self.latest_pose.position
        q = self.latest_pose.orientation

        # Sem tracking confirmado, track_id pode ser None
        ids = boxes.id.int().tolist() if boxes.id is not None else [-1] * len(boxes)
        classes = boxes.cls.int().tolist()
        confs = boxes.conf.tolist()
        xyxy = boxes.xyxy.tolist()

        for tid, cls_id, conf, (x1, y1, x2, y2) in zip(ids, classes, confs, xyxy):
            self.writer.writerow([
                f'{timestamp:.4f}',
                f'{p.x:.4f}', f'{p.y:.4f}', f'{p.z:.4f}',
                f'{q.x:.4f}', f'{q.y:.4f}', f'{q.z:.4f}', f'{q.w:.4f}',
                tid, self.class_names[cls_id], f'{conf:.4f}',
                f'{x1:.1f}', f'{y1:.1f}', f'{x2:.1f}', f'{y2:.1f}',
            ])
        self.csv_file.flush()

    def destroy_node(self):
        self.csv_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = CoralDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()