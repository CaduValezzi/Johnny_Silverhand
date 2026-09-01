"""
Assistente Virtual "Johnny Silverhand"
=======================================
Projeto acadêmico de assistente virtual por voz, inspirado no
Google Assistente / Alexa.

Funcionalidades implementadas:
 1. Ativação por palavra-chave ("Johnny Silverhand" ou apenas "Johnny")
 2. Cadastro de evento na agenda (agenda.txt)
 3. Leitura da agenda
 4. Consulta do horário atual
 5. Consulta da data atual
 6. Calculadora por voz (adição, subtração, multiplicação, divisão)
 7. Reconhecimento facial (OpenCV EigenFaceRecognizer)
 8. Limpeza da agenda (sem apagar o arquivo)
 9. Integração com IA generativa (Groq) como fallback para perguntas abertas
 10. Extras (desafio do grupo):
       - Previsão do tempo por voz
       - Controle de um dispositivo (LED) via Arduino

Qualquer comando só é aceito depois que a palavra de ativação é reconhecida
na mesma fala. Caso contrário, o texto reconhecido é apenas exibido no
console, sem nenhuma ação.
"""

import os
import re
import time
from datetime import datetime

import cv2
import pyttsx3
import requests
import speech_recognition as sr
from groq import Groq

try:
    import serial  # pyserial - só é necessário se for usar o Arduino
except ImportError:
    serial = None


class AssistenteVirtual:
    """Encapsula toda a lógica do assistente: ouvir, decidir, agir e falar."""

    # Palavras que ativam a assistente (aceita o nome completo ou o apelido)
    PALAVRAS_ATIVACAO = ["johnny silverhand", "johnny"]
    GATILHOS_CADASTRAR_EVENTO = ["cadastrar evento", "cadastra um evento", "cadastra evento", "novo evento", "criar evento"]
    GATILHOS_LER_AGENDA = ["ler agenda", "leia a agenda", "ler minha agenda", "mostrar agenda", "quais são meus eventos"]
    GATILHOS_LIMPAR_AGENDA = ["limpar agenda", "apagar a agenda", "apagar agenda", "limpar minha agenda", "zerar agenda"]
    GATILHOS_HORA = ["que horas são", "que horas é", "me diz as horas", "qual é a hora", "que horas"]
    GATILHOS_DATA = ["que dia é hoje", "que dia é", "qual o dia de hoje", "qual a data de hoje", "que dia"]
    GATILHOS_CALCULAR = ["calcular"]
    GATILHOS_RECONHECER_FACE = ["reconhecer face", "quem sou eu", "reconheça minha face", "reconhece minha face"]
    GATILHOS_CLIMA = ["clima", "previsão do tempo", "previsao do tempo", "qual o clima", "vai chover"]
    GATILHOS_LIGAR_LUZ = ["ligar luz", "acender luz", "acende a luz"]
    GATILHOS_DESLIGAR_LUZ = ["desligar luz", "apagar luz", "apaga a luz"]
    # Operadores aceitos na calculadora por voz (chave -> função)
    OPERADORES = {
        "multiplicado por": lambda a, b: a * b,
        "dividido por": lambda a, b: a / b,
        "mais": lambda a, b: a + b,
        "menos": lambda a, b: a - b,
        "vezes": lambda a, b: a * b,
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "x": lambda a, b: a * b,
        "/": lambda a, b: a / b,
    }

    def __init__(self, arquivo_agenda="agenda.txt", modelo_facial="classificador_eigen.yml",
                 groq_api_key=None, porta_arduino=None, cidade_padrao="Santo André"):
        # --- Reconhecimento e síntese de voz ---
        self.reconhecedor = sr.Recognizer()
        self.reconhecedor.pause_threshold = 1.2
        self.reconhecedor.non_speaking_duration = 1

        self.motor_voz = pyttsx3.init()
        self.motor_voz.setProperty("rate", 180)
        self.motor_voz.setProperty("volume", 1.0)

        # --- Agenda ---
        self.arquivo_agenda = arquivo_agenda

        # --- IA generativa (Groq) ---
        self.groq_client = Groq(api_key=groq_api_key or os.environ.get("GROQ_API_KEY"))

        # --- Reconhecimento facial ---
        self.classificador_face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.modelo_facial = modelo_facial
        self.reconhecedor_facial = cv2.face.EigenFaceRecognizer_create()
        self.mapa_nomes = self._carregar_mapa_nomes()
        self.modelo_carregado = self._carregar_modelo_facial()

        # --- Extras: clima e Arduino ---
        self.cidade_padrao = cidade_padrao
        self.arduino = self._conectar_arduino(porta_arduino)

    # ------------------------------------------------------------------
    # Métodos utilitários de voz
    # ------------------------------------------------------------------
    def falar(self, texto):
        """Converte texto em fala e também imprime no console (debug/apresentação)."""
        print(f"[Johnny]: {texto}")
        self.motor_voz.say(texto)
        self.motor_voz.runAndWait()

    def ouvir(self, timeout=5, phrase_time_limit=8):
        """Captura áudio do microfone e devolve o texto reconhecido em minúsculas (ou None)."""
        with sr.Microphone() as microfone:
            self.reconhecedor.adjust_for_ambient_noise(microfone, duration=1)
            try:
                audio = self.reconhecedor.listen(microfone, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return None

        try:
            texto = self.reconhecedor.recognize_google(audio, language="pt-BR")
            return texto.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as erro:
            print(f"Erro ao acessar o serviço de reconhecimento de voz: {erro}")
            return None

    # ------------------------------------------------------------------
    # Ativação e roteamento de comandos (item 1)
    # ------------------------------------------------------------------
    def contem_ativacao(self, texto):
        """Verifica se alguma palavra de ativação está presente no texto reconhecido."""
        return any(palavra in texto for palavra in self.PALAVRAS_ATIVACAO)

    def extrair_comando(self, texto):
        """Remove a palavra de ativação do texto, sobrando só o comando em si."""
        comando = texto
        for palavra in sorted(self.PALAVRAS_ATIVACAO, key=len, reverse=True):
            comando = comando.replace(palavra, "")
        return comando.strip()

    def processar_comando(self, comando):
        """Roteia (dispatch) o comando reconhecido para o método correspondente."""
        if not comando:
            self.falar("Sim, como posso ajudar?")
            return

        if any(gatilho in comando for gatilho in self.GATILHOS_CADASTRAR_EVENTO):
            self.cadastrar_evento()
        elif any(gatilho in comando for gatilho in self.GATILHOS_LER_AGENDA):
            self.ler_agenda()
        elif any(gatilho in comando for gatilho in self.GATILHOS_LIMPAR_AGENDA):
            self.limpar_agenda()
        elif any(gatilho in comando for gatilho in self.GATILHOS_HORA):
            self.falar_hora()
        elif any(gatilho in comando for gatilho in self.GATILHOS_DATA):
            self.falar_data()
        elif any(gatilho in comando for gatilho in self.GATILHOS_CALCULAR):
            self.calcular(comando)
        elif any(gatilho in comando for gatilho in self.GATILHOS_RECONHECER_FACE):
            self.reconhecer_face()
        elif any(gatilho in comando for gatilho in self.GATILHOS_CLIMA):
            self.falar_previsao_tempo(comando)
        else:
            # Nenhum comando fixo bateu -> cai para a IA generativa (item 9)
            self.perguntar_ia(comando)

    # ------------------------------------------------------------------
    # Itens 2 e 3: agenda
    # ------------------------------------------------------------------
    def cadastrar_evento(self):
        """Pergunta o evento, escuta a resposta e grava em agenda.txt."""
        self.falar("Ok, qual evento devo cadastrar?")
        evento = self.ouvir(timeout=8, phrase_time_limit=15)

        if not evento:
            self.falar("Não consegui te ouvir, tente novamente.")
            return

        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(self.arquivo_agenda, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{data_hora}] {evento}\n")

        self.falar("Evento cadastrado com sucesso.")

    def ler_agenda(self):
        """Lê e fala todos os eventos gravados em agenda.txt."""
        if not os.path.exists(self.arquivo_agenda) or os.path.getsize(self.arquivo_agenda) == 0:
            self.falar("Sua agenda está vazia.")
            return

        with open(self.arquivo_agenda, "r", encoding="utf-8") as arquivo:
            eventos = [linha.strip() for linha in arquivo if linha.strip()]

        self.falar(f"Você tem {len(eventos)} evento{'s' if len(eventos) != 1 else ''} cadastrado{'s' if len(eventos) != 1 else ''}.")
        for evento in eventos:
            self.falar(evento)

    def limpar_agenda(self):
        """Apaga o conteúdo de agenda.txt sem excluir o arquivo em si."""
        if not os.path.exists(self.arquivo_agenda) or os.path.getsize(self.arquivo_agenda) == 0:
            self.falar("Sua agenda já está vazia.")
            return

        with open(self.arquivo_agenda, "w", encoding="utf-8"):
            pass  # abrir em modo "w" já trunca o arquivo, sem precisar escrever nada

        self.falar("Agenda limpa com sucesso.")
    # ------------------------------------------------------------------
    # Item 4 e 5: hora e data
    # ------------------------------------------------------------------
    def falar_hora(self):
        agora = datetime.now().strftime("%H:%M")
        self.falar(f"Agora são {agora}.")

    def falar_data(self):
        hoje = datetime.now().strftime("%d de %B de %Y")
        self.falar(f"Hoje é {hoje}.")

    # ------------------------------------------------------------------
    # Item 6: calculadora por voz
    # ------------------------------------------------------------------
    def calcular(self, comando):
        """Extrai dois números e um operador do comando falado e resolve a conta."""
        numeros = re.findall(r"-?\d+(?:[.,]\d+)?", comando)
        numeros = [float(numero.replace(",", ".")) for numero in numeros]

        operador_encontrado = None
        for operador in sorted(self.OPERADORES, key=len, reverse=True):
            if operador in comando:
                operador_encontrado = operador
                break

        if len(numeros) < 2 or operador_encontrado is None:
            self.falar("Não consegui entender a conta. Tente algo como: calcular dois mais dois.")
            return

        try:
            resultado = self.OPERADORES[operador_encontrado](numeros[0], numeros[1])
            self.falar(f"O resultado é {resultado}.")
        except ZeroDivisionError:
            self.falar("Não é possível dividir por zero.")

    # ------------------------------------------------------------------
    # Item 7: reconhecimento facial
    # ------------------------------------------------------------------
    def _carregar_mapa_nomes(self):
        """Carrega o mapa rótulo numérico -> nome, gerado por treinar_modelo.py."""
        mapa = {0: "desconhecido"}
        caminho = os.path.join("rostos", "mapa_nomes.txt")
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as arquivo:
                for linha in arquivo:
                    rotulo, nome = linha.strip().split(",", 1)
                    mapa[int(rotulo)] = nome
        return mapa

    def _carregar_modelo_facial(self):
        """Carrega o modelo .yml pré-treinado, se ele existir."""
        if os.path.exists(self.modelo_facial):
            self.reconhecedor_facial.read(self.modelo_facial)
            return True
        print("Aviso: modelo facial não encontrado. Rode capturar_rosto.py e treinar_modelo.py antes de usar 'reconhecer face'.")
        return False

    def reconhecer_face(self):
        """Abre a webcam e tenta identificar a pessoa em frente à câmera."""
        if not self.modelo_carregado:
            self.falar("Ainda não tenho um modelo treinado para reconhecer rostos.")
            return

        self.falar("Deixa eu dar uma olhada...")
        camera = cv2.VideoCapture(0)
        nome_reconhecido = None
        tentativas = 0
        limite_tentativas = 60  # evita loop infinito se ninguém aparecer na câmera

        while tentativas < limite_tentativas:
            ok, frame = camera.read()
            if not ok:
                break

            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.classificador_face.detectMultiScale(cinza, scaleFactor=1.2, minSize=(150, 150))

            for (x, y, largura, altura) in faces:
                rosto = cv2.resize(cinza[y:y + altura, x:x + largura], (220, 220))
                rotulo, confianca = self.reconhecedor_facial.predict(rosto)
                # confiança alta = pouco parecido -> trata como desconhecido
                nome_reconhecido = self.mapa_nomes.get(rotulo, "desconhecido") if confianca <= 4000 else "desconhecido"
                cv2.rectangle(frame, (x, y), (x + largura, y + altura), (0, 0, 255), 2)
                break

            cv2.imshow("Reconhecimento facial - pressione Q para sair", frame)
            if nome_reconhecido or (cv2.waitKey(1) & 0xFF == ord("q")):
                break
            tentativas += 1

        camera.release()
        cv2.destroyAllWindows()

        if nome_reconhecido and nome_reconhecido != "desconhecido":
            self.falar(f"Você é {nome_reconhecido}!")
        else:
            self.falar("Não consegui reconhecer você.")

    # ------------------------------------------------------------------
    # Item 9: IA generativa (Groq) - fallback para perguntas abertas
    # ------------------------------------------------------------------
    def perguntar_ia(self, comando):
        self.falar("Deixa eu pensar...")
        try:
            resposta = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é o Johnny Silverhand, uma assistente virtual objetiva. "
                            "Responda sempre em português, em no máximo 40 palavras."
                        ),
                    },
                    {"role": "user", "content": comando},
                ],
            )
            self.falar(resposta.choices[0].message.content)
        except Exception as erro:
            print(f"Erro ao consultar a IA generativa: {erro}")
            self.falar("Não consegui pensar em uma resposta agora.")

    # ------------------------------------------------------------------
    # Item 10 (extra 1): previsão do tempo
    # ------------------------------------------------------------------
    def falar_previsao_tempo(self, comando):
        """Consulta o clima atual (wttr.in, sem necessidade de API key)."""
        match = re.search(r"em (.+)", comando)
        cidade = match.group(1).strip() if match else self.cidade_padrao

        try:
            resposta = requests.get(f"https://wttr.in/{cidade}?format=j1", timeout=6)
            dados = resposta.json()
            condicao_atual = dados["current_condition"][0]
            temperatura = condicao_atual["temp_C"]
            descricao = (
                condicao_atual["lang_pt"][0]["value"]
                if "lang_pt" in condicao_atual
                else condicao_atual["weatherDesc"][0]["value"]
            )
            self.falar(f"Em {cidade} agora está {temperatura} graus, com {descricao}.")
        except Exception as erro:
            print(f"Erro ao consultar previsão do tempo: {erro}")
            self.falar("Não consegui consultar a previsão do tempo agora.")

    # ------------------------------------------------------------------
    # Item 10 (extra 2): controle de dispositivo via Arduino
    # ------------------------------------------------------------------
    def _conectar_arduino(self, porta):
        """Tenta conectar ao Arduino; falha graciosamente se não houver hardware."""
        if not porta or serial is None:
            return None
        try:
            conexao = serial.Serial(porta, 9600, timeout=1)
            time.sleep(2)  # aguarda o Arduino reiniciar após abrir a porta
            return conexao
        except Exception as erro:
            print(f"Aviso: não foi possível conectar ao Arduino ({erro}). Comando de luz ficará indisponível.")
            return None

    def controlar_luz(self, comando):
        if not self.arduino:
            self.falar("Não encontrei nenhum Arduino conectado.")
            return
        if "ligar" in comando:
            self.arduino.write(b"a")
            self.falar("Luz ligada.")
        elif "desligar" in comando:
            self.arduino.write(b"b")
            self.falar("Luz desligada.")

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def executar(self):
        """Loop de escuta contínua: só age quando ouve a palavra de ativação."""
        self.falar("Johnny Silverhand ativado. Estou ouvindo.")
        while True:
            texto = self.ouvir()
            if not texto:
                continue

            # Requisito 1: qualquer fala reconhecida é impressa na tela
            print(f"[Reconhecido]: {texto}")

            if self.contem_ativacao(texto):
                comando = self.extrair_comando(texto)
                self.processar_comando(comando)
            # sem a palavra de ativação, nenhuma ação é executada


if __name__ == "__main__":
    def carregar_chave_groq(caminho="api_AI.txt"):
        """Lê a chave da API da Groq de um arquivo de texto simples (1 linha, só a chave)."""
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                return arquivo.read().strip()
        except FileNotFoundError:
            print(f"Aviso: arquivo '{caminho}' não encontrado. Crie esse arquivo com sua chave da Groq dentro.")
            return None
    assistente = AssistenteVirtual(
        groq_api_key=carregar_chave_groq(),
        porta_arduino=None,
        cidade_padrao="Santo André",
    )
    assistente.executar()
