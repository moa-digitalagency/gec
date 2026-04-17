"""
Extensions Flask centralisées — évite les imports circulaires.
Tous les modèles importent db depuis ce fichier, pas depuis app.py.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
