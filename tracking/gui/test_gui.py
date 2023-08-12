from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QTimer
import copy
import cv2
import matplotlib.pyplot as plt

from matplotlib.backends.backend_qt5agg import FigureCanvas as FigureCanvas
from matplotlib.figure import Figure
from functools import partial
import static.stylesheet as style
from controller.test_control import Controller
from data.test_data import DcmData

class Gui(QMainWindow):
    def __init__(self, get):
        super().__init__()
        self.get = get
        self.initUI()

    def initUI(self):
        self.setWindowTitle("InsightMedi Viewer")
        self.setGeometry(100, 100, 1280, 720)    # 초기 window 위치, size

        # main widget
        self.main_widget = QWidget()
        self.main_widget.setStyleSheet(style.main)
        self.setCentralWidget(self.main_widget)

        self.canvas = FigureCanvas(Figure(figsize=(4, 3)))
        fig = self.canvas.figure
        ax = fig.add_subplot(111, aspect='auto')

        # canvas fig 색상 변경
        fig.patch.set_facecolor('#303030')
        ax.patch.set_facecolor("#3A3A3A")
        ax.axis("off")
        # self.ax.tick_params(axis = 'x', colors = 'gray')
        # self.ax.tick_params(axis = 'y', colors = 'gray')
        
        # label list
        self.label_layout = QVBoxLayout()
        self.set_buttons()

        # slider
        self.slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider_layout.addWidget(self.slider)

        # Frame label
        self.frame_label = QLabel("")
        self.frame_label.setStyleSheet(style.lightfont)
        self.slider_layout.addWidget(self.frame_label)

        # play button
        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet(style.playbutton)
        self.play_button.setFocusPolicy(Qt.NoFocus)

        # GUI Layout
        self.set_gui_layout()
        
        # 창 중앙 정렬
        screen_geometry = QApplication.desktop().availableGeometry()
        center_x = (screen_geometry.width() - self.width()) // 2
        center_y = (screen_geometry.height() - self.height()) // 2
        self.move(center_x, center_y)

        self.is_tracking = False
        self.video_status = None
        self.timer = None

        # Create a toolbar
        toolbar = self.addToolBar("Toolbar")

        # Create actions
        self.create_actions(toolbar)

    def init_instance_member(self):
        self.dd = self.get('data')   # dcm_data.py의 DcmData()
        self.cl = self.get('control') # control.py의 Controller()

    def closeEvent(self, event):
        # mainWindow종료시 할당된 메모리 해제하기
        self.release_resources()
        event.accept()

    def release_resources(self):
        # 동영상 플레이어 메모리 해제
        print("release resource")
        if self.dd.video_player:
            self.video_status = None
            self.dd.video_player.release()

    def set_frame_label(self, init=False):
        if init:
            frame = 0
        else:
            frame = self.dd.frame_number

        total_frame = int(self.dd.total_frame) - 1
        self.frame_label.setText(f"{frame} / {total_frame}")

    def open_file(self):
        # 파일 열기 기능 구현
        options = QFileDialog.Options()
        fname = QFileDialog.getOpenFileName(
            self, "Open File", "", "Video Files (*.mp4);;All Files (*)", options=options)

        if fname[0]:   # 새로운 파일 열기 한 경우
            # 기존 파일 정보 삭제
            self.setCursor(Qt.ArrowCursor)
            self.canvas.figure.clear()
            self.release_resources()
            self.slider.setValue(0)    # slider value 초기화

            # 파일 열기
            dd = self.dd
            dd.open_file(fname)

            # viewer 설정 초기화
            # open한 파일에 이미 저장되어 있는 label button 활성화하는 함수
            self.load_label_button(dd.frame_label_dict)
            self.set_frame_label(init=True)

            if dd.file_mode == "mp4":  # mp4 파일인 경우
                self.timer = QTimer()
                self.set_frame_label()

                self.cl.img_show(dd.image, init=True)
                if self.dd.frame_label_check(self.dd.frame_number):
                    self.cl.label_clicked(self.dd.frame_number)

                # slider 설정
                self.slider.setMaximum(dd.total_frame - 1)
                self.slider.setTickPosition(
                    QSlider.TicksBelow)  # 눈금 위치 설정 (아래쪽)
                self.slider.setTickInterval(10)  # 눈금 간격 설정
                self.slider.valueChanged.connect(self.sliderValueChanged)
                self.play_button.clicked.connect(self.playButtonClicked)

            else:    # viewer에 호환되지 않는 확장자 파일
                print("Not accepted file format")
        else:
            print("Open fail")

    def load_label_button(self, ld):    # frame_label_dict에 있는 label 정보 버튼에 반영하기
        all_labels = set()
        for frame in ld:
            labels = self.dd.frame_label_check(frame)
            if labels:
                for label in labels:
                    all_labels.add(label)

        for label_name in self.buttons:
            temp_label_buttons = self.buttons[label_name]
            if label_name in all_labels:
                temp_label_buttons[0].setStyleSheet(
                    "color: white; font-weight: bold; height: 30px; width: 120px;")
                temp_label_buttons[1].setStyleSheet(
                    "color: white; font-weight: bold; height: 30px; width: 50px;")
            else:
                temp_label_buttons[0].setStyleSheet(
                    "color: gray; font-weight: normal; height: 30px; width: 120px;")
                temp_label_buttons[1].setStyleSheet(
                    "color: gray; font-weight: normal; height: 30px; width: 50px;")

        self.label_layout.update()

    def label_button_clicked(self, label):
        button_list = self.buttons[label]
        # print(f"self.buttons : {self.buttons}")
        button_list[0].setStyleSheet(
            "color: white; font-weight: bold; height: 30px; width: 120px;")
        button_list[1].setStyleSheet(
            "color: white; font-weight: bold; height: 30px; width: 50px;")

        for frame in self.dd.frame_label_dict:
            frame_labels = self.dd.frame_label_check(frame)
            if frame_labels and label in frame_labels:
                self.dd.delete_label(label, frame)
                self.cl.erase_annotation(label)

        self.cl.is_tracking = False

        if self.cl.annotation_mode == "line":
            self.draw_straight_line(label)
        else:
            self.draw_rectangle(label)

    def go_button_clicked(self, label):
        found_label = False

        for frame in self.dd.frame_label_dict:
            labels = self.dd.frame_label_check(frame)
            if labels and label in labels:
                first_frame = frame
                found_label = True
                break

        if found_label:
            self.frame_label_show(first_frame, label)

    def frame_label_show(self, frame, label):
        # go 버튼 클릭시 frame값을 전달받고 이동 후 선택된 label은 두껍게 보여짐
        self.setCursor(Qt.ArrowCursor)
        if self.dd.file_mode == "mp4":
            self.dd.frame_number = frame
            self.slider.setValue(frame)

        self.cl.label_clicked(frame, label)

    """ def disable_total_label(self):
        # 해당 프레임에 있는 전체 label 버튼 비활성화
        frame_labels = self.dd.frame_label_check(self.dd.frame_number)
        if frame_labels:
            for _label_name in frame_labels:
                button_list = self.buttons[_label_name]
                button_list[0].setStyleSheet(
                    "color: gray; font-weight: normal; height: 30px; width: 120px;")
                button_list[1].setStyleSheet(
                    "color: gray; font-weight: normal; height: 30px; width: 50px;")
                self.dd.delete_label(_label_name)
            self.label_layout.update()

        # data에서 해당 라벨 이름 정보 제거하기
        self.dd.delete_label(_label_name) """

    def disable_label_button(self, _label_name):
        # 특정 label 버튼 볼드체 풀기 (비활성화)
        if _label_name in self.buttons:
            button_list = self.buttons[_label_name]
            button_list[0].setStyleSheet(
                "color: gray; font-weight: normal; height: 30px; width: 120px;")
            button_list[1].setStyleSheet(
                "color: gray; font-weight: normal; height: 30px; width: 50px;")
        else:
            print(f"{_label_name} 라벨에 대한 버튼을 찾을 수 없음")
        self.label_layout.update()

    def save(self):
        # 저장 기능 구현
        self.dd.save_label()
        print("Save...")

    def sliderValueChanged(self, value):
        # 슬라이더 값에 따라 frame 보여짐
        if not self.timer.isActive():    # 영상 재생 중인 경우
            self.dd.frame_number = value
            self.dd.video_player.set(
                cv2.CAP_PROP_POS_FRAMES, self.dd.frame_number)
            self.updateFrame()
        elif self.timer.isActive() and value != self.dd.frame_number:
            # 영상이 정지 중이거나 사용자가 slider value를 바꾼 경우
            self.dd.frame_number = value
            self.dd.video_player.set(
                cv2.CAP_PROP_POS_FRAMES, self.dd.frame_number)

    def playButtonClicked(self):
        # 영상 재생 버튼의 함수
        if not self.timer:    # timer 없으면 새로 생성하고 updateFrame을 callback으로 등록
            self.timer = self.canvas.new_timer(interval=16)  # 60FPS
            # self.timer.add_callback(self.updateFrame)

        if not self.timer.isActive():   # 재생 시작
            self.play_button.setText("Pause")
            self.timer.start()
            self.timer.timeout.connect(self.updateFrame)
            self.timer.start(16)
        else:    # 영상 정지
            self.play_button.setText("Play")
            self.timer.timeout.disconnect(self.updateFrame)
            self.set_frame_label()   # 현재 frame 상태 화면에 update
            self.timer.stop()
            self.dd.frame_number = int(
                self.dd.video_player.get(cv2.CAP_PROP_POS_FRAMES)) - 1
    
    def updateFrame(self):
        # frame update
        prev_frame = copy.deepcopy(self.dd.image)
        ret, frame = self.dd.video_player.read()
        if ret:
            self.dd.frame_number = int(
                self.dd.video_player.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            self.set_frame_label()  # 현재 frame 상태 화면에 update
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.cl.img_show(rgb_frame, clear=True)
            self.dd.image = rgb_frame
            # frame에 라벨이 존재하면 라벨을 보여줍니다.
            if self.is_tracking:
                self.cl.init_object_tracking(prev_frame, rgb_frame)
            if self.dd.frame_number in self.dd.frame_label_dict:
                self.cl.label_clicked(self.dd.frame_number)

            if self.timer.isActive():   # 영상 재생 중
                self.slider.setValue(self.dd.frame_number)

        print("update Frame 호출, 현재 frame: ", self.dd.frame_number)

    def selector(self):
        self.setCursor(Qt.ArrowCursor)
        self.cl.init_selector("selector")

    def draw_rectangle(self, label=None):
        if label or self.cl.selector_mode == "drawing":
            self.setCursor(Qt.CrossCursor)
            self.cl.init_draw_mode("rectangle", label)
        else:
            self.cl.annotation_mode = "rectangle"
            QMessageBox.information(
                self, 'Message', 'Click label button before drawing')

    def delete(self):
        self.cl.init_selector("delete")

    def delete_all(self):
        # print("erase")
        reply = QMessageBox.question(self, 'Message', 'Do you erase all?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.cl.erase_all_annotation()    # canvas 위에 그려진 label 삭제
            # self.disable_total_label()    # label 버튼 비활성화
            for label_name in self.dd.frame_label_check(self.dd.frame_number):
                self.cl.delete_label(label_name)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_T:
            print("t 키 눌림")
            if not self.is_tracking:
                self.is_tracking = True
                self.playButtonClicked()
            else:
                self.is_tracking = False
                self.playButtonClicked()

        elif event.key() == Qt.Key_Delete:
            print("delete 키 눌림")
            self.cl.remove_annotation()

        elif event.key() == Qt.Key_Escape:
            print('esc키 눌림')
            self.cl.select_off_all()

        if event.key() == Qt.Key_Space:
            print("space bar 눌림")
            self.playButtonClicked()

    def set_buttons(self):
        self.buttons = {}
        for i in range(8):
            button_layout = QHBoxLayout()
            label_name = "label %d" % (i + 1)
            label_button = QPushButton(label_name)
            label_button.setStyleSheet(style.labelbutton)
            label_button.clicked.connect(
                partial(self.label_button_clicked, label_name))
            label_button.setFocusPolicy(Qt.NoFocus)

            go_button = QPushButton("GO")
            go_button.setStyleSheet(style.gobutton)
            go_button.clicked.connect(
                partial(self.go_button_clicked, label_name))
            go_button.setFocusPolicy(Qt.NoFocus)

            button_layout.addWidget(label_button)
            button_layout.addWidget(go_button)
            self.label_layout.addLayout(button_layout)

            label_go_buttons = [label_button, go_button]
            self.buttons[label_name] = label_go_buttons

    def set_gui_layout(self):
        grid_box = QGridLayout(self.main_widget)
        grid_box.setColumnStretch(0, 4)   # column 0 width 4
        # grid_box.setColumnStretch(1, 1)   # column 1 width 1

        # column 0
        grid_box.addWidget(self.canvas, 0, 0, 8, 1)
        grid_box.addLayout(self.slider_layout, 8, 0)

        # column 1
        # grid_box.addWidget(self.frame_label, 8, 1)

        # column 2
        grid_box.addLayout(self.label_layout, 0, 1)
        grid_box.addWidget(self.play_button, 1, 1)

    def create_actions(self, toolbar):
        # Open file action
        actions = ["open", "save", "selector", "rectangle", "delete", "clear"]
        func = [self.open_file, self.save, self.selector, self.draw_rectangle, self.delete, self.delete_all]
        icon_dir = 'gui/icon'
        pack = zip(actions, func)
        for x in pack:
            action = QAction(QIcon(f'{icon_dir}/{x[0]}_icon.png'), x[0].title(), self)
            action.triggered.connect(x[1])
            toolbar.addAction(action)