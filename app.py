from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
from email.mime.text import MIMEText
import smtplib
import os
import pandas as pd
import io
import re


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Caminhos dos arquivos
ARQUIVOS = {
    'usuarios': 'usuarios.txt',
    'clientes': 'clientes.txt',
    'obras': 'obras.txt',
    'andaimes': 'andaimes.txt',
    'montagem': 'montagem.txt',
    'desmontagem': 'desmontagem.txt',
    'status_andaimes': 'status_andaimes.txt',
}


@app.route('/')
def home():
    return redirect(url_for('login'))
    
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('password', '').strip()

        try:
            with open(ARQUIVOS['usuarios'], 'r', encoding='utf-8') as f:
                for linha in f:
                    e, s, nome, *_ = linha.strip().split(',')
                    if email == e and senha == s:
                        session['usuario'] = {'email': email, 'nome': nome}
                        return redirect(url_for('dashboard'))
            erro = "E-mail ou senha incorretos."
        except FileNotFoundError:
            erro = "Nenhum usuário cadastrado ainda."

    return render_template('login.html', erro=erro)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmarSenha', '')
        tipo = request.form.get('tipoUsuario', 'usuario')

        if senha != confirmar:
            erro = "As senhas não coincidem."
        elif not email or not nome or not senha:
            erro = "Todos os campos devem ser preenchidos."
        else:
            try:
                with open(ARQUIVOS['usuarios'], 'r', encoding='utf-8') as f:
                    for linha in f:
                        e, *_ = linha.strip().split(',')
                        if e == email:
                            erro = "E-mail já cadastrado."
                            break
            except FileNotFoundError:
                pass

            if not erro:
                with open(ARQUIVOS['usuarios'], 'a', encoding='utf-8') as f:
                    f.write(f"{email},{senha},{nome},{tipo}\n")
                flash('Cadastro realizado com sucesso! Faça login.')
                return redirect(url_for('login'))

    return render_template('cadastro.html', erro=erro)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def ler_arquivo_5_ultimos(caminho, num_campos):
    registros = []
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            for linha in f:
                campos = linha.strip().split(',')
                if len(campos) >= num_campos:
                    registros.append(campos[:num_campos])
    except FileNotFoundError:
        pass
    return registros[-5:]

@app.route('/dashboard')
@login_required
def dashboard():
    nome_usuario = session['usuario']['nome']

    # Função para contar clientes reais
    def contar_clientes():
        try:
            with open(ARQUIVOS['clientes'], 'r', encoding='utf-8') as f:
                return sum(1 for linha in f if linha.strip())
        except FileNotFoundError:
            return 0

    total_clientes = contar_clientes()

    clientes = ler_arquivo_5_ultimos(ARQUIVOS['clientes'], 3)
    obras = ler_arquivo_5_ultimos(ARQUIVOS['obras'], 5)
    andaimes = ler_arquivo_5_ultimos(ARQUIVOS['andaimes'], 2)
    desmontagens = ler_arquivo_5_ultimos(ARQUIVOS['desmontagem'], 4)
    montagens = ler_arquivo_5_ultimos(ARQUIVOS['montagem'], 4)

    def contar_andaimes_montados():
        try:
            with open(ARQUIVOS['status_andaimes'], 'r', encoding='utf-8') as f:
                return sum(1 for linha in f if 'Disponível' in linha or 'Montado' in linha)
        except FileNotFoundError:
            return 0

    total_andaimes_montados = contar_andaimes_montados()

    return render_template('dashboard.html',
                           nome_usuario=nome_usuario,
                           clientes=clientes,
                           obras=obras,
                           andaimes=andaimes,
                           desmontagens=desmontagens,
                           montagens=montagens,
                           total_andaimes=total_andaimes_montados,
                           total_clientes=total_clientes)





@app.route('/logout')
@login_required
def logout():
    session.pop('usuario', None)
    flash('Você saiu do sistema.')
    return redirect(url_for('login'))

@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def clientes():
    if request.method == 'POST':
        empresa = request.form['empresa']
        responsavel = request.form['responsavel']
        contato = request.form['contato']
        with open(ARQUIVOS['clientes'], 'a', encoding='utf-8') as f:
            f.write(f"{responsavel},{empresa},{contato}\n")
        flash('Cliente cadastrado com sucesso!')
        return redirect(url_for('clientes'))

    lista_clientes = []
    try:
        with open(ARQUIVOS['clientes'], 'r', encoding='utf-8') as f:
            for linha in f:
                campos = linha.strip().split(',')
                if len(campos) >= 3:
                    responsavel, empresa, contato = campos[:3]
                    lista_clientes.append({
                        'empresa': empresa,
                        'responsavel': responsavel,
                        'contato': contato
                    })
    except FileNotFoundError:
        pass

    return render_template('clientes.html', clientes=lista_clientes)

@app.route('/suporte', methods=['GET', 'POST'])
@login_required
def suporte():
    if request.method == 'POST':
        nome = request.form['nome']
        setor = request.form['setor']
        duvida = request.form['duvida']

        destinatario = 'suporteacessarequipamentos@gmail.com'
        remetente = 'suporteacessarequipamentos@gmail.com'
        senha = 'glbu vakk gpym hxmf'  # CUIDADO: Senhas em texto puro não são seguras

        corpo = f"""
        Novo pedido de suporte enviado pelo sistema:

        Nome: {nome}
        Setor: {setor}
        Dúvida:
        {duvida}
        """

        msg = MIMEText(corpo)
        msg['Subject'] = f'Suporte - {nome}'
        msg['From'] = remetente
        msg['To'] = destinatario

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(remetente, senha)
                server.send_message(msg)
            flash('Sua mensagem foi enviada com sucesso!')
        except Exception as e:
            flash(f'Erro ao enviar e-mail: {e}')
        return redirect(url_for('suporte'))

    return render_template('suporte.html')

@app.route('/montagem', methods=['GET', 'POST'])
@login_required
def montagem():
    if request.method == 'POST':
        try:
            cliente = request.form.get('cliente')
            obra = request.form.get('obra')
            local = request.form.get('local')
            data = request.form.get('data')
            responsavel = request.form.get('responsavel')

            tubos = request.form.getlist('tubos[]')
            qtd_tubos = request.form.getlist('quantidade_tubos[]')

            pranchoes = request.form.getlist('pranchoes[]')
            qtd_pranchoes = request.form.getlist('quantidade_pranchoes[]')

            acessorios = request.form.getlist('acessorios[]')
            qtd_acessorios = request.form.getlist('quantidade_acessorios[]')

            rodape = request.form.getlist('rodape[]')
            qtd_rodape = request.form.getlist('quantidade_rodape[]')

            diversos = request.form.get('diversos')  # <-- agora é um campo de texto simples

            def formatar(lista, qtds):
                return [f"{item} x {qtd}" for item, qtd in zip(lista, qtds) if item and qtd and qtd.isdigit() and int(qtd) > 0]

            tubos_fmt = formatar(tubos, qtd_tubos)
            pranchoes_fmt = formatar(pranchoes, qtd_pranchoes)
            acessorios_fmt = formatar(acessorios, qtd_acessorios)
            rodape_fmt = formatar(rodape, qtd_rodape)

            total = sum(
                int(q) for q in qtd_tubos + qtd_pranchoes + qtd_acessorios + qtd_rodape if q.isdigit()
            )

            def calcular_peso_total(lista_formatada):
                peso_total = 0.0
                for item in lista_formatada:
                    match = re.search(r"([\d.,]+)kg", item)
                    qtd_match = re.search(r"x\s*(\d+)", item)
                    if match and qtd_match:
                        peso_unitario = float(match.group(1).replace(",", "."))
                        qtd = int(qtd_match.group(1))
                        peso_total += peso_unitario * qtd
                return peso_total

            peso_total_kg = (
                calcular_peso_total(tubos_fmt) +
                calcular_peso_total(pranchoes_fmt) +
                calcular_peso_total(acessorios_fmt) +
                calcular_peso_total(rodape_fmt)
            )

            detalhes = (
                tubos_fmt + pranchoes_fmt + acessorios_fmt + rodape_fmt +
                ([f"Diversos: {diversos}"] if diversos else []) +
                [f"Total de peças: {total}", f"Peso total: {peso_total_kg:.2f} kg"]
            )

            with open(ARQUIVOS['montagem'], 'a', encoding='utf-8') as f:
                f.write(f"{cliente},{obra},{local},{data},{responsavel},{' | '.join(detalhes)}\n")

            try:
                with open(ARQUIVOS['montagem'], 'r', encoding='utf-8') as f:
                    novo_id = len(f.readlines()) - 1
            except FileNotFoundError:
                novo_id = 0

            with open(ARQUIVOS['status_andaimes'], 'a', encoding='utf-8') as f:
                f.write(f"{novo_id},Disponível\n")

            flash('Montagem registrada com sucesso!')
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f"Erro ao registrar montagem: {e}")
            return redirect(url_for('montagem'))

    # GET
    clientes = set()
    try:
        with open('clientes.txt', 'r', encoding='utf-8') as f:
            for linha in f:
                partes = linha.strip().split(',')
                if len(partes) >= 1 and partes[0].strip():
                    nome = partes[0].strip()
                    clientes.add(nome)
    except FileNotFoundError:
        clientes = set()

    return render_template('montagem.html', clientes=sorted(clientes))



@app.route('/atualizar_status', methods=['POST'])
@login_required
def atualizar_status():
    id_andaime = int(request.form.get('id'))
    novo_status = request.form.get('status')

    status_dict = {}
    try:
        with open('status_andaimes.txt', 'r', encoding='utf-8') as f:
            for linha in f:
                partes = linha.strip().split(',')
                if len(partes) == 2:
                    status_dict[int(partes[0])] = partes[1]
    except FileNotFoundError:
        pass

    status_dict[id_andaime] = novo_status

    with open('status_andaimes.txt', 'w', encoding='utf-8') as f:
        for k, v in status_dict.items():
            f.write(f"{k},{v}\n")

    flash("Status atualizado com sucesso!")
    return redirect(url_for('desmontagem'))





@app.route('/desmontagem', methods=['GET'])
@login_required
def desmontagem():
    try:
        with open(ARQUIVOS['montagem'], 'r', encoding='utf-8') as f:
            montagens = [linha.strip() for linha in f if linha.strip()]
    except FileNotFoundError:
        montagens = []

    status_dict = {}
    try:
        with open('status_andaimes.txt', 'r', encoding='utf-8') as f:
            for linha in f:
                partes = linha.strip().split(',')
                if len(partes) == 2:
                    status_dict[int(partes[0])] = partes[1]
                    continue
    except FileNotFoundError:
        pass


    andaimes = []
    for idx, linha in enumerate(montagens):
        status = status_dict.get(idx, "Disponível")
        if status == "Disponível":
            campos = linha.split(',')
            if len(campos) >= 5:
                andaimes.append({
                    'id': idx,
                    'cliente': campos[0],
                    'obra': campos[1],
                    'local': campos[2],
                    'data': campos[3],
                    'materiais': ','.join(campos[4:]).replace('|', '\n').strip(),
                    'status': status
                })

    return render_template('desmontagem.html', andaimes=andaimes)

    
@app.route('/relatorios')
@login_required
def relatorios():
    return render_template('relatorios.html')

@app.route('/relatorio')
@login_required
def baixar_relatorio():
    dados = {}

    arquivos = {
        'Clientes': ARQUIVOS['clientes'],
        'Andaimes Montados': ARQUIVOS['montagem'],
        'Andaimes Desmontados': ARQUIVOS['desmontagem']
    }

    # Ler status dos andaimes (linha a linha)
    try:
        with open(ARQUIVOS['status_andaimes'], 'r', encoding='utf-8') as f_status:
            status_linhas = [linha.strip().split(',', 1) for linha in f_status if linha.strip()]
    except Exception:
        status_linhas = []

    for nome, caminho in arquivos.items():
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                linhas = [linha.strip() for linha in f if linha.strip()]

            if nome == 'Clientes':
                colunas = ['Responsável', 'Empresa', 'Contato']
                linhas_split = [linha.split(',') for linha in linhas]

            elif nome == 'Andaimes Montados':
                colunas = ['Cliente', 'Obra', 'Local', 'Data', 'Responsável', 'Materiais', 'Status']

                linhas_split = []
                for i, linha in enumerate(linhas):
                    partes = linha.split(',', 5)  # Agora considera o campo "Responsável"
                    if len(partes) < 6:
                        partes += [''] * (6 - len(partes))
                    status = status_linhas[i][1] if i < len(status_linhas) else 'Status desconhecido'
                    partes.append(status)
                    linhas_split.append(partes)

            elif nome == 'Andaimes Desmontados':
                colunas = ['ID', 'Status']
                linhas_split = [linha.split(',') for linha in linhas]

            else:
                colunas = ['Informações {}'.format(i+1) for i in range(len(linhas[0].split(',')))]
                linhas_split = [linha.split(',') for linha in linhas]

            linhas_validas = [linha for linha in linhas_split if len(linha) == len(colunas)]
            dados[nome] = pd.DataFrame(linhas_validas, columns=colunas)

        except FileNotFoundError:
            dados[nome] = pd.DataFrame()
        except Exception as e:
            flash(f"Erro ao processar o relatório {nome}: {e}")
            dados[nome] = pd.DataFrame()

    # Criar o arquivo Excel em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for aba, df in dados.items():
            df.to_excel(writer, sheet_name=aba, index=False)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='Relatorio_GTA_System.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

