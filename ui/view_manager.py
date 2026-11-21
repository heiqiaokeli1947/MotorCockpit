"""ViewManager：页面注册、切换、事件分发（DESIGN §7.4）。"""
import lvgl as lv

from ui import theme


class ViewManager:
    # 切页事件映射：right/enc_cw 下一页，left/enc_ccw 上一页
    NEXT_EVENTS = ("right", "enc_cw")
    PREV_EVENTS = ("left", "enc_ccw")

    def __init__(self, app):
        self.app = app
        self.pages = []
        self.idx = 0
        self.current = None
        self._screen = None

    def register(self, page):
        self.pages.append(page)

    def start(self):
        self._screen = lv.obj()
        theme.apply_root(self._screen)
        lv.screen_load(self._screen)
        self.show(0)

    def show(self, idx):
        if idx < 0 or idx >= len(self.pages):
            return
        if self.current is not None:
            self.current.destroy()
        self.idx = idx
        self.current = self.pages[idx]
        self.current.build(self._screen)
        self._update_indicator()

    def next(self):
        self.show((self.idx + 1) % len(self.pages))

    def prev(self):
        self.show((self.idx - 1) % len(self.pages))

    def update(self):
        if self.current is not None:
            self.current.update()

    def dispatch(self, event):
        if event in self.NEXT_EVENTS:
            self.next()
            return True
        if event in self.PREV_EVENTS:
            self.prev()
            return True
        if self.current is not None:
            return self.current.on_event(event)
        return False

    def _update_indicator(self):
        """底部页面指示条由各页面自绘或由状态栏统一管理（M1 留空）。"""
        pass
