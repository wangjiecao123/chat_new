"""
TCP Socket封装
"""
import socket
import threading
from .constants import BUFFER_SIZE

class TCPServer:
    """TCP服务端"""
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.client_socket = None
        self.client_addr = None
        self.is_running = False
    
    def start(self):
        """启动服务端"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.is_running = True
            return True
        except Exception as e:
            print(f"服务端启动失败: {e}")
            return False
    
    def accept(self):
        """接受客户端连接（阻塞）"""
        if not self.is_running:
            return None
        try:
            self.client_socket, self.client_addr = self.socket.accept()
            return self.client_addr
        except Exception as e:
            print(f"接受连接失败: {e}")
            return None
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self.client_socket:
            return False
        try:
            self.client_socket.sendall(data)
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def receive(self) -> bytes:
        """接收数据（阻塞）"""
        if not self.client_socket:
            return b''
        try:
            # 先接收4字节长度头
            header = self.client_socket.recv(4)
            if not header:
                return b''
            # 解析长度
            import struct
            msg_len = struct.unpack('>I', header)[0]
            if msg_len > 1024:  # 安全检查
                return b''
            # 接收内容
            data = self.client_socket.recv(msg_len)
            return header + data
        except Exception as e:
            print(f"接收失败: {e}")
            return b''
    
    def close(self):
        """关闭连接"""
        self.is_running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


class TCPClient:
    """TCP客户端"""
    def __init__(self, host, port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """连接服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self.is_connected or not self.socket:
            return False
        try:
            self.socket.sendall(data)
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def receive(self) -> bytes:
        """接收数据（阻塞）"""
        if not self.is_connected or not self.socket:
            return b''
        try:
            header = self.socket.recv(4)
            if not header:
                self.is_connected = False
                return b''
            import struct
            msg_len = struct.unpack('>I', header)[0]
            if msg_len > 1024:
                return b''
            data = self.socket.recv(msg_len)
            return header + data
        except Exception as e:
            print(f"接收失败: {e}")
            self.is_connected = False
            return b''
    
    def close(self):
        """关闭连接"""
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass