"""
手机端 - 极简聊天APP
使用 Kivy 实现（修复中文显示和Window错误）
"""
import sys
import os
import threading
import socket

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window  # 确保这行存在
from kivy.core.text import LabelBase

# ============ 注册中文字体 ============
try:
    # Windows系统字体路径
    font_paths = [
        "C:/Windows/Fonts/simsun.ttc",      # 宋体
        "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",      # 黑体
        "C:/Windows/Fonts/fangsong.ttf",    # 仿宋
    ]
    
    font_registered = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            LabelBase.register(name='CustomFont', fn_regular=font_path)
            font_registered = True
            print(f"✓ 使用字体: {font_path}")
            break
    
    if not font_registered:
        # 如果系统字体找不到，使用Kivy默认字体
        LabelBase.register(name='CustomFont', fn_regular='DejaVuSans.ttf')
        print("⚠ 使用默认字体，中文可能显示为方块")
except Exception as e:
    print(f"⚠ 字体注册失败: {e}")

# ============ 导入公共模块 ============
from common.constants import DEFAULT_PORT, MAX_MSG_LEN, CMD_EXIT
from common.protocol import encode_message, decode_message, validate_length, is_control_cmd
from common.socket_handler import TCPClient


class ChatScreen(BoxLayout):
    """聊天界面"""
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        
        self.client = None
        self.is_connected = False
        self.receive_thread = None
        self.running = True
        
        # 界面
        self._create_widgets()
        
        # 弹出连接对话框
        Clock.schedule_once(lambda dt: self.show_connect_dialog(), 0.5)
    
    def _create_widgets(self):
        """创建界面组件"""
        # 状态栏 - 使用自定义字体
        self.status_label = Label(
            text="未连接", 
            size_hint_y=0.08, 
            font_size='16sp', 
            color=(0.3, 0.6, 1, 1),
            font_name='CustomFont'
        )
        self.add_widget(self.status_label)
        
        # 消息显示区域（滚动）
        scroll = ScrollView(size_hint_y=0.77)
        self.msg_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.msg_layout.bind(minimum_height=self.msg_layout.setter('height'))
        scroll.add_widget(self.msg_layout)
        self.add_widget(scroll)
        
        # 输入区
        input_layout = BoxLayout(size_hint_y=0.15, spacing=5)
        
        self.input_text = TextInput(
            hint_text=f"输入消息（≤{MAX_MSG_LEN}字符）", 
            multiline=False, 
            font_size='14sp',
            font_name='CustomFont'
        )
        self.input_text.bind(text=self.on_text_change)
        self.input_text.bind(on_text_validate=lambda x: self.send_message())
        self.input_text.disabled = True
        input_layout.add_widget(self.input_text)
        
        self.send_btn = Button(
            text="发送", 
            size_hint_x=0.2, 
            disabled=True,
            font_name='CustomFont'
        )
        self.send_btn.bind(on_press=lambda x: self.send_message())
        input_layout.add_widget(self.send_btn)
        
        self.add_widget(input_layout)
    
    def on_text_change(self, instance, value):
        """输入变化时限制长度"""
        if len(value) > MAX_MSG_LEN:
            self.input_text.text = value[:MAX_MSG_LEN]
    
    def show_connect_dialog(self):
        """显示连接对话框"""
        content = GridLayout(cols=2, spacing=10, padding=10)
        
        # 所有Label都使用自定义字体
        content.add_widget(Label(text="服务器IP:", size_hint_x=0.3, font_name='CustomFont'))
        
        ip_input = TextInput(text=self._get_local_ip(), multiline=False, font_name='CustomFont')
        content.add_widget(ip_input)
        
        content.add_widget(Label(text="端口:", size_hint_x=0.3, font_name='CustomFont'))
        port_input = TextInput(
            text=str(DEFAULT_PORT), 
            multiline=False, 
            input_filter='int',
            font_name='CustomFont'
        )
        content.add_widget(port_input)
        
        # 连接按钮
        connect_btn = Button(
            text="连接", 
            size_hint_y=None, 
            height=50,
            font_name='CustomFont'
        )
        content.add_widget(connect_btn)
        content.add_widget(Label(font_name='CustomFont'))  # 占位
        
        popup = Popup(
            title="连接到电脑", 
            content=content, 
            size_hint=(0.8, 0.5), 
            auto_dismiss=False,
            title_font='CustomFont'
        )
        
        def on_connect(btn):
            ip = ip_input.text.strip()
            try:
                port = int(port_input.text.strip())
            except:
                port = DEFAULT_PORT
            
            if not ip:
                return
            
            popup.dismiss()
            self.connect_to_server(ip, port)
        
        connect_btn.bind(on_press=on_connect)
        popup.open()
    
    def _get_local_ip(self):
        """获取本机IP（尝试获取）"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "192.168.1.100"
    
    def connect_to_server(self, ip, port):
        """连接服务器"""
        self.status_label.text = f"连接中... {ip}:{port}"
        
        def connect_thread():
            self.client = TCPClient(ip, port)
            if self.client.connect():
                self.is_connected = True
                Clock.schedule_once(lambda dt: self.on_connected(ip))
            else:
                Clock.schedule_once(lambda dt: self.on_connect_failed())
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connected(self, ip):
        """连接成功"""
        self.status_label.text = f"已连接到 {ip}"
        self.input_text.disabled = False
        self.send_btn.disabled = False
        self.add_message("系统", "连接成功！可以开始聊天了")
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receive_thread.start()
    
    def on_connect_failed(self):
        """连接失败"""
        self.status_label.text = "连接失败"
        self.add_message("系统", "连接失败，请检查IP和端口")
        
        # 重新弹出连接对话框
        Clock.schedule_once(lambda dt: self.show_connect_dialog(), 1)
    
    def receive_loop(self):
        """接收消息循环（子线程）"""
        while self.running and self.is_connected:
            data = self.client.receive()
            if not data:
                Clock.schedule_once(lambda dt: self.on_disconnect())
                break
            
            # 检查控制指令
            cmd = is_control_cmd(data)
            if cmd == CMD_EXIT:
                Clock.schedule_once(lambda dt: self.on_disconnect())
                break
            
            # 解码消息
            msg = decode_message(data)
            if msg:
                Clock.schedule_once(lambda dt, m=msg: self.add_message("电脑", m))
    
    def send_message(self):
        """发送消息"""
        if not self.is_connected:
            return
        
        msg = self.input_text.text.strip()
        if not msg:
            return
        
        if not validate_length(msg):
            self.add_message("系统", f"消息不能超过{MAX_MSG_LEN}个字符！")
            return
        
        # 发送
        data = encode_message(msg)
        if self.client.send(data):
            self.add_message("我", msg)
            self.input_text.text = ""
        else:
            self.add_message("系统", "发送失败")
            self.on_disconnect()
    
    def add_message(self, sender, msg):
        """添加消息到显示区"""
        label = Label(
            text=f"[{sender}] {msg}", 
            size_hint_y=None, 
            height=30, 
            text_size=(Window.width * 0.9, None),
            halign='left', 
            valign='middle',
            font_size='14sp',
            font_name='CustomFont'
        )
        label.bind(size=label.setter('text_size'))
        self.msg_layout.add_widget(label)
        
        # 滚动到底部
        if self.parent and hasattr(self.parent, 'scroll_y'):
            self.parent.scroll_y = 0
    
    def on_disconnect(self):
        """断开连接"""
        if not self.is_connected:
            return
        
        self.is_connected = False
        self.status_label.text = "已断开"
        self.input_text.disabled = True
        self.send_btn.disabled = True
        self.add_message("系统", "对方已断开连接")
        
        if self.client:
            self.client.close()
            self.client = None
        
        # 重新弹出连接对话框
        Clock.schedule_once(lambda dt: self.show_connect_dialog(), 1)
    
    def on_stop(self):
        """APP停止时"""
        self.running = False
        self.is_connected = False
        
        # 发送退出指令
        if self.client and self.client.is_connected:
            try:
                exit_data = encode_message(CMD_EXIT)
                self.client.send(exit_data)
            except:
                pass
        
        if self.client:
            self.client.close()


class ChatApp(App):
    """Kivy应用"""
    def build(self):
        # 设置窗口大小
        Window.size = (400, 700)
        # 设置窗口标题
        Window.title = '极简聊天'
        return ChatScreen()
    
    def on_stop(self):
        """应用停止"""
        if hasattr(self.root, 'on_stop'):
            self.root.on_stop()


if __name__ == "__main__":
    ChatApp().run()