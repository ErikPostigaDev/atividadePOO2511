# vetcare - sistema de clínica veterinária (tela em tkinter)
# para rodar: python app.py
import tkinter as tk
from datetime import datetime, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from database import (animaldao, conexao, consultadao, errobanco, relatoriodao,
                      tutordao, veterinariodao)
from models import (especies, status_consulta, tipos_consulta, consulta, tutor,
                    validacaoerror, veterinario, criar_animal)

cor_principal = "#2a7f62"
cor_fundo = "#f4f7f6"


class campo:
    """um campo do formulário (texto ou combobox)"""

    def __init__(self, chave, rotulo, tipo="entry", opcoes=None, fk=False):
        self.chave = chave
        self.rotulo = rotulo
        self.tipo = tipo
        self.opcoes = opcoes or []
        self.fk = fk  # true quando o combobox guarda um id ("3 - nome")


class abacrud(ttk.Frame):
    """aba genérica com cadastrar, atualizar, excluir e pesquisar.
    as abas de verdade herdam daqui e só dizem os campos, colunas e o dao."""

    nome = "registro"
    dao = None
    campos = []
    colunas = []         # (chave, título, largura)
    fontes_opcoes = {}   # campo fk -> dao que fornece as opções

    def __init__(self, master):
        super().__init__(master, padding=10)
        self.meu_dao = self.dao()
        self.id_selecionado = None
        self.widgets = {}
        self.linhas = {}
        self.montar()
        self.atualizar()

    # ---------- montagem da tela ----------
    def montar(self):
        form = ttk.LabelFrame(self, text=f"dados - {self.nome}", padding=10)
        form.pack(fill="x")
        for i, c in enumerate(self.campos):
            linha, col = divmod(i, 2)
            ttk.Label(form, text=c.rotulo).grid(row=linha, column=col * 2, sticky="e", padx=(10, 4), pady=4)
            if c.tipo == "combo":
                w = ttk.Combobox(form, values=c.opcoes, state="readonly", width=38)
            else:
                w = ttk.Entry(form, width=40)
            w.grid(row=linha, column=col * 2 + 1, sticky="w", pady=4)
            self.widgets[c.chave] = w

        botoes = ttk.Frame(self)
        botoes.pack(fill="x", pady=8)
        ttk.Button(botoes, text="cadastrar", command=self.cadastrar).pack(side="left", padx=3)
        ttk.Button(botoes, text="atualizar", command=self.atualizar_registro).pack(side="left", padx=3)
        ttk.Button(botoes, text="excluir", command=self.excluir).pack(side="left", padx=3)
        ttk.Button(botoes, text="limpar", command=self.limpar).pack(side="left", padx=3)
        for texto, comando in self.botoes_extras():
            ttk.Button(botoes, text=texto, command=lambda c=comando: self.proteger(c)).pack(side="left", padx=3)

        busca = ttk.Frame(self)
        busca.pack(fill="x")
        ttk.Label(busca, text="pesquisar:").pack(side="left")
        self.var_busca = tk.StringVar()
        entrada = ttk.Entry(busca, textvariable=self.var_busca, width=40)
        entrada.pack(side="left", padx=6)
        entrada.bind("<KeyRelease>", lambda e: self.carregar())
        ttk.Button(busca, text="mostrar todos", command=self.limpar_busca).pack(side="left")

        quadro = ttk.Frame(self)
        quadro.pack(fill="both", expand=True, pady=(8, 0))
        self.tabela = ttk.Treeview(quadro, columns=[c[0] for c in self.colunas], show="headings", height=10)
        for chave, titulo, largura in self.colunas:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor="w")
        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tabela.bind("<<TreeviewSelect>>", self.ao_selecionar)

    def botoes_extras(self):
        return []

    def criar_modelo(self, dados):
        raise NotImplementedError

    # ---------- ler e preencher o formulário ----------
    def ler(self):
        dados = {}
        for c in self.campos:
            texto = self.widgets[c.chave].get().strip()
            dados[c.chave] = texto.split(" - ")[0] if (c.fk and texto) else texto
        return dados

    def preencher(self, linha):
        for c in self.campos:
            w = self.widgets[c.chave]
            valor = linha.get(c.chave, "")
            if c.tipo == "combo" and c.fk:
                prefixo = f"{valor} - "
                w.set(next((o for o in w["values"] if o.startswith(prefixo)), ""))
            elif c.tipo == "combo":
                w.set(valor)
            else:
                w.delete(0, "end")
                w.insert(0, "" if valor is None else str(valor))

    # ---------- ações ----------
    def proteger(self, funcao):
        """roda a ação e mostra uma mensagem se der erro"""
        try:
            funcao()
        except validacaoerror as e:
            messagebox.showwarning("dados inválidos", str(e))
        except errobanco as e:
            messagebox.showerror("erro no banco", str(e))
        except Exception as e:  # o programa não pode fechar do nada
            messagebox.showerror("erro inesperado", f"deu algo errado: {e}")

    def cadastrar(self):
        def acao():
            dados = self.criar_modelo(self.ler()).para_dict()
            self.meu_dao.inserir(dados)
            messagebox.showinfo("pronto", f"{self.nome} cadastrado com sucesso!")
            self.limpar()
            self.carregar()
        self.proteger(acao)

    def atualizar_registro(self):
        def acao():
            if self.id_selecionado is None:
                raise validacaoerror(f"clique em um {self.nome} na tabela para atualizar.")
            dados = self.criar_modelo(self.ler()).para_dict()
            self.meu_dao.atualizar(self.id_selecionado, dados)
            messagebox.showinfo("pronto", f"{self.nome} atualizado com sucesso!")
            self.limpar()
            self.carregar()
        self.proteger(acao)

    def excluir(self):
        def acao():
            if self.id_selecionado is None:
                raise validacaoerror(f"clique em um {self.nome} na tabela para excluir.")
            if not messagebox.askyesno("confirmar", f"quer mesmo excluir este {self.nome}?"):
                return
            self.meu_dao.excluir(self.id_selecionado)
            self.limpar()
            self.carregar()
        self.proteger(acao)

    def limpar(self):
        self.id_selecionado = None
        for c in self.campos:
            w = self.widgets[c.chave]
            if c.tipo == "combo":
                w.set("")
            else:
                w.delete(0, "end")
        self.tabela.selection_remove(self.tabela.selection())

    def limpar_busca(self):
        self.var_busca.set("")
        self.carregar()

    # ---------- tabela ----------
    @staticmethod
    def formatar(valor):
        if isinstance(valor, (Decimal, float)):
            return f"{valor:.2f}"
        return "" if valor is None else valor

    def carregar(self):
        def acao():
            self.tabela.delete(*self.tabela.get_children())
            self.linhas = {}
            for linha in self.meu_dao.listar(self.var_busca.get().strip()):
                self.linhas[linha["id"]] = linha
                valores = [self.formatar(linha.get(c[0])) for c in self.colunas]
                self.tabela.insert("", "end", iid=str(linha["id"]), values=valores)
        self.proteger(acao)

    def atualizar_opcoes(self):
        for chave, dao in self.fontes_opcoes.items():
            w = self.widgets[chave]
            atual = w.get()
            w["values"] = dao.opcoes()
            if atual not in w["values"]:
                w.set("")

    def atualizar(self):
        self.proteger(self.atualizar_opcoes)
        self.carregar()

    def ao_selecionar(self, _evento):
        selecao = self.tabela.selection()
        if not selecao:
            return
        self.id_selecionado = int(selecao[0])
        self.preencher(self.linhas[self.id_selecionado])


# ---------- as abas ----------
class abatutores(abacrud):
    nome = "tutor"
    dao = tutordao
    campos = [
        campo("nome", "nome completo"), campo("cpf", "cpf"),
        campo("telefone", "telefone (com ddd)"), campo("email", "e-mail"),
        campo("endereco", "endereço"),
    ]
    colunas = [("id", "id", 40), ("nome", "nome", 220), ("cpf", "cpf", 110),
               ("telefone", "telefone", 110), ("email", "e-mail", 200), ("endereco", "endereço", 220)]

    def criar_modelo(self, d):
        return tutor(d["nome"], d["cpf"], d["telefone"], d["email"], d["endereco"])


class abaveterinarios(abacrud):
    nome = "veterinário"
    dao = veterinariodao
    campos = [
        campo("nome", "nome completo"), campo("crmv", "crmv (ex.: rs-12345)"),
        campo("especialidade", "especialidade"), campo("telefone", "telefone (com ddd)"),
        campo("email", "e-mail"),
    ]
    colunas = [("id", "id", 40), ("nome", "nome", 220), ("crmv", "crmv", 100),
               ("especialidade", "especialidade", 160), ("telefone", "telefone", 110), ("email", "e-mail", 200)]

    def criar_modelo(self, d):
        return veterinario(d["nome"], d["crmv"], d["especialidade"], d["telefone"], d["email"])


class abaanimais(abacrud):
    nome = "animal"
    dao = animaldao
    campos = [
        campo("nome", "nome do animal"), campo("especie", "espécie", "combo", list(especies)),
        campo("raca", "raça"), campo("idade", "idade (anos)"),
        campo("peso", "peso (kg)"), campo("tutor_id", "tutor", "combo", fk=True),
    ]
    colunas = [("id", "id", 40), ("nome", "nome", 130), ("especie", "espécie", 90), ("raca", "raça", 130),
               ("idade", "idade", 55), ("peso", "peso (kg)", 75), ("tutor_nome", "tutor", 200)]
    fontes_opcoes = {"tutor_id": tutordao()}

    def criar_modelo(self, d):
        return criar_animal(d["especie"], d["nome"], d["raca"], d["idade"], d["peso"], d["tutor_id"])

    def botoes_extras(self):
        return [("ver cuidados", self.ver_cuidados)]

    def ver_cuidados(self):
        if self.id_selecionado is None:
            raise validacaoerror("clique em um animal na tabela.")
        a = self.criar_modelo(self.ler())
        messagebox.showinfo(f"cuidados - {a.nome} ({a.especie})", a.cuidados())


class abaconsultas(abacrud):
    nome = "consulta"
    dao = consultadao
    campos = [
        campo("animal_id", "animal", "combo", fk=True),
        campo("veterinario_id", "veterinário", "combo", fk=True),
        campo("data_hora", "data/hora (dd/mm/aaaa hh:mm)"),
        campo("tipo", "tipo", "combo", list(tipos_consulta)),
        campo("valor", "valor (r$)"),
        campo("status", "status", "combo", status_consulta),
        campo("observacoes", "observações"),
    ]
    colunas = [("id", "id", 40), ("animal_nome", "animal", 120), ("veterinario_nome", "veterinário", 160),
               ("data_hora", "data/hora", 120), ("tipo", "tipo", 90), ("valor", "valor (r$)", 80),
               ("status", "status", 80), ("observacoes", "observações", 200)]
    fontes_opcoes = {"animal_id": animaldao(), "veterinario_id": veterinariodao()}

    def criar_modelo(self, d):
        return consulta(d["animal_id"], d["veterinario_id"], d["data_hora"], d["tipo"],
                        d["valor"], d["status"] or "agendada", d["observacoes"])

    def botoes_extras(self):
        return [("calcular valor", self.calcular_valor)]

    def calcular_valor(self):
        d = self.ler()
        if not d["animal_id"]:
            raise validacaoerror("escolha o animal para calcular o valor.")
        l = animaldao().buscar(int(d["animal_id"]))
        a = criar_animal(l["especie"], l["nome"], l["raca"], l["idade"], l["peso"], l["tutor_id"], l["id"])
        valor = consulta.calcular_valor(d["tipo"], a)
        self.widgets["valor"].delete(0, "end")
        self.widgets["valor"].insert(0, f"{valor:.2f}")


class abarelatorios(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        ttk.Button(self, text="atualizar relatório", command=self.atualizar).pack(anchor="w")
        self.texto = tk.Text(self, font=("Consolas", 11), state="disabled", bg="white", relief="flat")
        self.texto.pack(fill="both", expand=True, pady=8)
        self.atualizar()

    @staticmethod
    def secao(titulo, dicionario, moeda=False):
        linhas = [f"\n== {titulo} ==\n"]
        if not dicionario:
            linhas.append("  (sem dados)\n")
        for chave, valor in dicionario.items():
            valor = f"r$ {valor:,.2f}" if moeda else valor
            linhas.append(f"  {chave:<30} {valor}\n")
        return "".join(linhas)

    def atualizar(self):
        try:
            texto = "relatório geral da clínica\n"
            texto += self.secao("animais por espécie", relatoriodao.animais_por_especie())
            texto += self.secao("consultas por status", relatoriodao.consultas_por_status())
            texto += self.secao("faturamento por veterinário (consultas realizadas)",
                                relatoriodao.faturamento_por_veterinario(), moeda=True)
            proximas = {f"{c['data_hora']}  {c['animal']}": f"{c['tipo']} - {c['veterinario']}"
                        for c in relatoriodao.proximas_consultas()}
            texto += self.secao("próximas consultas agendadas", proximas)
        except errobanco as e:
            texto = f"erro ao gerar o relatório:\n{e}"
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", texto)
        self.texto.configure(state="disabled")


# ---------- janela principal ----------
class app(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("vetcare - clínica veterinária")
        self.geometry("1000x640")
        self.minsize(900, 560)
        self.configure(bg=cor_fundo)
        self.estilo()
        self.menu()

        topo = tk.Frame(self, bg=cor_principal)
        topo.pack(fill="x")
        tk.Label(topo, text="vetcare", bg=cor_principal, fg="white",
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(topo, text="gestão de clínica veterinária", bg=cor_principal, fg="#d8efe6",
                 font=("Segoe UI", 11)).pack(side="left")

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=8, pady=8)
        self.paginas = [
            (abatutores(self.abas), "tutores"),
            (abaanimais(self.abas), "animais"),
            (abaveterinarios(self.abas), "veterinários"),
            (abaconsultas(self.abas), "consultas"),
            (abarelatorios(self.abas), "relatórios"),
        ]
        for pagina, titulo in self.paginas:
            self.abas.add(pagina, text=f"  {titulo}  ")
        self.abas.bind("<<NotebookTabChanged>>", self.ao_trocar_aba)

    def estilo(self):
        e = ttk.Style(self)
        e.theme_use("clam")
        e.configure("TFrame", background=cor_fundo)
        e.configure("TLabelframe", background=cor_fundo)
        e.configure("TLabelframe.Label", background=cor_fundo, foreground=cor_principal,
                    font=("Segoe UI", 10, "bold"))
        e.configure("TLabel", background=cor_fundo, font=("Segoe UI", 10))
        e.configure("TButton", font=("Segoe UI", 10), padding=6)
        e.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(10, 6))
        e.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        e.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                    background=cor_principal, foreground="white")
        e.map("Treeview", background=[("selected", "#bfe3d5")], foreground=[("selected", "black")])

    def menu(self):
        barra = tk.Menu(self)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="carregar dados de exemplo", command=self.carregar_exemplo)
        arquivo.add_separator()
        arquivo.add_command(label="sair", command=self.destroy)
        barra.add_cascade(label="arquivo", menu=arquivo)
        self.config(menu=barra)

    def ao_trocar_aba(self, _evento):
        pagina = self.nametowidget(self.abas.select())
        if isinstance(pagina, (abacrud, abarelatorios)):
            pagina.atualizar()

    def carregar_exemplo(self):
        """coloca alguns registros pra facilitar a apresentação"""
        try:
            tutores, animais, vets = tutordao(), animaldao(), veterinariodao()
            if conexao.consultar("select id from tutores limit 1"):
                messagebox.showinfo("exemplo", "o banco já tem dados. nada foi inserido.")
                return
            t1 = tutores.inserir(tutor("mariana souza", "52998224725", "51999990001",
                                       "mariana@email.com", "rua das flores, 120").para_dict())
            t2 = tutores.inserir(tutor("carlos pereira", "11144477735", "51988880002",
                                       "carlos@email.com", "av. central, 450").para_dict())
            v1 = vets.inserir(veterinario("dra. helena costa", "rs-12345", "clínica geral",
                                          "51977770003", "helena@vetcare.com").para_dict())
            v2 = vets.inserir(veterinario("dr. rafael lima", "rs-54321", "cirurgia",
                                          "51966660004", "rafael@vetcare.com").para_dict())
            a1 = animais.inserir(criar_animal("cachorro", "thor", "labrador", 4, 32, t1).para_dict())
            a2 = animais.inserir(criar_animal("gato", "mia", "siamês", 2, 4.2, t1).para_dict())
            a3 = animais.inserir(criar_animal("ave", "loro", "calopsita", 1, 0.09, t2).para_dict())
            agora = datetime.now().replace(minute=0, second=0, microsecond=0)
            consultas = consultadao()
            exemplos = [(a1, v1, 2, "rotina", "agendada"),
                        (a2, v1, 3, "vacinação", "agendada"),
                        (a3, v2, -5, "exame", "realizada"),
                        (a1, v2, -10, "cirurgia", "realizada")]
            for animal_id, vet_id, dias, tipo, status in exemplos:
                l = animais.buscar(animal_id)
                a = criar_animal(l["especie"], l["nome"], l["raca"], l["idade"], l["peso"], l["tutor_id"], l["id"])
                valor = consulta.calcular_valor(tipo, a)
                consultas.inserir(consulta(animal_id, vet_id, agora + timedelta(days=dias), tipo, valor,
                                           status, "exemplo").para_dict())
            for pagina, _ in self.paginas:
                pagina.atualizar()
            messagebox.showinfo("exemplo", "dados de exemplo carregados!")
        except (errobanco, validacaoerror) as e:
            messagebox.showerror("erro", str(e))


def main():
    try:
        conexao.inicializar()
    except errobanco as e:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("erro de conexão", f"{e}\n\nveja se o mysql está ligado e confira o config.py.")
        return
    app().mainloop()


if __name__ == "__main__":
    main()
