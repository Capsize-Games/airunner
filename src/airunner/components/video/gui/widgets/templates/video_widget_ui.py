# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'video_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFrame, QGraphicsView, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QProgressBar, QPushButton,
    QSizePolicy, QSlider, QSpacerItem, QSpinBox,
    QSplitter, QVBoxLayout, QWidget)

class Ui_video_widget(object):
    def setupUi(self, video_widget):
        if not video_widget.objectName():
            video_widget.setObjectName(u"video_widget")
        video_widget.resize(1200, 800)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(video_widget.sizePolicy().hasHeightForWidth())
        video_widget.setSizePolicy(sizePolicy)
        self.verticalLayout_main = QVBoxLayout(video_widget)
        self.verticalLayout_main.setSpacing(0)
        self.verticalLayout_main.setObjectName(u"verticalLayout_main")
        self.verticalLayout_main.setContentsMargins(0, 0, 0, 0)
        self.top_bar = QWidget(video_widget)
        self.top_bar.setObjectName(u"top_bar")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.top_bar.sizePolicy().hasHeightForWidth())
        self.top_bar.setSizePolicy(sizePolicy1)
        self.top_bar.setMinimumSize(QSize(0, 50))
        self.top_bar.setMaximumSize(QSize(16777215, 50))
        self.horizontalLayout_topbar = QHBoxLayout(self.top_bar)
        self.horizontalLayout_topbar.setSpacing(10)
        self.horizontalLayout_topbar.setObjectName(u"horizontalLayout_topbar")
        self.horizontalLayout_topbar.setContentsMargins(10, 5, 10, 5)
        self.label_video_model = QLabel(self.top_bar)
        self.label_video_model.setObjectName(u"label_video_model")

        self.horizontalLayout_topbar.addWidget(self.label_video_model)

        self.model_selector = QComboBox(self.top_bar)
        self.model_selector.addItem("")
        self.model_selector.addItem("")
        self.model_selector.addItem("")
        self.model_selector.setObjectName(u"model_selector")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.model_selector.sizePolicy().hasHeightForWidth())
        self.model_selector.setSizePolicy(sizePolicy2)
        self.model_selector.setMinimumSize(QSize(200, 30))

        self.horizontalLayout_topbar.addWidget(self.model_selector)

        self.horizontalSpacer_topbar = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_topbar.addItem(self.horizontalSpacer_topbar)

        self.btn_model_settings = QPushButton(self.top_bar)
        self.btn_model_settings.setObjectName(u"btn_model_settings")
        self.btn_model_settings.setMinimumSize(QSize(30, 30))
        self.btn_model_settings.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_topbar.addWidget(self.btn_model_settings)


        self.verticalLayout_main.addWidget(self.top_bar)

        self.splitter_main = QSplitter(video_widget)
        self.splitter_main.setObjectName(u"splitter_main")
        self.splitter_main.setOrientation(Qt.Vertical)
        self.preview_container = QWidget(self.splitter_main)
        self.preview_container.setObjectName(u"preview_container")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(3)
        sizePolicy3.setHeightForWidth(self.preview_container.sizePolicy().hasHeightForWidth())
        self.preview_container.setSizePolicy(sizePolicy3)
        self.verticalLayout_preview = QVBoxLayout(self.preview_container)
        self.verticalLayout_preview.setSpacing(0)
        self.verticalLayout_preview.setObjectName(u"verticalLayout_preview")
        self.verticalLayout_preview.setContentsMargins(0, 0, 0, 0)
        self.video_preview = QGraphicsView(self.preview_container)
        self.video_preview.setObjectName(u"video_preview")
        sizePolicy.setHeightForWidth(self.video_preview.sizePolicy().hasHeightForWidth())
        self.video_preview.setSizePolicy(sizePolicy)
        self.video_preview.setFrameShape(QFrame.NoFrame)
        self.video_preview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.verticalLayout_preview.addWidget(self.video_preview)

        self.playback_controls = QWidget(self.preview_container)
        self.playback_controls.setObjectName(u"playback_controls")
        sizePolicy1.setHeightForWidth(self.playback_controls.sizePolicy().hasHeightForWidth())
        self.playback_controls.setSizePolicy(sizePolicy1)
        self.playback_controls.setMinimumSize(QSize(0, 60))
        self.playback_controls.setMaximumSize(QSize(16777215, 60))
        self.verticalLayout_playback = QVBoxLayout(self.playback_controls)
        self.verticalLayout_playback.setSpacing(5)
        self.verticalLayout_playback.setObjectName(u"verticalLayout_playback")
        self.verticalLayout_playback.setContentsMargins(10, 5, 10, 5)
        self.timeline_slider = QSlider(self.playback_controls)
        self.timeline_slider.setObjectName(u"timeline_slider")
        self.timeline_slider.setOrientation(Qt.Horizontal)
        self.timeline_slider.setTickPosition(QSlider.TicksBelow)
        self.timeline_slider.setTickInterval(10)

        self.verticalLayout_playback.addWidget(self.timeline_slider)

        self.horizontalLayout_playback = QHBoxLayout()
        self.horizontalLayout_playback.setObjectName(u"horizontalLayout_playback")
        self.btn_play = QPushButton(self.playback_controls)
        self.btn_play.setObjectName(u"btn_play")
        self.btn_play.setMinimumSize(QSize(30, 30))
        self.btn_play.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_playback.addWidget(self.btn_play)

        self.btn_pause = QPushButton(self.playback_controls)
        self.btn_pause.setObjectName(u"btn_pause")
        self.btn_pause.setMinimumSize(QSize(30, 30))
        self.btn_pause.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_playback.addWidget(self.btn_pause)

        self.btn_stop = QPushButton(self.playback_controls)
        self.btn_stop.setObjectName(u"btn_stop")
        self.btn_stop.setMinimumSize(QSize(30, 30))
        self.btn_stop.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_playback.addWidget(self.btn_stop)

        self.line_separator_1 = QFrame(self.playback_controls)
        self.line_separator_1.setObjectName(u"line_separator_1")
        self.line_separator_1.setFrameShape(QFrame.Shape.VLine)
        self.line_separator_1.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_playback.addWidget(self.line_separator_1)

        self.btn_prev_frame = QPushButton(self.playback_controls)
        self.btn_prev_frame.setObjectName(u"btn_prev_frame")
        self.btn_prev_frame.setMinimumSize(QSize(30, 30))
        self.btn_prev_frame.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_playback.addWidget(self.btn_prev_frame)

        self.btn_next_frame = QPushButton(self.playback_controls)
        self.btn_next_frame.setObjectName(u"btn_next_frame")
        self.btn_next_frame.setMinimumSize(QSize(30, 30))
        self.btn_next_frame.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_playback.addWidget(self.btn_next_frame)

        self.label_timecode = QLabel(self.playback_controls)
        self.label_timecode.setObjectName(u"label_timecode")
        self.label_timecode.setMinimumSize(QSize(100, 0))
        self.label_timecode.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_playback.addWidget(self.label_timecode)

        self.horizontalSpacer_playback = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_playback.addItem(self.horizontalSpacer_playback)

        self.btn_export = QPushButton(self.playback_controls)
        self.btn_export.setObjectName(u"btn_export")
        self.btn_export.setMinimumSize(QSize(80, 30))

        self.horizontalLayout_playback.addWidget(self.btn_export)


        self.verticalLayout_playback.addLayout(self.horizontalLayout_playback)


        self.verticalLayout_preview.addWidget(self.playback_controls)

        self.splitter_main.addWidget(self.preview_container)
        self.controls_container = QWidget(self.splitter_main)
        self.controls_container.setObjectName(u"controls_container")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(1)
        sizePolicy4.setHeightForWidth(self.controls_container.sizePolicy().hasHeightForWidth())
        self.controls_container.setSizePolicy(sizePolicy4)
        self.controls_container.setMinimumSize(QSize(0, 200))
        self.verticalLayout_controls = QVBoxLayout(self.controls_container)
        self.verticalLayout_controls.setSpacing(10)
        self.verticalLayout_controls.setObjectName(u"verticalLayout_controls")
        self.verticalLayout_controls.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout_prompt = QHBoxLayout()
        self.horizontalLayout_prompt.setObjectName(u"horizontalLayout_prompt")
        self.label_prompt = QLabel(self.controls_container)
        self.label_prompt.setObjectName(u"label_prompt")
        self.label_prompt.setMinimumSize(QSize(80, 0))
        self.label_prompt.setMaximumSize(QSize(80, 16777215))
        self.label_prompt.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_prompt.addWidget(self.label_prompt)

        self.prompt_input = QPlainTextEdit(self.controls_container)
        self.prompt_input.setObjectName(u"prompt_input")
        sizePolicy2.setHeightForWidth(self.prompt_input.sizePolicy().hasHeightForWidth())
        self.prompt_input.setSizePolicy(sizePolicy2)
        self.prompt_input.setMinimumSize(QSize(0, 60))
        self.prompt_input.setMaximumSize(QSize(16777215, 60))

        self.horizontalLayout_prompt.addWidget(self.prompt_input)


        self.verticalLayout_controls.addLayout(self.horizontalLayout_prompt)

        self.horizontalLayout_negative = QHBoxLayout()
        self.horizontalLayout_negative.setObjectName(u"horizontalLayout_negative")
        self.label_negative = QLabel(self.controls_container)
        self.label_negative.setObjectName(u"label_negative")
        self.label_negative.setMinimumSize(QSize(80, 0))
        self.label_negative.setMaximumSize(QSize(80, 16777215))
        self.label_negative.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_negative.addWidget(self.label_negative)

        self.negative_prompt_input = QPlainTextEdit(self.controls_container)
        self.negative_prompt_input.setObjectName(u"negative_prompt_input")
        sizePolicy2.setHeightForWidth(self.negative_prompt_input.sizePolicy().hasHeightForWidth())
        self.negative_prompt_input.setSizePolicy(sizePolicy2)
        self.negative_prompt_input.setMinimumSize(QSize(0, 60))
        self.negative_prompt_input.setMaximumSize(QSize(16777215, 60))

        self.horizontalLayout_negative.addWidget(self.negative_prompt_input)


        self.verticalLayout_controls.addLayout(self.horizontalLayout_negative)

        self.horizontalLayout_params = QHBoxLayout()
        self.horizontalLayout_params.setObjectName(u"horizontalLayout_params")
        self.label_steps = QLabel(self.controls_container)
        self.label_steps.setObjectName(u"label_steps")

        self.horizontalLayout_params.addWidget(self.label_steps)

        self.spinbox_steps = QSpinBox(self.controls_container)
        self.spinbox_steps.setObjectName(u"spinbox_steps")
        self.spinbox_steps.setMinimumSize(QSize(80, 0))
        self.spinbox_steps.setMinimum(1)
        self.spinbox_steps.setMaximum(150)
        self.spinbox_steps.setValue(30)

        self.horizontalLayout_params.addWidget(self.spinbox_steps)

        self.label_cfg = QLabel(self.controls_container)
        self.label_cfg.setObjectName(u"label_cfg")

        self.horizontalLayout_params.addWidget(self.label_cfg)

        self.spinbox_cfg = QDoubleSpinBox(self.controls_container)
        self.spinbox_cfg.setObjectName(u"spinbox_cfg")
        self.spinbox_cfg.setMinimumSize(QSize(80, 0))
        self.spinbox_cfg.setDecimals(1)
        self.spinbox_cfg.setMinimum(1.000000000000000)
        self.spinbox_cfg.setMaximum(20.000000000000000)
        self.spinbox_cfg.setSingleStep(0.500000000000000)
        self.spinbox_cfg.setValue(7.000000000000000)

        self.horizontalLayout_params.addWidget(self.spinbox_cfg)

        self.label_frames = QLabel(self.controls_container)
        self.label_frames.setObjectName(u"label_frames")

        self.horizontalLayout_params.addWidget(self.label_frames)

        self.spinbox_frames = QSpinBox(self.controls_container)
        self.spinbox_frames.setObjectName(u"spinbox_frames")
        self.spinbox_frames.setMinimumSize(QSize(80, 0))
        self.spinbox_frames.setMinimum(1)
        self.spinbox_frames.setMaximum(513)
        self.spinbox_frames.setValue(65)

        self.horizontalLayout_params.addWidget(self.spinbox_frames)

        self.label_fps = QLabel(self.controls_container)
        self.label_fps.setObjectName(u"label_fps")

        self.horizontalLayout_params.addWidget(self.label_fps)

        self.spinbox_fps = QSpinBox(self.controls_container)
        self.spinbox_fps.setObjectName(u"spinbox_fps")
        self.spinbox_fps.setMinimumSize(QSize(80, 0))
        self.spinbox_fps.setMinimum(1)
        self.spinbox_fps.setMaximum(60)
        self.spinbox_fps.setValue(30)

        self.horizontalLayout_params.addWidget(self.spinbox_fps)

        self.label_seed = QLabel(self.controls_container)
        self.label_seed.setObjectName(u"label_seed")

        self.horizontalLayout_params.addWidget(self.label_seed)

        self.spinbox_seed = QSpinBox(self.controls_container)
        self.spinbox_seed.setObjectName(u"spinbox_seed")
        self.spinbox_seed.setMinimumSize(QSize(100, 0))
        self.spinbox_seed.setMinimum(-1)
        self.spinbox_seed.setMaximum(2147483647)
        self.spinbox_seed.setValue(-1)

        self.horizontalLayout_params.addWidget(self.spinbox_seed)

        self.horizontalSpacer_params = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_params.addItem(self.horizontalSpacer_params)


        self.verticalLayout_controls.addLayout(self.horizontalLayout_params)

        self.horizontalLayout_image = QHBoxLayout()
        self.horizontalLayout_image.setObjectName(u"horizontalLayout_image")
        self.checkbox_img2vid = QCheckBox(self.controls_container)
        self.checkbox_img2vid.setObjectName(u"checkbox_img2vid")
        self.checkbox_img2vid.setChecked(True)

        self.horizontalLayout_image.addWidget(self.checkbox_img2vid)

        self.label_source_image = QLabel(self.controls_container)
        self.label_source_image.setObjectName(u"label_source_image")
        self.label_source_image.setEnabled(True)

        self.horizontalLayout_image.addWidget(self.label_source_image)

        self.lineedit_source_path = QLineEdit(self.controls_container)
        self.lineedit_source_path.setObjectName(u"lineedit_source_path")
        self.lineedit_source_path.setEnabled(True)
        self.lineedit_source_path.setReadOnly(True)

        self.horizontalLayout_image.addWidget(self.lineedit_source_path)

        self.btn_browse_source = QPushButton(self.controls_container)
        self.btn_browse_source.setObjectName(u"btn_browse_source")
        self.btn_browse_source.setEnabled(True)
        self.btn_browse_source.setMinimumSize(QSize(80, 30))

        self.horizontalLayout_image.addWidget(self.btn_browse_source)

        self.btn_clear_source = QPushButton(self.controls_container)
        self.btn_clear_source.setObjectName(u"btn_clear_source")
        self.btn_clear_source.setEnabled(True)
        self.btn_clear_source.setMinimumSize(QSize(30, 30))
        self.btn_clear_source.setMaximumSize(QSize(30, 30))

        self.horizontalLayout_image.addWidget(self.btn_clear_source)

        self.horizontalSpacer_image = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_image.addItem(self.horizontalSpacer_image)


        self.verticalLayout_controls.addLayout(self.horizontalLayout_image)

        self.horizontalLayout_generate = QHBoxLayout()
        self.horizontalLayout_generate.setObjectName(u"horizontalLayout_generate")
        self.progress_bar = QProgressBar(self.controls_container)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.horizontalLayout_generate.addWidget(self.progress_bar)

        self.btn_generate = QPushButton(self.controls_container)
        self.btn_generate.setObjectName(u"btn_generate")
        self.btn_generate.setMinimumSize(QSize(120, 40))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.btn_generate.setFont(font)

        self.horizontalLayout_generate.addWidget(self.btn_generate)

        self.btn_cancel = QPushButton(self.controls_container)
        self.btn_cancel.setObjectName(u"btn_cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setMinimumSize(QSize(80, 40))

        self.horizontalLayout_generate.addWidget(self.btn_cancel)


        self.verticalLayout_controls.addLayout(self.horizontalLayout_generate)

        self.splitter_main.addWidget(self.controls_container)

        self.verticalLayout_main.addWidget(self.splitter_main)


        self.retranslateUi(video_widget)

        QMetaObject.connectSlotsByName(video_widget)
    # setupUi

    def retranslateUi(self, video_widget):
        video_widget.setWindowTitle(QCoreApplication.translate("video_widget", u"Video Generation", None))
        self.label_video_model.setText(QCoreApplication.translate("video_widget", u"Video Model:", None))
        self.model_selector.setItemText(0, QCoreApplication.translate("video_widget", u"HunyuanVideo (I2V)", None))
        self.model_selector.setItemText(1, QCoreApplication.translate("video_widget", u"CogVideoX-5B (T2V)", None))
        self.model_selector.setItemText(2, QCoreApplication.translate("video_widget", u"AnimateDiff (SD1.5)", None))

        self.btn_model_settings.setText(QCoreApplication.translate("video_widget", u"\u2699", None))
#if QT_CONFIG(tooltip)
        self.btn_model_settings.setToolTip(QCoreApplication.translate("video_widget", u"Model Settings", None))
#endif // QT_CONFIG(tooltip)
        self.btn_play.setText(QCoreApplication.translate("video_widget", u"\u25b6", None))
#if QT_CONFIG(tooltip)
        self.btn_play.setToolTip(QCoreApplication.translate("video_widget", u"Play", None))
#endif // QT_CONFIG(tooltip)
        self.btn_pause.setText(QCoreApplication.translate("video_widget", u"\u23f8", None))
#if QT_CONFIG(tooltip)
        self.btn_pause.setToolTip(QCoreApplication.translate("video_widget", u"Pause", None))
#endif // QT_CONFIG(tooltip)
        self.btn_stop.setText(QCoreApplication.translate("video_widget", u"\u23f9", None))
#if QT_CONFIG(tooltip)
        self.btn_stop.setToolTip(QCoreApplication.translate("video_widget", u"Stop", None))
#endif // QT_CONFIG(tooltip)
        self.btn_prev_frame.setText(QCoreApplication.translate("video_widget", u"\u23ee", None))
#if QT_CONFIG(tooltip)
        self.btn_prev_frame.setToolTip(QCoreApplication.translate("video_widget", u"Previous Frame", None))
#endif // QT_CONFIG(tooltip)
        self.btn_next_frame.setText(QCoreApplication.translate("video_widget", u"\u23ed", None))
#if QT_CONFIG(tooltip)
        self.btn_next_frame.setToolTip(QCoreApplication.translate("video_widget", u"Next Frame", None))
#endif // QT_CONFIG(tooltip)
        self.label_timecode.setText(QCoreApplication.translate("video_widget", u"0:00 / 0:00", None))
        self.btn_export.setText(QCoreApplication.translate("video_widget", u"Export", None))
#if QT_CONFIG(tooltip)
        self.btn_export.setToolTip(QCoreApplication.translate("video_widget", u"Export Video", None))
#endif // QT_CONFIG(tooltip)
        self.label_prompt.setText(QCoreApplication.translate("video_widget", u"Prompt:", None))
        self.prompt_input.setPlaceholderText(QCoreApplication.translate("video_widget", u"Describe the video you want to generate...", None))
        self.label_negative.setText(QCoreApplication.translate("video_widget", u"Negative:", None))
        self.negative_prompt_input.setPlaceholderText(QCoreApplication.translate("video_widget", u"What to avoid in the video...", None))
        self.label_steps.setText(QCoreApplication.translate("video_widget", u"Steps:", None))
        self.label_cfg.setText(QCoreApplication.translate("video_widget", u"CFG Scale:", None))
        self.label_frames.setText(QCoreApplication.translate("video_widget", u"Frames:", None))
        self.label_fps.setText(QCoreApplication.translate("video_widget", u"FPS:", None))
        self.label_seed.setText(QCoreApplication.translate("video_widget", u"Seed:", None))
        self.checkbox_img2vid.setText(QCoreApplication.translate("video_widget", u"Image-to-Video", None))
        self.label_source_image.setText(QCoreApplication.translate("video_widget", u"Source:", None))
        self.lineedit_source_path.setPlaceholderText(QCoreApplication.translate("video_widget", u"No image selected", None))
        self.btn_browse_source.setText(QCoreApplication.translate("video_widget", u"Browse...", None))
        self.btn_clear_source.setText(QCoreApplication.translate("video_widget", u"\u2715", None))
#if QT_CONFIG(tooltip)
        self.btn_clear_source.setToolTip(QCoreApplication.translate("video_widget", u"Clear Source Image", None))
#endif // QT_CONFIG(tooltip)
        self.progress_bar.setFormat(QCoreApplication.translate("video_widget", u"%p% - Ready", None))
        self.btn_generate.setText(QCoreApplication.translate("video_widget", u"Generate Video", None))
        self.btn_cancel.setText(QCoreApplication.translate("video_widget", u"Cancel", None))
    # retranslateUi

