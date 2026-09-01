# Johnny Silverhand — Assistente Virtual por Voz

Projeto acadêmico de assistente virtual por voz, inspirado no Google Assistente e na Alexa. Reconhece comandos de voz em português, responde por síntese de voz, reconhece rostos via webcam e integra com uma IA generativa (Groq) para perguntas abertas.

## Funcionalidades

| # | Comando de voz | O que faz |
|---|---|---|
| 1 | `"Johnny"` / `"Johnny Silverhand"` | Palavra de ativação. Sem ela, nenhum comando é executado — o texto ouvido é só exibido no console. |
| 2 | `"Johnny cadastrar evento na agenda"` | Pergunta o evento, escuta a resposta e grava em `agenda.txt`. |
| 3 | `"Johnny ler agenda"` | Lê em voz alta todos os eventos cadastrados. |
| 4 | `"Johnny que horas são"` | Fala o horário atual. |
| 5 | `"Johnny que dia é hoje"` | Fala a data atual. |
| 6 | `"Johnny calcular ..."` | Resolve contas de adição, subtração, multiplicação e divisão. |
| 7 | `"Johnny reconhecer face"` / `"Johnny quem sou eu"` | Abre a webcam e tenta identificar a pessoa. |
| 8 | `"Johnny limpar agenda"` | Apaga o conteúdo de `agenda.txt` sem excluir o arquivo. |
| 9 | Qualquer pergunta aberta | Cai como *fallback* para a IA generativa (Groq). |
| 10 | `"Johnny qual o clima"` / `"Johnny ligar luz"` / `"Johnny desligar luz"` | Extras: previsão do tempo e controle de um LED via Arduino. |

## Estrutura do projeto

```
assistente-johnny/
├── assistente.py          # classe AssistenteVirtual + loop principal
├── capturar_rosto.py       # captura amostras de rosto para o treinamento
├── treinar_modelo.py       # treina o EigenFaceRecognizer e salva o modelo
├── requirements.txt
├── agenda.txt               # criado automaticamente no primeiro uso
├── classificador_eigen.yml  # gerado por treinar_modelo.py
└── rostos/
    ├── fotos/                # amostras capturadas por pessoa
    └── mapa_nomes.txt         # gerado por treinar_modelo.py
```

## Instalação

1. Clone o repositório e entre na pasta:
   ```bash
   git clone <url-do-seu-repositorio>
   cd assistente-johnny
   ```

2. (Recomendado) crie um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

   > No Windows, se `pip install pyaudio` falhar, instale o pacote pré-compilado com
   > `pip install pipwin && pipwin install pyaudio`, ou baixe o wheel correspondente.

4. Configure sua chave da API da Groq (gratuita em [console.groq.com](https://console.groq.com)):
   ```bash
   export GROQ_API_KEY="sua_chave_aqui"      # Windows: set GROQ_API_KEY=sua_chave_aqui
   ```

## Como treinar o reconhecimento facial (item 7)

1. Capture suas amostras (rode uma vez por pessoa):
   ```bash
   python capturar_rosto.py
   ```
   Digite o nome quando solicitado e pressione `q` repetidas vezes com o rosto enquadrado, até completar 25 fotos.

2. Capture também amostras de rostos aleatórios com o nome `desconhecido`, para o modelo aprender a rejeitar quem não está cadastrado.

3. Treine o modelo:
   ```bash
   python treinar_modelo.py
   ```
   Isso gera `classificador_eigen.yml` e `rostos/mapa_nomes.txt`.

## Como executar

```bash
python assistente.py
```

A assistente vai falar "Johnny Silverhand ativado" e ficar ouvindo o microfone. Diga o nome de ativação seguido do comando, por exemplo: *"Johnny, que horas são"*.

### Controle do Arduino (extra)

Para usar os comandos de luz, informe a porta serial ao instanciar a classe em `assistente.py`:

```python
assistente = AssistenteVirtual(porta_arduino="COM3")  # ou "/dev/ttyUSB0" no Linux
```

O Arduino deve estar programado para ligar/desligar um LED ao receber os bytes `b"a"` (ligar) e `b"b"` (desligar) pela porta serial.

## Dependências principais

- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) + PyAudio — captura e transcrição de voz
- [pyttsx3](https://pypi.org/project/pyttsx3/) — síntese de voz offline
- [opencv-contrib-python](https://pypi.org/project/opencv-contrib-python/) — detecção e reconhecimento facial
- [groq](https://pypi.org/project/groq/) — IA generativa
- [requests](https://pypi.org/project/requests/) — consulta de previsão do tempo (wttr.in)
- [pyserial](https://pypi.org/project/pyserial/) — comunicação com Arduino

## Autor

Cadu — projeto acadêmico.
