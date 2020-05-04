from sqlalchemy import Column, String, Integer
from Models.Model import Model

class ProtocolStatus(Model):
    __tablename__ = 'sv_protocol'
    __table_args__ = {"schema": "oncore"}
    protocol_id = Column(Integer, primary_key=True, nullable=False)
    status = Column(String, nullable=False)