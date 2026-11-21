"""Page 基类：所有页面继承它，实现 build/update/on_event/destroy。"""
import lvgl as lv


class Page:
    name = "base"

    def __init__(self, app):
        self.app = app
        self._root = None

    @property
    def bus(self):
        return self.app.bus

    @property
    def settings(self):
        return self.app.settings

    def build(self, parent):
        """创建页面控件。返回根容器。"""
        self._root = lv.obj(parent)
        from ui import theme
        theme.apply_root(self._root)
        return self._root

    def update(self):
        """每个 UI 刷新周期调用，从 DataBus 读数据刷新控件。"""
        pass

    def on_event(self, event):
        """处理标准输入事件，返回 True 表示已消费。"""
        return False

    def destroy(self):
        if self._root is not None:
            self._root.delete()
            self._root = None
