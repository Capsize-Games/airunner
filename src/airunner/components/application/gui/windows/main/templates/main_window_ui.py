# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)
from airunner.components.art.gui.widgets.generator_form.generator_form_widget import (
    GeneratorForm,
)
from airunner.components.browser.gui.widgets.browser_widget import (
    BrowserWidget,
)
from airunner.components.document_editor.gui.widgets.document_editor_container_widget import (
    DocumentEditorContainerWidget,
)
from airunner.components.documents.gui.widgets.documents import DocumentsWidget
from airunner.components.home_stage.gui.widgets.home_stage_widget import (
    HomeStageWidget,
)
from airunner.components.map.gui.widgets.map_widget import MapWidget
from airunner.components.nodegraph.gui.widgets.node_graph_widget import (
    NodeGraphWidget,
)
from airunner.components.voice_visualizer.gui.widgets.voice_visualizer_widget import (
    VoiceVisualizerWidget,
)
from airunner.components.weather.gui.widgets.weather_widget import (
    WeatherWidget,
)
import airunner.feather_rc


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1074, 760)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            MainWindow.sizePolicy().hasHeightForWidth()
        )
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QSize(0, 0))
        font = QFont()
        font.setPointSize(8)
        MainWindow.setFont(font)
        icon = QIcon()
        icon.addFile(
            ":/icons/icon_256.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off
        )
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet("")
        self.actionCopy = QAction(MainWindow)
        self.actionCopy.setObjectName("actionCopy")
        icon1 = QIcon()
        icon1.addFile(
            ":/light/icons/feather/light/copy.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionCopy.setIcon(icon1)
        self.actionPaste = QAction(MainWindow)
        self.actionPaste.setObjectName("actionPaste")
        icon2 = QIcon()
        icon2.addFile(
            ":/light/icons/feather/light/clipboard.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionPaste.setIcon(icon2)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        icon3 = QIcon()
        icon3.addFile(
            ":/light/icons/feather/light/x-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionQuit.setIcon(icon3)
        self.actionBug_report = QAction(MainWindow)
        self.actionBug_report.setObjectName("actionBug_report")
        icon4 = QIcon()
        icon4.addFile(
            ":/light/icons/feather/light/external-link.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionBug_report.setIcon(icon4)
        self.actionReport_vulnerability = QAction(MainWindow)
        self.actionReport_vulnerability.setObjectName(
            "actionReport_vulnerability"
        )
        self.actionReport_vulnerability.setIcon(icon4)
        self.actionPrompt_Browser = QAction(MainWindow)
        self.actionPrompt_Browser.setObjectName("actionPrompt_Browser")
        icon5 = QIcon()
        icon5.addFile(
            ":/light/icons/feather/light/book-open.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionPrompt_Browser.setIcon(icon5)
        self.actionClear_all_prompts = QAction(MainWindow)
        self.actionClear_all_prompts.setObjectName("actionClear_all_prompts")
        icon6 = QIcon()
        icon6.addFile(
            ":/light/icons/feather/light/delete.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionClear_all_prompts.setIcon(icon6)
        self.actionCut = QAction(MainWindow)
        self.actionCut.setObjectName("actionCut")
        icon7 = QIcon()
        icon7.addFile(
            ":/light/icons/feather/light/scissors.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionCut.setIcon(icon7)
        self.actionBrowse_AI_Runner_Path = QAction(MainWindow)
        self.actionBrowse_AI_Runner_Path.setObjectName(
            "actionBrowse_AI_Runner_Path"
        )
        icon8 = QIcon()
        icon8.addFile(
            ":/light/icons/feather/light/folder.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionBrowse_AI_Runner_Path.setIcon(icon8)
        self.actionBrowse_Images_Path_2 = QAction(MainWindow)
        self.actionBrowse_Images_Path_2.setObjectName(
            "actionBrowse_Images_Path_2"
        )
        self.actionBrowse_Images_Path_2.setIcon(icon8)
        self.actionReset_Settings_2 = QAction(MainWindow)
        self.actionReset_Settings_2.setObjectName("actionReset_Settings_2")
        icon9 = QIcon()
        icon9.addFile(
            ":/light/icons/feather/light/refresh-cw.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionReset_Settings_2.setIcon(icon9)
        self.actionSafety_Checker = QAction(MainWindow)
        self.actionSafety_Checker.setObjectName("actionSafety_Checker")
        self.actionSafety_Checker.setCheckable(True)
        self.actionSafety_Checker.setChecked(False)
        icon10 = QIcon()
        icon10.addFile(
            ":/light/icons/feather/light/slash.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionSafety_Checker.setIcon(icon10)
        self.actionRun_setup_wizard_2 = QAction(MainWindow)
        self.actionRun_setup_wizard_2.setObjectName("actionRun_setup_wizard_2")
        icon11 = QIcon()
        icon11.addFile(
            ":/light/icons/feather/light/zap.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionRun_setup_wizard_2.setIcon(icon11)
        self.actionStats = QAction(MainWindow)
        self.actionStats.setObjectName("actionStats")
        icon12 = QIcon()
        icon12.addFile(
            ":/light/icons/feather/light/activity.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionStats.setIcon(icon12)
        self.actionSettings = QAction(MainWindow)
        self.actionSettings.setObjectName("actionSettings")
        icon13 = QIcon()
        icon13.addFile(
            ":/light/icons/feather/light/settings.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionSettings.setIcon(icon13)
        self.actionToggle_LLM = QAction(MainWindow)
        self.actionToggle_LLM.setObjectName("actionToggle_LLM")
        self.actionToggle_LLM.setCheckable(True)
        self.actionToggle_LLM.setChecked(False)
        icon14 = QIcon()
        icon14.addFile(
            ":/light/icons/feather/light/cpu.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionToggle_LLM.setIcon(icon14)
        self.actionToggle_Text_to_Speech = QAction(MainWindow)
        self.actionToggle_Text_to_Speech.setObjectName(
            "actionToggle_Text_to_Speech"
        )
        self.actionToggle_Text_to_Speech.setCheckable(True)
        icon15 = QIcon()
        icon15.addFile(
            ":/light/icons/feather/light/speaker.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionToggle_Text_to_Speech.setIcon(icon15)
        self.actionToggle_Speech_to_Text = QAction(MainWindow)
        self.actionToggle_Speech_to_Text.setObjectName(
            "actionToggle_Speech_to_Text"
        )
        self.actionToggle_Speech_to_Text.setCheckable(True)
        icon16 = QIcon()
        icon16.addFile(
            ":/light/icons/feather/light/mic.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionToggle_Speech_to_Text.setIcon(icon16)
        self.actionToggle_Stable_Diffusion = QAction(MainWindow)
        self.actionToggle_Stable_Diffusion.setObjectName(
            "actionToggle_Stable_Diffusion"
        )
        self.actionToggle_Stable_Diffusion.setCheckable(True)
        icon17 = QIcon()
        icon17.addFile(
            ":/light/icons/feather/light/image.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionToggle_Stable_Diffusion.setIcon(icon17)
        self.actionToggle_Controlnet = QAction(MainWindow)
        self.actionToggle_Controlnet.setObjectName("actionToggle_Controlnet")
        self.actionToggle_Controlnet.setCheckable(True)
        self.actionToggle_Controlnet.setChecked(False)
        icon18 = QIcon()
        icon18.addFile(
            ":/light/icons/feather/light/crosshair.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionToggle_Controlnet.setIcon(icon18)
        self.artActionNew = QAction(MainWindow)
        self.artActionNew.setObjectName("artActionNew")
        icon19 = QIcon()
        icon19.addFile(
            ":/light/icons/feather/light/plus-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.artActionNew.setIcon(icon19)
        self.actionImport_image = QAction(MainWindow)
        self.actionImport_image.setObjectName("actionImport_image")
        icon20 = QIcon()
        icon20.addFile(
            ":/light/icons/feather/light/download.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionImport_image.setIcon(icon20)
        self.actionExport_image_button = QAction(MainWindow)
        self.actionExport_image_button.setObjectName(
            "actionExport_image_button"
        )
        icon21 = QIcon()
        icon21.addFile(
            ":/light/icons/feather/light/upload.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionExport_image_button.setIcon(icon21)
        self.actionNew_Conversation = QAction(MainWindow)
        self.actionNew_Conversation.setObjectName("actionNew_Conversation")
        icon22 = QIcon()
        icon22.addFile(
            ":/light/icons/feather/light/message-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionNew_Conversation.setIcon(icon22)
        self.actionDelete_conversation = QAction(MainWindow)
        self.actionDelete_conversation.setObjectName(
            "actionDelete_conversation"
        )
        icon23 = QIcon()
        icon23.addFile(
            ":/light/icons/feather/light/trash-2.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionDelete_conversation.setIcon(icon23)
        self.actionDiscord = QAction(MainWindow)
        self.actionDiscord.setObjectName("actionDiscord")
        icon24 = QIcon()
        icon24.addFile(
            ":/light/icons/feather/light/message-square.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.actionDiscord.setIcon(icon24)
        self.workflow_actionRun = QAction(MainWindow)
        self.workflow_actionRun.setObjectName("workflow_actionRun")
        icon25 = QIcon()
        icon25.addFile(
            ":/light/icons/feather/light/play.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_actionRun.setIcon(icon25)
        self.workflow_actionPause = QAction(MainWindow)
        self.workflow_actionPause.setObjectName("workflow_actionPause")
        icon26 = QIcon()
        icon26.addFile(
            ":/light/icons/feather/light/pause-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_actionPause.setIcon(icon26)
        self.workflow_actionStop = QAction(MainWindow)
        self.workflow_actionStop.setObjectName("workflow_actionStop")
        icon27 = QIcon()
        icon27.addFile(
            ":/light/icons/feather/light/stop-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_actionStop.setIcon(icon27)
        self.workflow_actionSave = QAction(MainWindow)
        self.workflow_actionSave.setObjectName("workflow_actionSave")
        icon28 = QIcon()
        icon28.addFile(
            ":/light/icons/feather/light/save.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_actionSave.setIcon(icon28)
        self.workflow_actionClear = QAction(MainWindow)
        self.workflow_actionClear.setObjectName("workflow_actionClear")
        self.workflow_actionClear.setIcon(icon23)
        self.workflow_actionEdit = QAction(MainWindow)
        self.workflow_actionEdit.setObjectName("workflow_actionEdit")
        icon29 = QIcon()
        icon29.addFile(
            ":/light/icons/feather/light/edit.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_actionEdit.setIcon(icon29)
        self.workflow_actionOpen = QAction(MainWindow)
        self.workflow_actionOpen.setObjectName("workflow_actionOpen")
        self.workflow_actionOpen.setIcon(icon8)
        self.actionSave_As = QAction(MainWindow)
        self.actionSave_As.setObjectName("actionSave_As")
        self.actionSave_As.setIcon(icon28)
        self.actionDownload_Model = QAction(MainWindow)
        self.actionDownload_Model.setObjectName("actionDownload_Model")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setEnabled(True)
        sizePolicy1 = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.centralwidget.sizePolicy().hasHeightForWidth()
        )
        self.centralwidget.setSizePolicy(sizePolicy1)
        self.centralwidget.setMinimumSize(QSize(0, 0))
        self.centralwidget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.gridLayout_3 = QGridLayout(self.centralwidget)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.mode_tab_widget = QWidget(self.centralwidget)
        self.mode_tab_widget.setObjectName("mode_tab_widget")
        self.mode_tab_widget.setAutoFillBackground(False)
        self.mode_tab_widget.setStyleSheet(
            "QTabWidget#mode_tab_widget::pane { border: 0; background: transparent; }"
        )
        self.gridLayout_9 = QGridLayout(self.mode_tab_widget)
        self.gridLayout_9.setSpacing(0)
        self.gridLayout_9.setObjectName("gridLayout_9")
        self.gridLayout_9.setContentsMargins(0, 0, 0, 0)
        self.actionsidebar = QWidget(self.mode_tab_widget)
        self.actionsidebar.setObjectName("actionsidebar")
        self.action_sidebar = QVBoxLayout(self.actionsidebar)
        self.action_sidebar.setSpacing(5)
        self.action_sidebar.setObjectName("action_sidebar")
        self.action_sidebar.setContentsMargins(5, 5, 5, 5)
        self.home_button = QPushButton(self.actionsidebar)
        self.home_button.setObjectName("home_button")
        self.home_button.setMinimumSize(QSize(35, 35))
        self.home_button.setMaximumSize(QSize(35, 35))
        icon30 = QIcon()
        icon30.addFile(
            ":/light/icons/feather/light/home.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.home_button.setIcon(icon30)
        self.home_button.setIconSize(QSize(20, 20))
        self.home_button.setCheckable(True)
        self.home_button.setChecked(True)
        self.home_button.setFlat(True)

        self.action_sidebar.addWidget(self.home_button)

        self.art_editor_button = QPushButton(self.actionsidebar)
        self.art_editor_button.setObjectName("art_editor_button")
        self.art_editor_button.setMinimumSize(QSize(35, 35))
        self.art_editor_button.setMaximumSize(QSize(35, 35))
        self.art_editor_button.setBaseSize(QSize(0, 0))
        self.art_editor_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.art_editor_button.setIcon(icon17)
        self.art_editor_button.setIconSize(QSize(20, 20))
        self.art_editor_button.setCheckable(True)
        self.art_editor_button.setChecked(False)
        self.art_editor_button.setFlat(True)

        self.action_sidebar.addWidget(self.art_editor_button)

        self.workflow_editor_button = QPushButton(self.actionsidebar)
        self.workflow_editor_button.setObjectName("workflow_editor_button")
        self.workflow_editor_button.setMinimumSize(QSize(35, 35))
        self.workflow_editor_button.setMaximumSize(QSize(35, 35))
        self.workflow_editor_button.setBaseSize(QSize(0, 0))
        self.workflow_editor_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        icon31 = QIcon()
        icon31.addFile(
            ":/light/icons/feather/light/codesandbox.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.workflow_editor_button.setIcon(icon31)
        self.workflow_editor_button.setIconSize(QSize(20, 20))
        self.workflow_editor_button.setCheckable(True)
        self.workflow_editor_button.setFlat(True)

        self.action_sidebar.addWidget(self.workflow_editor_button)

        self.browser_button = QPushButton(self.actionsidebar)
        self.browser_button.setObjectName("browser_button")
        self.browser_button.setMinimumSize(QSize(35, 35))
        self.browser_button.setMaximumSize(QSize(35, 35))
        self.browser_button.setBaseSize(QSize(0, 0))
        self.browser_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        icon32 = QIcon()
        icon32.addFile(
            ":/light/icons/feather/light/chrome.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.browser_button.setIcon(icon32)
        self.browser_button.setIconSize(QSize(20, 20))
        self.browser_button.setCheckable(True)
        self.browser_button.setFlat(True)

        self.action_sidebar.addWidget(self.browser_button)

        self.document_editor_button = QPushButton(self.actionsidebar)
        self.document_editor_button.setObjectName("document_editor_button")
        self.document_editor_button.setMinimumSize(QSize(35, 35))
        self.document_editor_button.setMaximumSize(QSize(35, 35))
        self.document_editor_button.setBaseSize(QSize(0, 0))
        self.document_editor_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        icon33 = QIcon()
        icon33.addFile(
            ":/light/icons/feather/light/file-text.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.document_editor_button.setIcon(icon33)
        self.document_editor_button.setIconSize(QSize(20, 20))
        self.document_editor_button.setCheckable(True)
        self.document_editor_button.setFlat(True)

        self.action_sidebar.addWidget(self.document_editor_button)

        self.map_button = QPushButton(self.actionsidebar)
        self.map_button.setObjectName("map_button")
        self.map_button.setMinimumSize(QSize(35, 35))
        self.map_button.setMaximumSize(QSize(35, 35))
        self.map_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon34 = QIcon()
        icon34.addFile(
            ":/light/icons/feather/light/map.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.map_button.setIcon(icon34)
        self.map_button.setIconSize(QSize(17, 17))
        self.map_button.setCheckable(True)
        self.map_button.setFlat(True)

        self.action_sidebar.addWidget(self.map_button)

        self.weather_button = QPushButton(self.actionsidebar)
        self.weather_button.setObjectName("weather_button")
        self.weather_button.setMinimumSize(QSize(35, 35))
        self.weather_button.setMaximumSize(QSize(35, 35))
        self.weather_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        icon35 = QIcon()
        icon35.addFile(
            ":/light/icons/feather/light/sun.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.weather_button.setIcon(icon35)
        self.weather_button.setIconSize(QSize(20, 20))
        self.weather_button.setCheckable(True)
        self.weather_button.setFlat(True)

        self.action_sidebar.addWidget(self.weather_button)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.action_sidebar.addItem(self.verticalSpacer)

        self.visualizer_button = QPushButton(self.actionsidebar)
        self.visualizer_button.setObjectName("visualizer_button")
        self.visualizer_button.setMinimumSize(QSize(35, 35))
        self.visualizer_button.setMaximumSize(QSize(35, 35))
        icon36 = QIcon()
        icon36.addFile(
            ":/dark/icons/feather/dark/radio.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.visualizer_button.setIcon(icon36)
        self.visualizer_button.setIconSize(QSize(20, 20))
        self.visualizer_button.setCheckable(True)
        self.visualizer_button.setFlat(True)

        self.action_sidebar.addWidget(self.visualizer_button)

        self.chat_button = QPushButton(self.actionsidebar)
        self.chat_button.setObjectName("chat_button")
        self.chat_button.setMinimumSize(QSize(35, 35))
        self.chat_button.setMaximumSize(QSize(35, 35))
        self.chat_button.setIcon(icon24)
        self.chat_button.setIconSize(QSize(20, 20))
        self.chat_button.setCheckable(True)
        self.chat_button.setChecked(True)
        self.chat_button.setFlat(True)

        self.action_sidebar.addWidget(self.chat_button)

        self.settings_button = QPushButton(self.actionsidebar)
        self.settings_button.setObjectName("settings_button")
        self.settings_button.setMinimumSize(QSize(35, 35))
        self.settings_button.setMaximumSize(QSize(35, 35))
        self.settings_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.settings_button.setIcon(icon13)
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setFlat(True)

        self.action_sidebar.addWidget(self.settings_button)

        self.gridLayout_9.addWidget(self.actionsidebar, 0, 0, 1, 1)

        self.main_window_splitter = QSplitter(self.mode_tab_widget)
        self.main_window_splitter.setObjectName("main_window_splitter")
        self.main_window_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.generator_widget = GeneratorForm(self.main_window_splitter)
        self.generator_widget.setObjectName("generator_widget")
        self.generator_widget.setEnabled(True)
        sizePolicy1.setHeightForWidth(
            self.generator_widget.sizePolicy().hasHeightForWidth()
        )
        self.generator_widget.setSizePolicy(sizePolicy1)
        self.generator_widget.setMinimumSize(QSize(250, 0))
        self.generator_widget.setMaximumSize(QSize(16777215, 16777215))
        self.generator_widget.setBaseSize(QSize(250, 0))
        self.gridLayout_6 = QGridLayout(self.generator_widget)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.main_window_splitter.addWidget(self.generator_widget)
        self.center_widget = QWidget(self.main_window_splitter)
        self.center_widget.setObjectName("center_widget")
        sizePolicy1.setHeightForWidth(
            self.center_widget.sizePolicy().hasHeightForWidth()
        )
        self.center_widget.setSizePolicy(sizePolicy1)
        self.center_widget.setMinimumSize(QSize(64, 0))
        self.gridLayout_4 = QGridLayout(self.center_widget)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.center_tab_container = QTabWidget(self.center_widget)
        self.center_tab_container.setObjectName("center_tab_container")
        sizePolicy2 = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(
            self.center_tab_container.sizePolicy().hasHeightForWidth()
        )
        self.center_tab_container.setSizePolicy(sizePolicy2)
        self.center_tab_container.setBaseSize(QSize(0, 0))
        self.center_tab_container.setDocumentMode(False)
        self.center_tab_container.setTabsClosable(False)
        self.center_tab_container.setMovable(False)
        self.home_tab = QWidget()
        self.home_tab.setObjectName("home_tab")
        self.gridLayout_8 = QGridLayout(self.home_tab)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.gridLayout_8.setContentsMargins(0, 0, 0, 0)
        self.home_stage = HomeStageWidget(self.home_tab)
        self.home_stage.setObjectName("home_stage")

        self.gridLayout_8.addWidget(self.home_stage, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.home_tab, "")
        self.art_tab = QWidget()
        self.art_tab.setObjectName("art_tab")
        self.gridLayout_2 = QGridLayout(self.art_tab)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.canvas = CanvasWidget(self.art_tab)
        self.canvas.setObjectName("canvas")
        sizePolicy2.setHeightForWidth(
            self.canvas.sizePolicy().hasHeightForWidth()
        )
        self.canvas.setSizePolicy(sizePolicy2)
        self.canvas.setMinimumSize(QSize(0, 0))
        self.canvas.setMaximumSize(QSize(16777215, 16777215))
        self.canvas.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.canvas.setAcceptDrops(True)

        self.gridLayout_2.addWidget(self.canvas, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.art_tab, "")
        self.agent_workflow_tab = QWidget()
        self.agent_workflow_tab.setObjectName("agent_workflow_tab")
        self.gridLayout_5 = QGridLayout(self.agent_workflow_tab)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.graph = NodeGraphWidget(self.agent_workflow_tab)
        self.graph.setObjectName("graph")

        self.gridLayout_5.addWidget(self.graph, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.agent_workflow_tab, "")
        self.browser_tab = QWidget()
        self.browser_tab.setObjectName("browser_tab")
        self.gridLayout_7 = QGridLayout(self.browser_tab)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.browser = QTabWidget(self.browser_tab)
        self.browser.setObjectName("browser")
        self.browser.setMovable(True)
        self.browser_page = BrowserWidget()
        self.browser_page.setObjectName("browser_page")
        self.browser.addTab(self.browser_page, "")

        self.gridLayout_7.addWidget(self.browser, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.browser_tab, "")
        self.document_editor_tab = QWidget()
        self.document_editor_tab.setObjectName("document_editor_tab")
        self.gridLayout = QGridLayout(self.document_editor_tab)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget = DocumentEditorContainerWidget(self.document_editor_tab)
        self.widget.setObjectName("widget")

        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.document_editor_tab, "")
        self.map_tab = QWidget()
        self.map_tab.setObjectName("map_tab")
        self.gridLayout_12 = QGridLayout(self.map_tab)
        self.gridLayout_12.setObjectName("gridLayout_12")
        self.gridLayout_12.setContentsMargins(0, 0, 0, 0)
        self.map = MapWidget(self.map_tab)
        self.map.setObjectName("map")

        self.gridLayout_12.addWidget(self.map, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.map_tab, "")
        self.weather_tab = QWidget()
        self.weather_tab.setObjectName("weather_tab")
        self.gridLayout_13 = QGridLayout(self.weather_tab)
        self.gridLayout_13.setObjectName("gridLayout_13")
        self.gridLayout_13.setContentsMargins(0, 0, 0, 0)
        self.weather = WeatherWidget(self.weather_tab)
        self.weather.setObjectName("weather")

        self.gridLayout_13.addWidget(self.weather, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.weather_tab, "")
        self.visualizer_tab = QWidget()
        self.visualizer_tab.setObjectName("visualizer_tab")
        self.gridLayout_14 = QGridLayout(self.visualizer_tab)
        self.gridLayout_14.setObjectName("gridLayout_14")
        self.gridLayout_14.setContentsMargins(0, 0, 0, 0)
        self.visualizer = VoiceVisualizerWidget(self.visualizer_tab)
        self.visualizer.setObjectName("visualizer")

        self.gridLayout_14.addWidget(self.visualizer, 0, 0, 1, 1)

        self.center_tab_container.addTab(self.visualizer_tab, "")

        self.gridLayout_4.addWidget(self.center_tab_container, 0, 0, 1, 1)

        self.main_window_splitter.addWidget(self.center_widget)
        self.knowledgebase = QWidget(self.main_window_splitter)
        self.knowledgebase.setObjectName("knowledgebase")
        self.gridLayout_10 = QGridLayout(self.knowledgebase)
        self.gridLayout_10.setObjectName("gridLayout_10")
        self.gridLayout_10.setContentsMargins(0, 0, 0, 0)
        self.splitter_2 = QSplitter(self.knowledgebase)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Vertical)
        self.documents_container = QWidget(self.splitter_2)
        self.documents_container.setObjectName("documents_container")
        self.gridLayout_11 = QGridLayout(self.documents_container)
        self.gridLayout_11.setObjectName("gridLayout_11")
        self.gridLayout_11.setContentsMargins(0, 0, 0, 0)
        self.documents = DocumentsWidget(self.documents_container)
        self.documents.setObjectName("documents")

        self.gridLayout_11.addWidget(self.documents, 0, 0, 1, 1)

        self.splitter_2.addWidget(self.documents_container)
        self.widget_3 = QWidget(self.splitter_2)
        self.widget_3.setObjectName("widget_3")
        self.splitter_2.addWidget(self.widget_3)

        self.gridLayout_10.addWidget(self.splitter_2, 0, 0, 1, 1)

        self.main_window_splitter.addWidget(self.knowledgebase)

        self.gridLayout_9.addWidget(self.main_window_splitter, 0, 1, 1, 1)

        self.gridLayout_3.addWidget(self.mode_tab_widget, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1074, 23))
        font1 = QFont()
        font1.setPointSize(11)
        self.menubar.setFont(font1)
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuFile.setTearOffEnabled(False)
        self.menuFile.setSeparatorsCollapsible(False)
        self.menuArt = QMenu(self.menuFile)
        self.menuArt.setObjectName("menuArt")
        self.menuArt.setIcon(icon17)
        self.menuChat = QMenu(self.menuFile)
        self.menuChat.setObjectName("menuChat")
        self.menuChat.setIcon(icon22)
        self.menuWorkflow = QMenu(self.menuFile)
        self.menuWorkflow.setObjectName("menuWorkflow")
        self.menuWorkflow.setIcon(icon31)
        self.menuEdit = QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuFilters = QMenu(self.menubar)
        self.menuFilters.setObjectName("menuFilters")
        self.menuAbout = QMenu(self.menubar)
        self.menuAbout.setObjectName("menuAbout")
        self.menuAbout.setTearOffEnabled(False)
        self.menuView = QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuStable_Diffusion = QMenu(self.menuTools)
        self.menuStable_Diffusion.setObjectName("menuStable_Diffusion")
        self.menuStable_Diffusion.setIcon(icon17)
        self.menuImage = QMenu(self.menubar)
        self.menuImage.setObjectName("menuImage")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.model_toolbar = QToolBar(MainWindow)
        self.model_toolbar.setObjectName("model_toolbar")
        self.model_toolbar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.model_toolbar.setMovable(True)
        self.model_toolbar.setOrientation(Qt.Orientation.Horizontal)
        self.model_toolbar.setIconSize(QSize(18, 18))
        self.model_toolbar.setFloatable(False)
        MainWindow.addToolBar(
            Qt.ToolBarArea.BottomToolBarArea, self.model_toolbar
        )

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuImage.menuAction())
        self.menubar.addAction(self.menuFilters.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuAbout.menuAction())
        self.menuFile.addAction(self.menuArt.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menuChat.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menuWorkflow.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionReset_Settings_2)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuArt.addAction(self.artActionNew)
        self.menuArt.addAction(self.actionImport_image)
        self.menuArt.addAction(self.actionExport_image_button)
        self.menuChat.addAction(self.actionNew_Conversation)
        self.menuChat.addAction(self.actionDelete_conversation)
        self.menuWorkflow.addAction(self.workflow_actionRun)
        self.menuWorkflow.addAction(self.workflow_actionPause)
        self.menuWorkflow.addAction(self.workflow_actionStop)
        self.menuWorkflow.addSeparator()
        self.menuWorkflow.addAction(self.workflow_actionSave)
        self.menuWorkflow.addAction(self.actionSave_As)
        self.menuWorkflow.addAction(self.workflow_actionClear)
        self.menuWorkflow.addAction(self.workflow_actionEdit)
        self.menuWorkflow.addAction(self.workflow_actionOpen)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionCut)
        self.menuEdit.addAction(self.actionCopy)
        self.menuEdit.addAction(self.actionPaste)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionClear_all_prompts)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionSettings)
        self.menuFilters.addSeparator()
        self.menuAbout.addAction(self.actionAbout)
        self.menuAbout.addAction(self.actionBug_report)
        self.menuAbout.addAction(self.actionReport_vulnerability)
        self.menuAbout.addSeparator()
        self.menuAbout.addAction(self.actionDiscord)
        self.menuView.addAction(self.actionPrompt_Browser)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionBrowse_AI_Runner_Path)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionBrowse_Images_Path_2)
        self.menuView.addSeparator()
        self.menuTools.addAction(self.menuStable_Diffusion.menuAction())
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionToggle_LLM)
        self.menuTools.addAction(self.actionToggle_Text_to_Speech)
        self.menuTools.addAction(self.actionToggle_Speech_to_Text)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionStats)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionRun_setup_wizard_2)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionDownload_Model)
        self.menuStable_Diffusion.addAction(self.actionSafety_Checker)
        self.menuStable_Diffusion.addAction(self.actionToggle_Stable_Diffusion)
        self.menuStable_Diffusion.addAction(self.actionToggle_Controlnet)
        self.menuImage.addSeparator()
        self.menuImage.addSeparator()
        self.model_toolbar.addAction(self.actionSettings)
        self.model_toolbar.addSeparator()
        self.model_toolbar.addAction(self.actionToggle_Speech_to_Text)
        self.model_toolbar.addAction(self.actionToggle_Text_to_Speech)
        self.model_toolbar.addAction(self.actionToggle_LLM)
        self.model_toolbar.addSeparator()
        self.model_toolbar.addAction(self.actionToggle_Controlnet)
        self.model_toolbar.addAction(self.actionToggle_Stable_Diffusion)

        self.retranslateUi(MainWindow)

        self.center_tab_container.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", "AI Runner", None)
        )
        self.actionCopy.setText(
            QCoreApplication.translate("MainWindow", "Copy", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionCopy.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+C", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionPaste.setText(
            QCoreApplication.translate("MainWindow", "Paste", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionPaste.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+V", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionAbout.setText(
            QCoreApplication.translate("MainWindow", "About", None)
        )
        self.actionQuit.setText(
            QCoreApplication.translate("MainWindow", "Quit", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionQuit.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+Q", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionBug_report.setText(
            QCoreApplication.translate("MainWindow", "Bug report", None)
        )
        self.actionReport_vulnerability.setText(
            QCoreApplication.translate(
                "MainWindow", "Report vulnerability", None
            )
        )
        self.actionPrompt_Browser.setText(
            QCoreApplication.translate("MainWindow", "Prompt browser", None)
        )
        self.actionClear_all_prompts.setText(
            QCoreApplication.translate("MainWindow", "Clear all prompts", None)
        )
        # if QT_CONFIG(tooltip)
        self.actionClear_all_prompts.setToolTip(
            QCoreApplication.translate(
                "MainWindow",
                "Remove text from all prompts and negative prompts",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.actionCut.setText(
            QCoreApplication.translate("MainWindow", "Cut", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionCut.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+X", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionBrowse_AI_Runner_Path.setText(
            QCoreApplication.translate(
                "MainWindow", "Browse AI Runner Path", None
            )
        )
        self.actionBrowse_Images_Path_2.setText(
            QCoreApplication.translate("MainWindow", "Browse Images", None)
        )
        self.actionReset_Settings_2.setText(
            QCoreApplication.translate("MainWindow", "Reset Settings", None)
        )
        self.actionSafety_Checker.setText(
            QCoreApplication.translate("MainWindow", "Safety Checker", None)
        )
        self.actionRun_setup_wizard_2.setText(
            QCoreApplication.translate("MainWindow", "Run Setup Wizard", None)
        )
        self.actionStats.setText(
            QCoreApplication.translate("MainWindow", "Stats", None)
        )
        self.actionSettings.setText(
            QCoreApplication.translate("MainWindow", "Preferences", None)
        )
        self.actionToggle_LLM.setText(
            QCoreApplication.translate("MainWindow", "Toggle LLM", None)
        )
        self.actionToggle_Text_to_Speech.setText(
            QCoreApplication.translate(
                "MainWindow", "Toggle Text to Speech", None
            )
        )
        self.actionToggle_Speech_to_Text.setText(
            QCoreApplication.translate(
                "MainWindow", "Toggle Speech to Text", None
            )
        )
        self.actionToggle_Stable_Diffusion.setText(
            QCoreApplication.translate(
                "MainWindow", "Toggle Stable Diffusion", None
            )
        )
        self.actionToggle_Controlnet.setText(
            QCoreApplication.translate("MainWindow", "Toggle Controlnet", None)
        )
        self.artActionNew.setText(
            QCoreApplication.translate("MainWindow", "New", None)
        )
        # if QT_CONFIG(shortcut)
        self.artActionNew.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+N", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionImport_image.setText(
            QCoreApplication.translate("MainWindow", "Import image", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionImport_image.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+I", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionExport_image_button.setText(
            QCoreApplication.translate("MainWindow", "Export image", None)
        )
        # if QT_CONFIG(shortcut)
        self.actionExport_image_button.setShortcut(
            QCoreApplication.translate("MainWindow", "Ctrl+E", None)
        )
        # endif // QT_CONFIG(shortcut)
        self.actionNew_Conversation.setText(
            QCoreApplication.translate("MainWindow", "New Conversation", None)
        )
        self.actionDelete_conversation.setText(
            QCoreApplication.translate(
                "MainWindow", "Delete conversation", None
            )
        )
        self.actionDiscord.setText(
            QCoreApplication.translate("MainWindow", "Discord", None)
        )
        self.workflow_actionRun.setText(
            QCoreApplication.translate("MainWindow", "Run", None)
        )
        self.workflow_actionPause.setText(
            QCoreApplication.translate("MainWindow", "Pause", None)
        )
        self.workflow_actionStop.setText(
            QCoreApplication.translate("MainWindow", "Stop", None)
        )
        self.workflow_actionSave.setText(
            QCoreApplication.translate("MainWindow", "Save", None)
        )
        self.workflow_actionClear.setText(
            QCoreApplication.translate("MainWindow", "Clear", None)
        )
        self.workflow_actionEdit.setText(
            QCoreApplication.translate("MainWindow", "Edit", None)
        )
        self.workflow_actionOpen.setText(
            QCoreApplication.translate("MainWindow", "Load", None)
        )
        self.actionSave_As.setText(
            QCoreApplication.translate("MainWindow", "Save As", None)
        )
        self.actionDownload_Model.setText(
            QCoreApplication.translate("MainWindow", "Download Model", None)
        )
        # if QT_CONFIG(tooltip)
        self.home_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Home", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.home_button.setText("")
        # if QT_CONFIG(tooltip)
        self.art_editor_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Art Editor", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.art_editor_button.setText("")
        # if QT_CONFIG(tooltip)
        self.workflow_editor_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Workflow Editor", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.workflow_editor_button.setText("")
        # if QT_CONFIG(tooltip)
        self.browser_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Browser", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.browser_button.setText("")
        # if QT_CONFIG(tooltip)
        self.document_editor_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Document Editor", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.document_editor_button.setText("")
        # if QT_CONFIG(tooltip)
        self.map_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Maps", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.map_button.setText("")
        # if QT_CONFIG(tooltip)
        self.weather_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Weather", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.weather_button.setText("")
        self.visualizer_button.setText("")
        # if QT_CONFIG(tooltip)
        self.chat_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Chat", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.chat_button.setText("")
        # if QT_CONFIG(tooltip)
        self.settings_button.setToolTip(
            QCoreApplication.translate("MainWindow", "Settings", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.settings_button.setText("")
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.home_tab),
            QCoreApplication.translate("MainWindow", "Home", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.art_tab),
            QCoreApplication.translate("MainWindow", "Art", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.agent_workflow_tab),
            QCoreApplication.translate("MainWindow", "Agent Workflow", None),
        )
        self.browser.setTabText(self.browser.indexOf(self.browser_page), "")
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.browser_tab),
            QCoreApplication.translate("MainWindow", "Browser", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.document_editor_tab),
            QCoreApplication.translate("MainWindow", "Document Editor", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.map_tab),
            QCoreApplication.translate("MainWindow", "Maps", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.weather_tab),
            QCoreApplication.translate("MainWindow", "Weather", None),
        )
        self.center_tab_container.setTabText(
            self.center_tab_container.indexOf(self.visualizer_tab),
            QCoreApplication.translate("MainWindow", "Visualizer", None),
        )
        self.menuFile.setTitle(
            QCoreApplication.translate("MainWindow", "File", None)
        )
        self.menuArt.setTitle(
            QCoreApplication.translate("MainWindow", "Art", None)
        )
        self.menuChat.setTitle(
            QCoreApplication.translate("MainWindow", "Chat", None)
        )
        self.menuWorkflow.setTitle(
            QCoreApplication.translate("MainWindow", "Workflow", None)
        )
        self.menuEdit.setTitle(
            QCoreApplication.translate("MainWindow", "Edit", None)
        )
        self.menuFilters.setTitle(
            QCoreApplication.translate("MainWindow", "Filters", None)
        )
        self.menuAbout.setTitle(
            QCoreApplication.translate("MainWindow", "Help", None)
        )
        self.menuView.setTitle(
            QCoreApplication.translate("MainWindow", "View", None)
        )
        self.menuTools.setTitle(
            QCoreApplication.translate("MainWindow", "Tools", None)
        )
        self.menuStable_Diffusion.setTitle(
            QCoreApplication.translate("MainWindow", "Stable Diffusion", None)
        )
        self.menuImage.setTitle(
            QCoreApplication.translate("MainWindow", "Canvas", None)
        )
        self.model_toolbar.setWindowTitle(
            QCoreApplication.translate("MainWindow", "toolBar_2", None)
        )

    # retranslateUi
