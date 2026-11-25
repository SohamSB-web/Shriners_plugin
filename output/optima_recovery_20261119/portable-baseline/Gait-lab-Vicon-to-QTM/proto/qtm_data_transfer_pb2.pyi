from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class QtmFields(_message.Message):
    __slots__ = ("frames", "capture_frequency", "first_frame", "last_frame")
    FRAMES_FIELD_NUMBER: _ClassVar[int]
    CAPTURE_FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    FIRST_FRAME_FIELD_NUMBER: _ClassVar[int]
    LAST_FRAME_FIELD_NUMBER: _ClassVar[int]
    frames: int
    capture_frequency: float
    first_frame: int
    last_frame: int
    def __init__(self, frames: _Optional[int] = ..., capture_frequency: _Optional[float] = ..., first_frame: _Optional[int] = ..., last_frame: _Optional[int] = ...) -> None: ...

class Ack(_message.Message):
    __slots__ = ("message", "success")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    message: str
    success: bool
    def __init__(self, message: _Optional[str] = ..., success: bool = ...) -> None: ...

class CommandToQtm(_message.Message):
    __slots__ = ("command_name", "command_args_json")
    COMMAND_NAME_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ARGS_JSON_FIELD_NUMBER: _ClassVar[int]
    command_name: str
    command_args_json: str
    def __init__(self, command_name: _Optional[str] = ..., command_args_json: _Optional[str] = ...) -> None: ...
