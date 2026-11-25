# classes do vetcare e validações dos dados
import re
from datetime import datetime


class validacaoerror(Exception):
    """erro quando o usuário digita algo errado"""


# ---------- funções de apoio ----------
def so_digitos(texto):
    return re.sub(r"\D", "", str(texto))


def validar_cpf(cpf):
    cpf = so_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def texto_obrigatorio(valor, campo, minimo=2, maximo=100):
    valor = str(valor).strip()
    if len(valor) < minimo:
        raise validacaoerror(f"o campo '{campo}' é obrigatório (mínimo {minimo} letras).")
    if len(valor) > maximo:
        raise validacaoerror(f"o campo '{campo}' aceita no máximo {maximo} letras.")
    return valor


def numero(valor, campo, tipo=float, minimo=0, maximo=None):
    try:
        n = tipo(str(valor).replace(",", ".").strip())
    except ValueError:
        raise validacaoerror(f"o campo '{campo}' precisa ser um número.")
    if n < minimo:
        raise validacaoerror(f"o campo '{campo}' não pode ser menor que {minimo}.")
    if maximo is not None and n > maximo:
        raise validacaoerror(f"o campo '{campo}' não pode ser maior que {maximo}.")
    return n


# ---------- pessoas ----------
class pessoa:
    """base para tutor e veterinário (atributos privados + property)"""

    def __init__(self, nome, telefone, email, id=None):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.email = email

    @property
    def nome(self):
        return self.__nome

    @nome.setter
    def nome(self, valor):
        valor = texto_obrigatorio(valor, "nome", 3, 100)
        if re.search(r"\d", valor):
            raise validacaoerror("o nome não pode ter números.")
        self.__nome = valor

    @property
    def telefone(self):
        return self.__telefone

    @telefone.setter
    def telefone(self, valor):
        digitos = so_digitos(valor)
        if len(digitos) not in (10, 11):
            raise validacaoerror("telefone inválido. use ddd + número (10 ou 11 dígitos).")
        self.__telefone = digitos

    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, valor):
        valor = str(valor).strip().lower()
        if not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", valor):
            raise validacaoerror("e-mail inválido.")
        self.__email = valor

    def para_dict(self):
        return {"nome": self.nome, "telefone": self.telefone, "email": self.email}


class tutor(pessoa):
    def __init__(self, nome, cpf, telefone, email, endereco="", id=None):
        super().__init__(nome, telefone, email, id)
        self.cpf = cpf
        self.endereco = endereco

    @property
    def cpf(self):
        return self.__cpf

    @cpf.setter
    def cpf(self, valor):
        if not validar_cpf(valor):
            raise validacaoerror("cpf inválido.")
        self.__cpf = so_digitos(valor)

    @property
    def endereco(self):
        return self.__endereco

    @endereco.setter
    def endereco(self, valor):
        valor = str(valor).strip()
        if len(valor) > 150:
            raise validacaoerror("o endereço aceita no máximo 150 letras.")
        self.__endereco = valor

    def para_dict(self):
        dados = super().para_dict()
        dados.update({"cpf": self.cpf, "endereco": self.endereco})
        return dados


class veterinario(pessoa):
    def __init__(self, nome, crmv, especialidade, telefone, email, id=None):
        super().__init__(nome, telefone, email, id)
        self.crmv = crmv
        self.especialidade = especialidade

    @property
    def crmv(self):
        return self.__crmv

    @crmv.setter
    def crmv(self, valor):
        valor = str(valor).strip().lower()
        if not re.fullmatch(r"[a-z]{2}-?\d{3,6}", valor):
            raise validacaoerror("crmv inválido. use o formato uf-12345 (ex.: rs-12345).")
        self.__crmv = valor

    @property
    def especialidade(self):
        return self.__especialidade

    @especialidade.setter
    def especialidade(self, valor):
        self.__especialidade = texto_obrigatorio(valor, "especialidade", 3, 60).lower()

    def para_dict(self):
        dados = super().para_dict()
        dados.update({"crmv": self.crmv, "especialidade": self.especialidade})
        return dados


# ---------- animais ----------
class animal:
    """base dos animais. cada espécie muda fator_porte() e cuidados()"""

    especie = "outro"

    def __init__(self, nome, raca, idade, peso, tutor_id, id=None):
        self.id = id
        self.nome = nome
        self.raca = raca
        self.idade = idade
        self.peso = peso
        self.tutor_id = tutor_id

    @property
    def nome(self):
        return self.__nome

    @nome.setter
    def nome(self, valor):
        self.__nome = texto_obrigatorio(valor, "nome do animal", 2, 60)

    @property
    def raca(self):
        return self.__raca

    @raca.setter
    def raca(self, valor):
        self.__raca = str(valor).strip()[:60]

    @property
    def idade(self):
        return self.__idade

    @idade.setter
    def idade(self, valor):
        self.__idade = numero(valor, "idade", int, 0, 60)

    @property
    def peso(self):
        return self.__peso

    @peso.setter
    def peso(self, valor):
        self.__peso = round(numero(valor, "peso", float, 0.01, 1000), 2)

    @property
    def tutor_id(self):
        return self.__tutor_id

    @tutor_id.setter
    def tutor_id(self, valor):
        if valor in (None, ""):
            raise validacaoerror("escolha o tutor do animal.")
        self.__tutor_id = int(valor)

    def fator_porte(self):
        return 1.0

    def cuidados(self):
        return "converse com o veterinário para orientações específicas."

    def para_dict(self):
        return {"nome": self.nome, "especie": self.especie, "raca": self.raca,
                "idade": self.idade, "peso": self.peso, "tutor_id": self.tutor_id}


class cachorro(animal):
    especie = "cachorro"

    def fator_porte(self):
        if self.peso > 25:
            return 1.4  # grande
        if self.peso > 10:
            return 1.2  # médio
        return 1.0

    def cuidados(self):
        return "vacina v10 e antirrábica todo ano, vermífugo a cada 3 meses e passeios diários."


class gato(animal):
    especie = "gato"

    def fator_porte(self):
        return 1.1 if self.peso > 6 else 1.0

    def cuidados(self):
        return "vacina v4 e antirrábica todo ano, castração recomendada e atenção às vias urinárias."


class ave(animal):
    especie = "ave"

    def fator_porte(self):
        return 1.3  # atendimento exótico

    def cuidados(self):
        return "ambiente arejado, dieta variada, check-up a cada 6 meses e cuidado com vento forte."


class outro(animal):
    especie = "outro"

    def fator_porte(self):
        return 1.5

    def cuidados(self):
        return "animal exótico: marque uma avaliação com veterinário especializado."


# liga o nome da espécie à classe
especies = {"cachorro": cachorro, "gato": gato, "ave": ave, "outro": outro}


def criar_animal(especie, nome, raca, idade, peso, tutor_id, id=None):
    classe = especies.get(especie)
    if classe is None:
        raise validacaoerror("escolha a espécie do animal.")
    return classe(nome, raca, idade, peso, tutor_id, id)


# ---------- consultas ----------
tipos_consulta = {  # tipo -> valor base (r$)
    "rotina": 120.0,
    "vacinação": 80.0,
    "exame": 150.0,
    "emergência": 350.0,
    "cirurgia": 600.0,
}
status_consulta = ["agendada", "realizada", "cancelada"]
formato_data = "%d/%m/%Y %H:%M"


class consulta:
    def __init__(self, animal_id, veterinario_id, data_hora, tipo, valor,
                 status="agendada", observacoes="", id=None):
        self.id = id
        self.animal_id = animal_id
        self.veterinario_id = veterinario_id
        self.data_hora = data_hora
        self.tipo = tipo
        self.valor = valor
        self.status = status
        self.observacoes = observacoes

    @staticmethod
    def calcular_valor(tipo, animal):
        """valor = base do tipo x fator de porte do animal"""
        if tipo not in tipos_consulta:
            raise validacaoerror("escolha o tipo da consulta.")
        return round(tipos_consulta[tipo] * animal.fator_porte(), 2)

    @property
    def data_hora(self):
        return self.__data_hora

    @data_hora.setter
    def data_hora(self, valor):
        if isinstance(valor, datetime):
            self.__data_hora = valor
            return
        try:
            self.__data_hora = datetime.strptime(str(valor).strip(), formato_data)
        except ValueError:
            raise validacaoerror("data/hora inválida. use dd/mm/aaaa hh:mm (ex.: 15/11/2026 14:30).")

    @property
    def tipo(self):
        return self.__tipo

    @tipo.setter
    def tipo(self, valor):
        if valor not in tipos_consulta:
            raise validacaoerror("escolha o tipo da consulta.")
        self.__tipo = valor

    @property
    def valor(self):
        return self.__valor

    @valor.setter
    def valor(self, valor):
        self.__valor = round(numero(valor, "valor", float, 0, 100000), 2)

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, valor):
        if valor not in status_consulta:
            raise validacaoerror("escolha o status da consulta.")
        self.__status = valor

    @property
    def animal_id(self):
        return self.__animal_id

    @animal_id.setter
    def animal_id(self, valor):
        if valor in (None, ""):
            raise validacaoerror("escolha o animal.")
        self.__animal_id = int(valor)

    @property
    def veterinario_id(self):
        return self.__veterinario_id

    @veterinario_id.setter
    def veterinario_id(self, valor):
        if valor in (None, ""):
            raise validacaoerror("escolha o veterinário.")
        self.__veterinario_id = int(valor)

    def para_dict(self):
        return {"animal_id": self.animal_id, "veterinario_id": self.veterinario_id,
                "data_hora": self.data_hora, "tipo": self.tipo, "valor": self.valor,
                "status": self.status, "observacoes": str(self.observacoes).strip()[:255]}
