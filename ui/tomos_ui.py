from core import tomos, events

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QTabWidget, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QLabel, QScrollArea)
from PyQt6.QtGui import QPixmap, QColor, QImage

# relative to /core. useful for retrieving sprites
base_dir = tomos.base_dir

# manages the entire Tomo viewbox, handling events and interactions with the backend before passing into each of its children for displaying
class TomoViewManager(QWidget):

    @staticmethod
    def get_tomos_view():
        my_tomos = tomos.UserTomos.get_user_tomos()
        return TomoViewManager(my_tomos)

    def __init__(self, tomos : tomos.UserTomos):
        super().__init__()

        self.setWindowTitle("tomo | tomos")

        self.tomos = tomos
        self.tomos.select_tomo(self.tomos.get_tomos()[0])

        self.view_layout = QVBoxLayout()
        self.setLayout(self.view_layout)

        self.sprite_view = TomoSpriteView(self)
        self.view_layout.addWidget(self.sprite_view)
        self.view_layout.setAlignment(self.sprite_view, Qt.AlignmentFlag.AlignCenter)

        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)

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
        self.stat_update_event(self.tomos.current_tomo)

        events.tomo_topic.get_event("STATE_CHANGED").register(self.tomo_state_change_event)
        # ensures that the start state is represented as a response icon on startup
        self.tomo_state_change_event(self.tomos.current_tomo)

        self.fixed_size = self.sizeHint()
        self.setFixedSize(self.fixed_size)
        self.setMaximumSize(self.fixed_size)

    # updates the tomo stats on occurence of either of the stat_update_events
    def stat_update_event(self, tomo : tomos.Tomo):
        self.stat_view.update_stats(tomo.get_base_stats(), tomo.hp, tomo.xp, tomo.bond_level)
        self.sprite_view.update_sprite(tomo.get_base_stats()["sprite_path"])

    # behaviours that occur on the change of a state in the fsm
    def tomo_state_change_event(self, tomo : tomos.Tomo):
        state = tomo.fsm.current_state
        print(f"TOMO UI: current tomo state: {state.name}")
        # whenever the same state is executed again, it will activate its correct response icon
        # remember that by default the state's name is passed as argument into callback
        self.sprite_view.activate_response_icon(state.name)
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

    def update_sprite(self, sprite_path : str):
        print(f"TOMO UI: updating sprite")
        self.painter.set_tomo_sprite(sprite_path)

# constructs the scene by creating and adopting TomoSprite objects -- choosing what is displayed and where
class TomoSpriteConstructor(QGraphicsScene):

    def __init__(self, rect_x : int, rect_y : int, rect_w : int, rect_h : int):
        super().__init__()

        self.setSceneRect(rect_x, rect_y, rect_w, rect_h)

        response_icon_size = (30, 30)
        response_icon_pos = 200 - response_icon_size[0], 0

        self.response_icons = {"idle" : ResponseIcon("idle", "grey", response_icon_size), "happy": ResponseIcon("happy", "green", response_icon_size), "playful" : ResponseIcon("playful", "pink", response_icon_size),
                               "proud" : ResponseIcon("proud", "yellow", response_icon_size), "relieved" : ResponseIcon("relieved", "orange", response_icon_size), "tired" : ResponseIcon("tired", "blue", response_icon_size)}
        for icon in self.response_icons.values():
            icon.setPos(*response_icon_pos)
            self.addItem(icon)

        self.tomo_sprite = None

    # activates one specific response icon depending on the tomo state passed into method
    def activate_response_icon(self, tomo_state : str):
        for icon_name in self.response_icons:
            visible = icon_name == tomo_state
            self.response_icons[icon_name].setVisible(visible)

    # sets the tomo sprite to the screen
    def set_tomo_sprite(self, sprite_path : str):

        if self.tomo_sprite:
            self.removeItem(self.tomo_sprite)

        tomo_sprite_size = 250, 250
        sprite_pos = 100, 100

        self.tomo_sprite = TomoSprite(sprite_path)

        original_size = self.tomo_sprite.boundingRect().size().width(), self.tomo_sprite.boundingRect().size().height()

        scale = tomo_sprite_size[0] / original_size[0]
        self.tomo_sprite.setScale(scale)

        scaled_size = self.tomo_sprite.boundingRect().size().width(), self.tomo_sprite.boundingRect().size().height()

        self.tomo_sprite.setOffset(scaled_size[0] / -2, scaled_size[1] / -2)
        self.tomo_sprite.setPos(*sprite_pos)

        self.addItem(self.tomo_sprite)
        self.tomo_sprite.setVisible(True)

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
            actual_file_path = base_dir / file_path
            if not actual_file_path.is_file():
                raise FileExistsError(f"TOMO UI: Invalid file path for TomoSprite: {actual_file_path}")
            sprite_image = QImage(str(actual_file_path))
            sprite_pixmap = QPixmap().fromImage(sprite_image)
            self.file_path = actual_file_path

        self.setPixmap(sprite_pixmap)
        self.setVisible(False)

# icons representing the current state of the user's Tomo
class ResponseIcon(TomoSprite):

    def __init__(self, icon_name : str, file_path : str, size : tuple[int, int] = None, description : str = None):
        super().__init__(file_path, size)

        self.description = description
        if not self.description:
            self.description = f"Your Tomo is <b>{icon_name}</b>."

        self.tool_tip = QLabel()
        self.tool_tip.setWindowFlag(Qt.WindowType.ToolTip, True)

        self.setAcceptHoverEvents(True)

    # shows the tooltip as soon as mouse enters responseicon
    def hoverMoveEvent(self, event):

        pos = event.screenPos()
        # prevents clipping of mouse and the tooltip itself
        pos.setY(pos.y() + 20)
        self.tool_tip.move(pos)
        self.tool_tip.setText(self.description)

        if self.tool_tip.isHidden():
            self.tool_tip.show()

        return super().hoverMoveEvent(event)

    # hide tooltip as soon as mouse leaves
    def hoverLeaveEvent(self, event):

        self.tool_tip.hide()

        return super().hoverLeaveEvent(event)

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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)