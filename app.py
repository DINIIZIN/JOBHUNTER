from flask import Flask, render_template, request, redirect, url_for, session, flash,abort #criaçao web
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy#cria o objeto db que uso nos models
import os # serve para montar o caminho do arquivo database.db sem dar erro no windows
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Empresa, Acao, Contato
from datetime import timedelta, date, datetime
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer,BadSignature,SignatureExpired
from functools import wraps

mail = Mail()



def create_app():
    app = Flask(__name__)#cria app e usa o nome do modulo para localizar templates/static
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_url = os.environ.get("DATABASE_URL")
    
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://","postgresql", 1)
    

    app.config ["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///database.db"
    app.config #base dir pasta onde esta o app.py
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False#Isso só desliga um recurso antigo que: n e necessário gasta memoria e gera warning
    app.config["SECRET_KEY"] = "Dinicompany"#login, proteção de dados
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)#caso o usuario fique 30 minutos logado porem nao usando a sessão expira
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"]=True
    app.config["MAIL_USE_SSL"]=False
    app.config["MAIL_USERNAME"] =  "jobhunter.dinicompany@gmail.com"
    app.config["MAIL_PASSWORD"] = "brqhoflszfoxssdx"
    app.config["MAIL_DEFAULT_SENDER"] = ("Dinicompany", "jobhunter.dinicompany@gmail.com")
    mail.init_app(app)

    db.init_app(app)#agora você liga o db nesse app com essas configs
    with app.app_context():
        print("TOTAL USUARIOS", Usuario.query.count())
        
        db.create_all()
    
   
    
    
    
    
    
   
    def admin_required(f):
        @wraps(f)
        def wrapper(*args,**kwargs):
            uid = session.get("usuario_id")
            if not uid:
                return redirect(url_for("login"))
            usuario = Usuario.query.get(uid)
            if not usuario or not usuario.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    
    @app.route("/admin/usuarios")
    @admin_required
    def admin_usuarios():
        usuarios = Usuario.query.order_by(Usuario.nome.asc()).all()
        return render_template("admin_usuarios.html", usuarios=usuarios)
    
    @app.route("/admin/impersonar/<int:usuario_id>")
    @admin_required
    def admin_impersonar(usuario_id):
        alvo = Usuario.query.get_or_404(usuario_id)
        if alvo.is_admin:
            abort(403)  
        session["cliente_contexto_id"] = usuario_id
        return redirect(url_for("dashboard"))
    
    @app.route("/admin/sair_cliente")
    @admin_required
    def admin_sair_cliente():
        session.pop("cliente_contexto_id",None)
        return redirect(url_for("admin_usuarios"))


    @app.route("/")
    def home():
        return redirect(url_for("login"))
    
    @app.route("/cadastro", methods = ["GET", "POST"])
    def cadastro():
     if request.method == "GET":
        return render_template("cadastro.html")

     nome = request.form.get("nome")
     email = request.form.get("email")
     senha = request.form.get("senha")
     confirmar = request.form.get("confirmar")

    
    #validações dos dados

     if not nome or not email or not senha or not confirmar:
       flash("Preencha todos os campos.", "error")
       return redirect(url_for("cadastro"))
     if senha != confirmar:
        flash ("Senhas não conferem.","error")
        return redirect(url_for("cadastro"))
     #evitar email duplicado
     existente = Usuario.query.filter_by(email=email).first() #busca o email no banco
     if existente:
        flash ("Email já cadastrado.","error")
        return redirect(url_for("cadastro"))
     #hash senha (criptografia)
     senha_hash = generate_password_hash(senha)


    #criar usuário
     novo = Usuario(nome=nome,email=email,senha_hash=senha_hash)
     db.session.add(novo)#manda para o banco, mas nao salva ainda
     db.session.commit()#Salva os dados no banco
     return redirect(url_for("login"))#Rediriciona para a tela de login
        
    @app.route("/login", methods = ["GET", "POST"])
    def login():
        if request.method == "GET":
                return render_template("login.html")
        email = request.form.get("email")
        senha = request.form.get("senha")
        if not email or not senha:
           flash("Preencha todos os campos", "error")
           return redirect(url_for("login"))
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario or not check_password_hash(usuario.senha_hash, senha):

            flash("Email ou senhas incorretos.", "error")             
            return redirect(url_for("login"))
        
        session.permanent = True
        session["usuario_id"] = usuario.id
        return redirect(url_for("dashboard"))
    
    def gerar_token_reset(email):
        s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        return s.dumps(email, salt = "reset-senha")
    def validar_token_reset(token,max_age=1300):
        s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        try:
            email = s.loads(token, salt="reset-senha", max_age=max_age)
        except:
            return None    
        return email
    
    

    @app.route("/recuperar_senha", methods=["GET", "POST"])
    def recuperar_senha():
     if request.method == "POST":
            email = request.form.get("email")

            if not email:
                flash("Preencha o campo Email", "error")
                return redirect(url_for("recuperar_senha"))

            usuario = Usuario.query.filter_by(email=email).first()

            if not usuario:
                flash("Email incorreto", "error")
                return redirect(url_for("recuperar_senha"))

            token = gerar_token_reset(usuario.email)
            link = url_for("nova_senha", token=token, _external=True)
            msg = Message(
                subject="Recuperação de senha - DiniCompany",
                recipients=[usuario.email]
            )

            msg.body = f"Olá! Clique aqui para redefinir a senha:\n\n{link}.\n\n"
            mail.send(msg)
            
            print("LINK DE RESET:", link)

            flash("Enviamos um link de recuperação para seu email.", "success")
            return redirect(url_for("recuperar_senha"))

     return render_template("recuperar_senha.html")
    # GET
        
    
    @app.route("/nova_senha", methods = ["GET","POST"])
    def nova_senha():
        if request.method == "GET":
            return render_template("nova_senha.html")
        
        
        senha_hash = request.form.get("senha")
        confirmar = request.form.get("confirmar")
        
        usuario_id = session.get("reset_usuario_id")#pega o usuario id da session   
        if not usuario_id:
            return redirect(url_for("recuperar_senha"))
        
        
        
        if not senha_hash or not confirmar:
            return "Preencha todos os campos."   


        if senha_hash != confirmar:
            return "As senhas não conferem"
                
        usuario = Usuario.query.get(usuario_id)
        senha_hash = generate_password_hash(senha_hash)
        db.session.commit()
        
        session.pop("reset_usuario_id", None)
        return redirect(url_for("login"))
    
    @app.route("/reset/<token>", methods =["GET" ,"POST"] )
    def reset_senha(token):
        email = validar_token_reset(token)
        if not email:
            flash("Link inválido ou expirado.")
            return redirect(url_for("login"))
        usuario = Usuario.query.filter_by(eamil=email).first()
        if not usuario:
            flash("Usuário não encontrado.")
            return redirect(url_for("login"))
        if request.method == "GET":
            return render_template("nova_senha.html", token=token)
        nova_senha = request.form.get("senha")
        confirmar = request.form.get("confirmar")

        if nova_senha != confirmar:
            flash("As senhas não conferem.")
            return redirect(url_for("reset_senha", token=token))
        usuario.senha_hash=generate_password_hash(nova_senha)
        db.session.commit()
        flash("Senha alteradada com sucesso!")
        return redirect(url_for("login"))
    @app.route("/dashboard")
    def dashboard():
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        
        if not usuario:
            session.pop("cliente_contexto_id", None)
            uid = session["usuario_id"]
            usuario = Usuario.query.get(uid)
        
        
        admin_id = session.get("usuario_id")
        admin = Usuario.query.get(session["usuario_id"])
        if not admin:
            return redirect(url_for("login"))

        admin_view = False
        usuario = admin  # por padrão, é ele mesmo

        if admin.is_admin and session.get("cliente_contexto_id"):
            usuario = Usuario.query.get(session["cliente_contexto_id"])
            admin_view = True

        if not usuario:
            flash("Cliente inválido."), 400

        empresas = (
            Empresa.query
            .filter_by(usuario_id=usuario.id)
            .order_by(Empresa.status.asc())
            .all()
            )

    # ✅ ações do usuário (cliente alvo)
        acoes = (
            Acao.query
            .filter_by(usuario_id=usuario.id)
            .order_by(Acao.data.desc())
            .all()
        )

    # ✅ agrupa por empresa_id
        acoes_por_empresa = defaultdict(list)
        for a in acoes:
            if a.empresa_id:
                acoes_por_empresa[a.empresa_id].append(a)

        return render_template(
            "dashboard.html",
        usuario=usuario,
        empresas=empresas,
        acoes_por_empresa=acoes_por_empresa,
        admin_view=admin_view,
        admin = admin
    )
    @app.route("/empresa/<int:empresa_id>")
    def empresa_detalhe(empresa_id):

        #proteger rota

        if "usuario_id" not in session:
            return redirect(url_for("login"))

        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))
        #pega o id do usuario logado   
        
        usuario_id = session["usuario_id"]
        
        
        #buscar empresa garantindo que aquela empresa é do usuário
        empresa = Empresa.query.filter_by(id=empresa_id, usuario_id = uid).first()

        if not empresa:
            return "Empresa não encontrada", 404
        
        #contatos da empresa
        contatos = empresa.contatos

        #açoes da empresa, ultimos 30 dias
        inicio = date.today() - timedelta(days=30)
        acoes = Acao.query.filter(
                                  Acao.empresa_id == empresa.id,
                                  Acao.data >=inicio, Acao.usuario_id==usuario.id).order_by(Acao.data.desc()).all()
        return render_template(
            "empresa_detalhe.html",
            usuario=usuario,
            empresa=empresa,
            contatos = contatos,
            acoes = acoes
        )
    
    @app.route("/empresas/nova", methods=["GET", "POST"])
    def nova_empresa():
        print("ENTROU NA ROTA NOVA_EMPRESA")

    # só entra logado
        if "usuario_id" not in session:
            return redirect(url_for("login"))

    # pega o usuario "real" (cliente selecionado pelo admin OU o próprio logado)
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)

        if not usuario:
            return redirect(url_for("login"))

    # GET mostra o formulário
        if request.method == "GET":
            return render_template("nova_empresa.html", usuario=usuario)

    # POST pega dados do form

    # dados do PERFIL (do usuario)
        nome = (request.form.get("nome") or "").strip()
        setor = (request.form.get("setor") or "").strip()

        if not nome or not setor:
            return render_template(
            "nova_empresa.html",
            usuario=usuario,
            erro="Preencha nome e setor."
        )

    # cria empresa vinculada ao usuário correto (admin ou cliente selecionado)
        empresa = Empresa(name=nome, setor=setor, usuario_id=usuario.id)

        db.session.add(empresa)
        db.session.commit()

        return redirect(url_for("dashboard"))
    @app.route("/empresa/<empresa_id>/contatos/novo", methods = ["GET", "POST"])

    def novo_contato(empresa_id):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
          

        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))

        empresa = Empresa.query.filter_by(
            id=empresa_id,
            usuario_id = uid).first()
        
        
        if request.method =="GET":
            return render_template("novo_contato.html", empresa=empresa)
        

        nome = request.form.get("nome")
        cargo = request.form.get('cargo')
        tipo = request.form.get("tipo")

        if not nome or not cargo or not tipo:
            return "Preencha todos os campos.",400
        

        
        contato = Contato(name=nome, cargo=cargo, tipo=tipo, empresa_id=empresa.id)
        db.session.add(contato)
        db.session.commit()
        
        return redirect(url_for("empresa_detalhe", empresa_id=empresa.id))
   
   
    @app.route("/empresa/<int:empresa_id>/acao/novo", methods = ["GET", "POST"])
    def nova_acao(empresa_id):    
        if "usuario_id" not in session:
            return redirect(url_for("login"))   



        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))
        empresa = Empresa.query.filter_by(id=empresa_id, usuario_id=uid).first()
        if not empresa:
            return "Empresa nao encontrada",404

        if request.method == "GET":
            return render_template("nova_acao.html", usuario=usuario, empresa=empresa)
        acoes = Acao.query.filter_by(usuario_id=uid).order_by(Acao.id.desc()).all()
        
        acoes_por_empresa = {}
        for a in acoes:
           if not a.empresa_id:
                continue
           if a.empresa_id not in acoes_por_empresa:
              acoes_por_empresa[a.empresa_id] = {}
           acoes_por_empresa[a.empresa_id]

        
        acao = Acao(
        descricao = request.form.get("descricao").strip(),
        tipo = request.form.get("tipo").strip(),
        status = request.form.get("status", "").strip(),
        responsavel = request.form.get("responsavel", "").strip(),
        data= datetime.strptime(request.form.get("data"), "%Y-%m-%d").date(),
        usuario_id=uid,
        empresa_id=empresa_id
        )
        
        db.session.add(acao)
        db.session.commit()
        return redirect(url_for("empresa_detalhe", empresa_id=empresa.id))
    

    @app.route("/empresa/<int:empresa_id>/editar", methods = ["GET","POST"])
    def editar_empresa(empresa_id):

        if "usuario_id" not in session:
            return redirect(url_for("login"))
        
        usuario_id = session["usuario_id"]
       
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))

        empresa=Empresa.query.filter_by(
            id = empresa_id,
            usuario_id = uid,
        ).first()
       

        if not empresa:
            return "Empresa não encontrada", 404
        


        if request.method == "GET":
            return render_template("editar_empresa.html", usuario=usuario, empresa=empresa)

        nome = (request.form.get("nome") or "").strip()
        setor = (request.form.get("setor") or "").strip() 
        status = (request.form.get("status") or "").strip()

        if not nome or not setor:
            return "Preencha nome e setor"

        empresa.name = nome        
        empresa.setor = setor
        empresa.status = status

        
            
        db.session.commit()

        return redirect(url_for("empresa_detalhe", empresa_id=empresa.id))        
        
    @app.route("/mapeamento", methods = ["GET","POST"])
    def editar_mapeamento():
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        usuario = Usuario.query.get(session['usuario_id'])
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))
        if request.method == "GET":
            return render_template("editar_mapeamento.html", usuario=usuario)
        usuario.senioridade = (request.form.get("senioridade") or "").strip()
        usuario.objetivo = (request.form.get("objetivo") or "").strip()
        usuario.empresa_interesse = (request.form.get("empresa_interesse") or "").strip()
        db.session.commit()
        print(request.form)
        return redirect(url_for("dashboard"))
       
    @app.route("/perfil", methods = ["GET", "POST"])
    def perfil():
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        usuario = Usuario.query.get(session["usuario_id"])

        
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))
        
        if request.method == "GET":
            return render_template("perfil.html", usuario=usuario)  
        usuario.nome = request.form.get("nome")
        usuario.cargo_atual = request.form.get("cargo_atual")
        usuario.empresa_atual = request.form.get("empresa_atual")

        db.session.commit()
        return redirect(url_for("dashboard"))
    
    @app.route("/acao/<int:acao_id>/editar", methods=["GET", "POST"])
    def editar_acao(acao_id):
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        
        uid = session.get("cliente_contexto_id") or session["usuario_id"]
        usuario = Usuario.query.get(uid)
        if not usuario:
            return redirect(url_for("login"))
        usuario_id = session["usuario_id"]

        acao = Acao.query.filter_by(id=acao_id, usuario_id=usuario_id).first()
        if not acao:
                flash( "Ação não encontrada"), 404


        

        if request.method == "GET":
            return render_template("editar_acao.html", acao=acao)

        acao.descricao = request.form.get("descricao")
        acao.tipo = request.form.get("tipo")
        acao.status = request.form.get("status")
        acao.responsavel = request.form.get("responsavel")
        data_str=request.form.get("data")
        usuario_id=usuario_id,
        acao.empresa_id=acao.empresa_id
        if data_str:
            try:
                acao.data=datetime.strptime(data_str,"%Y-%m-%d").date()
            except ValueError:
                acao.data=None
        else:
                acao.data = None


        db.session.commit()

        if acao.empresa_id:
            return redirect(url_for("empresa_detalhe", empresa_id=acao.empresa_id))

        return redirect(url_for("dashboard"))

    @app.route("/empresa/<int:empresa_id>/anotacoes", methods = ["POST"])

    def salvar_anotacoes_cliente(empresa_id):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        
        usuario_id = session["usuario_id"]

        empresa = Empresa.query.filter_by(id=empresa_id,usuario_id=usuario_id).first_or_404()
        if not empresa:
            return "empresa não encontrada", 404

        texto = request.form.get("anotacoes_cliente", "").strip()

        empresa.anotacoes_cliente = texto
        db.session.commit()
        
        return redirect(url_for("empresa_detalhe", empresa_id=empresa.id))


    @app.route("/logout")
    def logout():
        session.pop("usuario_id", None)
        return redirect(url_for("login"))
    return app#retorna o app, está configurado e conectado ao banco




