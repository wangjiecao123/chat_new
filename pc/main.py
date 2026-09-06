"""
电脑端 - 极简聊天窗口
使用 tkinter 实现
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import socket
import sys
import os

# 添加父目录到路径，以便导入common
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.constants import DEFAULT_PORT, MAX_MSG_LEN, CMD_EXIT
from common.protocol import encode_message, decode_message, validate_length, is_control_cmd
from common.socket_handler import TCPServer


class ChatWindow:
    def __init__(self):
        self.server = None
        self.is_connected = False
        self.receive_thread = None
        self.running = True
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("极简聊天 - 电脑端")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # 获取本机IP
        self.local_ip = self._get_local_ip()
        
        # 创建界面
        self._create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _get_local_ip(self):
        """获取本机局域网IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _create_widgets(self):
        """创建界面组件"""
        # 状态栏
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text=f"IP: {self.local_ip} | 状态: 未启动", 
                                     font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)
        
        self.start_btn = tk.Button(status_frame, text="启动监听", 
                                   command=self.start_server, width=12)
        self.start_btn.pack(side=tk.RIGHT)
        
        # 消息显示区
        self.msg_display = scrolledtext.ScrolledText(self.root, height=18, 
                                                     font=("Arial", 10), state='disabled')
        self.msg_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 输入区
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.input_entry = tk.Entry(input_frame, font=("Arial", 10))
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind('<Return>', lambda e: self.send_message())
        self.input_entry.bind('<KeyRelease>', self._on_input_change)
        self.input_entry.config(state='disabled')
        
        self.send_btn = tk.Button(input_frame, text="发送", 
                                  command=self.send_message, width=8, state='disabled')
        self.send_btn.pack(side=tk.RIGHT)
        
        # 提示标签
        self.hint_label = tk.Label(self.root, text="启动监听后等待手机连接...", 
                                   font=("Arial", 9), fg="gray")
        self.hint_label.pack(pady=(0, 5))
    
    def _on_input_change(self, event):
        """输入框内容变化时检查长度"""
        text = self.input_entry.get()
        if len(text) > MAX_MSG_LEN:
            self.input_entry.delete(MAX_MSG_LEN, tk.END)
    
    def start_server(self):
        """启动服务端"""
        self.start_btn.config(state='disabled')
        self.start_btn.config(text="启动中...")
        
        def start():
            self.server = TCPServer(host='0.0.0.0', port=DEFAULT_PORT)
            if not self.server.start():
                self.root.after(0, lambda: messagebox.showerror("错误", "启动监听失败！"))
                self.root.after(0, lambda: self.start_btn.config(state='normal', text="启动监听"))
                return
            
            self.root.after(0, lambda: self.status_label.config(
                text=f"IP: {self.local_ip} | 状态: 等待连接..."))
            self.root.after(0, lambda: self.start_btn.config(text="等待连接..."))
            
            # 接受连接（阻塞）
            addr = self.server.accept()
            if addr:
                self.is_connected = True
                self.root.after(0, lambda: self.status_label.config(
                    text=f"IP: {self.local_ip} | 状态: 已连接 ({addr[0]})"))
                self.root.after(0, lambda: self.start_btn.config(text="已连接", state='disabled'))
                self.root.after(0, lambda: self.input_entry.config(state='normal'))
                self.root.after(0, lambda: self.send_btn.config(state='normal'))
                self.root.after(0, lambda: self.hint_label.config(text="可以开始聊天了！"))
                self.root.after(0, lambda: self.append_message("系统", f"手机已连接 ({addr[0]})"))
                
                # 启动接收线程
                self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
                self.receive_thread.start()
            else:
                self.root.after(0, lambda: self.start_btn.config(state='normal', text="启动监听"))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"IP: {self.local_ip} | 状态: 已停止"))
        
        threading.Thread(target=start, daemon=True).start()
    
    def receive_loop(self):
        """接收消息循环（在子线程运行）"""
        while self.running and self.is_connected:
            data = self.server.receive()
            if not data:
                # 连接断开
                self.root.after(0, self.on_disconnect)
                break
            
            # 检查是否为控制指令
            cmd = is_control_cmd(data)
            if cmd == CMD_EXIT:
                self.root.after(0, self.on_disconnect)
                break
            
            # 解码消息
            msg = decode_message(data)
            if msg:
                self.root.after(0, lambda m=msg: self.append_message("手机", m))
    
    def send_message(self):
        """发送消息"""
        if not self.is_connected:
            return
        
        msg = self.input_entry.get().strip()
        if not msg:
            return
        
        if not validate_length(msg):
            messagebox.showwarning("提示", f"消息不能超过{MAX_MSG_LEN}个字符！")
            return
        
        # 发送消息
        data = encode_message(msg)
        if self.server.send(data):
            self.append_message("我", msg)
            self.input_entry.delete(0, tk.END)
        else:
            messagebox.showerror("错误", "发送失败！")
            self.on_disconnect()
    
    def append_message(self, sender, msg):
        """在显示区追加消息"""
        self.msg_display.config(state='normal')
        self.msg_display.insert(tk.END, f"[{sender}] {msg}\n")
        self.msg_display.see(tk.END)
        self.msg_display.config(state='disabled')
    
    def on_disconnect(self):
        """断开连接"""
        if not self.is_connected:
            return
        
        self.is_connected = False
        self.status_label.config(text=f"IP: {self.local_ip} | 状态: 已断开")
        self.start_btn.config(state='normal', text="启动监听")
        self.input_entry.config(state='disabled')
        self.send_btn.config(state='disabled')
        self.hint_label.config(text="对方已离开，重新启动监听等待连接")
        self.append_message("系统", "对方已断开连接")
        
        # 关闭连接
        if self.server:
            self.server.close()
            self.server = None
    
    def on_closing(self):
        """窗口关闭事件"""
        self.running = False
        self.is_connected = False
        
        # 发送退出指令
        if self.server and self.server.client_socket:
            try:
                exit_data = encode_message(CMD_EXIT)
                self.server.send(exit_data)
            except:
                pass
        
        # 关闭连接
        if self.server:
            self.server.close()
        
        self.root.destroy()
    
    def run(self):
        """运行主循环"""
        self.root.mainloop()


if __name__ == "__main__":
    app = ChatWindow()
    app.run()