import requests
from urllib.parse import urljoin
from urllib3.exceptions import InsecureRequestWarning
from urllib3._collections import HTTPHeaderDict
from bs4 import BeautifulSoup
from datetime import date
import re

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class DetranClientException(Exception):
    pass

class DetranClient:
    def __init__(self):
        self._base_url = "https://novocfcweb.detran.rj.gov.br"
        self._token = "28f01b0e84b6d53e:pt-BR:2a06c7e2-728e-4b15-83d6-9b269fb7261e:de1feab2:f2c8e708:720a52bf:f9cec9bc:7311d143"
        
        self._client = requests.Session()
        self._client.verify = False
    
    def login(self, username, password):
        response = self._client.get(urljoin(self._base_url, "/login.aspx"))
        self._update_state(response.text)

        req_data = {
            "txtUsuario" : username,
            "txtSenha" : password,
            "btnLogin" : "Entrar",
            "ComputerName" : "",
            "__LASTFOCUS" : "",
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/login.aspx"), data=req_data)

        doc = BeautifulSoup(response.text, "html.parser")
        span = doc.find("span", {"id": "CFCMaster_lblNmUsuario"})
        
        if span is None:
            span = doc.find("span", {"id": "lblMensagem"})
            msg = "Erro desconhecido." if span is None else span.text
            raise DetranClientException(msg)
    
    def logout(self):
        self._client.get(urljoin(self._base_url, "/logout.aspx"))
    
    def get_agendamentos(self, curso):
        agendamentos = []

        response = self._client.get(urljoin(self._base_url, "/CFC/AGENDAMENTO3.ASPX"))
        self._update_state(response.text)

        req_data = HTTPHeaderDict()
        req_data.add("CFCMaster_cphBody_ToolkitScriptManager1_HiddenField", f";;AjaxControlToolkit, Version=3.5.51116.0, Culture=neutral, PublicKeyToken={self._token}")
        req_data.add("CFCMaster$cphBody$Acord_AccordionExtender_ClientState", "0")
        req_data.add("chkServico", "on")
        req_data.add("CFCMaster$cphBody$btnAgendamento", "Button")
        req_data.add("CFCMaster$cphBody$hdiServi", f"1_{curso['tipo']}{curso['idCurso']},")
        req_data.add("CFCMaster$cphBody$hdiPeriodo", "")
        req_data.add("CFCMaster$cphBody$hdiData", curso["data"])

        for i in range(0, 7):
            req_data.add("DataServico", curso["data"])

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/AGENDAMENTO3.ASPX"), data=req_data)

        results = re.findall('_dados\[".*;', response.text)
        for result in results:
            agendamento = {}
            result_parts = result.split('=')
            match = re.match('_dados\["(.*?)"', result_parts[0])
            parts = match.group(1).split("_")
            agendamento["id"] = parts[0][1:]
            agendamento["idInstrutor"] = parts[1]
            
            match = re.match('\[(.*)\]', result_parts[1].strip())
            parts = match.group(1).split(',')
            parts = [p.strip("'").strip('"').strip(" ") for p in parts]
            parts = [p.strip("'").strip('"').strip(" ") for p in parts]
            hi = parts[1].zfill(4)
            ht = parts[3].zfill(4)
            agendamento["tipoCurso"] = parts[0]
            agendamento["horaInicio"] = hi[0:2] + ":" + hi[2:]
            agendamento["horaTermino"] = ht[0:2] + ":" + ht[2:]
            agendamento["nomeInstrutor"] = parts[4]
            agendamentos.append(agendamento)
        
        agendamentos = list(filter(lambda x: x["tipoCurso"] == curso["tipo"], agendamentos))
        
        if 'idInstrutor' in curso:
            agendamentos = list(filter(lambda x: x["idInstrutor"] == curso["idInstrutor"], agendamentos))
        
        if 'horaInicio' in curso:
            agendamentos = list(filter(lambda x: x["horaInicio"] == curso["horaInicio"], agendamentos))
        
        
        return agendamentos
    
    def get_alunos_teoricos(self,agendamento):
        alunos = []
        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx?idGradeCurso=" + agendamento["idAula"] + "&"))
        self._update_state(response.text)
        doc = BeautifulSoup(response.text, "html.parser")
        
        alunos_cpfs = doc.find_all('span', {'id': re.compile(r'_Label2')})
        alunos_nomes = doc.find_all('span', {'id': re.compile(r'_Label1')})
        i = 0
        for aluno_cpf in alunos_cpfs:
            aluno = {}
            aluno['cpf'] = aluno_cpf.text
            aluno['nome'] = alunos_nomes[i].text
            alunos.append(aluno)
            i += 1
        
        return alunos

    def get_salas(self):
        salas = dict()
        hoje = date.today()
        data_hoje = hoje.strftime("%d/%m/%Y")

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento3_Novo.aspx?tpCurso=T&data=" + data_hoje + "&hrInicio=600&hrTermino=1715&idInstrutor=0&idCurso=2&categoria=&servico=1"))
        self._update_state(response.text)
    
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlSala"})
        options = filter(None, select.findAll("option"))
        for option in options:
            if option.text in option:
                option_value = int(option['value'])
                option_text = option.text
                salas[option_value]=option_text
        
        return salas
    
        
    def get_instrutores(self):
        instrutores = dict()
        curso = dict()
        hoje = date.today()
        data_futura = date(hoje.year + 1, hoje.month, hoje.day)
        data_futura = data_futura.strftime("%d/%m/%Y")

        
        response = self._client.get(urljoin(self._base_url, "/CFC/AGENDAMENTO3.ASPX"))
        self._update_state(response.text)

        req_data = HTTPHeaderDict()
        req_data.add("CFCMaster_cphBody_ToolkitScriptManager1_HiddenField", f";;AjaxControlToolkit, Version=3.5.51116.0, Culture=neutral, PublicKeyToken={self._token}")
        req_data.add("CFCMaster$cphBody$Acord_AccordionExtender_ClientState", "0")
        req_data.add("chkServico", "on")
        req_data.add("CFCMaster$cphBody$btnAgendamento", "Button")
        ''' req_data.add("CFCMaster$cphBody$hdiServi", f"1_{curso['tipo']}{curso['idCurso']},") '''
        req_data.add("CFCMaster$cphBody$hdiServi","1_T1,1_T2,1_T3,1_T4,1_T5,1_P7,1_P8,1_P9,1_P13,1_P14,1_P16,1_P17,1_P18,1_P35,1_P36,1_P37,1_P38,1_P39,1_P40,")
        req_data.add("CFCMaster$cphBody$hdiPeriodo", "")
        req_data.add("CFCMaster$cphBody$hdiData", data_futura)

        for i in range(0, 7):
            req_data.add("DataServico", data_futura)

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/AGENDAMENTO3.ASPX"), data=req_data)

        nome_instrutores = re.findall('<div class="divInstrutor">([^<]+)</div>', response.text)
        ids_instrutores_raw = re.findall('<div onclick="cNovo([^<]+);" class="CellAulaVE CellAulaVD" style="width: 1036px;" >&nbsp;</div>', response.text)
    
        for linha in range(len(ids_instrutores_raw)):
            id_instrutor = ids_instrutores_raw[linha]
            id_instrutor = id_instrutor.replace("'","").replace('"','').replace('(','').replace(')','')
            id_instrutor = id_instrutor.split(',')
            id_instrutor = id_instrutor[4]
            instrutores[id_instrutor]=nome_instrutores[linha]
        
        return instrutores
    
    def get_veiculos(self):
        veiculos = dict()
        hoje = date.today()
        data_hoje = hoje.strftime("%d/%m/%Y")
        
        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx?data=" + data_hoje + "&idInstrutor=0&idCurso=8&categoria=A"))
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = filter(None, select.findAll("option"))
    
        for option in options:
            option_value = int(option['value'])
            option_text = option.text
            if option_value > 0:
                ''' veiculos_categoria_a.insert(option_value, option_text) '''
                veiculos[option_value]=option_text
        
        
        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx?data=" + data_hoje + "&idInstrutor=0&idCurso=9&categoria=B"))
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = filter(None, select.findAll("option"))
    
        for option in options:
            option_value = int(option['value'])
            option_text = option.text
            if option_value > 0:
                ''' veiculos_categoria_b.insert(option_value, option_text) '''
                veiculos[option_value]=option_text
        
        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx?data=" + data_hoje + "&idInstrutor=0&idCurso=8&categoria=C"))
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = filter(None, select.findAll("option"))
    
        for option in options:
            option_value = int(option['value'])
            option_text = option.text
            if option_value > 0:
                ''' veiculos_categoria_a.insert(option_value, option_text) '''
                veiculos[option_value]=option_text

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx?data=" + data_hoje + "&idInstrutor=0&idCurso=11&categoria=D"))
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = filter(None, select.findAll("option"))
    
        for option in options:
            option_value = int(option['value'])
            option_text = option.text
            if option_value > 0:
                ''' veiculos_categoria_b.insert(option_value, option_text) '''
                veiculos[option_value]=option_text
        
        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx?data=" + data_hoje + "&idInstrutor=0&idCurso=8&categoria=E"))
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = filter(None, select.findAll("option"))
    
        for option in options:
            option_value = int(option['value'])
            option_text = option.text
            if option_value > 0:
                ''' veiculos_categoria_a.insert(option_value, option_text) '''
                veiculos[option_value]=option_text
        ''' veiculos = veiculos_categoria_a + veiculos_categoria_b '''
        
        return veiculos

    def criar_agendamento(self, agendamento):
        req_params = {
            "tpCurso" : agendamento["tipoCurso"],
            "data" : agendamento["data"],
            "hrInicio" : "650",
            "hrTermino" : "2300",
            "idInstrutor" : agendamento["idInstrutor"],
            "idCurso" : agendamento["idCurso"],
            "categoria" : "",
            "servico" : "1",
        }

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento3_Novo.aspx"), params=req_params)
        self._update_state(response.text)

        doc = BeautifulSoup(response.text, "html.parser")
        hdiServCurso = doc.find("input", {"id" : "hdiServCurso"})["value"]

        select = doc.find("select", {"id": "ddlSala"})
        options = select.findAll("option")
        salas = [option["value"] for option in options]
        salas = list(filter(lambda x: len(x) > 0, salas))

        sala = None
        if "sala" not in agendamento:
            sala = salas[0]
        else:
            sala = agendamento["sala"]

        req_data = {
            "txtHoraInicio" : agendamento["horaInicio"],
            "txtHoraTermino" : agendamento["horaTermino"],
            "hdiServCurso" : hdiServCurso,
            "ddlSala" : sala,
            "btnCriarTeorico" : "Criar Aula Teórica",
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/Agendamento3_Novo.aspx"), params=req_params, data=req_data)
        doc = BeautifulSoup(response.text, "html.parser")
        span = doc.find("span", {"id" : "lblMensagem"})

        if span is None:
            span = doc.find("span", {"id": "lblMotivo"})
        
        if span is not None:
            raise DetranClientException(span.text)

    def excluir_agendamento(self, agendamento):
        req_params = {
            "idGradeCurso" : agendamento["id"],
            "tpCurso" : agendamento["tipoCurso"],
            "idInstrutor" : agendamento["idInstrutor"]
        }

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx"), params=req_params)
        self._update_state(response.text)

        req_data = {
            "__EVENTTARGET" : "lkbExcluirGrade",
            "txtCPF": "",
            "uf": "RJ",
            "TxtRJ": "",
        }
        
        self._add_state(req_data)
        self._client.post(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx"), params=req_params, data=req_data)
    
    def agendar_candidato_teorica(self, candidato, agendamento):
        req_params = {
            "idGradeCurso" : agendamento["id"],
            "tpCurso" : agendamento["tipoCurso"],
            "idInstrutor" : agendamento["idInstrutor"]
        }

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx"), params=req_params)
        self._update_state(response.text)

        req_data = {
            "txtCPF": candidato["cpf"],
            "uf": "RJ",
            "TxtRJ": candidato["renach"],
            "btnConsultarCandidato" : "Consultar"
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx"), params=req_params, data=req_data)
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        button = doc.find("input", {"id" : "btnAgendarCandidato"})
        if button is None:
            raise DetranClientException("Erro ao tentar consultar candidato.")
        
        req_data = {
            "uf": "RJ",
            "btnAgendarCandidato": "Agendar Candidato",
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/Agendamento_Candidato.aspx"), params=req_params, data=req_data)
        
        doc = BeautifulSoup(response.text, "html.parser")
        span = doc.find("span", {"id" : "lblMensagem"})

        if span.text.find("Candidato agendado com sucesso.") != -1:
            return

        error_msg = "Erro desconhecido." if span is None else span.text
        raise DetranClientException(error_msg)

    def agendar_candidato_pratica(self, candidato, agendamento):
        req_params = {
            "data" : agendamento["data"],
            "idInstrutor" : agendamento["idInstrutor"],
            "idCurso" : agendamento["idCurso"],
            "categoria" : agendamento["categoria"]
        }

        response = self._client.get(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx"), params=req_params)
        self._update_state(response.text)
        


        doc = BeautifulSoup(response.text, "html.parser")
        select = doc.find("select", {"id": "ddlVeiculo"})
        options = select.findAll("option")
        veiculos = [option["value"] for option in options]
        veiculos = list(filter(lambda x: len(x) > 0, veiculos))

        veiculo = None
        if "veiculo" not in agendamento:
            veiculo = veiculos[0]
        else:
            veiculo = agendamento["veiculo"]
            '''
            if veiculo not in veiculos:
                raise DetranClientException(f"Veículo ({veiculo}) não encontrado.")
            '''
        req_data = {
            "ddlVeiculo" : veiculo,
            "txtCPF" : candidato["cpf"],
            "uf" : "RJ",
            "TxtRJ" : candidato["renach"],
            "ddlMinutos" : agendamento["minutos"],
            "btnBuscar" : "Buscar"
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx"), params=req_params, data=req_data)
        self._update_state(response.text)
        
        doc = BeautifulSoup(response.text, "html.parser")
        button = doc.find("input", {"id" : "btnAgendarPratico"})
        if button is None:
            raise DetranClientException("Erro ao tentar consultar candidato.")

        select = doc.find("select", {"id": "ddlServicoPratico"})
        options = select.findAll("option")
        servicos = [option["value"] for option in options]
        servicos = list(filter(lambda x: len(x) > 0, servicos))

        horarios_temp = []
        horarios = {}

        tables = doc.find_all('table')
        table = tables[4]
        rows = table.find_all('tr')
        for row in rows[1:-1]:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            horarios_temp.append([ele for ele in cols if ele])
        
        divs = doc.find_all("div", {"style": "position: absolute; visibility: hidden; top: 500px"})
        for idx, div in enumerate(divs[:-1]):
            horarioId = div.find_all("span")[0].find("input")["name"]
            horarios[horarios_temp[idx][0]] = horarioId

        horario = agendamento["horario"]
        if horario not in horarios:
            raise DetranClientException(f"Horário ({horario}) não encontrado.")

        req_data = {
            "uf" : "RJ",
            horarios[horario] : "on",
            "ddlServicoPratico" : servicos[0],
            "btnAgendarPratico" : "Agendar Candidato",
        }

        self._add_state(req_data)
        response = self._client.post(urljoin(self._base_url, "/CFC/Agendamento_Pratico.aspx"), params=req_params, data=req_data)
        
        doc = BeautifulSoup(response.text, "html.parser")
        span = doc.find("span", {"id" : "lblResultado"})

        if span.text.find("Agendamento realizado com sucesso") != -1:
            return

        error_msg = "Erro desconhecido." if span is None else span.text
        raise DetranClientException(error_msg)
        
    def consulta_presenca(self, candidato):
        agendamentos = dict()  #vai retornar por aqui 
        #agendamentos['cpf'] = candidato["cpf"] 
        response = self._client.get(urljoin(self._base_url, "/CRT/CONSCURSOS2.ASPX"))
        self._update_state(response.text)
        
        
        req_data = HTTPHeaderDict()
        req_data.add("CFCMaster_cphBody_ToolkitScriptManager1_HiddenField", f";;AjaxControlToolkit, Version=3.5.51116.0, Culture=neutral, PublicKeyToken={self._token}")
        req_data.add("CFCMaster$cphBody$txtCPF", candidato["cpf"])
        req_data.add("CFCMaster$cphBody$TxtRJ", "")
        req_data.add("CFCMaster$cphBody$uf", "RJ")
        req_data.add("CFCMaster$cphBody$btnConsultar", "Consultar")
        self._add_state(req_data)
        
        response = self._client.post(urljoin(self._base_url, "/CRT/CONSCURSOS2.ASPX"), data=req_data)
        #self._update_state(response.text)
        #return response.text
        data = []
        #if candidato["IdServico"] == 1 and candidato["IdCurso"] == 0:
        disciplinas = ["1","2","3","4","5"]
        for disciplina_id in disciplinas:
            url_consulta_aulas = self._base_url + "/CRT/ConsAulas.aspx?CPF=" + candidato["cpf"] + "&IdCurso=" + disciplina_id + "&IdServico=" + candidato["IdServico"]
            response = self._client.get(url_consulta_aulas)
            soap = BeautifulSoup(response.text, "html.parser")
            table = soap.find("table", {"class": "TabelaTexto"})
            self.decomposeHtmlPresenca(table)
            data = data + self.extractDataPresenca(table,disciplina_id)
                #data = data + disciplina_id
        #else:
        #    url_consulta_aulas = self._base_url + "/CRT/ConsAulas.aspx?CPF=" + candidato["cpf"] + "&IdCurso=" + candidato["IdCurso"] + "&IdServico=" + candidato["IdServico"]
        #    response = self._client.get(url_consulta_aulas)
        #    soap = BeautifulSoup(response.text, "html.parser")
        #    table = soap.find("table", {"class": "TabelaTexto"})
        #    self.decomposeHtmlPresenca(table)
        #    data = self.extractDataPresenca(table,candidato["IdCurso"])
        #    #self._update_state(response.text)
        
        return data
    
    ##########
    
    def candidato_status_presenca(self,html):
        retorno = {}
        match_entrada = re.search(r'imgInicioCandidatoS" src="(.*?)imagem(.*?)"', html)
        if match_entrada:
            match_entrada = match_entrada.group(2).replace("/","").replace(".jpg","").replace(".gif","")
            if(match_entrada == 'ok'):
                retorno['entrada'] = True
            else:
                retorno['entrada'] = False
        else:
            retorno['entrada'] = False    
            
        match_saida = re.search(r'imgSaidaCandidatoS" src="(.*?)imagem(.*?)"', html)
        if match_saida:
            match_saida = match_saida.group(2).replace("/","").replace(".jpg","").replace(".gif","")
            if(match_saida == 'ok'):
                retorno['saida'] = True
            else:
                retorno['saida'] = False
        else:
            retorno['saida'] = False
            
        return retorno
    
    def instrutor_status_presenca(self,html):
        retorno = {}
        match_entrada = re.search(r'imgInicioInstrutorS" src="(.*?)imagem(.*?)"', html)
        if match_entrada:
            match_entrada = match_entrada.group(2).replace("/","").replace(".jpg","").replace(".gif","")
            if(match_entrada == 'ok'):
                retorno['entrada'] = True
            else:
                retorno['entrada'] = False
        else:
            retorno['entrada'] = False    
            
        match_saida = re.search(r'imgSaidaInstrutorS" src="(.*?)imagem(.*?)"', html)
        if match_saida:
            match_saida = match_saida.group(2).replace("/","").replace(".jpg","").replace(".gif","")
            if(match_saida == 'ok'):
                retorno['saida'] = True
            else:
                retorno['saida'] = False
        else:
            retorno['saida'] = False
            
        return retorno 
    
    def decomposeHtmlPresenca(self, htmlParant: BeautifulSoup.object_was_parsed):
        decompseObject = [{"class": "TrTitulo"}, {"style": "background-color: #FFFFFF"}]
        for objectHtml in decompseObject:
            htmlParant.find("tr", objectHtml).decompose()

    def extractDataPresenca(self, table, disciplina_id):
        infos = list()

        for tr in table.findAll("tr"):
            tds = tr.findAll("td")
            
            #Gambiarra catarenta para eliminar duplicidade =)
            imagens_status_clear = {}
            for coluna in tds:
                imagens_coluna = coluna.findAll("img")
                for imagem_coluna in imagens_coluna:
                    imagens_status_clear[str(imagem_coluna)] = str(imagem_coluna)

            imagens_status = ""
            for imagem_status in imagens_status_clear:
                imagens_status = imagens_status + imagem_status + '<br/>'

            if tds[0]['align'] == 'center':
                continue
            
            horarios_aula = re.findall("\d{2}:\d{2}", tds[2].text.strip())

            if len(horarios_aula) > 0:
                horario_aula_inicial = horarios_aula[0]
            else:
                horario_aula_inicial = '00:00'

            if len(horarios_aula) > 1:
                horario_aula_final = horarios_aula[1]
            else:
                horario_aula_final = '00:00'

            aluno_presenca = self.candidato_status_presenca(imagens_status)
            instrutor_presenca = self.instrutor_status_presenca(imagens_status)   
                
            infos.append({
                "disciplina_id": disciplina_id,
                "cfc": tds[0].text.strip(),
                "data_agendamento": tds[1].text.strip(), #datetime.datetime.strptime(tds[1].text.strip(), '%d/%m/%Y')
                "hora_inicio": horario_aula_inicial,
                "hora_fim": horario_aula_final,
                "instrutor": tds[3].text.strip(),
                "aluno_entrada": aluno_presenca['entrada'], #ok.jpg = true e erro.gif = false - rptAulas_ctl01_imgInicioCandidatoS esse 01 vai aumentando o numero
                "aluno_saida": aluno_presenca['saida'],  #ok.jpg = true e erro.gif = false  - rptAulas_ctl01_imgSaidaCandidatoS  esse 01 vai aumentando o numero
                "instrutor_entrada": instrutor_presenca['entrada'], #ok.jpg = true e erro.gif = false - rptAulas_ctl01_imgInicioInstrutorS esse 01 vai aumentando o numero
                "instrutor_saida": instrutor_presenca['saida'],  #ok.jpg = true e erro.gif = false - rptAulas_ctl01_imgSaidaInstrutorS esse 01 vai aumentando o numero
                "situacao": tds[12].text.strip(),
                "periodo": tds[13].text.strip()
                #"imagens_status": imagens_status
            })
        
        return infos 
    
    ##########
        
    def _update_state(self, html):
        doc = BeautifulSoup(html, "html.parser")
        self._viewstate = doc.find("input", {"id": "__VIEWSTATE"})["value"]
        self._viewstate_generator = doc.find("input", {"id": "__VIEWSTATEGENERATOR"})["value"]
        self._eventvalidation = doc.find("input", {"id": "__EVENTVALIDATION"})["value"]
    
    def _add_state(self, req):
        req["__VIEWSTATE"] = self._viewstate
        req["__VIEWSTATEGENERATOR"] = self._viewstate_generator
        req["__EVENTVALIDATION"] = self._eventvalidation

        if "__EVENTARGUMENT" not in req:
            req["__EVENTARGUMENT"] = ""
        
        if "__EVENTTARGET" not in req:
            req["__EVENTTARGET"] = ""