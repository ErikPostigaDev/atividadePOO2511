# acesso ao mysql (dao = uma classe por tabela)
# todas as consultas usam %s para evitar sql injection
from pathlib import Path

import mysql.connector
from mysql.connector import Error, errorcode

import config
from models import formato_data, validacaoerror


class errobanco(Exception):
    """erro do banco, já com mensagem pronta pro usuário"""


class conexao:
    @staticmethod
    def abrir(com_banco=True):
        dados = dict(config.db_config)
        if com_banco:
            dados["database"] = config.db_name
        try:
            return mysql.connector.connect(**dados)
        except Error as e:
            if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise errobanco("usuário ou senha do mysql errados. ajuste o config.py.")
            raise errobanco(f"não deu pra conectar no mysql: {e}")

    @classmethod
    def inicializar(cls):
        """cria o banco e as tabelas se ainda não existirem"""
        script = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
        script = script.replace("exists clinica_vet", f"exists {config.db_name}")
        script = script.replace("use clinica_vet", f"use {config.db_name}")
        # tira os comentários antes de separar os comandos pelo ';'
        script = "\n".join(l for l in script.splitlines() if not l.strip().startswith("--"))
        con = cls.abrir(com_banco=False)
        try:
            cur = con.cursor()
            for comando in script.split(";"):
                if comando.strip():
                    cur.execute(comando)
            con.commit()
        except Error as e:
            raise errobanco(f"erro ao criar o banco: {e}")
        finally:
            con.close()

    @classmethod
    def executar(cls, sql, params=()):
        """insert, update e delete. devolve o id criado (se tiver)"""
        con = cls.abrir()
        try:
            cur = con.cursor()
            cur.execute(sql, params)
            con.commit()
            return cur.lastrowid
        except Error as e:
            con.rollback()
            if e.errno == errorcode.ER_DUP_ENTRY:
                raise errobanco("já existe um registro com esse cpf/crmv.")
            if e.errno == errorcode.ER_ROW_IS_REFERENCED_2:
                raise errobanco("não dá pra excluir: esse registro está ligado a outros "
                                "(animais ou consultas).")
            if e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
                raise errobanco("o tutor, animal ou veterinário escolhido não existe mais.")
            raise errobanco(f"erro no banco: {e}")
        finally:
            con.close()

    @classmethod
    def consultar(cls, sql, params=()):
        """select. devolve uma lista de dicionários"""
        con = cls.abrir()
        try:
            cur = con.cursor(dictionary=True)
            cur.execute(sql, params)
            return cur.fetchall()
        except Error as e:
            raise errobanco(f"erro ao consultar o banco: {e}")
        finally:
            con.close()


class basedao:
    """crud genérico. cada tabela só diz os campos e o select da lista"""

    tabela = ""
    campos = []          # colunas que podem ser gravadas
    sql_lista = ""       # select usado na listagem
    colunas_busca = []   # colunas da pesquisa
    ordem = "id"

    def inserir(self, dados):
        cols = ", ".join(self.campos)
        marcas = ", ".join(["%s"] * len(self.campos))
        sql = f"insert into {self.tabela} ({cols}) values ({marcas})"
        return conexao.executar(sql, [dados[c] for c in self.campos])

    def atualizar(self, id, dados):
        sets = ", ".join(f"{c} = %s" for c in self.campos)
        sql = f"update {self.tabela} set {sets} where id = %s"
        conexao.executar(sql, [dados[c] for c in self.campos] + [id])

    def excluir(self, id):
        conexao.executar(f"delete from {self.tabela} where id = %s", (id,))

    def buscar(self, id):
        linhas = conexao.consultar(f"select * from {self.tabela} where id = %s", (id,))
        return linhas[0] if linhas else None

    def listar(self, filtro=""):
        sql = self.sql_lista
        params = []
        if filtro:
            condicoes = " or ".join(f"{c} like %s" for c in self.colunas_busca)
            sql += f" where {condicoes}"
            params = [f"%{filtro}%"] * len(self.colunas_busca)
        sql += f" order by {self.ordem}"
        return conexao.consultar(sql, params)

    def opcoes(self):
        """lista 'id - nome' para os comboboxes"""
        linhas = conexao.consultar(f"select id, nome from {self.tabela} order by nome")
        return [f"{l['id']} - {l['nome']}" for l in linhas]


class tutordao(basedao):
    tabela = "tutores"
    campos = ["nome", "cpf", "telefone", "email", "endereco"]
    sql_lista = "select * from tutores"
    colunas_busca = ["nome", "cpf", "email"]
    ordem = "nome"


class veterinariodao(basedao):
    tabela = "veterinarios"
    campos = ["nome", "crmv", "especialidade", "telefone", "email"]
    sql_lista = "select * from veterinarios"
    colunas_busca = ["nome", "crmv", "especialidade"]
    ordem = "nome"


class animaldao(basedao):
    tabela = "animais"
    campos = ["nome", "especie", "raca", "idade", "peso", "tutor_id"]
    sql_lista = ("select a.*, t.nome as tutor_nome from animais a "
                 "join tutores t on t.id = a.tutor_id")
    colunas_busca = ["a.nome", "a.especie", "a.raca", "t.nome"]
    ordem = "a.nome"

    def opcoes(self):
        return [f"{l['id']} - {l['nome']} ({l['tutor_nome']})" for l in self.listar()]


class consultadao(basedao):
    tabela = "consultas"
    campos = ["animal_id", "veterinario_id", "data_hora", "tipo", "valor", "status", "observacoes"]
    sql_lista = ("select c.*, a.nome as animal_nome, v.nome as veterinario_nome "
                 "from consultas c "
                 "join animais a on a.id = c.animal_id "
                 "join veterinarios v on v.id = c.veterinario_id")
    colunas_busca = ["a.nome", "v.nome", "c.tipo", "c.status"]
    ordem = "c.data_hora desc"

    def listar(self, filtro=""):
        linhas = super().listar(filtro)
        for linha in linhas:  # data vira texto dd/mm/aaaa hh:mm
            linha["data_hora"] = linha["data_hora"].strftime(formato_data)
        return linhas

    def verificar_conflito(self, dados, id_atual=None):
        """o veterinário não pode ter duas consultas no mesmo horário"""
        if dados["status"] == "cancelada":
            return
        sql = ("select id from consultas where veterinario_id = %s and data_hora = %s "
               "and status <> 'cancelada'")
        params = [dados["veterinario_id"], dados["data_hora"]]
        if id_atual is not None:
            sql += " and id <> %s"
            params.append(id_atual)
        if conexao.consultar(sql, params):
            raise validacaoerror("esse veterinário já tem consulta nesse horário.")

    def inserir(self, dados):
        self.verificar_conflito(dados)
        return super().inserir(dados)

    def atualizar(self, id, dados):
        self.verificar_conflito(dados, id)
        super().atualizar(id, dados)


class relatoriodao:
    """consultas agrupadas para a aba de relatórios"""

    @staticmethod
    def animais_por_especie():
        linhas = conexao.consultar("select especie, count(*) as total from animais group by especie")
        return {l["especie"]: l["total"] for l in linhas}

    @staticmethod
    def consultas_por_status():
        linhas = conexao.consultar("select status, count(*) as total from consultas group by status")
        return {l["status"]: l["total"] for l in linhas}

    @staticmethod
    def faturamento_por_veterinario():
        linhas = conexao.consultar(
            "select v.nome, coalesce(sum(c.valor), 0) as total from veterinarios v "
            "left join consultas c on c.veterinario_id = v.id and c.status = 'realizada' "
            "group by v.id, v.nome order by total desc")
        return {l["nome"]: float(l["total"]) for l in linhas}

    @staticmethod
    def proximas_consultas(limite=8):
        linhas = conexao.consultar(
            "select c.data_hora, a.nome as animal, v.nome as veterinario, c.tipo "
            "from consultas c "
            "join animais a on a.id = c.animal_id join veterinarios v on v.id = c.veterinario_id "
            "where c.status = 'agendada' and c.data_hora >= now() "
            "order by c.data_hora limit %s", (limite,))
        for linha in linhas:
            linha["data_hora"] = linha["data_hora"].strftime(formato_data)
        return linhas
