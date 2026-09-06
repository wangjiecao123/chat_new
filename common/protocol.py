"""
消息编解码协议
格式: [4字节长度头(大端序)] + [UTF-8编码的内容]
"""
import struct
from .constants import MAX_MSG_LEN, CMD_EXIT, CMD_PING

def encode_message(msg: str) -> bytes:
    """
    将消息编码为字节流
    返回: 4字节长度头 + UTF-8内容
    """
    if not msg:
        msg = ""
    content = msg.encode('utf-8')
    # 打包长度（4字节，大端序）
    header = struct.pack('>I', len(content))
    return header + content

def decode_message(data: bytes) -> str:
    """
    从字节流解码消息
    返回: 原始字符串
    """
    if len(data) < 4:
        return ""
    # 解包长度
    msg_len = struct.unpack('>I', data[:4])[0]
    if len(data) < 4 + msg_len:
        return ""
    content = data[4:4+msg_len]
    return content.decode('utf-8')

def validate_length(msg: str) -> bool:
    """检查消息长度是否合法（≤10字符）"""
    return len(msg) <= MAX_MSG_LEN

def is_control_cmd(data: bytes) -> str:
    """
    判断是否为控制指令
    返回: 指令字符串 或 None
    """
    try:
        msg = decode_message(data)
        if msg in (CMD_EXIT, CMD_PING):
            return msg
    except:
        pass
    return None