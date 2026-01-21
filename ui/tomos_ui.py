from core import tomos

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QProgressBar, QTabWidget, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem)
from PyQt6.QtGui import QPixmap, QColor, QImage

class TomoViewManager(QWidget):

    @staticmethod
    def get_tomos_view():
        my_tomos = tomos.UserTomos.get_user_tomos()
        return TomoViewManager(my_tomos)

    def __init__(self, tomos : tomos.UserTomos):
        super().__init__()

        self.tomos = tomos
        self.tomos.select_tomo(self.tomos.get_tomos()[0])

        self.view_layout = QVBoxLayout()
        self.setLayout(self.view_layout)

        self.sprite_view = TomoSpriteView(self)
        self.view_layout.addWidget(self.sprite_view)
        self.view_layout.setAlignment(self.sprite_view, Qt.AlignmentFlag.AlignCenter)

        self.tab_widget = QTabWidget()
        self.view_layout.addWidget(self.tab_widget)

        self.stat_view = TomoStatView(self)
        self.tab_widget.addTab(self.stat_view, f"{self.get_current_tomo().name}'s Stats")

        self.list_view = TomoListView(self)
        self.tab_widget.addTab(self.list_view, "Your Tomos")

        # testing sprite anim stuff -- eventually this will be triggered by fsm/events
        self.line_edit = QLineEdit()
        self.view_layout.addWidget(self.line_edit)
        # self.line_edit.returnPressed.connect(lambda : self.sprite_view.animator.update_sprite(self.line_edit.text()))

    def get_current_tomo(self):
        return self.tomos.current_tomo

    def quit_proc(self):
        self.tomos.update_tomos()

class TomoSpriteView(QGraphicsView):

    def __init__(self, manager : TomoViewManager):
        super().__init__()

        self.manager = manager

        self.frame_size = 200, 200
        self.setFixedSize(*self.frame_size)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        rect = self.rect()
        self.painter = TomoSpriteConstructor(rect.x(), rect.y(), rect.width(), rect.height())
        self.setScene(self.painter)

class TomoSpriteConstructor(QGraphicsScene):

    def __init__(self, rect_x : int, rect_y : int, rect_w : int, rect_h : int):
        super().__init__()

        self.setSceneRect(rect_x, rect_y, rect_w, rect_h)

        response_icon_size = (20, 20)
        self.response_icons = {"idle" : TomoSprite("green", response_icon_size), "playful" : TomoSprite("red", response_icon_size), "tired" : TomoSprite("blue", response_icon_size)}
        for sprite in self.response_icons.values():
            self.addItem(sprite)
            print(sprite.colour)
            sprite.setPos(150, 150)

    def set_tomo_sprite(self, tomo : tomos.Tomo):

        # this doesn't actually exist yet -- still need to implement backend sprite retrieval
        # sprite = tomo.get_base_stats()["sprite"]
        # TomoSprite(sprite)

        return

class TomoSprite(QGraphicsPixmapItem):

    def __init__(self, file_path : str, size : tuple[int, int] = None):
        super().__init__()

        self.colour = None
        self.size = size
        self.file_path = None

        if file_path in QColor.colorNames() and size:
            sprite_pixmap = QPixmap(*size)
            sprite_pixmap.fill(QColor(file_path))
            self.colour = file_path
        else:
            sprite_image = QImage(file_path)
            sprite_pixmap = QPixmap().fromImage(sprite_image)
            self.file_path = file_path

        self.setPixmap(sprite_pixmap)

class TomoStatView(QWidget):

    def __init__(self, manager : TomoViewManager):
        super().__init__()

        self.manager = manager

        self.stat_layout = QHBoxLayout()
        self.setLayout(self.stat_layout)

        self.hp_bar = QProgressBar()
        self.hp_bar.setFormat("HP: %v/%m")
        self.hp_bar.setMinimum(0)
        self.stat_layout.addWidget(self.hp_bar)

        self.xp_bar = QProgressBar()
        self.xp_bar.setFormat("XP: %v/%m")
        self.xp_bar.setMinimum(0)
        self.stat_layout.addWidget(self.xp_bar)

        self.update_stats()

    def update_stats(self):
        current_tomo = self.manager.get_current_tomo()
        if not current_tomo:
            return False
        base_stats = current_tomo.get_base_stats()

        self.hp_bar.setMaximum(base_stats["hp"])
        self.hp_bar.setValue(current_tomo.hp)

        self.xp_bar.setMaximum(base_stats["required_xp"])
        self.xp_bar.setValue(current_tomo.xp)

class TomoListView(QWidget):

    def __init__(self, manager : TomoViewManager):
        super().__init__()

        self.manager = manager

        self.view_layout = QHBoxLayout()
        self.setLayout(self.view_layout)