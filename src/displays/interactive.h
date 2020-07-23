// TAMSVIZ
// (c) 2020 Philipp Ruppel

#pragma once

#include "frame.h"
#include "marker.h"
#include "text.h"

#include "../core/topic.h"
#include "../core/watcher.h"

#include <geometry_msgs/PointStamped.h>
#include <geometry_msgs/PoseStamped.h>
#include <visualization_msgs/InteractiveMarker.h>
#include <visualization_msgs/InteractiveMarkerFeedback.h>
#include <visualization_msgs/InteractiveMarkerInit.h>
#include <visualization_msgs/InteractiveMarkerUpdate.h>

class InteractiveMarker;
class InteractiveMarkerArray;

struct InteractiveMarkerParameters {
  bool show_descriptions = false;
  double description_size = 1.0;
  Eigen::Vector2d description_offset = Eigen::Vector2d::Zero();
  std::shared_ptr<Material> description_material;
};

class InteractiveMarkerControl : public SceneNode {
  std::mutex _mutex;
  std::vector<std::shared_ptr<VisualizationMarker>> _markers;
  int _interaction_mode = 0;
  InteractiveMarker *_parent = nullptr;
  Eigen::Quaterniond _orientation = Eigen::Quaterniond::Identity();
  std::string _name;
  std::shared_ptr<InteractiveMarkerParameters> _params;

public:
  InteractiveMarkerControl(
      const visualization_msgs::InteractiveMarkerControl &message,
      const std::shared_ptr<InteractiveMarkerParameters> &params,
      InteractiveMarker *parent);
  virtual bool interact(const Interaction &interaction) override;
  void update(const visualization_msgs::InteractiveMarkerControl &message);
  InteractiveMarker *parentInteractiveMarker() { return _parent; }
  const std::string &controlName() const { return _name; }
};

class InteractiveMarker : public SceneNode {
  std::shared_ptr<TextRenderer> _text;
  InteractiveMarkerArray *_parent = nullptr;
  std::mutex _mutex;
  std::vector<std::shared_ptr<InteractiveMarkerControl>> _controls;
  std::string _name;
  bool _dragged = false;
  std::shared_ptr<InteractiveMarkerParameters> _params;
  double _scale = 1.0;

public:
  InteractiveMarker(const visualization_msgs::InteractiveMarker &message,
                    const std::shared_ptr<InteractiveMarkerParameters> &params,
                    InteractiveMarkerArray *parent);
  void update(const visualization_msgs::InteractiveMarker &message);
  void update(const visualization_msgs::InteractiveMarkerPose &message);
  InteractiveMarkerArray *parentInteractiveMarkerArray() { return _parent; }
  const std::string &markerName() const { return _name; }
  virtual bool interact(const Interaction &interaction) override;
  virtual void renderSync(const RenderSyncContext &context) override;
};

class InteractiveMarkerArray : public SceneNode {
  std::mutex _mutex;
  std::map<std::string, std::shared_ptr<InteractiveMarker>> _markers;
  std::shared_ptr<InteractiveMarkerParameters> _params;

public:
  InteractiveMarkerArray(
      const std::shared_ptr<InteractiveMarkerParameters> &params);
  void init(const visualization_msgs::InteractiveMarkerInit &message);
  void update(const visualization_msgs::InteractiveMarkerUpdate &message);
  virtual void renderSync(const RenderSyncContext &context) override;
  Event<void(const visualization_msgs::InteractiveMarkerFeedback &)> feedback;
  std::shared_ptr<InteractiveMarker> marker(const std::string &name);
};

class InteractiveMarkerDisplayBase : public MeshDisplayBase {
protected:
  std::shared_ptr<InteractiveMarkerParameters> _params;
  std::shared_ptr<InteractiveMarkerArray> _markers;
  InteractiveMarkerDisplayBase();

public:
  virtual void renderSync(const RenderSyncContext &context) override;
};
DECLARE_TYPE(InteractiveMarkerDisplayBase, MeshDisplayBase);

class InteractiveMarkerDisplay : public InteractiveMarkerDisplayBase {
  std::shared_ptr<Subscriber<visualization_msgs::InteractiveMarkerUpdate>>
      _update_subscriber;
  std::shared_ptr<Subscriber<visualization_msgs::InteractiveMarkerInit>>
      _init_subscriber;
  Watcher _watcher;
  std::shared_ptr<Publisher<visualization_msgs::InteractiveMarkerFeedback>>
      _publisher;
  static std::vector<std::string> listTopicNamespaces();

public:
  PROPERTY(std::string, topicNamespace, "",
           list = [](const Property &property) {
             return InteractiveMarkerDisplay::listTopicNamespaces();
           });
  PROPERTY(bool, showDescriptions, true);
  PROPERTY(double, descriptionSize, 0.2, min = 0);
  PROPERTY(Eigen::Vector2d, descriptionOffset, Eigen::Vector2d(0, 0.85));
  PROPERTY(Color3, descriptionColor, Color3(1, 1, 1));
  PROPERTY(double, descriptionOpacity, 1.0, min = 0, max = 1);
  InteractiveMarkerDisplay();
  virtual void renderSync(const RenderSyncContext &context) override;
};
DECLARE_TYPE(InteractiveMarkerDisplay, InteractiveMarkerDisplayBase);

class InteractivePoseDisplayBase : public InteractiveMarkerDisplayBase {
protected:
  InteractivePoseDisplayBase();

public:
  PROPERTY(Frame, frame);
  PROPERTY(Pose, transform);
  PROPERTY(double, scale, 1.0, min = 0.0);
  virtual void renderSync(const RenderSyncContext &context) override;
  virtual bool interact(const Interaction &interaction) override;
  virtual void publish(const std::string &frame,
                       const Eigen::Isometry3d &pose) {}
};
DECLARE_TYPE(InteractivePoseDisplayBase, InteractiveMarkerDisplayBase);

struct PointPublisherDisplay : InteractivePoseDisplayBase {
  Publisher<geometry_msgs::PointStamped> _publisher;
  PROPERTY(std::string, topic);
  PointPublisherDisplay();
  virtual void publish(const std::string &frame,
                       const Eigen::Isometry3d &pose) override;
};
DECLARE_TYPE(PointPublisherDisplay, InteractivePoseDisplayBase);

struct PosePublisherDisplay : InteractivePoseDisplayBase {
  Publisher<geometry_msgs::PoseStamped> _publisher;
  PROPERTY(std::string, topic);
  PosePublisherDisplay();
  virtual void publish(const std::string &frame,
                       const Eigen::Isometry3d &pose) override;
};
DECLARE_TYPE(PosePublisherDisplay, InteractivePoseDisplayBase);
