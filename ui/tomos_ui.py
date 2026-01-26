from core import tomos, events

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QProgressBar, QTabWidget, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QLabel)
from PyQt6.QtGui import QPixmap, QColor, QImage

# manages the entire Tomo viewbox, handling events and interactions with the backend before passing into each of its children for displaying
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
        self.tab_widget.addTab(self.stat_view, f"{self.tomos.current_tomo.name}'s Stats")

        # on completion of either the XP_INCREASED or LVL_INCREASED events in the tomo topic, the stat view is updated
        for event in events.tomo_topic.get_events("XP_INCREASED", "LVL_INCREASED"):
            event.register(self.stat_update_event)

        self.list_view = TomoListView(self)
        self.tab_widget.addTab(self.list_view, "Your Tomos")

        self.sprite_view.display_view()
        self.stat_view.update_stats(self.tomos.current_tomo.get_base_stats(), self.tomos.current_tomo.hp, self.tomos.current_tomo.xp, self.tomos.current_tomo.bond_level)

        events.tomo_topic.get_event("STATE_CHANGED").register(self.tomo_state_change_event)

    # updates the tomo stats on occurence of either of the stat_update_events
    def stat_update_event(self, tomo : tomos.Tomo):
        self.stat_view.update_stats(tomo.get_base_stats(), tomo.hp, tomo.xp, tomo.bond_level)

    # behaviours that occur on the change of a state in the fsm
    def tomo_state_change_event(self, tomo : tomos.Tomo):
        state = tomo.fsm.current_state
        print(f"TOMO UI: current tomo state: {state.name}")
        # whenever the same state is executed again, it will activate its correct response icon
        # remember that by default the state's name is passed as argument into callback
        self.sprite_view.activate_response_icon(state.name  )
        state.set_callback(self.sprite_view.activate_response_icon)

    # what happens on quit of this window/widget
    def quit_proc(self):
        self.tomos.update_tomos()

# displays sprites in the scene according to the TomoSpriteConstructor (self.painter)
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

    def display_view(self):
        self.setScene(self.painter)

    def activate_response_icon(self, tomo_state : str):
        print(f"TOMO UI: activating response icon for {tomo_state}")
        self.painter.activate_response_icon(tomo_state)

# constructs the scene by creating and adopting TomoSprite objects -- choosing what is displayed and where
class TomoSpriteConstructor(QGraphicsScene):

    def __init__(self, rect_x : int, rect_y : int, rect_w : int, rect_h : int):
        super().__init__()

        self.setSceneRect(rect_x, rect_y, rect_w, rect_h)

        response_icon_size = (20, 20)
        self.response_icons = {"idle" : TomoSprite("green", response_icon_size), "playful" : TomoSprite("red", response_icon_size), "tired" : TomoSprite("blue", response_icon_size)}
        for sprite in self.response_icons.values():
            self.addItem(sprite)

    # activates one specific response icon depending on the tomo state passed into method
    def activate_response_icon(self, tomo_state : str):
        for icon_name in self.response_icons:
            visible = icon_name == tomo_state
            self.response_icons[icon_name].setVisible(visible)

    def set_tomo_sprite(self, tomo : tomos.Tomo):

        # this doesn't actually exist yet -- still need to implement backend sprite retrieval
        # sprite = tomo.get_base_stats()["sprite"]
        # TomoSprite(sprite)

        return

# an object that is a member of the TomoSpriteConstructor's scene -- can be drawn to the TomoSpriteView
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
        self.setVisible(False)

# overviews the stats of the currently selected Tomo
class TomoStatView(QWidget):

    def __init__(self, manager : TomoViewManager):
        super().__init__()

        self.manager = manager

        self.stat_layout = QVBoxLayout()
        self.setLayout(self.stat_layout)
        self.stat_layout.setSpacing(0)
        self.setContentsMargins(11, 0, 11, 0)

        self.bond_level = QProgressBar()
        self.bond_level.setFormat("BOND LVL: %v")
        self.bond_level.setMinimum(1)
        # you can think about centering this later in css -- windows 11 styling doesnt support centering or thick bars
        # self.bond_level.setStyleSheet('text-align: center')
        # or
        # self.bond_level.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stat_layout.addWidget(self.bond_level)

        self.bottom_stats = QWidget()
        self.bottom_stats_layout = QHBoxLayout()
        self.bottom_stats.setLayout(self.bottom_stats_layout)

        self.hp_bar = QProgressBar()
        self.hp_bar.setFormat("HP: %v/%m")
        self.hp_bar.setMinimum(0)
        self.bottom_stats_layout.addWidget(self.hp_bar)

        self.xp_bar = QProgressBar()
        self.xp_bar.setFormat("XP: %v/%m")
        self.xp_bar.setMinimum(0)
        self.bottom_stats_layout.addWidget(self.xp_bar)

        self.stat_layout.addWidget(self.bottom_stats)

    # updates the each tomo stat in the view
    def update_stats(self, base_stats : dict, hp : int, xp : int, bond_lvl : int):

        self.bond_level.setMaximum(len(base_stats) + 1)
        self.bond_level.setValue(bond_lvl)

        self.hp_bar.setMaximum(base_stats["hp"])
        self.hp_bar.setValue(hp)

        self.xp_bar.setMaximum(base_stats["required_xp"])
        self.xp_bar.setValue(xp)

# overviews all of the non-selected Tomos that the user owns
class TomoListView(QWidget):

    def __init__(self, manager : TomoViewManager):
        super().__init__()

        self.manager = manager

        self.view_layout = QHBoxLayout()
        self.setLayout(self.view_layout)