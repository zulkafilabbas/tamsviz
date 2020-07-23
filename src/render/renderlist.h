// TAMSVIZ
// (c) 2020 Philipp Ruppel

#pragma once

#include "opengl.h"

#include <memory>
#include <vector>

#include <Eigen/Dense>

class Mesh;

struct CameraBlock {
  Eigen::Matrix4f view_matrix = Eigen::Matrix4f::Identity();
  Eigen::Matrix4f projection_matrix = Eigen::Matrix4f::Identity();
};

enum class LightType : uint32_t {
  Ambient = 0,
  Directional = 1,
  Point = 2,
  Spot = 3,
};

struct LightBlock {
  Eigen::Matrix4f pose = Eigen::Matrix4f::Identity();
  Eigen::Vector3f color = Eigen::Vector3f::Zero();
  uint32_t type = 0;
  Eigen::Vector3f position = Eigen::Vector3f::Zero();
  float softness = 1.0f;
};

struct LightArrayBlock {
  LightBlock light_array[16];
  uint32_t light_count = 0;
};

struct MaterialBlock {
  Eigen::Vector4f color = Eigen::Vector4f(1, 1, 1, 1);
  float roughness = 0.5f;
  float metallic = 0.0f;
  uint32_t color_texture = 0;
  uint32_t normal_texture = 0;
  uint32_t id = 0;
  uint32_t flags = 0;
  uint8_t transparent = false;
};

struct InstanceBlock {
  Eigen::Vector4f pose_x = Eigen::Vector4f(1, 0, 0, 0),
                  pose_y = Eigen::Vector4f(0, 1, 0, 0),
                  pose_z = Eigen::Vector4f(0, 0, 1, 0);
  inline void setPose(const Eigen::Matrix4f &matrix) {
    pose_x = matrix.row(0);
    pose_y = matrix.row(1);
    pose_z = matrix.row(2);
  }
  inline void setPose(const Eigen::Isometry3d &pose) {
    setPose(pose.matrix().cast<float>());
  }
  inline void setPose(const Eigen::Affine3d &pose) {
    setPose(pose.matrix().cast<float>());
  }
};

struct RenderOptions {
  GLuint primitive_type = GL_TRIANGLES;
  bool transparent = false;
  bool double_sided = false;
};

struct RenderCommand {
  RenderOptions options;
  GLuint vertex_array_object = 0;
  size_t element_count = 0;
  size_t first_instance = 0;
  size_t instance_count = 0;
  size_t material_index = 0;
  bool indexed = false;
};

class RenderList {
  std::vector<MaterialBlock, Eigen::aligned_allocator<MaterialBlock>>
      _materials;
  std::vector<InstanceBlock, Eigen::aligned_allocator<InstanceBlock>>
      _instances;
  std::vector<RenderCommand> _commands;
  std::vector<LightBlock, Eigen::aligned_allocator<LightBlock>> _lights;

public:
  void push(const MaterialBlock &material);
  void push(const std::shared_ptr<Mesh> &mesh, const RenderOptions &options);
  void push(const InstanceBlock &instance);

  inline void push(const MaterialBlock &material,
                   const std::shared_ptr<Mesh> &mesh,
                   const InstanceBlock &instance,
                   const RenderOptions &options = RenderOptions()) {
    push(material);
    push(mesh, options);
    push(instance);
  }

  template <class IT>
  inline void push(const MaterialBlock &material,
                   const std::shared_ptr<Mesh> &mesh, const IT &instance_begin,
                   const IT &instance_end,
                   const RenderOptions &options = RenderOptions()) {
    push(material);
    push(mesh, options);
    for (auto &instance = instance_begin; instance != instance_end;
         ++instance) {
      push(mesh, *instance);
    }
  }

  inline void push(const LightBlock &light) { _lights.push_back(light); }

  void clear();

  friend class Renderer;
};
