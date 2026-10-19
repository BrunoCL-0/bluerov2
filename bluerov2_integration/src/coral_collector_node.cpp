#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
// Se for usar OpenCV para converter a imagem:
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>

class CoralCollectorNode : public rclcpp::Node
{
public:
    CoralCollectorNode() : Node("coral_collector_node")
    {
        // QoS configuration para sensores (ótimo para Gazebo)
        rclcpp::SensorDataQoS qos;

        // Subscriber da Câmera do BlueROV2
        image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "/bluerov2/image", qos,
            std::bind(&CoralCollectorNode::imageCallback, this, std::placeholders::_1));

        // Subscriber da Pose do Robô (Ground Truth)
        pose_sub_ = this->create_subscription<geometry_msgs::msg::Pose>(
            "/bluerov2/pose_gt", 10,
            std::bind(&CoralCollectorNode::poseCallback, this, std::placeholders::_1));

        RCLCPP_INFO(this->get_node_logger(), "Coral Collector Node em C++ iniciado com sucesso!");
    }

private:
    void poseCallback(const geometry_msgs::msg::Pose::SharedPtr msg)
    {
        // Guarda a última pose válida do robô em cache
        latest_pose_ = *msg;
        has_pose_ = true;
        
        // Exemplo de leitura das coordenadas X, Y, Z globais
        // RCLCPP_INFO_THROTTLE(this->get_node_logger(), *this->get_clock(), 2000,
        //     "Posição atual -> X: %.2f, Y: %.2f, Z: %.2f", 
        //     latest_pose_.position.x, latest_pose_.position.y, latest_pose_.position.z);
    }

    void imageCallback(const sensor_msgs::msg::Image::SharedPtr msg)
    {
        if (!has_pose_) {
            RCLCPP_WARN_THROTTLE(this->get_node_logger(), *this->get_clock(), 2000,
                "Aguardando a primeira pose do robô chegar...");
            return;
        }

        try {
            // Converte a mensagem ROS Image para Mat do OpenCV
            cv::Mat cv_image = cv_bridge::toCvShare(msg, "bgr8")->image;

            // --- AQUI ENTRA A SUA INTEGRAÇÃO COM A IA / API ---
            // 1. Você pode chamar a função do modelo de IA passando 'cv_image'
            // 2. Juntar com as coordenadas de 'latest_pose_'
            // 3. Enviar para a sua API web (ex: via libcurl ou cpp-httplib)

            RCLCPP_INFO_THROTTLE(this->get_node_logger(), *this->get_clock(), 3000,
                "Frame recebido (%dx%d) sincronizado com a pose (X=%.2f, Y=%.2f)",
                cv_image.cols, cv_image.rows, 
                latest_pose_.position.x, latest_pose_.position.y);

        } catch (cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_node_logger(), "Erro no cv_bridge: %s", e.what());
        }
    }

    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::Subscription<geometry_msgs::msg::Pose>::SharedPtr pose_sub_;
    
    geometry_msgs::msg::Pose latest_pose_;
    bool has_pose_ = false;
};

int main(int argc, char* argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CoralCollectorNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
