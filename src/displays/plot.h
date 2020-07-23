// TAMSVIZ
// (c) 2020 Philipp Ruppel

#pragma once

#include "../core/document.h"
#include "../core/struct.h"
#include "../core/timeseries.h"
#include "../core/topic.h"
#include "../core/workspace.h"

#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>

#include <QPainter>

class MessageQueryProperty {
  mutable std::mutex _subscriber_mutex;
  std::shared_ptr<Subscriber<Message>> _subscriber;
  std::string _query;

public:
  MessageQueryProperty() {}
  MessageQueryProperty(const std::string &query) : _query(query) {}
  MessageQueryProperty(const MessageQueryProperty &other) {
    _query = other._query;
  }
  MessageQueryProperty &operator=(const MessageQueryProperty &other) {
    _query = other._query;
    return *this;
  }
  MessageQuery query() const { return MessageQuery(_query); };
  const std::string &str() const { return _query; }
  void assign(const std::string &query) { _query = query; }
  void subscriber(const std::shared_ptr<Subscriber<Message>> &subscriber) {
    std::unique_lock<std::mutex> lock(_subscriber_mutex);
    _subscriber = subscriber;
  }
  std::shared_ptr<Subscriber<Message>> subscriber() const {
    std::unique_lock<std::mutex> lock(_subscriber_mutex);
    return _subscriber;
  }
  bool empty() const { return _query.empty(); }
};
static void toString(const MessageQueryProperty &x, std::string &str) {
  str = x.str();
}
static void fromString(MessageQueryProperty &x, const std::string &str) {
  x.assign(str);
}
static bool operator==(const MessageQueryProperty &a,
                       const MessageQueryProperty &b) {
  return a.str() == b.str();
}
static bool operator!=(const MessageQueryProperty &a,
                       const MessageQueryProperty &b) {
  return a.str() != b.str();
}
template <> struct DefaultPropertyAttributes<MessageQueryProperty> {
  static void initialize(PropertyAttributes *attributes) {
    attributes->complete = [](const Property &property,
                              const std::string &text) {
      LOG_DEBUG("complete");
      if (auto sub = property.get<MessageQueryProperty>().subscriber()) {
        LOG_DEBUG("subscriber found");
        if (auto msg = sub->topic()->message()) {
          LOG_DEBUG("message found");
          return MessageQuery(text).complete(MessageParser(msg));
        }
      }
      LOG_DEBUG("no message");
      return std::vector<std::string>();
    };
  }
};

AUTO_STRUCT_BEGIN(PlotMargins);
AUTO_STRUCT_FIELD(double, left, 0.0, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, bottom, 0.0, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, right, 0.0, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, top, 0.0, step_scale = 10, min = 0);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotAxis);
AUTO_STRUCT_FIELD(std::string, label);
AUTO_STRUCT_EXTRA(PlotAxis(const std::string &label) : label(label){});
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotAxes);
AUTO_STRUCT_FIELD(double, lineWidth, 1.5, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, fontSize, 18, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(PlotAxis, x, PlotAxis("Time"));
AUTO_STRUCT_FIELD(PlotAxis, y, PlotAxis("Value"));
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotTicksX);
AUTO_STRUCT_FIELD(double, stride, 100, step_scale = 10, min = 10);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotTicksY);
AUTO_STRUCT_FIELD(double, stride, 100, step_scale = 10, min = 10);
AUTO_STRUCT_FIELD(double, width, 100, step_scale = 10, min = 10);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotTicks);
AUTO_STRUCT_FIELD(double, length, 10, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, width, 1.5, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, fontSize, 18, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(PlotTicksX, x);
AUTO_STRUCT_FIELD(PlotTicksY, y);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotTitle);
AUTO_STRUCT_FIELD(bool, enable, false);
AUTO_STRUCT_FIELD(std::string, text, "Title");
AUTO_STRUCT_FIELD(double, fontSize, 18, step_scale = 10, min = 0);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotGrid);
AUTO_STRUCT_FIELD(bool, enable, true);
AUTO_STRUCT_FIELD(double, width, 1.0);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotStyle);
AUTO_STRUCT_FIELD(PlotAxes, axes);
AUTO_STRUCT_FIELD(PlotMargins, margins);
AUTO_STRUCT_FIELD(PlotTicks, ticks);
AUTO_STRUCT_FIELD(double, frameWidth, 1.5, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, graphWidth, 1.5, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(double, padding, 5, step_scale = 10, min = 0);
AUTO_STRUCT_FIELD(Color3, backgroundColor, Color3(1, 1, 1));
AUTO_STRUCT_FIELD(Color3, foregroundColor, Color3(0, 0, 0));
AUTO_STRUCT_FIELD(PlotTitle, title);
AUTO_STRUCT_FIELD(PlotGrid, grid);
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotQuery);
AUTO_STRUCT_FIELD(MessageQueryProperty, query);
AUTO_STRUCT_FIELD(Color3, color, Color3(0, 0, 0));
AUTO_STRUCT_EXTRA(bool empty() const { return query.empty(); });
AUTO_STRUCT_END();

AUTO_STRUCT_BEGIN(PlotTopic);
AUTO_STRUCT_FIELD(std::string, topic, "", list = [](const Property &property) {
  return TopicManager::instance()->listTopics();
});
AUTO_STRUCT_FIELD(std::vector<PlotQuery>, queries);
AUTO_STRUCT_EXTRA(bool empty() const {
  return topic.empty() && (queries.size() == 0 ||
                           (queries.size() == 1 && queries.front().empty()));
});
AUTO_STRUCT_EXTRA(std::weak_ptr<TimeSeriesSubscriber> subscriber);
AUTO_STRUCT_END();

class PlotDisplay : public Display {

public:
  PlotDisplay() {}
  PROPERTY(double, duration, 10.0, min = 0.0);
  PROPERTY(std::vector<PlotTopic>, topics);
  PROPERTY(std::vector<double>, test, std::vector<double>({1.0, 2.0, 3.0}));
  PROPERTY(PlotStyle, style);
  template <class T> static void filterArray(std::vector<T> &data) {
    for (auto it = data.begin(); it + 1 < data.end();) {
      if (it->empty()) {
        it = data.erase(it);
      } else {
        ++it;
      }
    }
    if (data.empty() || !data.back().empty()) {
      data.emplace_back();
    }
  }
  virtual void refresh() override {
    filterArray(topics());
    for (auto &v : topics()) {
      filterArray(v.queries);
    }
  }
};
DECLARE_TYPE(PlotDisplay, Display);

class PlotRenderer {
  struct PlotRendererQuery {
    std::vector<std::pair<int64_t, double>> points;
    std::shared_ptr<TimeSeriesQuery> query;
    Color3 color;
  };
  struct PlotRendererTopic {
    std::shared_ptr<TimeSeriesSubscriber> subscriber;
    std::vector<PlotRendererQuery> queries;
    MessageParser parser;
  };
  struct PlotRendererData {
    std::shared_ptr<PlotDisplay> display;
    std::vector<PlotRendererTopic> topics;
    void update();
  };
  std::shared_ptr<PlotRendererData> _data =
      std::make_shared<PlotRendererData>();
  PlotStyle _style;
  double _duration = 1.0;
  std::vector<PlotRendererTopic> _topics_async;
  std::shared_ptr<BagPlayer> _bag_player;

public:
  std::shared_ptr<PlotDisplay> plotDisplay() const { return _data->display; }
  PlotRenderer(const std::shared_ptr<PlotDisplay> &display);
  void renderSync();
  void renderAsync(QPainter *painter);
};
