from flask import Flask, request
import uuid

from shared_memory_dict import SharedMemoryDict
from detran_rj import DetranClient, DetranClientException

app = Flask(__name__)

#clients = {}
clients = SharedMemoryDict(name='clients', size=1024)

@app.route("/")
def padrao():
    return '<meta http-equiv="refresh" content="0;url=https://cfcnuvem.com"/>' 

@app.route('/rj/login', methods=['POST'])
def login():
    try:
        content = get_content(["usuario", "senha"])

        client = DetranClient()
        client.login(content["usuario"], content["senha"])
        token = uuid.uuid4().hex
        
        clients = SharedMemoryDict(name='clients', size=1024)
        
        clients[token] = client
        
        return {
            "sucesso" : True,
            "token" : token
        }    
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error() 

@app.route('/rj/logout', methods=['POST'])
def logout():
    try:
        content = get_content(["token"])
        
        client = get_client(content)
        client.logout()
        clients = SharedMemoryDict(name='clients', size=1024)
        del clients[content["token"]]
        return ok()
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/agendamentos', methods=['POST'])
def get_agendamentos():
    try:
        content = get_content(["token", "idCurso", "tipo", "data"])
        client = get_client(content)

        agendamentos = client.get_agendamentos(content)
        return {
            "sucesso" : True,
            "agendamentos" : agendamentos
        }
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/alunos/teoricos', methods=['POST'])
def get_alunos_teoricos():
    try:
        content = get_content(["token", "idAula"])
        client = get_client(content)

        alunos = client.get_alunos_teoricos(content)
        return {
            "sucesso" : True,
            "alunos" : alunos
        }
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/salas', methods=['POST'])
def get_salas():
    try:
        content = get_content(["token"])
        client = get_client(content)

        salas = client.get_salas()
        return {
            "sucesso" : True,
            "salas" : salas
        }
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error() 

@app.route('/rj/veiculos', methods=['POST'])
def get_veiculos():
    try:
        content = get_content(["token"])
        client = get_client(content)

        veiculos = client.get_veiculos()
        return {
            "sucesso" : True,
            "veiculos" : veiculos
        }
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()        

@app.route('/rj/instrutores', methods=['POST'])
def get_instrutores():
    try:
        content = get_content(["token"])
        client = get_client(content)

        instrutores = client.get_instrutores()
        return {
            "sucesso" : True,
            "instrutores" : instrutores
        }
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()        

@app.route('/rj/agendamentos/novo', methods=['POST'])
def criar_agendamento():
    try:
        content = get_content(["token", "tipoCurso", "data", "idInstrutor", "idCurso", "horaInicio", "horaTermino"])
        
        client = get_client(content)
        client.criar_agendamento(content)
        return ok()
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/agendamentos/excluir', methods=['POST'])
def excluir_agendamento():
    try:
        content = get_content(["token", "id", "tipoCurso", "idInstrutor"])
        
        client = get_client(content)
        client.excluir_agendamento(content)
        return ok()
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/candidatos/agendar/teorica', methods=['POST'])
def agendar_candidato_teorica():
    try:
        content = get_content(["token", "cpf", "renach", "agendamento"])
        validate_content(content["agendamento"], ["id", "tipoCurso", "idInstrutor"])
        
        client = get_client(content)
        client.agendar_candidato_teorica(content, content["agendamento"])
        return ok()
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()

@app.route('/rj/candidatos/agendar/pratica', methods=['POST'])
def agendar_candidato_pratica():
    try:
        content = get_content(["token", "cpf", "renach", "agendamento"])
        validate_content(content["agendamento"], ["data", "idInstrutor", "idCurso", "categoria", "veiculo", "minutos", "horario"])
    
        client = get_client(content)
        client.agendar_candidato_pratica(content, content["agendamento"])
        return ok()
    except DetranClientException as e:
        return error(e.args[0])
    except:
        return error()
        
###################################################################
#   Utils
###################################################################

def get_client(content):
    token = content["token"]
    clients = SharedMemoryDict(name='clients', size=1024)
    if token not in clients:
        raise DetranClientException("Token não encontrado.")
    return clients[token]

def get_content(required_fields):
    content = request.json
    validate_content(content, required_fields)
    return content

def validate_content(content, required_fields):
    for field in required_fields:
        if field not in content:
            raise DetranClientException("Requisição inválida.")

def error(msg="Erro desconhecido ao processar requisição."):
    return {
        "sucesso" : False,
        "msg": msg
    }

def invalid_request():
    return error("Requisição inválida.")

def ok():
    return {
        "sucesso" : True
    }