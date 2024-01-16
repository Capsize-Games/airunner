import datetime
import os

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex

from airunner.settings import BASE_PATH


DEFAULT_PATHS = {
    "art": {
        "models": {
            "txt2img": "",
            "depth2img": "",
            "pix2pix": "",
            "inpaint": "",
            "upscale": "",
            "txt2vid": "",
            "embeddings": "",
            "lora": "",
            "vae": "",
        },
        "other": {
            "images": "",
            "videos": "",
        },
    },
    "text": {
        "models": {
            "casuallm": "",
            "seq2seq": "",
            "visualqa": "",
        },
        "other": {
            "ebooks": "",
        }
    }
}

for k, v in DEFAULT_PATHS.items():
    for k2, v2 in v.items():
        if isinstance(v2, dict):
            for k3, v3 in v2.items():
                path = os.path.join(BASE_PATH, k, k2, k3)
                DEFAULT_PATHS[k][k2][k3] = path
                #check if path exists, if not, create it:
                if not os.path.exists(path):
                    print("creating path: ", path)
                    os.makedirs(path)
        else:
            path = os.path.join(BASE_PATH, k, k2)
            DEFAULT_PATHS[k][k2] = path
            #check if path exists, if not, create it:
            if not os.path.exists(path):
                print("creating path: ", path)
                os.makedirs(path)


class ModelBase(QAbstractTableModel):
    _headers = []

    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            attr = self._headers[col]["column_name"]
            if hasattr(self._data[row], attr):
                return getattr(self._data[row], attr)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]["display_name"]
        return None


Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ControlnetModel(BaseModel):
    __tablename__ = 'controlnet_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    default = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

    def __repr__(self):
        return f"<ControlnetModel(name='{self.name}', path='{self.path}', default='{self.is_default}')>"


class AIModel(BaseModel):
    __tablename__ = 'ai_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    branch = Column(String)
    version = Column(String)
    category = Column(String)
    pipeline_action = Column(String)
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=True)
    model_type = Column(String, default="art")


class Pipeline(BaseModel):
    __tablename__ = 'pipelines'

    id = Column(Integer, primary_key=True)
    category = Column(String)
    version = Column(String)
    pipeline_action = Column(String)
    classname = Column(String)
    singlefile_classname = Column(String)
    default = Column(Boolean, default=True)
    

class ImageFilter(BaseModel):
    __tablename__ = 'image_filter'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    image_filter_values = relationship("ImageFilterValue", back_populates="image_filter", lazy='joined')
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, default="")


class ImageFilterValue(BaseModel):
    __tablename__ = 'image_filter_value'

    id = Column(Integer, primary_key=True)
    image_filter_id = Column(Integer, ForeignKey('image_filter.id'))
    image_filter = relationship("ImageFilter", back_populates="image_filter_values")
    name = Column(String)
    value = Column(String)
    value_type = Column(String, default="int")
    min_value = Column(Integer, default=0)
    max_value = Column(Integer, default=100)

