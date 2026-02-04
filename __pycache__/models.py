from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
db = SQLAlchemy()





class Empresa(db.Model):
    
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(40), nullable = False)
    setor = db.Column(db.String(120), nullable = False)
    status = db.Column(db.String(30), nullable = False, default = "Mapeada")
    anotacoes_cliente = db.Column(db.Text(), nullable = True, default = "")


    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable = False,
    

)
    contatos = db.relationship("Contato", backref = "empresa", lazy = True)#uma empresa tem vários contatos
 
class Contato(db.Model):
   
    __tablename__ = "contatos"
   
    id = db.Column(db.Integer, primary_key = True)
    name =  db.Column(db.String(40), nullable = False)
    cargo = db.Column(db.String(30), nullable = False)
    tipo = db.Column(db.String(20), nullable = False)
   
    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id"),# cada contanto pertence a uma unica empresa
        nullable = False
    )


class Acao(db.Model):
    
    __tablename__ = "acoes"
    
    id = db.Column(db.Integer, primary_key = True)
    descricao = db.Column(db.String(150), nullable = True)
    tipo = db.Column(db.String(30), nullable = False)
    status = db.Column(db.String(20), nullable = False)

    responsavel = db.Column(db.String(30), nullable = False)

    data = db.Column(db.Date, nullable = False, default = date.today)
   
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable = False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable = True)
    contato_id = db.Column(db.Integer, db.ForeignKey("contatos.id"), nullable = True)

class Usuario(db.Model):
    
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key = True)
    nome = db.Column(db.String(40), nullable = False)
    email = db.Column(db.String(100), nullable = False, unique = True)
    senha_hash =db.Column(db.String(200), nullable=False) 
    
    is_admin = db.Column(db.Boolean, default = False)
    
    status = db.Column(db.String(30), nullable = False, default = "Mapeada")

    senioridade = db.Column(db.String(30), nullable = True)
    cargo_alvo= db.Column(db.String(20), nullable = True)
    objetivo = db.Column(db.String(250), nullable = True)
    cargo_atual = db.Column(db.String(20), nullable = True)
    empresa_atual = db.Column(db.String(30), nullable = True)
    empresa_interesse = db.Column(db.String(200), nullable = True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    empresas = db.relationship("Empresa", backref = "usuario", lazy=True, cascade = "all, delete-orphan")
    acoes = db.relationship("Acao", backref = "usuario", lazy = True, cascade = "all, delete-orphan")